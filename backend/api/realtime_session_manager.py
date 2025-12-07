"""
backend/api/realtime_session_manager.py

RealtimeSessionManager - Manages OpenAI Realtime sessions per conversation.

Architecture:
- ONE OpenAI WebRTC connection per conversation_id (not global singleton)
- Session persists even when all frontends disconnect
- Handles tool execution, nested agents, and Claude Code integration
- Audio received from OpenAI is broadcast to all connected frontends via callback
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Callable, Dict, List, Optional

import aiohttp
import numpy as np
from av import AudioFrame

from .openai_webrtc_client import OpenAIWebRTCClient

try:
    from .realtime_voice import VOICE_SYSTEM_PROMPT, stream_manager
except Exception:
    VOICE_SYSTEM_PROMPT = "You are a realtime voice assistant."
    stream_manager = None

try:
    from ..utils.voice_conversation_store import store as conversation_store
except ImportError:
    from utils.voice_conversation_store import store as conversation_store

logger = logging.getLogger(__name__)


# Tool definitions for OpenAI Realtime API
REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "send_to_nested",
        "description": "Send a user message to the nested agents team via WebSocket.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The user message or task to send to the nested agents team"
                }
            },
            "required": ["text"]
        }
    },
    {
        "type": "function",
        "name": "send_to_claude_code",
        "description": "Send a self-editing instruction to Claude Code.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The instruction for Claude Code to execute"
                }
            },
            "required": ["text"]
        }
    },
    {
        "type": "function",
        "name": "pause",
        "description": "Pause the current nested agents conversation.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "type": "function",
        "name": "reset",
        "description": "Reset the nested agents team conversation state.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "type": "function",
        "name": "pause_claude_code",
        "description": "Pause or interrupt the currently running Claude Code task.",
        "parameters": {"type": "object", "properties": {}}
    }
]


async def _append_and_broadcast(
    conversation_id: str,
    payload: Dict,
    source: str = "voice",
    event_type: Optional[str] = None,
) -> None:
    """Record an event to the conversation store and broadcast to subscribers."""
    try:
        record = conversation_store.append_event(
            conversation_id,
            payload,
            source=source,
            event_type=event_type,
        )
    except Exception as exc:
        logger.error("Failed to append voice event: %s", exc)
        return

    if not stream_manager:
        return

    try:
        await stream_manager.broadcast(
            conversation_id,
            {"type": "event", "event": record},
        )
    except Exception as exc:
        logger.error("Failed to broadcast voice event: %s", exc)


class OpenAISession:
    """
    Represents a single OpenAI Realtime session for one conversation.

    Handles:
    - OpenAI WebRTC connection
    - Tool execution (send_to_nested, send_to_claude_code, etc.)
    - Nested agent and Claude Code WebSocket connections
    - Audio callback for broadcasting to frontends
    """

    def __init__(
        self,
        conversation_id: str,
        voice: str = "alloy",
        agent_name: str = "MainConversation",
        system_prompt: Optional[str] = None,
        model: str = "gpt-realtime",
        on_audio_callback: Optional[Callable[[AudioFrame], None]] = None,
    ):
        self.session_id = str(uuid.uuid4())
        self.conversation_id = conversation_id
        self.voice = voice
        self.agent_name = agent_name
        self.system_prompt = system_prompt or VOICE_SYSTEM_PROMPT
        self.model = model

        # Callback to broadcast audio to all connected frontends
        self.on_audio_callback = on_audio_callback

        # OpenAI WebRTC client
        self.openai_client: Optional[OpenAIWebRTCClient] = None

        # WebSocket connections for nested agents and Claude Code
        self.nested_ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.claude_code_ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.nested_ws_task: Optional[asyncio.Task] = None
        self.claude_code_ws_task: Optional[asyncio.Task] = None
        self.aiohttp_session: Optional[aiohttp.ClientSession] = None

        # Configuration
        self.backend_base_url = os.getenv("BACKEND_WS_URL", "ws://localhost:8000")
        self.input_gain = float(os.getenv("VOICE_INPUT_GAIN", "4.0"))

        # State
        self._connected = False
        self._closing = False

    async def connect(self) -> None:
        """Establish connection to OpenAI Realtime API."""
        if self._connected:
            logger.warning(f"[OpenAISession {self.conversation_id}] Already connected")
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")

        logger.info(f"[OpenAISession {self.conversation_id}] Connecting to OpenAI...")
        logger.info(f"[OpenAISession {self.conversation_id}]   Model: {self.model}")
        logger.info(f"[OpenAISession {self.conversation_id}]   Voice: {self.voice}")

        # Create OpenAI client
        self.openai_client = OpenAIWebRTCClient(
            api_key=api_key,
            model=self.model,
            voice=self.voice,
            tools=REALTIME_TOOLS,
            on_audio_callback=self._handle_openai_audio,
            on_function_call_callback=self._handle_function_call,
            on_event_callback=self._handle_openai_event,
            system_prompt=self.system_prompt,
            enable_server_vad=True,
            input_gain=self.input_gain,
        )
        await self.openai_client.connect()

        # Connect to nested agents and Claude Code
        await self._connect_nested_websocket()
        await self._connect_claude_code_websocket()

        self._connected = True

        await _append_and_broadcast(
            self.conversation_id,
            {
                "type": "session_started",
                "session_id": self.session_id,
                "transport": "webrtc_bridge",
                "voice": self.voice,
            },
            source="controller",
            event_type="session_started",
        )

        logger.info(f"[OpenAISession {self.conversation_id}] ✅ Connected successfully")

    async def close(self) -> None:
        """Close the OpenAI session and cleanup resources."""
        if self._closing:
            return
        self._closing = True

        logger.info(f"[OpenAISession {self.conversation_id}] Closing...")

        # Stop WebSocket listener tasks
        for task in [self.nested_ws_task, self.claude_code_ws_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close WebSocket connections
        for ws in [self.nested_ws, self.claude_code_ws]:
            if ws and not ws.closed:
                try:
                    await ws.close()
                except Exception as exc:
                    logger.error(f"Error closing WebSocket: {exc}")

        # Close aiohttp session
        if self.aiohttp_session:
            try:
                await self.aiohttp_session.close()
            except Exception as exc:
                logger.error(f"Error closing aiohttp session: {exc}")

        # Close OpenAI client
        if self.openai_client:
            try:
                await self.openai_client.close()
            except Exception as exc:
                logger.error(f"Error closing OpenAI client: {exc}")

        self._connected = False

        await _append_and_broadcast(
            self.conversation_id,
            {"type": "session_stopped", "session_id": self.session_id},
            source="controller",
            event_type="session_stopped",
        )

        logger.info(f"[OpenAISession {self.conversation_id}] Closed")

    @property
    def is_connected(self) -> bool:
        return self._connected and not self._closing

    # ========================================================================
    # Audio Handling
    # ========================================================================

    async def _handle_openai_audio(self, frame: AudioFrame) -> None:
        """Handle audio from OpenAI and broadcast to frontends."""
        if self.on_audio_callback:
            await self.on_audio_callback(frame)

    async def send_audio(self, frame: AudioFrame) -> None:
        """Send audio from a frontend to OpenAI."""
        if self.openai_client and self.is_connected:
            await self.openai_client.send_audio_frame(frame)

    async def send_text(self, text: str) -> None:
        """Send text message to OpenAI."""
        if not text.strip():
            return
        if self.openai_client and self.is_connected:
            await self.openai_client.send_text(text.strip())

    async def commit_audio_buffer(self) -> None:
        """Manually commit audio buffer (for manual VAD mode)."""
        if self.openai_client and self.is_connected:
            await self.openai_client.commit_audio_buffer()

    # ========================================================================
    # Event Handling
    # ========================================================================

    def _handle_openai_event(self, event: Dict) -> None:
        """Handle events from OpenAI data channel."""
        asyncio.create_task(
            _append_and_broadcast(
                self.conversation_id,
                event,
                source="voice",
                event_type=event.get("type"),
            )
        )

    async def _handle_function_call(self, event: Dict) -> None:
        """Handle function calls from OpenAI."""
        call_id = event.get("call_id")
        tool_name = event.get("name")
        arguments_str = event.get("arguments", "{}")

        try:
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
        except json.JSONDecodeError:
            logger.error(f"[Tool Call] Failed to parse arguments: {arguments_str}")
            arguments = {}

        logger.info(f"[Tool Call] Executing: {tool_name} with args: {arguments}")

        # Record the function call
        await _append_and_broadcast(
            self.conversation_id,
            {"type": "function_call", "tool": tool_name, "arguments": arguments, "call_id": call_id},
            source="voice",
            event_type="function_call",
        )

        # Execute the tool
        try:
            result = await self._execute_tool(call_id, tool_name, arguments)
        except Exception as exc:
            logger.error(f"[Tool Call] Error executing {tool_name}: {exc}")
            result = {"success": False, "error": str(exc)}

        # Send result back to OpenAI
        if self.openai_client and call_id:
            await self.openai_client.send_function_call_result(call_id, result)

        # Record the result
        await _append_and_broadcast(
            self.conversation_id,
            {"type": "function_result", "tool": tool_name, "result": result, "call_id": call_id},
            source="voice",
            event_type="function_result",
        )

    async def _execute_tool(self, call_id: str, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool and return result."""
        if tool_name == "send_to_nested":
            return await self._tool_send_to_nested(arguments.get("text", ""))
        elif tool_name == "send_to_claude_code":
            return await self._tool_send_to_claude_code(arguments.get("text", ""))
        elif tool_name == "pause":
            return await self._tool_pause()
        elif tool_name == "reset":
            return await self._tool_reset()
        elif tool_name == "pause_claude_code":
            return await self._tool_pause_claude_code()
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    # ========================================================================
    # Tool Implementations
    # ========================================================================

    async def _tool_send_to_nested(self, text: str) -> Dict:
        if not text.strip():
            return {"success": False, "error": "Empty message"}
        if not self.nested_ws or self.nested_ws.closed:
            return {"success": False, "error": "Nested WebSocket not connected"}
        try:
            await self.nested_ws.send_json({"type": "user_message", "data": text})
            logger.info(f"[Tool] Sent to nested agents: {text[:100]}...")
            return {"success": True, "message": f"Sent to nested agents: {text[:100]}..."}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _tool_send_to_claude_code(self, text: str) -> Dict:
        if not text.strip():
            return {"success": False, "error": "Empty message"}
        if not self.claude_code_ws or self.claude_code_ws.closed:
            return {"success": False, "error": "Claude Code WebSocket not connected"}
        try:
            await self.claude_code_ws.send_json({"type": "user_message", "data": text})
            logger.info(f"[Tool] Sent to Claude Code: {text[:100]}...")
            return {"success": True, "message": f"Sent to Claude Code: {text[:100]}..."}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _tool_pause(self) -> Dict:
        if not self.nested_ws or self.nested_ws.closed:
            return {"success": False, "error": "Nested WebSocket not connected"}
        try:
            await self.nested_ws.send_json({"type": "control", "action": "pause"})
            return {"success": True, "message": "Nested agents paused"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _tool_reset(self) -> Dict:
        if not self.nested_ws or self.nested_ws.closed:
            return {"success": False, "error": "Nested WebSocket not connected"}
        try:
            await self.nested_ws.send_json({"type": "control", "action": "reset"})
            return {"success": True, "message": "Nested agents reset"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _tool_pause_claude_code(self) -> Dict:
        if not self.claude_code_ws or self.claude_code_ws.closed:
            return {"success": False, "error": "Claude Code WebSocket not connected"}
        try:
            await self.claude_code_ws.send_json({"type": "control", "action": "pause"})
            return {"success": True, "message": "Claude Code paused"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ========================================================================
    # WebSocket Connections (Nested Agents & Claude Code)
    # ========================================================================

    async def _connect_nested_websocket(self) -> None:
        try:
            if not self.aiohttp_session:
                self.aiohttp_session = aiohttp.ClientSession()
            ws_url = f"{self.backend_base_url}/api/runs/{self.agent_name}"
            logger.info(f"[OpenAISession] Connecting to nested agents at {ws_url}")
            self.nested_ws = await self.aiohttp_session.ws_connect(ws_url)
            self.nested_ws_task = asyncio.create_task(self._listen_nested_websocket())
            logger.info("[OpenAISession] Connected to nested agents")
        except Exception as exc:
            logger.error(f"[OpenAISession] Failed to connect to nested agents: {exc}")
            self.nested_ws = None

    async def _connect_claude_code_websocket(self) -> None:
        try:
            if not self.aiohttp_session:
                self.aiohttp_session = aiohttp.ClientSession()
            ws_url = f"{self.backend_base_url}/api/runs/ClaudeCode"
            logger.info(f"[OpenAISession] Connecting to Claude Code at {ws_url}")
            self.claude_code_ws = await self.aiohttp_session.ws_connect(ws_url)
            self.claude_code_ws_task = asyncio.create_task(self._listen_claude_code_websocket())
            logger.info("[OpenAISession] Connected to Claude Code")
        except Exception as exc:
            logger.error(f"[OpenAISession] Failed to connect to Claude Code: {exc}")
            self.claude_code_ws = None

    async def _listen_nested_websocket(self) -> None:
        if not self.nested_ws:
            return
        try:
            async for msg in self.nested_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        event = json.loads(msg.data)
                        await self._handle_nested_message(event)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON from nested agents: {msg.data}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"Nested agents error: {self.nested_ws.exception()}")
                    break
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"Error listening to nested agents: {exc}")

    async def _listen_claude_code_websocket(self) -> None:
        if not self.claude_code_ws:
            return
        try:
            async for msg in self.claude_code_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        event = json.loads(msg.data)
                        await self._handle_claude_code_message(event)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON from Claude Code: {msg.data}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"Claude Code error: {self.claude_code_ws.exception()}")
                    break
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(f"Error listening to Claude Code: {exc}")

    async def _handle_nested_message(self, event: Dict) -> None:
        event_type = event.get("type", "").lower()
        message = None

        if event_type == "textmessage":
            agent = event.get("data", {}).get("source", "Agent")
            content = event.get("data", {}).get("content", "")
            message = f"[TEAM {agent}] {content}"
        elif event_type == "toolcallexecutionevent":
            tool_name = event.get("data", {}).get("name", "Tool")
            result = str(event.get("data", {}).get("result", ""))[:200]
            message = f"[TEAM {tool_name}] {result}"
        elif event_type == "taskresult":
            outcome = event.get("data", {}).get("outcome", "completed")
            summary = event.get("data", {}).get("message", "")
            message = f"[TEAM] Task {outcome}: {summary}"

        if message and self.openai_client:
            logger.info(f"[Event Forward] {message[:100]}...")
            await self.openai_client.forward_message_to_voice("system", message)

        if message:
            await _append_and_broadcast(
                self.conversation_id,
                {"type": "nested_event", "event_type": event_type, "message": message},
                source="nested_agent",
                event_type="nested_event",
            )

    async def _handle_claude_code_message(self, event: Dict) -> None:
        event_type = event.get("type", "").lower()
        message = None

        if event_type == "textmessage":
            content = event.get("data", {}).get("content", "")
            message = f"[CODE ClaudeCode] {content}"
        elif event_type == "toolcallexecutionevent":
            tool_name = event.get("data", {}).get("name", "Tool")
            result = str(event.get("data", {}).get("result", ""))[:200]
            message = f"[CODE {tool_name}] {result}"
        elif event_type == "taskresult":
            outcome = event.get("data", {}).get("outcome", "completed")
            summary = event.get("data", {}).get("message", "")
            message = f"[CODE] Task {outcome}: {summary}"

        if message and self.openai_client:
            logger.info(f"[Event Forward] {message[:100]}...")
            await self.openai_client.forward_message_to_voice("system", message)

        if message:
            await _append_and_broadcast(
                self.conversation_id,
                {"type": "claude_code_event", "event_type": event_type, "message": message},
                source="claude_code",
                event_type="claude_code_event",
            )


class RealtimeSessionManager:
    """
    Manages OpenAI Realtime sessions per conversation.

    Each conversation_id gets its own isolated OpenAI session.
    Sessions persist even when all frontends disconnect (until explicitly closed).
    """

    def __init__(self):
        self._sessions: Dict[str, OpenAISession] = {}
        self._lock = asyncio.Lock()

    async def get_or_create_session(
        self,
        conversation_id: str,
        voice: str = "alloy",
        agent_name: str = "MainConversation",
        system_prompt: Optional[str] = None,
        model: str = "gpt-realtime",
        on_audio_callback: Optional[Callable[[AudioFrame], None]] = None,
    ) -> OpenAISession:
        """
        Get existing session or create new one for a conversation.

        Args:
            conversation_id: Unique conversation identifier
            voice: Voice name (e.g., "alloy")
            agent_name: Nested agent name
            system_prompt: System instructions
            model: OpenAI model name
            on_audio_callback: Called when audio received from OpenAI

        Returns:
            OpenAISession for the conversation
        """
        async with self._lock:
            if conversation_id in self._sessions:
                session = self._sessions[conversation_id]
                if session.is_connected:
                    logger.info(f"[SessionManager] Reusing existing session for {conversation_id}")
                    # Update the audio callback for new frontend connections
                    session.on_audio_callback = on_audio_callback
                    return session
                else:
                    # Session exists but not connected, clean it up
                    del self._sessions[conversation_id]

            # Create new session
            logger.info(f"[SessionManager] Creating new session for {conversation_id}")
            session = OpenAISession(
                conversation_id=conversation_id,
                voice=voice,
                agent_name=agent_name,
                system_prompt=system_prompt,
                model=model,
                on_audio_callback=on_audio_callback,
            )
            await session.connect()
            self._sessions[conversation_id] = session
            return session

    async def get_session(self, conversation_id: str) -> Optional[OpenAISession]:
        """Get existing session for a conversation (if any)."""
        async with self._lock:
            session = self._sessions.get(conversation_id)
            if session and session.is_connected:
                return session
            return None

    async def close_session(self, conversation_id: str) -> bool:
        """Close and remove session for a conversation."""
        async with self._lock:
            session = self._sessions.pop(conversation_id, None)
            if session:
                await session.close()
                return True
            return False

    async def close_all(self) -> None:
        """Close all sessions (for shutdown)."""
        async with self._lock:
            for session in self._sessions.values():
                try:
                    await session.close()
                except Exception as exc:
                    logger.error(f"Error closing session: {exc}")
            self._sessions.clear()

    def get_active_conversations(self) -> List[str]:
        """Get list of conversation IDs with active sessions."""
        return [cid for cid, s in self._sessions.items() if s.is_connected]


# Global instance
_session_manager: Optional[RealtimeSessionManager] = None


def get_session_manager() -> RealtimeSessionManager:
    """Get the global RealtimeSessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = RealtimeSessionManager()
    return _session_manager
