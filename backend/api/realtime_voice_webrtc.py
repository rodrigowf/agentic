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

try:
    from .realtime_voice import prepare_voice_system_prompt, VOICE_SYSTEM_PROMPT
except Exception:
    VOICE_SYSTEM_PROMPT = "You are a realtime voice assistant."
    def prepare_voice_system_prompt(base_prompt, agent_name, conversation_id=None, memory_file_path=None):
        return base_prompt

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
        "voice": "alloy",
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

    voice = voice_config.get("voice", "alloy")
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
