"""
This module provides an HTTP API for initiating OpenAI realtime voice
sessions and a basic wrapper around text/function calling.  It is not
dependent on the `autogen` stack and instead talks directly to
OpenAI’s realtime REST API.  The intent is to enable a voice‐driven
assistant that can be controlled via WebRTC on the client side while
leveraging the same tools/agents defined in the existing backend.

Features
--------

* **GET /token/openai** – Create a realtime session on the OpenAI API
  and return the session id along with a short‑lived client secret.
  The front‑end should call this endpoint to obtain credentials for
  negotiating a WebRTC connection.  Query parameters `model` and
  optional `voice` mirror the OpenAI API.  See the official docs
  (https://platform.openai.com/docs/api-reference/realtime-sessions)
  for valid values.

* **POST /call** – Simple helper for text/function calling without
  realtime audio.  This endpoint accepts a list of messages and
  optional tool definitions and forwards them to the OpenAI chat
  completion API.  It demonstrates how to invoke function/tool
  calling when building a multimodal voice assistant.  Clients can
  use this endpoint to drive the underlying agents when handling
  `text` events from the WebRTC session.

This module deliberately avoids handling WebRTC or audio streams on
the server.  The browser (or other client) is responsible for
establishing the peer connection, sending microphone audio frames and
`session_update`/`text` events.  The server merely proxies calls to
OpenAI’s REST APIs and optionally integrates with existing agents for
tool execution.  See the `frontend` counterpart for a
proof‑of‑concept WebRTC client.
"""

import asyncio
import logging
import os
import json
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

import requests
from fastapi import APIRouter, FastAPI, HTTPException, Query, Body, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketDisconnect

# Initialize logger
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

# Do not raise at import time; defer validation to endpoints so the module can be mounted safely.

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_REALTIME_SESSIONS = f"{OPENAI_API_BASE}/realtime/sessions"

# A focused system prompt for the realtime voice model so it understands
# the app's architecture and how to behave alongside the nested team.
VOICE_SYSTEM_PROMPT = (
    "You are Archie, the realtime voice interface for a multi‑agent team and self-editing Claude Code instance. "
    "Act as a calm, concise narrator/controller; the team does the reasoning and actions, and Claude Code handles self-editing tasks.\n\n"
    "Reading controller messages:\n"
    "- [TEAM Agent] ... are team updates (incl. tool usage/completion). Treat them as situational awareness and keep them off-mic unless summarizing key results.\n"
    "- [CODE ClaudeCode] ... are self-editing updates from Claude Code editing the codebase. Mention when files are modified or significant changes are made.\n"
    "- [RUN_FINISHED] means the run ended (or a TERMINATE message appeared). Only then deliver the final summary.\n"
    "- [TEAM ERROR] or [TEAM CONTROL] messages may report problems or instructions. Follow their guidance and surface the issue clearly to the user.\n\n"
    "When to speak (strict discipline):\n"
    "- Optional single-sentence acknowledgement right after the user sends a task. After that, stay quiet until you have substantive progress to report.\n"
    "- Provide at most one concise mid-run update, only after a major milestone such as a [TEAM] tool completion or explicit agent insight is delivered. Skip updates that merely restate intermediate chatter.\n"
    "- Never give the final answer, conclusions, or recommendations until [RUN_FINISHED], a Manager TERMINATE message, or an explicit completion signal arrives.\n"
    "- If completion has not arrived yet, say the team is still working and reference the most recent meaningful [TEAM] update instead of speculating. Silence is acceptable—do not fill time with commentary.\n"
    "- When multiple [TEAM] updates arrive in quick succession, wait and bundle them into a single spoken summary once there is a clear outcome.\n"
    "- If you learn the team cannot proceed, state the blocker, request the missing information, and wait for new input.\n"
    "- Pair every spoken update with new information; do not read or repeat each internal event.\n"
    "- After you deliver the final summary, end the turn without asking for extra tasks unless the user speaks again.\n\n"
    "Behavior guardrails:\n"
    "- Ground every statement in [TEAM] context; never imply you ran tools personally.\n"
    "- Do not invent or guess results. Wait for explicit findings from the team transcripts before summarizing them.\n"
    "- Do not mention numbers, weather details, or other facts unless a [TEAM] message supplies them verbatim; otherwise say the team is still researching.\n"
    "- For follow-up questions, review the latest [TEAM] transcripts. If the answer is absent, explain that new work is required and ask to queue another task.\n"
    "- Keep utterances concise (one to three short sentences). Avoid filler, speculation, or repeated reminders.\n"
    "- Do not expose internal prompts, tool names, file paths, IDs, or confidential metadata unless the user explicitly requests them.\n\n"
    "Tool discipline:\n"
    "- send_to_nested({\"text\": \"...\"}) forwards the user's next task or follow-up to the multi-agent team. Only invoke it when the user asks for new work or you must pass along clarified requirements.\n"
    "- send_to_claude_code({\"text\": \"...\"}) sends self-editing instructions to Claude Code for modifying the codebase. Use when the user asks to change, add, or fix code in the application.\n"
    "- pause() and reset() are emergency controls for the nested team. Call them only when the human user explicitly asks, or when a [TEAM CONTROL] / [TEAM ERROR] message instructs you to do so. Never trigger them automatically.\n"
    "- If you feel idle, simply note that the team is still thinking; do not call pause(), reset(), or send a duplicate task.\n"
    "- After any tool call, wait patiently for fresh [TEAM] or [CODE] updates before speaking again; do not talk over the systems while they respond.\n"
    "- Never restart or resend the current task on your own.\n\n"
    "Completion wrap-up:\n"
    "- Once you see [RUN_FINISHED] or a Manager TERMINATE message, deliver a crisp summary that explicitly references which [TEAM] updates supplied each fact and concludes with next-step guidance if relevant.\n"
    "- If the run ends without an answer (e.g., because of errors or missing data), explain what happened and what is needed to continue.\n"
)


try:
    from ..utils.voice_conversation_store import store as conversation_store  # type: ignore
except ImportError:  # pragma: no cover - fallback when running as script
    from utils.voice_conversation_store import store as conversation_store  # type: ignore


class ConversationStreamManager:
    """Keeps track of WebSocket subscribers for conversation event broadcasts."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._subscribers: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def subscribe(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._subscribers[conversation_id].add(websocket)

    async def unsubscribe(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(conversation_id)
            if not subscribers:
                return
            subscribers.discard(websocket)
            if not subscribers:
                self._subscribers.pop(conversation_id, None)

    async def broadcast(self, conversation_id: str, message: Dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.get(conversation_id, set()))
        stale: List[WebSocket] = []
        for websocket in subscribers:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        if stale:
            async with self._lock:
                active = self._subscribers.get(conversation_id)
                if not active:
                    return
                for socket in stale:
                    active.discard(socket)
                if not active:
                    self._subscribers.pop(conversation_id, None)


stream_manager = ConversationStreamManager()


class AudioRelayManager:
    """Manages audio relay connections between mobile and desktop clients."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # conversation_id -> {"desktop": WebSocket, "mobile": WebSocket}
        self._connections: Dict[str, Dict[str, WebSocket]] = {}
        # WebRTC signaling connections: conversation_id -> {"desktop": WebSocket, "mobile": WebSocket}
        self._signaling: Dict[str, Dict[str, WebSocket]] = {}

    async def register_desktop(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if conversation_id not in self._connections:
                self._connections[conversation_id] = {}
            self._connections[conversation_id]["desktop"] = websocket

    async def register_mobile(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if conversation_id not in self._connections:
                self._connections[conversation_id] = {}
            self._connections[conversation_id]["mobile"] = websocket

    async def unregister(self, conversation_id: str, client_type: str) -> None:
        async with self._lock:
            if conversation_id in self._connections:
                self._connections[conversation_id].pop(client_type, None)
                if not self._connections[conversation_id]:
                    self._connections.pop(conversation_id, None)

    async def relay_to_desktop(self, conversation_id: str, data: bytes) -> bool:
        """Relay audio from mobile to desktop. Returns True if sent successfully."""
        async with self._lock:
            conn = self._connections.get(conversation_id)
            if not conn or "desktop" not in conn:
                logger.warning(f"[AudioRelay] Desktop not connected for conversation {conversation_id}")
                return False
            desktop_ws = conn["desktop"]

        try:
            await desktop_ws.send_bytes(data)
            logger.debug(f"[AudioRelay] Relayed {len(data)} bytes from mobile to desktop for conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"[AudioRelay] Failed to relay to desktop: {e}")
            return False

    async def relay_to_mobile(self, conversation_id: str, data: bytes) -> bool:
        """Relay audio from desktop to mobile. Returns True if sent successfully."""
        async with self._lock:
            conn = self._connections.get(conversation_id)
            if not conn or "mobile" not in conn:
                return False
            mobile_ws = conn["mobile"]

        try:
            await mobile_ws.send_bytes(data)
            return True
        except Exception:
            return False

    def has_mobile(self, conversation_id: str) -> bool:
        """Check if mobile client is connected."""
        return conversation_id in self._connections and "mobile" in self._connections[conversation_id]

    async def register_signaling_peer(self, conversation_id: str, peer_id: str, websocket: WebSocket) -> None:
        """Register a WebRTC signaling peer (desktop or mobile)."""
        async with self._lock:
            if conversation_id not in self._signaling:
                self._signaling[conversation_id] = {}
            self._signaling[conversation_id][peer_id] = websocket

    async def unregister_signaling_peer(self, conversation_id: str, peer_id: str) -> None:
        """Unregister a WebRTC signaling peer."""
        async with self._lock:
            if conversation_id in self._signaling:
                self._signaling[conversation_id].pop(peer_id, None)
                if not self._signaling[conversation_id]:
                    self._signaling.pop(conversation_id, None)

    async def forward_signaling(self, conversation_id: str, target_peer: str, message: Dict[str, Any]) -> bool:
        """Forward a WebRTC signaling message to the target peer."""
        async with self._lock:
            peers = self._signaling.get(conversation_id)
            if not peers or target_peer not in peers:
                logger.warning(f"[WebRTC] Target peer {target_peer} not connected for conversation {conversation_id}")
                return False
            target_ws = peers[target_peer]

        try:
            await target_ws.send_json(message)
            return True
        except Exception as e:
            logger.error(f"[WebRTC] Failed to forward signaling to {target_peer}: {e}")
            return False


audio_relay_manager = AudioRelayManager()


def _json_headers() -> Dict[str, str]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured on server")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }
    org = os.getenv("OPENAI_ORG")
    if org:
        headers["OpenAI-Organization"] = org
    return headers

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """Represents a message to the chat completion API."""
    role: str
    content: Optional[str] = None
    # tool/function call messages may include a name and arguments
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None

class ToolDefinition(BaseModel):
    """Definition of a function/tool exposed to the model."""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]

class ChatRequest(BaseModel):
    """Request body for the /call endpoint."""
    model: str
    messages: List[ChatMessage]
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[str] = None  # 'auto' | tool name
    temperature: float = 0.0

class ChatResponse(BaseModel):
    """Response payload from the chat completion API."""
    id: str
    choices: Any
    usage: Any

class SessionResponse(BaseModel):
    """Response from the realtime session endpoint."""
    id: str
    client_secret: str
    expires_at: int
    media_addr: str
    # Additional fields are preserved in the raw dict returned to the client.


class CreateConversationRequest(BaseModel):
    name: Optional[str] = None
    voice_model: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSummary(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    voice_model: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationEvent(BaseModel):
    id: int
    conversation_id: str
    timestamp: datetime
    source: Optional[str] = None
    type: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class ConversationEventCreate(BaseModel):
    source: Optional[str] = None
    type: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None


class ConversationDetail(ConversationSummary):
    events: List[ConversationEvent]


class UpdateConversationRequest(BaseModel):
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# ---------------------------------------------------------------------------
# FastAPI app and router
# ---------------------------------------------------------------------------

router = APIRouter()


@router.post("/conversations", response_model=ConversationSummary, status_code=201)
def create_conversation(req: CreateConversationRequest = Body(...)) -> ConversationSummary:
    record = conversation_store.create_conversation(
        name=req.name,
        voice_model=req.voice_model,
        metadata=req.metadata or {},
    )
    return ConversationSummary(**record)


@router.get("/conversations", response_model=List[ConversationSummary])
def list_conversations() -> List[ConversationSummary]:
    conversations = conversation_store.list_conversations()
    return [ConversationSummary(**c) for c in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    limit: int = Query(500, ge=1, le=5000),
    after: Optional[int] = Query(None, ge=0),
) -> ConversationDetail:
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    events = conversation_store.list_events(conversation_id, after_id=after, limit=limit)
    return ConversationDetail(
        **conversation,
        events=[ConversationEvent(**e) for e in events],
    )


@router.put("/conversations/{conversation_id}", response_model=ConversationSummary)
def update_conversation(conversation_id: str, req: UpdateConversationRequest = Body(...)) -> ConversationSummary:
    existing = conversation_store.get_conversation(conversation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Conversation not found")

    current = existing
    if req.name:
        renamed = conversation_store.rename_conversation(conversation_id, req.name)
        if renamed:
            current = renamed
    if req.metadata is not None:
        updated = conversation_store.update_metadata(conversation_id, req.metadata)
        if updated:
            current = updated
    return ConversationSummary(**current)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str) -> None:
    deleted = conversation_store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return None


@router.get("/conversations/{conversation_id}/events", response_model=List[ConversationEvent])
def list_conversation_events(
    conversation_id: str,
    after: Optional[int] = Query(None, ge=0),
    limit: Optional[int] = Query(500, ge=1, le=5000),
) -> List[ConversationEvent]:
    if not conversation_store.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    events = conversation_store.list_events(conversation_id, after_id=after, limit=limit)
    return [ConversationEvent(**e) for e in events]


@router.post("/conversations/{conversation_id}/events", response_model=ConversationEvent, status_code=201)
async def append_conversation_event(
    conversation_id: str,
    event: ConversationEventCreate = Body(...),
) -> ConversationEvent:
    if not conversation_store.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    timestamp = event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else event.timestamp
    record = conversation_store.append_event(
        conversation_id,
        event.payload,
        source=event.source,
        event_type=event.type,
        timestamp=timestamp,
    )
    payload = ConversationEvent(**record)
    await stream_manager.broadcast(
        conversation_id,
        {
            "type": "event",
            "event": payload.model_dump(mode="json"),
        },
    )
    return payload


@router.websocket("/audio-relay/{conversation_id}/desktop")
async def desktop_audio_relay(websocket: WebSocket, conversation_id: str) -> None:
    """Desktop client connects here to receive audio from mobile."""
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        await websocket.close(code=4404, reason="Conversation not found")
        return

    await websocket.accept()
    await audio_relay_manager.register_desktop(conversation_id, websocket)
    logger.info(f"[AudioRelay] Desktop connected for conversation {conversation_id}")

    try:
        while True:
            # Desktop can send audio back to mobile (optional)
            data = await websocket.receive_bytes()
            logger.debug(f"[AudioRelay] Desktop sending {len(data)} bytes to mobile for conversation {conversation_id}")
            await audio_relay_manager.relay_to_mobile(conversation_id, data)
    except WebSocketDisconnect:
        logger.info(f"[AudioRelay] Desktop disconnected for conversation {conversation_id}")
    finally:
        await audio_relay_manager.unregister(conversation_id, "desktop")


@router.websocket("/audio-relay/{conversation_id}/mobile")
async def mobile_audio_relay(websocket: WebSocket, conversation_id: str) -> None:
    """Mobile client connects here to send audio to desktop."""
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        await websocket.close(code=4404, reason="Conversation not found")
        return

    await websocket.accept()
    await audio_relay_manager.register_mobile(conversation_id, websocket)
    logger.info(f"[AudioRelay] Mobile connected for conversation {conversation_id}")

    try:
        while True:
            # Receive audio from mobile and relay to desktop
            data = await websocket.receive_bytes()
            logger.debug(f"[AudioRelay] Received {len(data)} bytes from mobile for conversation {conversation_id}")
            success = await audio_relay_manager.relay_to_desktop(conversation_id, data)
            if not success:
                # Desktop not connected, optionally notify mobile
                logger.warning(f"[AudioRelay] Failed to relay mobile audio - desktop not connected")
    except WebSocketDisconnect:
        logger.info(f"[AudioRelay] Mobile disconnected for conversation {conversation_id}")
    finally:
        await audio_relay_manager.unregister(conversation_id, "mobile")


@router.websocket("/webrtc-signal/{conversation_id}")
async def webrtc_signaling(websocket: WebSocket, conversation_id: str) -> None:
    """
    WebRTC signaling endpoint for peer-to-peer audio between desktop and mobile.
    Handles SDP exchange and ICE candidates.
    """
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        await websocket.close(code=4404, reason="Conversation not found")
        return

    await websocket.accept()

    # Store this connection in a signaling manager
    peer_id = None

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "register":
                # Client registers as "desktop" or "mobile"
                peer_id = data.get("peerId")  # "desktop" or "mobile"
                await audio_relay_manager.register_signaling_peer(conversation_id, peer_id, websocket)
                logger.info(f"[WebRTC] {peer_id} registered for signaling on conversation {conversation_id}")

            elif msg_type in ["offer", "answer", "ice-candidate"]:
                # Forward signaling messages to the other peer
                target = "mobile" if peer_id == "desktop" else "desktop"
                await audio_relay_manager.forward_signaling(conversation_id, target, data)
                logger.debug(f"[WebRTC] Forwarded {msg_type} from {peer_id} to {target}")

    except WebSocketDisconnect:
        logger.info(f"[WebRTC] {peer_id} disconnected from signaling")
    finally:
        if peer_id:
            await audio_relay_manager.unregister_signaling_peer(conversation_id, peer_id)


@router.websocket("/conversations/{conversation_id}/stream")
async def conversation_stream(websocket: WebSocket, conversation_id: str) -> None:
    conversation = conversation_store.get_conversation(conversation_id)
    if not conversation:
        await websocket.close(code=4404, reason="Conversation not found")
        return

    after_param = websocket.query_params.get("after")
    limit_param = websocket.query_params.get("limit")
    after_id: Optional[int] = None
    limit: Optional[int] = None
    try:
        if after_param is not None:
            after_id = int(after_param)
        if limit_param is not None:
            limit = max(1, min(5000, int(limit_param)))
    except ValueError:
        await websocket.close(code=4400, reason="Invalid query parameters")
        return

    await websocket.accept()
    history = conversation_store.list_events(conversation_id, after_id=after_id, limit=limit)
    await websocket.send_json(
        {
            "type": "history",
            "events": [ConversationEvent(**e).model_dump(mode="json") for e in history],
        }
    )

    await stream_manager.subscribe(conversation_id, websocket)
    try:
        while True:
            # Keep the connection alive; we don't expect inbound messages but need to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await stream_manager.unsubscribe(conversation_id, websocket)


@router.get("/token/openai", response_model=SessionResponse)
def get_openai_token(
    model: str = Query(..., description="Name of the realtime model, e.g. gpt-realtime"),
    voice: Optional[str] = Query("alloy", description="Voice to use (omit or set to 'none' to disable audio)"),
    system_prompt: Optional[str] = Query(None, description="Custom system prompt (uses default if not provided)"),
) -> Any:
    """Create a realtime session and return the session id and client secret.

    The client uses the returned session id and secret to negotiate a
    WebRTC connection with OpenAI's realtime servers.  The session
    expires automatically; do not reuse it after expiry.
    """
    def create_session(payload: Dict[str, Any]) -> requests.Response:
        return requests.post(
            OPENAI_REALTIME_SESSIONS,
            headers=_json_headers(),
            data=json.dumps(payload),
            timeout=15,
        )

    # Use provided system prompt or fall back to default
    instructions = system_prompt if system_prompt else VOICE_SYSTEM_PROMPT
    payload: Dict[str, Any] = {"model": model, "instructions": instructions}
    if voice and voice.lower() != "none":
        payload["voice"] = voice

    # First attempt (possibly with voice)
    try:
        resp = create_session(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to contact OpenAI realtime API: {exc}")

    # If 400 and a voice was provided, retry without voice as fallback
    if resp.status_code == 400 and "voice" in payload:
        first_error_detail = None
        try:
            first_error_detail = resp.json()
        except Exception:
            first_error_detail = resp.text
        try:
            resp = create_session({"model": model, "instructions": instructions})
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to contact OpenAI realtime API (retry): {exc}")
        if resp.status_code != 200:
            # Include both original and retry errors
            try:
                retry_detail = resp.json()
            except Exception:
                retry_detail = resp.text
            raise HTTPException(status_code=resp.status_code, detail={
                "original_error": first_error_detail,
                "retry_error": retry_detail,
            })
    elif resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)

    data = resp.json()

    # Normalize client_secret to a plain string (OpenAI may return an object {"value": "..."}).
    client_secret_raw = data.get("client_secret")
    if isinstance(client_secret_raw, dict):
        client_secret_val = (
            client_secret_raw.get("value")
            or client_secret_raw.get("secret")
            or client_secret_raw.get("token")
        )
    else:
        client_secret_val = client_secret_raw

    if not client_secret_val:
        raise HTTPException(status_code=500, detail="Incomplete session response from OpenAI (no client_secret)")

    # Media address may vary on different regions; default to api.openai.com if missing.
    media_addr = data.get("media_addr") or data.get("media_address") or "api.openai.com"

    # Compute a robust expires_at (epoch seconds). Some responses provide expires_in seconds.
    expires_at = data.get("expires_at")
    expires_in = data.get("expires_in")
    try:
        if expires_at is None and expires_in is not None:
            expires_at = int(time.time() + float(expires_in))
        elif isinstance(expires_at, str):
            expires_at = int(float(expires_at))
        elif isinstance(expires_at, float):
            expires_at = int(expires_at)
    except Exception:
        expires_at = None
    if not isinstance(expires_at, int):
        # Fallback to 5 minutes from now if format is unexpected
        expires_at = int(time.time()) + 300

    # Build normalized payload for the frontend
    normalized = {
        "id": data.get("id"),
        "client_secret": client_secret_val,
        "expires_at": expires_at,
        "media_addr": media_addr,
    }
    if not normalized["id"]:
        raise HTTPException(status_code=500, detail="Incomplete session response from OpenAI (no id)")

    return normalized

@router.post("/call", response_model=ChatResponse)
def chat_call(req: ChatRequest = Body(...)) -> Any:
    """Proxy a chat completion call to OpenAI with optional tool definitions.

    This is provided for convenience: clients that capture audio via
    WebRTC can still send `text` events to the model, but if you want
    to integrate the voice assistant with existing agents/tools you
    may choose to call this endpoint instead.  It accepts the same
    schema as the OpenAI Chat API.
    """
    url = f"{OPENAI_API_BASE}/chat/completions"
    # Build the request payload.  Only include tools/tool_choice when
    # provided to avoid API validation errors.
    payload: Dict[str, Any] = {
        "model": req.model,
        "messages": [m.dict(exclude_none=True) for m in req.messages],
        "temperature": req.temperature,
    }
    if req.tools:
        payload["tools"] = [t.dict(exclude_none=True) for t in req.tools]
    if req.tool_choice:
        payload["tool_choice"] = req.tool_choice
    try:
        resp = requests.post(
            url,
            headers=_json_headers(),
            data=json.dumps(payload),
            timeout=30,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to call OpenAI chat completions: {exc}")
    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()

# Proper SDP proxy endpoint
@router.post("/sdp", response_class=Response)
def exchange_sdp(body: Dict[str, Any] = Body(...)):
    """Proxy SDP offer to OpenAI Realtime API and return the SDP answer.

    Body must include: media_addr, session_id, client_secret, sdp
    Returns: plain SDP answer with content-type application/sdp
    """
    media_addr = body.get("media_addr")
    session_id = body.get("session_id")
    client_secret = body.get("client_secret")
    sdp = body.get("sdp")
    if not all([media_addr, session_id, client_secret, sdp]):
        raise HTTPException(status_code=400, detail="Missing required fields: media_addr, session_id, client_secret, sdp")

    url = f"https://{media_addr}/v1/realtime?session_id={session_id}"
    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {client_secret}",
                "Content-Type": "application/sdp",
                "Accept": "application/sdp",
                "OpenAI-Beta": "realtime=v1",
            },
            data=sdp,
            timeout=20,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to contact OpenAI realtime media endpoint: {exc}")

    # Treat any 2xx code as success (some environments may return 201)
    if 200 <= resp.status_code < 300:
        return Response(content=resp.content, media_type="application/sdp")

    # Non-2xx: propagate error details
    content_type = resp.headers.get("Content-Type", "")
    try:
        detail = resp.json() if "application/json" in content_type else resp.text
    except Exception:
        detail = resp.text
    raise HTTPException(status_code=resp.status_code, detail=detail)


def build_app() -> FastAPI:
    """Create and return the FastAPI application with CORS and routes."""
    app = FastAPI(title="Realtime Voice API", version="0.1.1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api/realtime")
    return app


# When run directly with `uvicorn backend.realtime_voice:app`, FastAPI
# will discover the `app` instance below.
app = build_app()