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

import os
import json
from typing import List, Optional, Dict, Any

import requests
from fastapi import APIRouter, FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

# Do not raise at import time; defer validation to endpoints so the module can be mounted safely.

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_REALTIME_SESSIONS = f"{OPENAI_API_BASE}/realtime/sessions"


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

# ---------------------------------------------------------------------------
# FastAPI app and router
# ---------------------------------------------------------------------------

router = APIRouter()

@router.get("/token/openai", response_model=SessionResponse)
def get_openai_token(
    model: str = Query(..., description="Name of the realtime model, e.g. gpt-4o-realtime-preview-2025-06-03"),
    voice: str = Query("onyx", description="Name of the voice to use. See OpenAI docs for available voices."),
) -> Any:
    """Create a realtime session and return the session id and client secret.

    The client uses the returned session id and secret to negotiate a
    WebRTC connection with OpenAI’s realtime servers.  The session
    expires automatically; do not reuse it after expiry.
    """
    payload: Dict[str, Any] = {"model": model}
    # voice is optional; if omitted, audio output is disabled
    if voice:
        payload["voice"] = voice
    try:
        resp = requests.post(
            OPENAI_REALTIME_SESSIONS,
            headers=_json_headers(),
            data=json.dumps(payload),
            timeout=15,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to contact OpenAI realtime API: {exc}")
    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    data = resp.json()
    # Ensure required fields are present
    required = {"id", "client_secret", "expires_at", "media_addr"}
    if not required.issubset(data):
        raise HTTPException(status_code=500, detail="Incomplete session response from OpenAI")
    return data

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


def build_app() -> FastAPI:
    """Create and return the FastAPI application.

    This function isolates the app construction so that it can be used
    both in production and during testing.  It sets up CORS to allow
    cross‑origin requests from any domain (use a stricter policy in
    production).
    """
    app = FastAPI(title="Realtime Voice API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


# When run directly with `uvicorn backend.realtime_voice:app`, FastAPI
# will discover the `app` instance below.  This pattern avoids
# constructing the app at import time when running unit tests.
app = build_app()