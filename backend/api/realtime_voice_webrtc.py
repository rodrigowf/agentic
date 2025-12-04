"""
backend/api/realtime_voice_webrtc.py
WebRTC bridge between the browser and OpenAI Realtime (backend-controlled)
"""

import asyncio
import json
import logging
import os
import uuid
from fractions import Fraction
from typing import Dict, Optional

import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import AudioFrame, AudioResampler
from fastapi import APIRouter, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import aiohttp

from .openai_webrtc_client import OpenAIWebRTCClient, wait_for_ice_gathering_complete

try:
    from .realtime_voice import VOICE_SYSTEM_PROMPT, stream_manager  # type: ignore
except Exception:  # pragma: no cover - fallback when module not available
    VOICE_SYSTEM_PROMPT = "You are a realtime voice assistant."
    stream_manager = None

try:
    from ..utils.voice_conversation_store import store as conversation_store  # type: ignore
except ImportError:  # pragma: no cover - fallback path
    from utils.voice_conversation_store import store as conversation_store  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Tool Definitions for OpenAI Realtime API
# ============================================================================

REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "send_to_nested",
        "description": "Send a user message to the nested agents team via WebSocket. Use this when the user wants to perform complex tasks that require multiple agents working together.",
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
        "description": "Send a self-editing instruction to Claude Code. Use this when the user wants to modify code, add features, or refactor the codebase.",
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
        "description": "Pause the current nested agents conversation. Use this when the user wants to stop the current task.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "reset",
        "description": "Reset the nested agents team conversation state. Use this when the user wants to start fresh or clear the current context.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "type": "function",
        "name": "pause_claude_code",
        "description": "Pause or interrupt the currently running Claude Code task. Use this when the user wants to stop Claude Code.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]


class BridgeOffer(BaseModel):
    conversation_id: str
    offer: str
    voice: Optional[str] = "alloy"
    agent_name: Optional[str] = "MainConversation"
    system_prompt: Optional[str] = None


class BridgeAnswer(BaseModel):
    session_id: str
    answer: str


class BridgeText(BaseModel):
    text: str


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
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to append voice event: %s", exc)
        return

    if not stream_manager:
        return

    try:
        await stream_manager.broadcast(
            conversation_id,
            {"type": "event", "event": record},
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to broadcast voice event: %s", exc)


class AudioFrameSourceTrack(MediaStreamTrack):
    """Audio source track that feeds AudioFrames to the browser peer connection."""

    kind = "audio"

    def __init__(self, sample_rate: int = 48000):
        super().__init__()
        # CRITICAL: OpenAI sends 48000 Hz audio (not 24000 Hz as documented)
        # We must match the actual sample rate to avoid speed/pitch issues
        self.sample_rate = sample_rate
        self.queue: asyncio.Queue[AudioFrame] = asyncio.Queue()
        self._timestamp = 0
        logger.info(f"[AudioFrameSourceTrack] Initialized with sample_rate={sample_rate}")

    def _to_mono(self, frame: AudioFrame) -> AudioFrame:
        try:
            # Check if already mono
            if frame.layout.name == "mono":
                logger.info(f"[_to_mono] Already mono: samples={frame.samples}")
                mono = frame
            else:
                # Use AudioResampler to properly convert stereo to mono
                # This handles interleaved stereo data correctly and preserves sample count
                logger.info(f"[_to_mono] Converting {frame.layout.name} to mono: input samples={frame.samples}")
                resampler = AudioResampler(format="s16", layout="mono")
                mono_frames = resampler.resample(frame)
                mono = next(iter(mono_frames))
                logger.info(f"[_to_mono] After conversion: output samples={mono.samples}")

            # CRITICAL: Preserve the ORIGINAL sample rate from OpenAI's frame
            sr = getattr(frame, "sample_rate", None) or self.sample_rate

            # Set proper timestamps
            mono.sample_rate = sr
            mono.time_base = Fraction(1, sr)
            mono.pts = self._timestamp
            self._timestamp += mono.samples

            # Log first frame for debugging
            if self._timestamp == mono.samples:
                logger.info(f"[AudioFrameSourceTrack] ✅ First frame after conversion:")
                logger.info(f"[AudioFrameSourceTrack]    Sample rate: {sr} Hz")
                logger.info(f"[AudioFrameSourceTrack]    Samples: {mono.samples}")
                logger.info(f"[AudioFrameSourceTrack]    Duration: {mono.samples / sr * 1000:.2f}ms")
                logger.info(f"[AudioFrameSourceTrack]    Expected for 20ms @ 48kHz: 960 samples")
                if mono.samples != 960:
                    logger.warning(f"[AudioFrameSourceTrack] ⚠️  SAMPLE COUNT MISMATCH: got {mono.samples}, expected 960")
                if sr != self.sample_rate:
                    logger.warning(f"[AudioFrameSourceTrack] ⚠️  SAMPLE RATE MISMATCH: track={self.sample_rate} Hz, frame={sr} Hz")

            return mono
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to normalize audio frame: %s", exc)
            return frame

    async def send_frame(self, frame: AudioFrame):
        await self.queue.put(self._to_mono(frame))

    async def recv(self) -> AudioFrame:
        return await self.queue.get()


class BridgeSession:
    """Maintains a single browser ↔ OpenAI bridge."""

    def __init__(self, conversation_id: str, voice: str, agent_name: str, system_prompt: Optional[str], model: Optional[str] = None):
        self.session_id = str(uuid.uuid4())
        self.conversation_id = conversation_id
        self.voice = voice
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.model = model or "gpt-realtime"  # Default if not specified

        # Browser WebRTC connection
        self.browser_pc = RTCPeerConnection()
        self.browser_audio = AudioFrameSourceTrack()
        self.browser_audio_task: Optional[asyncio.Task] = None

        # OpenAI WebRTC client
        self.openai_client: Optional[OpenAIWebRTCClient] = None

        # WebSocket connections for nested agents and Claude Code
        self.nested_ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.claude_code_ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.nested_ws_task: Optional[asyncio.Task] = None
        self.claude_code_ws_task: Optional[asyncio.Task] = None

        # WebSocket configuration
        self.backend_base_url = os.getenv("BACKEND_WS_URL", "ws://localhost:8000")

        self.browser_pc.onconnectionstatechange = self._on_browser_state_change

    # --------------------------------------------
    # Setup
    # --------------------------------------------
    async def start(self, offer_sdp: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

        # Connect to OpenAI first (jitter prevention)
        logger.info(f"[WebRTC Bridge] Using model: {self.model}")

        self.openai_client = OpenAIWebRTCClient(
            api_key=api_key,
            model=self.model,
            voice=self.voice,
            on_audio_callback=self.handle_openai_audio,
            on_function_call_callback=self.handle_function_call,
            on_event_callback=self._handle_openai_event,
            system_prompt=self.system_prompt or VOICE_SYSTEM_PROMPT,
            enable_server_vad=True,
        )
        await self.openai_client.connect()

        # Set up ontrack handler BEFORE any SDP operations
        self.browser_pc.ontrack = self._on_browser_track
        logger.info("[WebRTC Bridge] DEBUG: ontrack handler set up")

        # Prepare browser peer connection and attach outbound track (assistant → browser)
        self.browser_pc.addTrack(self.browser_audio)

        logger.info("[WebRTC Bridge] DEBUG: Received offer SDP length: %d", len(offer_sdp))
        logger.info("[WebRTC Bridge] DEBUG: Offer contains 'a=sendrecv': %s", 'a=sendrecv' in offer_sdp)
        logger.info("[WebRTC Bridge] DEBUG: Offer contains 'a=recvonly': %s", 'a=recvonly' in offer_sdp)

        # Finish SDP negotiation with browser
        await self.browser_pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))

        # Check if we already have remote tracks from the offer (ontrack might not fire)
        logger.info("[WebRTC Bridge] Checking for existing remote tracks...")
        for transceiver in self.browser_pc.getTransceivers():
            if transceiver.receiver and transceiver.receiver.track:
                track = transceiver.receiver.track
                logger.info(f"[WebRTC Bridge] Found existing track: {track.kind}")
                if track.kind == "audio" and not self.browser_audio_task:
                    logger.info("[WebRTC Bridge] Starting audio forwarding for existing track...")
                    self.browser_audio_task = asyncio.create_task(self._forward_browser_audio(track))

        answer = await self.browser_pc.createAnswer()
        await self.browser_pc.setLocalDescription(answer)
        await wait_for_ice_gathering_complete(self.browser_pc)
        local_sdp = self.browser_pc.localDescription.sdp if self.browser_pc.localDescription else answer.sdp

        # Log SDP for debugging audio format issues
        logger.info("[WebRTC Bridge] DEBUG: Full Answer SDP:")
        logger.info(local_sdp)
        logger.info("[WebRTC Bridge] DEBUG: Checking for direction attributes...")
        if 'a=sendrecv' in local_sdp:
            logger.info("[WebRTC Bridge] ✅ Answer has a=sendrecv (bidirectional)")
        elif 'a=recvonly' in local_sdp:
            logger.warning("[WebRTC Bridge] ⚠️  Answer has a=recvonly (backend won't receive from browser!)")
        elif 'a=sendonly' in local_sdp:
            logger.warning("[WebRTC Bridge] ⚠️  Answer has a=sendonly (browser can't send!)")
        else:
            logger.info("[WebRTC Bridge] No explicit direction attribute (default is sendrecv)")

        await _append_and_broadcast(
            self.conversation_id,
            {"type": "session_started", "session_id": self.session_id, "transport": "webrtc_bridge", "voice": self.voice},
            source="controller",
            event_type="session_started",
        )

        return local_sdp

    # --------------------------------------------
    # Event handlers
    # --------------------------------------------
    def _on_browser_state_change(self):
        logger.info("[WebRTC Bridge] Browser PC state: %s", self.browser_pc.connectionState)

    def _on_browser_track(self, event):
        logger.info("="*60)
        logger.info("[WebRTC Bridge] 🎤 BROWSER TRACK EVENT FIRED!")
        logger.info("="*60)
        track: MediaStreamTrack = event.track
        logger.info(f"[WebRTC Bridge] Track kind: {track.kind}, Track ID: {track.id}")
        if track.kind != "audio":
            logger.warning(f"[WebRTC Bridge] Ignoring non-audio track: {track.kind}")
            return
        logger.info("[WebRTC Bridge] ✅ Audio track received, starting forwarding task...")
        if self.browser_audio_task:
            self.browser_audio_task.cancel()
        self.browser_audio_task = asyncio.create_task(self._forward_browser_audio(track))

    async def _forward_browser_audio(self, track: MediaStreamTrack):
        logger.info("[WebRTC Bridge] Forwarding browser audio → OpenAI")
        frame_count = 0
        try:
            while True:
                frame = await track.recv()
                frame_count += 1

                # Log first frame to confirm browser audio is flowing
                if frame_count == 1:
                    logger.info(f"[Browser Audio] ✅ First frame received: samples={frame.samples}, rate={frame.sample_rate}, layout={frame.layout.name}")

                if self.openai_client:
                    await self.openai_client.send_audio_frame(frame)

                    # Log periodically to show activity
                    if frame_count % 100 == 0:
                        logger.info(f"[Browser Audio] Forwarded {frame_count} frames to OpenAI")
                else:
                    logger.warning("[Browser Audio] OpenAI client not ready, cannot forward frame")
        except asyncio.CancelledError:  # pragma: no cover - expected on shutdown
            logger.info(f"[Browser Audio] Forwarding stopped after {frame_count} frames")
            pass
        except Exception as exc:
            logger.error("[WebRTC Bridge] Error forwarding browser audio: %s", exc)

    async def handle_openai_audio(self, frame: AudioFrame):
        """Assistant audio → browser"""
        await self.browser_audio.send_frame(frame)

    def _handle_openai_event(self, event: Dict):
        asyncio.create_task(
            _append_and_broadcast(
                self.conversation_id,
                event,
                source="voice",
                event_type=event.get("type"),
            )
        )

    async def handle_function_call(self, event: Dict):
        """Handle function calls emitted by the Realtime API."""
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
            result = await self.execute_tool_call(call_id, tool_name, arguments)
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

    async def execute_tool_call(self, call_id: str, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool call and return the result."""
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

    # --------------------------------------------
    # Tool execution methods
    # --------------------------------------------
    async def _tool_send_to_nested(self, text: str) -> Dict:
        """Send a message to the nested agents team."""
        if not text.strip():
            return {"success": False, "error": "Empty message"}

        if not self.nested_ws or self.nested_ws.closed:
            return {"success": False, "error": "Nested WebSocket not connected"}

        try:
            await self.nested_ws.send_json({
                "type": "user_message",
                "data": text
            })
            logger.info(f"[Tool] Sent to nested agents: {text[:100]}...")
            return {"success": True, "message": f"Sent to nested agents: {text[:100]}..."}
        except Exception as exc:
            logger.error(f"[Tool] Failed to send to nested agents: {exc}")
            return {"success": False, "error": str(exc)}

    async def _tool_send_to_claude_code(self, text: str) -> Dict:
        """Send a message to Claude Code."""
        if not text.strip():
            return {"success": False, "error": "Empty message"}

        if not self.claude_code_ws or self.claude_code_ws.closed:
            return {"success": False, "error": "Claude Code WebSocket not connected"}

        try:
            await self.claude_code_ws.send_json({
                "type": "user_message",
                "data": text
            })
            logger.info(f"[Tool] Sent to Claude Code: {text[:100]}...")
            return {"success": True, "message": f"Sent to Claude Code: {text[:100]}..."}
        except Exception as exc:
            logger.error(f"[Tool] Failed to send to Claude Code: {exc}")
            return {"success": False, "error": str(exc)}

    async def _tool_pause(self) -> Dict:
        """Pause the nested agents conversation."""
        if not self.nested_ws or self.nested_ws.closed:
            return {"success": False, "error": "Nested WebSocket not connected"}

        try:
            await self.nested_ws.send_json({
                "type": "control",
                "action": "pause"
            })
            logger.info("[Tool] Paused nested agents")
            return {"success": True, "message": "Nested agents paused"}
        except Exception as exc:
            logger.error(f"[Tool] Failed to pause nested agents: {exc}")
            return {"success": False, "error": str(exc)}

    async def _tool_reset(self) -> Dict:
        """Reset the nested agents conversation."""
        if not self.nested_ws or self.nested_ws.closed:
            return {"success": False, "error": "Nested WebSocket not connected"}

        try:
            await self.nested_ws.send_json({
                "type": "control",
                "action": "reset"
            })
            logger.info("[Tool] Reset nested agents")
            return {"success": True, "message": "Nested agents reset"}
        except Exception as exc:
            logger.error(f"[Tool] Failed to reset nested agents: {exc}")
            return {"success": False, "error": str(exc)}

    async def _tool_pause_claude_code(self) -> Dict:
        """Pause Claude Code."""
        if not self.claude_code_ws or self.claude_code_ws.closed:
            return {"success": False, "error": "Claude Code WebSocket not connected"}

        try:
            await self.claude_code_ws.send_json({
                "type": "control",
                "action": "pause"
            })
            logger.info("[Tool] Paused Claude Code")
            return {"success": True, "message": "Claude Code paused"}
        except Exception as exc:
            logger.error(f"[Tool] Failed to pause Claude Code: {exc}")
            return {"success": False, "error": str(exc)}

    # --------------------------------------------
    # WebSocket connection handlers
    # --------------------------------------------
    async def _connect_nested_websocket(self):
        """Connect to the nested agents WebSocket."""
        try:
            ws_url = f"{self.backend_base_url}/api/runs/{self.agent_name}"
            logger.info(f"[WebSocket] Connecting to nested agents at {ws_url}")

            async with aiohttp.ClientSession() as session:
                self.nested_ws = await session.ws_connect(ws_url)
                logger.info("[WebSocket] Connected to nested agents")

                # Start listening task
                self.nested_ws_task = asyncio.create_task(self._listen_nested_websocket())
        except Exception as exc:
            logger.error(f"[WebSocket] Failed to connect to nested agents: {exc}")
            self.nested_ws = None

    async def _connect_claude_code_websocket(self):
        """Connect to the Claude Code WebSocket."""
        try:
            ws_url = f"{self.backend_base_url}/api/runs/ClaudeCode"
            logger.info(f"[WebSocket] Connecting to Claude Code at {ws_url}")

            async with aiohttp.ClientSession() as session:
                self.claude_code_ws = await session.ws_connect(ws_url)
                logger.info("[WebSocket] Connected to Claude Code")

                # Start listening task
                self.claude_code_ws_task = asyncio.create_task(self._listen_claude_code_websocket())
        except Exception as exc:
            logger.error(f"[WebSocket] Failed to connect to Claude Code: {exc}")
            self.claude_code_ws = None

    async def _listen_nested_websocket(self):
        """Listen for messages from nested agents and forward to voice."""
        if not self.nested_ws:
            return

        try:
            async for msg in self.nested_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        event = json.loads(msg.data)
                        await self._handle_nested_message(event)
                    except json.JSONDecodeError:
                        logger.error(f"[WebSocket] Invalid JSON from nested agents: {msg.data}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"[WebSocket] Nested agents error: {self.nested_ws.exception()}")
                    break
        except asyncio.CancelledError:
            logger.info("[WebSocket] Nested agents listener cancelled")
        except Exception as exc:
            logger.error(f"[WebSocket] Error listening to nested agents: {exc}")

    async def _listen_claude_code_websocket(self):
        """Listen for messages from Claude Code and forward to voice."""
        if not self.claude_code_ws:
            return

        try:
            async for msg in self.claude_code_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        event = json.loads(msg.data)
                        await self._handle_claude_code_message(event)
                    except json.JSONDecodeError:
                        logger.error(f"[WebSocket] Invalid JSON from Claude Code: {msg.data}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"[WebSocket] Claude Code error: {self.claude_code_ws.exception()}")
                    break
        except asyncio.CancelledError:
            logger.info("[WebSocket] Claude Code listener cancelled")
        except Exception as exc:
            logger.error(f"[WebSocket] Error listening to Claude Code: {exc}")

    async def _handle_nested_message(self, event: Dict):
        """Process and forward nested agent events to voice."""
        event_type = event.get("type", "").lower()

        # Format message based on event type
        message = None
        if event_type == "textmessage":
            agent = event.get("data", {}).get("source", "Agent")
            content = event.get("data", {}).get("content", "")
            message = f"[TEAM {agent}] {content}"

        elif event_type == "toolcallexecutionevent":
            tool_name = event.get("data", {}).get("name", "Tool")
            result = event.get("data", {}).get("result", "")
            # Truncate long results
            result_str = str(result)[:200] + ("..." if len(str(result)) > 200 else "")
            message = f"[TEAM {tool_name}] {result_str}"

        elif event_type == "taskresult":
            outcome = event.get("data", {}).get("outcome", "completed")
            summary = event.get("data", {}).get("message", "")
            message = f"[TEAM] Task {outcome}: {summary}"

        # Forward to OpenAI for voice narration
        if message and self.openai_client:
            logger.info(f"[Event Forward] {message[:100]}...")
            await self.openai_client.forward_message_to_voice("system", message)

        # Also broadcast to conversation store
        if message:
            await _append_and_broadcast(
                self.conversation_id,
                {"type": "nested_event", "event_type": event_type, "message": message},
                source="nested_agent",
                event_type="nested_event",
            )

    async def _handle_claude_code_message(self, event: Dict):
        """Process and forward Claude Code events to voice."""
        event_type = event.get("type", "").lower()

        # Format message
        message = None
        if event_type == "textmessage":
            content = event.get("data", {}).get("content", "")
            message = f"[CODE ClaudeCode] {content}"

        elif event_type == "toolcallexecutionevent":
            tool_name = event.get("data", {}).get("name", "Tool")
            result = event.get("data", {}).get("result", "")
            result_str = str(result)[:200] + ("..." if len(str(result)) > 200 else "")
            message = f"[CODE {tool_name}] {result_str}"

        elif event_type == "taskresult":
            outcome = event.get("data", {}).get("outcome", "completed")
            summary = event.get("data", {}).get("message", "")
            message = f"[CODE] Task {outcome}: {summary}"

        # Forward to OpenAI for voice narration
        if message and self.openai_client:
            logger.info(f"[Event Forward] {message[:100]}...")
            await self.openai_client.forward_message_to_voice("system", message)

        # Also broadcast to conversation store
        if message:
            await _append_and_broadcast(
                self.conversation_id,
                {"type": "claude_code_event", "event_type": event_type, "message": message},
                source="claude_code",
                event_type="claude_code_event",
            )

    async def send_text(self, text: str):
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text payload is empty")
        if not self.openai_client:
            raise HTTPException(status_code=400, detail="OpenAI client not ready")
        await self.openai_client.send_text(text.strip())

    # --------------------------------------------
    # Cleanup
    # --------------------------------------------
    async def close(self):
        if self.browser_audio_task:
            self.browser_audio_task.cancel()
            self.browser_audio_task = None

        try:
            if self.browser_pc:
                await self.browser_pc.close()
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error closing browser peer connection: %s", exc)

        try:
            if self.openai_client:
                await self.openai_client.close()
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error closing OpenAI client: %s", exc)

        await _append_and_broadcast(
            self.conversation_id,
            {"type": "session_stopped", "session_id": self.session_id},
            source="controller",
            event_type="session_stopped",
        )


# Active bridges keyed by conversation_id (single active session per conversation)
active_bridges: Dict[str, BridgeSession] = {}


@router.post("/api/realtime/webrtc/bridge", response_model=BridgeAnswer)
async def handle_bridge(offer: BridgeOffer):
    """Accept a browser SDP offer, build the OpenAI bridge, and return the SDP answer."""
    conversation = conversation_store.get_conversation(offer.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Close any existing bridge for this conversation
    existing = active_bridges.pop(offer.conversation_id, None)
    if existing:
        await existing.close()

    # Get voice_model from conversation - use exact name from config
    voice_model = conversation.get("voice_model") or "gpt-realtime"

    session = BridgeSession(
        conversation_id=offer.conversation_id,
        voice=offer.voice or "alloy",
        agent_name=offer.agent_name or "MainConversation",
        system_prompt=offer.system_prompt or conversation.get("metadata", {}).get("system_prompt") or VOICE_SYSTEM_PROMPT,
        model=voice_model,
    )

    try:
        answer_sdp = await session.start(offer.offer)
    except Exception as exc:
        logger.error("Failed to establish WebRTC bridge: %s", exc)
        await session.close()
        raise HTTPException(status_code=500, detail=f"Failed to establish bridge: {exc}")

    active_bridges[offer.conversation_id] = session
    return BridgeAnswer(session_id=session.session_id, answer=answer_sdp)


@router.delete("/api/realtime/webrtc/bridge/{conversation_id}")
async def stop_bridge(conversation_id: str):
    """Close an active bridge for the given conversation."""
    session = active_bridges.pop(conversation_id, None)
    if not session:
        raise HTTPException(status_code=404, detail="Bridge not found")

    await session.close()
    return JSONResponse({"status": "closed", "session_id": session.session_id})


@router.post("/api/realtime/webrtc/bridge/{conversation_id}/text")
async def send_text(conversation_id: str, payload: BridgeText):
    """Send a user text message through an active WebRTC bridge."""
    session = active_bridges.get(conversation_id)
    if not session:
        raise HTTPException(status_code=404, detail="Bridge not found")

    try:
        await session.send_text(payload.text)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to send text over WebRTC bridge: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to send text: {exc}")

    await _append_and_broadcast(
        conversation_id,
        {"type": "user_text", "text": payload.text},
        source="controller",
        event_type="user_text",
    )
    return JSONResponse({"status": "sent"})


@router.post("/api/realtime/webrtc/bridge/{conversation_id}/commit")
async def commit_audio(conversation_id: str):
    """
    Manually commit audio buffer and trigger model response.
    Used in MANUAL MODE when turn detection is disabled.
    User signals they're done speaking via "Done Speaking" button.
    """
    session = active_bridges.get(conversation_id)
    if not session:
        raise HTTPException(status_code=404, detail="Bridge not found")

    try:
        if session.openai_client:
            await session.openai_client.commit_audio_buffer()
            logger.info(f"[Bridge] Audio committed for conversation {conversation_id}")
        else:
            raise HTTPException(status_code=400, detail="OpenAI client not ready")
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to commit audio: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to commit audio: {exc}")

    await _append_and_broadcast(
        conversation_id,
        {"type": "audio_committed", "timestamp": conversation_id},
        source="controller",
        event_type="audio_committed",
    )
    return JSONResponse({"status": "committed"})
