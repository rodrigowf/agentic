"""
backend/api/realtime_voice_webrtc.py

WebRTC bridge API for multi-frontend voice sessions.

Architecture (N:1 per conversation):
- Multiple browser tabs can connect to the same conversation
- Each conversation has ONE OpenAI Realtime session (managed by RealtimeSessionManager)
- Each conversation has ONE BrowserConnectionManager (handles N browser connections)
- Audio from any browser → OpenAI session
- Audio from OpenAI → broadcast to ALL connected browsers
- Frontend disconnects don't kill the OpenAI session (until explicitly closed)
- Voice configuration is loaded from the backend's selected config file (not from frontend)
"""

import asyncio
import json
import logging
import os
from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .realtime_session_manager import get_session_manager, OpenAISession
from .browser_connection_manager import (
    get_or_create_manager,
    get_manager,
    remove_manager,
    BrowserConnectionManager,
)
from .audio_chat_handler import AudioChatHandler

try:
    from ..config.schemas import AudioMessageRequest, AudioMessageResponse, TextMessageRequest
except ImportError:
    from config.schemas import AudioMessageRequest, AudioMessageResponse, TextMessageRequest

try:
    from .realtime_voice import prepare_voice_system_prompt, VOICE_SYSTEM_PROMPT, stream_manager, ConversationEvent
except Exception:
    VOICE_SYSTEM_PROMPT = "You are a realtime voice assistant."
    def prepare_voice_system_prompt(base_prompt, agent_name, conversation_id=None, memory_file_path=None):
        return base_prompt
    stream_manager = None
    ConversationEvent = None

try:
    from ..utils.voice_conversation_store import store as conversation_store
except ImportError:
    from utils.voice_conversation_store import store as conversation_store

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# Voice Configuration Loading
# ============================================================================

VOICE_CONFIGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "voice", "configs")
VOICE_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "voice", "prompts")
VOICE_SELECTED_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "voice", "selected_config.json")

def _load_voice_prompt_file(filename: str) -> str:
    """Load a voice prompt from the prompts directory.

    Falls back to VOICE_SYSTEM_PROMPT constant if file doesn't exist.
    """
    try:
        prompt_path = os.path.join(VOICE_PROMPTS_DIR, filename)
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"[VoiceConfig] Loaded prompt from '{filename}' ({len(content)} chars)")
                return content
        else:
            logger.warning(f"[VoiceConfig] Prompt file '{filename}' not found, using VOICE_SYSTEM_PROMPT fallback")
    except Exception as e:
        logger.error(f"[VoiceConfig] Error loading prompt file '{filename}': {e}, using VOICE_SYSTEM_PROMPT fallback")
    return VOICE_SYSTEM_PROMPT


def _load_selected_voice_config() -> dict:
    """
    Load the currently selected voice configuration from the backend.
    Returns the full config dict with keys: voice, agent_name, memory_file_path, etc.
    """
    try:
        # First, get the selected config name
        selected_name = "default"
        if os.path.exists(VOICE_SELECTED_CONFIG_PATH):
            with open(VOICE_SELECTED_CONFIG_PATH) as f:
                data = json.load(f)
                selected_name = data.get("selected", "default")

        # Load the config file
        config_path = os.path.join(VOICE_CONFIGS_DIR, f"{selected_name}.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
                logger.info(f"[VoiceConfig] Loaded config '{selected_name}': voice={config.get('voice')}, agent={config.get('agent_name')}")
                return config

        # Fall back to default if selected doesn't exist
        default_path = os.path.join(VOICE_CONFIGS_DIR, "default.json")
        if os.path.exists(default_path):
            with open(default_path) as f:
                config = json.load(f)
                logger.warning(f"[VoiceConfig] Selected config '{selected_name}' not found, using default")
                return config

    except Exception as e:
        logger.error(f"[VoiceConfig] Error loading config: {e}")

    # Ultimate fallback
    logger.warning("[VoiceConfig] No config found, using hardcoded defaults")
    return {
        "voice": "cedar",
        "agent_name": "MainConversation",
        "memory_file_path": "backend/data/memory/short_term_memory.txt",
        "voice_model": "gpt-realtime",
    }


# ============================================================================
# Request/Response Models
# ============================================================================

class SignalRequest(BaseModel):
    """Browser signaling request (connect).

    Note: Voice configuration (voice, agent_name, memory_file_path) is loaded
    from the backend's selected config file, not passed from frontend.
    """
    conversation_id: str
    offer: str  # SDP offer from browser


class SignalResponse(BaseModel):
    """Browser signaling response."""
    connection_id: str
    answer: str  # SDP answer for browser


class DisconnectRequest(BaseModel):
    """Browser disconnect request."""
    connection_id: str


class TextRequest(BaseModel):
    """Text message request."""
    text: str


# ============================================================================
# Active Session Tracking
# ============================================================================

# Maps conversation_id to (OpenAISession, BrowserConnectionManager) pair
# This keeps them linked together
_active_conversations: Dict[str, tuple] = {}
_lock = asyncio.Lock()


async def _get_or_setup_conversation(
    conversation_id: str,
) -> tuple[OpenAISession, BrowserConnectionManager]:
    """
    Get or set up a conversation with both OpenAI session and browser manager.

    Voice configuration is loaded from the backend's selected config file.

    This links the two managers together so audio flows correctly:
    Browser audio → OpenAI session
    OpenAI audio → broadcast to all browsers
    """
    async with _lock:
        if conversation_id in _active_conversations:
            openai_session, browser_mgr = _active_conversations[conversation_id]
            if openai_session.is_connected:
                return openai_session, browser_mgr
            # Session died, clean up
            del _active_conversations[conversation_id]

    # Verify conversation exists
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Load voice configuration from backend's selected config file
    voice_config = _load_selected_voice_config()

    voice = voice_config.get("voice", "cedar")
    agent_name = voice_config.get("agent_name", "MainConversation")
    memory_file_path = voice_config.get("memory_file_path", "backend/data/memory/short_term_memory.txt")
    voice_model = voice_config.get("voice_model", "gpt-realtime")
    system_prompt_file = voice_config.get("system_prompt_file", "default.txt")

    logger.info(f"[Setup] Creating session for {conversation_id} with config: voice={voice}, agent={agent_name}, prompt_file={system_prompt_file}")

    # Load the base prompt from file and prepare it with injections
    base_prompt = _load_voice_prompt_file(system_prompt_file)
    system_prompt = prepare_voice_system_prompt(
        base_prompt=base_prompt,
        agent_name=agent_name,
        conversation_id=conversation_id,
        memory_file_path=memory_file_path,
    )

    # Create browser manager first (we need to pass audio callback to OpenAI session)
    browser_mgr = await get_or_create_manager(conversation_id)

    # Create OpenAI session with audio callback that broadcasts to browsers
    session_mgr = get_session_manager()
    openai_session = await session_mgr.get_or_create_session(
        conversation_id=conversation_id,
        voice=voice,
        agent_name=agent_name,
        system_prompt=system_prompt,
        model=voice_model,
        on_audio_callback=browser_mgr.broadcast_audio,  # OpenAI audio → all browsers
        memory_file_path=memory_file_path,  # Memory file for context injection
    )

    # Set up browser audio callback → OpenAI
    browser_mgr.on_browser_audio = openai_session.send_audio  # Browser audio → OpenAI

    async with _lock:
        _active_conversations[conversation_id] = (openai_session, browser_mgr)

    return openai_session, browser_mgr


async def _cleanup_conversation(conversation_id: str) -> None:
    """Clean up a conversation's sessions and managers."""
    async with _lock:
        _active_conversations.pop(conversation_id, None)

    # Close OpenAI session
    session_mgr = get_session_manager()
    await session_mgr.close_session(conversation_id)

    # Close browser connections
    await remove_manager(conversation_id)


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/api/realtime/webrtc/signal", response_model=SignalResponse)
async def signal_connect(request: SignalRequest):
    """
    Connect a browser to a conversation via WebRTC signaling.

    This endpoint:
    1. Creates/reuses OpenAI session for the conversation
    2. Adds a new browser connection
    3. Returns SDP answer for the browser

    Multiple browsers can connect to the same conversation.
    """
    logger.info(f"[Signal] Browser connecting to conversation {request.conversation_id}")

    try:
        # Get or create the conversation setup (config loaded from backend)
        openai_session, browser_mgr = await _get_or_setup_conversation(
            conversation_id=request.conversation_id,
        )

        # Add browser connection
        connection_id, answer_sdp = await browser_mgr.add_connection(request.offer)

        logger.info(f"[Signal] ✅ Browser {connection_id[:8]} connected to {request.conversation_id}")
        logger.info(f"[Signal]    Total browsers: {browser_mgr.connection_count}")

        return SignalResponse(connection_id=connection_id, answer=answer_sdp)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[Signal] Failed to connect browser: {exc}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {exc}")


@router.post("/api/realtime/webrtc/disconnect")
async def signal_disconnect(request: DisconnectRequest):
    """
    Disconnect a single browser from a conversation.

    This only closes the specific browser connection.
    Other browsers and the OpenAI session remain active.
    OpenAI session stays alive even when all browsers disconnect.
    Use DELETE /conversation/{id} (Force Stop) to close everything.
    """
    connection_id = request.connection_id
    logger.info(f"[Signal] Browser {connection_id[:8]} disconnecting")

    connection_found = False
    conv_id_found = None

    # Find which conversation this connection belongs to
    async with _lock:
        for conv_id, (openai_session, browser_mgr) in _active_conversations.items():
            if connection_id in browser_mgr.connection_ids:
                removed = await browser_mgr.remove_connection(connection_id)
                if removed:
                    connection_found = True
                    conv_id_found = conv_id
                    remaining = browser_mgr.connection_count
                    logger.info(f"[Signal] ✅ Browser {connection_id[:8]} disconnected from {conv_id}")
                    logger.info(f"[Signal]    Remaining browsers: {remaining}")
                    # OpenAI session stays alive - only Force Stop closes it
                break

    if connection_found:
        return JSONResponse({
            "status": "disconnected",
            "connection_id": connection_id,
            "conversation_id": conv_id_found,
        })

    raise HTTPException(status_code=404, detail="Connection not found")


@router.delete("/api/realtime/webrtc/conversation/{conversation_id}")
async def stop_conversation(conversation_id: str):
    """
    Stop an entire conversation session.

    This closes:
    - All browser connections
    - The OpenAI session
    - Cleans up all resources

    Returns success even if the conversation was not active (idempotent).
    """
    logger.info(f"[Signal] Stopping conversation {conversation_id}")

    async with _lock:
        was_active = conversation_id in _active_conversations

    if was_active:
        await _cleanup_conversation(conversation_id)
        logger.info(f"[Signal] ✅ Conversation {conversation_id} stopped")
    else:
        logger.info(f"[Signal] Conversation {conversation_id} was not active (already stopped or never started)")

    return JSONResponse({"status": "stopped", "conversation_id": conversation_id, "was_active": was_active})


@router.get("/api/realtime/webrtc/conversation/{conversation_id}/status")
async def get_conversation_status(conversation_id: str):
    """Get status of an active conversation."""
    async with _lock:
        if conversation_id not in _active_conversations:
            return JSONResponse({
                "conversation_id": conversation_id,
                "active": False,
            })

        openai_session, browser_mgr = _active_conversations[conversation_id]
        return JSONResponse({
            "conversation_id": conversation_id,
            "active": True,
            "openai_connected": openai_session.is_connected,
            "browser_count": browser_mgr.connection_count,
            "browser_connections": list(browser_mgr.connection_ids),
        })


@router.post("/api/realtime/webrtc/conversation/{conversation_id}/text")
async def send_text(conversation_id: str, request: TextRequest):
    """Send a text message to the OpenAI session."""
    async with _lock:
        if conversation_id not in _active_conversations:
            raise HTTPException(status_code=404, detail="Conversation not active")
        openai_session, _ = _active_conversations[conversation_id]

    try:
        await openai_session.send_text(request.text)
        return JSONResponse({"status": "sent"})
    except Exception as exc:
        logger.error(f"Failed to send text: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to send text: {exc}")


@router.post("/api/realtime/webrtc/conversation/{conversation_id}/commit")
async def commit_audio(conversation_id: str):
    """
    Manually commit audio buffer (for manual VAD mode).
    Signals that the user is done speaking.
    """
    async with _lock:
        if conversation_id not in _active_conversations:
            raise HTTPException(status_code=404, detail="Conversation not active")
        openai_session, _ = _active_conversations[conversation_id]

    try:
        await openai_session.commit_audio_buffer()
        return JSONResponse({"status": "committed"})
    except Exception as exc:
        logger.error(f"Failed to commit audio: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to commit audio: {exc}")


@router.post("/api/realtime/webrtc/conversation/{conversation_id}/send-to-nested")
async def send_to_nested(conversation_id: str, request: TextRequest):
    """Manually send a message to nested agents."""
    async with _lock:
        if conversation_id not in _active_conversations:
            raise HTTPException(status_code=404, detail="Conversation not active")
        openai_session, _ = _active_conversations[conversation_id]

    result = await openai_session._tool_send_to_nested(request.text)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))
    return JSONResponse(result)


@router.post("/api/realtime/webrtc/conversation/{conversation_id}/send-to-claude-code")
async def send_to_claude_code(conversation_id: str, request: TextRequest):
    """Manually send a message to Claude Code."""
    async with _lock:
        if conversation_id not in _active_conversations:
            raise HTTPException(status_code=404, detail="Conversation not active")
        openai_session, _ = _active_conversations[conversation_id]

    result = await openai_session._tool_send_to_claude_code(request.text)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))
    return JSONResponse(result)


# ============================================================================
# Legacy Endpoint Compatibility (maps old endpoints to new)
# ============================================================================

class BridgeOffer(BaseModel):
    """Legacy bridge offer (for backwards compatibility).

    Note: Voice configuration is now loaded from backend, extra params are ignored.
    """
    conversation_id: str
    offer: str


class BridgeAnswer(BaseModel):
    """Legacy bridge answer."""
    session_id: str
    answer: str


@router.post("/api/realtime/webrtc/bridge", response_model=BridgeAnswer)
async def handle_bridge_legacy(offer: BridgeOffer):
    """
    Legacy endpoint for backwards compatibility.
    Maps to the new /signal endpoint.
    """
    logger.info(f"[Legacy] Bridge request for {offer.conversation_id}")

    result = await signal_connect(SignalRequest(
        conversation_id=offer.conversation_id,
        offer=offer.offer,
    ))

    # Return in legacy format
    return BridgeAnswer(session_id=result.connection_id, answer=result.answer)


@router.delete("/api/realtime/webrtc/bridge/{conversation_id}")
async def stop_bridge_legacy(conversation_id: str):
    """
    Legacy endpoint - stops entire conversation.
    Maps to the new /conversation/{id} DELETE endpoint.
    """
    return await stop_conversation(conversation_id)


class BridgeText(BaseModel):
    text: str


@router.post("/api/realtime/webrtc/bridge/{conversation_id}/text")
async def send_text_legacy(conversation_id: str, payload: BridgeText):
    """Legacy text endpoint."""
    return await send_text(conversation_id, TextRequest(text=payload.text))


@router.post("/api/realtime/webrtc/bridge/{conversation_id}/commit")
async def commit_audio_legacy(conversation_id: str):
    """Legacy commit endpoint."""
    return await commit_audio(conversation_id)


@router.post("/api/realtime/webrtc/bridge/{conversation_id}/send-to-nested")
async def send_to_nested_legacy(conversation_id: str, payload: BridgeText):
    """Legacy send-to-nested endpoint."""
    return await send_to_nested(conversation_id, TextRequest(text=payload.text))


@router.post("/api/realtime/webrtc/bridge/{conversation_id}/send-to-claude-code")
async def send_to_claude_code_legacy(conversation_id: str, payload: BridgeText):
    """Legacy send-to-claude-code endpoint."""
    return await send_to_claude_code(conversation_id, TextRequest(text=payload.text))


@router.get("/api/realtime/webrtc/bridge/{conversation_id}/status")
async def get_bridge_status_legacy(conversation_id: str):
    """Legacy status endpoint - maps to new conversation status."""
    return await get_conversation_status(conversation_id)


# ============================================================================
# Disconnected Voice Mode (non-WebRTC audio chat)
# ============================================================================

async def _store_and_broadcast_event(
    conversation_id: str,
    payload: dict,
    source: str,
    event_type: str
) -> dict:
    """
    Store an event and broadcast it to all connected WebSocket subscribers.
    This ensures disconnected mode events appear in the frontend conversation history.
    """
    record = conversation_store.append_event(
        conversation_id=conversation_id,
        payload=payload,
        source=source,
        event_type=event_type
    )

    # Broadcast to connected subscribers if stream_manager is available
    if stream_manager and ConversationEvent:
        try:
            event_obj = ConversationEvent(**record)
            await stream_manager.broadcast(
                conversation_id,
                {
                    "type": "event",
                    "event": event_obj.model_dump(mode="json"),
                },
            )
        except Exception as e:
            logger.warning(f"[DisconnectedMode] Failed to broadcast event: {e}")

    return record


async def _handle_agent_event(
    conversation_id: str,
    event: dict,
    source_type: str  # "nested_agent" or "claude_code"
) -> None:
    """
    Handle and broadcast an event from an agent WebSocket.
    Mirrors the logic from realtime_session_manager._handle_nested_message.
    """
    event_type = event.get("type", "").lower()
    event_data = event.get("data", {})

    # Extract agent/source info
    agent = event_data.get("source") or event_data.get("agent") or (
        "Agent" if source_type == "nested_agent" else "ClaudeCode"
    )

    # Build a message summary (for logging)
    message = None
    prefix = "[TEAM" if source_type == "nested_agent" else "[CODE"

    if event_type == "textmessage":
        content = event_data.get("content", "")
        message = f"{prefix} {agent}] {content}"
    elif event_type == "toolcallrequestevent":
        tool_name = event_data.get("name", "Tool")
        message = f"{prefix} {agent}] Requesting tool: {tool_name}"
    elif event_type == "toolcallexecutionevent":
        tool_name = event_data.get("name") or "Tool"
        content_items = event_data.get("content", [])
        if isinstance(content_items, list) and content_items:
            tool_name = content_items[0].get("name", tool_name)
        result_text = str(event_data.get("result", ""))[:200]
        message = f"{prefix} {tool_name}] {result_text}" if result_text else f"{prefix} {tool_name}] completed"
    elif event_type == "taskresult":
        outcome = event_data.get("outcome", "completed")
        summary = event_data.get("message", "")
        message = f"{prefix}] Task {outcome}: {summary}"
    elif event_type == "system":
        sys_message = event_data.get("message", "")
        message = f"{prefix} System] {sys_message}"
    else:
        message = f"{prefix} {agent}] {event_type}"

    if message:
        logger.info(f"[DisconnectedAgent] {message[:100]}...")

    # Broadcast the event to the frontend
    await _store_and_broadcast_event(
        conversation_id=conversation_id,
        payload={
            "type": "nested_event" if source_type == "nested_agent" else "claude_code_event",
            "event_type": event_type,
            "message": message,
            "source": agent,
            "agent": agent,
            "data": event_data,
        },
        source=source_type,
        event_type=event_type
    )


async def _listen_agent_websocket(
    conversation_id: str,
    ws,
    source_type: str,
    timeout: float = 120.0
) -> None:
    """
    Listen for events from an agent WebSocket and broadcast them.
    Runs until the agent completes or timeout is reached.
    """
    import aiohttp

    try:
        end_time = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < end_time:
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        event = json.loads(msg.data)
                        await _handle_agent_event(conversation_id, event, source_type)

                        # Check if this is a task completion event
                        event_type = event.get("type", "").lower()
                        if event_type in ("taskresult", "error", "complete"):
                            logger.info(f"[DisconnectedAgent] Task completed: {event_type}")
                            break
                    except json.JSONDecodeError:
                        logger.warning(f"[DisconnectedAgent] Invalid JSON: {msg.data[:100]}")
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info(f"[DisconnectedAgent] WebSocket closed")
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"[DisconnectedAgent] WebSocket error")
                    break
            except asyncio.TimeoutError:
                # No message received, continue listening
                continue
    except asyncio.CancelledError:
        logger.info(f"[DisconnectedAgent] Listener cancelled")
    except Exception as exc:
        logger.error(f"[DisconnectedAgent] Error listening: {exc}")


async def _execute_disconnected_tool_calls(
    conversation_id: str,
    tool_calls: list,
) -> list:
    """
    Execute tool calls from disconnected voice mode.

    In disconnected mode, we:
    1. Connect to the agent WebSocket
    2. Send the user message
    3. Start a background task to listen for and broadcast events
    4. Return immediately (events stream in background)

    Returns list of tool results.
    """
    import aiohttp

    results = []

    for tc in tool_calls:
        tool_name = tc.get("name", "")
        arguments = tc.get("arguments", "{}")

        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
        except json.JSONDecodeError:
            args = {}

        logger.info(f"[DisconnectedTool] Executing {tool_name} with args: {args}")

        result = {"tool": tool_name, "success": False, "error": None}

        if tool_name == "send_to_nested":
            text = args.get("text", "")
            if text:
                # First try existing session
                session_manager = get_session_manager()
                session = await session_manager.get_session(conversation_id)

                if session and session.nested_ws and not session.nested_ws.closed:
                    try:
                        await session.nested_ws.send_json({
                            "type": "user_message",
                            "data": text
                        })
                        result["success"] = True
                        logger.info(f"[DisconnectedTool] Sent to nested via existing session: {text[:100]}...")
                    except Exception as e:
                        result["error"] = f"Failed to send to nested: {e}"
                        logger.error(f"[DisconnectedTool] {result['error']}")
                else:
                    # Connect and start background listener
                    try:
                        voice_config = _load_selected_voice_config()
                        agent_name = voice_config.get("agent_name", "MainConversation")
                        ws_url = f"ws://localhost:8000/api/runs/{agent_name}"

                        # Create a persistent session for the background task
                        http_session = aiohttp.ClientSession()
                        ws = await http_session.ws_connect(ws_url)

                        # Send the user message
                        await ws.send_json({"type": "user_message", "data": text})
                        logger.info(f"[DisconnectedTool] Sent to nested agent {agent_name}: {text[:100]}...")

                        # Start background task to listen for events
                        async def listen_and_cleanup():
                            try:
                                await _listen_agent_websocket(
                                    conversation_id, ws, "nested_agent", timeout=120.0
                                )
                            finally:
                                await ws.close()
                                await http_session.close()

                        asyncio.create_task(listen_and_cleanup())
                        result["success"] = True

                    except Exception as e:
                        result["error"] = f"Failed to connect to nested agent: {e}"
                        logger.error(f"[DisconnectedTool] {result['error']}")
            else:
                result["error"] = "No text provided"

        elif tool_name == "send_to_claude_code":
            text = args.get("text", "")
            if text:
                # First try existing session
                session_manager = get_session_manager()
                session = await session_manager.get_session(conversation_id)

                if session and session.claude_code_ws and not session.claude_code_ws.closed:
                    try:
                        await session.claude_code_ws.send_json({
                            "type": "user_message",
                            "data": text
                        })
                        result["success"] = True
                        logger.info(f"[DisconnectedTool] Sent to Claude Code via existing session: {text[:100]}...")
                    except Exception as e:
                        result["error"] = f"Failed to send to Claude Code: {e}"
                        logger.error(f"[DisconnectedTool] {result['error']}")
                else:
                    # Connect and start background listener
                    try:
                        ws_url = "ws://localhost:8000/api/runs/ClaudeCode"

                        # Create a persistent session for the background task
                        http_session = aiohttp.ClientSession()
                        ws = await http_session.ws_connect(ws_url)

                        # Send the user message
                        await ws.send_json({"type": "user_message", "data": text})
                        logger.info(f"[DisconnectedTool] Sent to Claude Code: {text[:100]}...")

                        # Start background task to listen for events
                        async def listen_and_cleanup():
                            try:
                                await _listen_agent_websocket(
                                    conversation_id, ws, "claude_code", timeout=120.0
                                )
                            finally:
                                await ws.close()
                                await http_session.close()

                        asyncio.create_task(listen_and_cleanup())
                        result["success"] = True

                    except Exception as e:
                        result["error"] = f"Failed to connect to Claude Code: {e}"
                        logger.error(f"[DisconnectedTool] {result['error']}")
            else:
                result["error"] = "No text provided"
        else:
            result["error"] = f"Unknown tool: {tool_name}"

        results.append(result)

        # Store and broadcast tool call event
        await _store_and_broadcast_event(
            conversation_id=conversation_id,
            payload={
                "tool": tool_name,
                "arguments": args,
                "result": result,
            },
            source="assistant",
            event_type="disconnected_tool_call"
        )

    return results


@router.post("/api/realtime/conversations/{conversation_id}/audio-message", response_model=AudioMessageResponse)
async def send_audio_message(conversation_id: str, request: AudioMessageRequest):
    """
    Send an audio message in disconnected mode (no WebRTC).

    This endpoint:
    1. Receives base64-encoded audio from the client
    2. Builds conversation history from stored events
    3. Calls OpenAI Chat Completions API with gpt-4o-audio-preview
    4. Stores user audio + assistant response as events
    5. Executes any tool calls
    6. Returns text + audio response

    Use this when the WebRTC realtime session is not active.
    """
    logger.info(f"[AudioMessage] Received audio message for conversation {conversation_id}")

    # Verify conversation exists
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Load voice configuration
    voice_config = _load_selected_voice_config()
    voice = request.voice or voice_config.get("voice", "cedar")
    agent_name = voice_config.get("agent_name", "MainConversation")
    memory_file_path = voice_config.get("memory_file_path", "backend/data/memory/short_term_memory.txt")
    system_prompt_file = voice_config.get("system_prompt_file", "default.txt")

    # Load and prepare system prompt
    base_prompt = _load_voice_prompt_file(system_prompt_file)
    system_prompt = prepare_voice_system_prompt(
        base_prompt=base_prompt,
        agent_name=agent_name,
        conversation_id=conversation_id,
        memory_file_path=memory_file_path,
    )

    # Get conversation history
    events = conversation_store.list_events(conversation_id, limit=100)

    # Create audio chat handler
    handler = AudioChatHandler(
        model="gpt-4o-audio-preview",
        voice=voice
    )

    try:
        # Send audio and get response
        text_response, audio_response, transcript, tool_calls = await handler.send_audio_message(
            audio_base64=request.audio_base64,
            conversation_history=events,
            system_prompt=system_prompt,
            audio_format=request.format
        )

        logger.info(f"[AudioMessage] Got response: {len(text_response)} chars text, audio={'yes' if audio_response else 'no'}, tools={len(tool_calls) if tool_calls else 0}")

        # Store and broadcast user audio event
        await _store_and_broadcast_event(
            conversation_id=conversation_id,
            payload={
                "transcript": transcript or "",
                "format": request.format,
            },
            source="user",
            event_type="disconnected_user_audio"
        )

        # Store and broadcast assistant response event
        await _store_and_broadcast_event(
            conversation_id=conversation_id,
            payload={
                "text": text_response,
                "has_audio": bool(audio_response),
            },
            source="assistant",
            event_type="disconnected_assistant_response"
        )

        # Execute tool calls if any
        if tool_calls:
            await _execute_disconnected_tool_calls(conversation_id, tool_calls)

        return AudioMessageResponse(
            text=text_response,
            audio_base64=audio_response,
            transcript=transcript
        )

    except Exception as exc:
        logger.error(f"[AudioMessage] Failed to process audio: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {exc}")


@router.post("/api/realtime/conversations/{conversation_id}/text-message", response_model=AudioMessageResponse)
async def send_text_message(conversation_id: str, request: TextMessageRequest):
    """
    Send a text message in disconnected mode (no WebRTC).

    This endpoint:
    1. Receives text from the client
    2. Builds conversation history from stored events
    3. Calls OpenAI Chat Completions API with gpt-4o-audio-preview
    4. Stores user text + assistant response as events
    5. Executes any tool calls
    6. Returns text + optional audio response

    Use this when the WebRTC realtime session is not active.
    """
    logger.info(f"[TextMessage] Received text message for conversation {conversation_id}")

    # Verify conversation exists
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Load voice configuration
    voice_config = _load_selected_voice_config()
    voice = request.voice or voice_config.get("voice", "cedar")
    agent_name = voice_config.get("agent_name", "MainConversation")
    memory_file_path = voice_config.get("memory_file_path", "backend/data/memory/short_term_memory.txt")
    system_prompt_file = voice_config.get("system_prompt_file", "default.txt")

    # Load and prepare system prompt
    base_prompt = _load_voice_prompt_file(system_prompt_file)
    system_prompt = prepare_voice_system_prompt(
        base_prompt=base_prompt,
        agent_name=agent_name,
        conversation_id=conversation_id,
        memory_file_path=memory_file_path,
    )

    # Get conversation history
    events = conversation_store.list_events(conversation_id, limit=100)

    # Create audio chat handler
    handler = AudioChatHandler(
        model="gpt-4o-audio-preview",
        voice=voice
    )

    try:
        # Send text and get response
        text_response, audio_response, tool_calls = await handler.send_text_message(
            text=request.text,
            conversation_history=events,
            system_prompt=system_prompt,
            include_audio=request.include_audio
        )

        logger.info(f"[TextMessage] Got response: {len(text_response)} chars text, audio={'yes' if audio_response else 'no'}, tools={len(tool_calls) if tool_calls else 0}")

        # Store and broadcast user text event
        await _store_and_broadcast_event(
            conversation_id=conversation_id,
            payload={
                "text": request.text,
            },
            source="user",
            event_type="disconnected_user_text"
        )

        # Store and broadcast assistant response event
        await _store_and_broadcast_event(
            conversation_id=conversation_id,
            payload={
                "text": text_response,
                "has_audio": bool(audio_response),
            },
            source="assistant",
            event_type="disconnected_assistant_response"
        )

        # Execute tool calls if any
        if tool_calls:
            await _execute_disconnected_tool_calls(conversation_id, tool_calls)

        return AudioMessageResponse(
            text=text_response,
            audio_base64=audio_response,
            transcript=None  # No transcript for text input
        )

    except Exception as exc:
        logger.error(f"[TextMessage] Failed to process text: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to process text: {exc}")
