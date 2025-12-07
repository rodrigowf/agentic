"""
Voice Conversation Management Module

This module provides conversation management for the voice assistant system.
It handles persistence, event broadcasting, and conversation lifecycle.

The actual voice/audio handling is done by realtime_voice_webrtc.py which
uses the WebRTC bridge to connect to OpenAI's Realtime API.

Exports used by other modules:
- VOICE_SYSTEM_PROMPT: System prompt for the voice assistant
- stream_manager: ConversationStreamManager for event broadcasting
- _inject_available_agents: Helper to inject agent info into prompts
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

from fastapi import APIRouter, HTTPException, Query, Body, WebSocket
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketDisconnect

# Initialize logger
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voice System Prompt
# ---------------------------------------------------------------------------

VOICE_SYSTEM_PROMPT = (
    "You are Archie, the realtime voice interface for a multi‑agent team and self-editing Claude Code instance. "
    "**IMPORTANT: Always respond in English, regardless of the language you detect in the user's speech.** "
    "Act as a calm, concise narrator/controller; the team does the reasoning and actions, and Claude Code handles self-editing tasks.\n\n"
    "**AVAILABLE AGENTS IN THE TEAM**:\n"
    "{{AVAILABLE_AGENTS}}\n\n"
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

# ---------------------------------------------------------------------------
# Conversation Store
# ---------------------------------------------------------------------------

try:
    from ..utils.voice_conversation_store import store as conversation_store  # type: ignore
except ImportError:
    from utils.voice_conversation_store import store as conversation_store  # type: ignore


# ---------------------------------------------------------------------------
# Stream Manager for Event Broadcasting
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Agent Injection Helper
# ---------------------------------------------------------------------------

def _inject_available_agents(instructions: str, agent_name: str) -> str:
    """
    Inject available agents from the nested team into the voice system prompt.
    Replaces {{AVAILABLE_AGENTS}} placeholder with formatted list of agents.

    Args:
        instructions: The system prompt with placeholder
        agent_name: Name of the nested team agent (e.g., 'MainConversation')

    Returns:
        Updated instructions with agent list injected
    """
    try:
        from config.config_loader import load_agents

        agents_dir = "agents"
        all_agents = load_agents(agents_dir)

        # Find the requested agent
        agent_config = None
        for agent in all_agents:
            if agent.name == agent_name:
                agent_config = agent
                break

        if not agent_config:
            logger.warning(f"Agent '{agent_name}' not found, using default placeholder")
            return instructions.replace("{{AVAILABLE_AGENTS}}", "(No agents information available)")

        # Check if it's a nested_team agent with sub_agents
        if agent_config.agent_type != "nested_team" or not agent_config.sub_agents:
            logger.info(f"Agent '{agent_name}' is not a nested team, skipping agent list injection")
            return instructions.replace("{{AVAILABLE_AGENTS}}", "(Not a nested team - no sub-agents available)")

        # Extract sub-agent descriptions
        agent_descriptions = []
        for sub_agent in agent_config.sub_agents:
            if hasattr(sub_agent, 'name'):
                sub_agent_name = sub_agent.name
                description = sub_agent.description or "No description available"
                agent_descriptions.append(f"- **{sub_agent_name}**: {description}")
            else:
                sub_agent_name = sub_agent
                sub_agent_config = None
                for agent in all_agents:
                    if agent.name == sub_agent_name:
                        sub_agent_config = agent
                        break

                if sub_agent_config:
                    description = sub_agent_config.description or "No description available"
                    agent_descriptions.append(f"- **{sub_agent_name}**: {description}")
                else:
                    agent_descriptions.append(f"- **{sub_agent_name}**: (Configuration not found)")

        # Format the agents list
        if agent_descriptions:
            agents_text = "\n".join(agent_descriptions)
        else:
            agents_text = "(No sub-agents configured)"

        updated_instructions = instructions.replace("{{AVAILABLE_AGENTS}}", agents_text)
        logger.info(f"Injected {len(agent_descriptions)} agent descriptions into voice prompt")

        return updated_instructions

    except Exception as e:
        logger.error(f"Error injecting available agents: {e}")
        return instructions.replace("{{AVAILABLE_AGENTS}}", "(Error loading agents information)")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

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
# FastAPI Router
# ---------------------------------------------------------------------------

router = APIRouter()


# ---------------------------------------------------------------------------
# Conversation CRUD Endpoints
# ---------------------------------------------------------------------------

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


@router.post("/conversations/cleanup")
def cleanup_inactive_conversations(
    inactive_minutes: int = Query(30, ge=1, le=1440, description="Delete conversations inactive for this many minutes")
) -> Dict[str, Any]:
    """
    Delete conversations that haven't been updated in the specified time period.
    Default is 30 minutes. This helps clean up stale/abandoned conversations.
    """
    deleted_ids = conversation_store.cleanup_inactive_conversations(inactive_minutes)
    return {
        "deleted_count": len(deleted_ids),
        "deleted_ids": deleted_ids,
        "inactive_minutes": inactive_minutes
    }


# ---------------------------------------------------------------------------
# Conversation Events Endpoints
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Conversation Stream WebSocket
# ---------------------------------------------------------------------------

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
