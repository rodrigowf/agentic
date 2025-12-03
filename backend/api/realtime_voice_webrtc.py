"""
backend/api/realtime_voice_webrtc.py
Main controller for backend-controlled WebRTC voice sessions
"""

import asyncio
import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
import os
import uuid
import numpy as np

from .openai_webrtc_client import OpenAIWebRTCClient
from .frontend_audio_handler import FrontendAudioHandler

# Import conversation store for event persistence
try:
    from ..utils.voice_conversation_store import store as conversation_store
except ImportError:
    from utils.voice_conversation_store import store as conversation_store

logger = logging.getLogger(__name__)
router = APIRouter()

# Active sessions
sessions: Dict[str, dict] = {}


@router.post("/api/realtime/session")
async def create_session(request: Request):
    """Create new voice session with backend WebRTC"""
    body = await request.json()
    conversation_id = body.get("conversation_id")
    voice = body.get("voice", "alloy")
    agent_name = body.get("agent_name", "MainConversation")
    system_prompt = body.get("system_prompt", "")

    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")

    session_id = str(uuid.uuid4())

    # Get OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    # Create OpenAI client with event callback for persistence
    def on_event_callback(event: dict):
        """Record all OpenAI events to conversation store"""
        try:
            event_type = event.get("type", "unknown")
            conversation_store.append_event(
                conversation_id,
                event,
                source="voice",
                event_type=event_type
            )
        except Exception as e:
            logger.error(f"Failed to record event: {e}")

    openai_client = OpenAIWebRTCClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview-2024-12-17",
        voice=voice,
        on_audio_callback=lambda audio: handle_openai_audio(session_id, audio),
        on_function_call_callback=lambda event: handle_function_call(session_id, event),
        on_event_callback=on_event_callback
    )

    # Connect to OpenAI
    try:
        await openai_client.connect()
    except Exception as e:
        logger.error(f"Failed to connect to OpenAI: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to OpenAI: {str(e)}")

    # Store session with conversation context
    sessions[session_id] = {
        "openai_client": openai_client,
        "frontend_handlers": [],
        "audio_buffers": {},
        "conversation_id": conversation_id,
        "agent_name": agent_name
    }

    logger.info(f"Created session {session_id} for conversation {conversation_id}")

    return JSONResponse({
        "session_id": session_id,
        "status": "connected"
    })


@router.post("/api/realtime/sdp/{session_id}")
async def exchange_sdp(session_id: str, request: Request):
    """Exchange SDP with frontend"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get SDP offer from frontend
    offer_sdp = await request.body()
    offer_sdp = offer_sdp.decode("utf-8")

    # Create frontend handler
    frontend_handler = FrontendAudioHandler(
        session_id=session_id,
        on_audio_callback=lambda audio: handle_frontend_audio(session_id, audio)
    )

    # Handle SDP offer
    try:
        answer_sdp = await frontend_handler.handle_sdp_offer(offer_sdp)
    except Exception as e:
        logger.error(f"Failed to handle SDP offer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to exchange SDP: {str(e)}")

    # Store handler
    sessions[session_id]["frontend_handlers"].append(frontend_handler)

    logger.info(f"Frontend connected to session {session_id}")

    return Response(content=answer_sdp, media_type="application/sdp")


async def handle_frontend_audio(session_id: str, audio_data: bytes):
    """Handle audio from frontend, forward to OpenAI"""
    if session_id in sessions:
        openai_client = sessions[session_id]["openai_client"]
        try:
            await openai_client.send_audio(audio_data)
        except Exception as e:
            logger.error(f"Error forwarding audio to OpenAI: {e}")


async def handle_openai_audio(session_id: str, audio_data: bytes):
    """Handle audio from OpenAI, broadcast to all frontends"""
    if session_id in sessions:
        frontend_handlers = sessions[session_id]["frontend_handlers"]

        # Broadcast to all connected frontends
        for handler in frontend_handlers:
            try:
                await handler.send_audio(audio_data)
            except Exception as e:
                logger.error(f"Error sending audio to frontend: {e}")


async def handle_function_call(session_id: str, event: dict):
    """Handle function calls from OpenAI"""
    function_name = event.get("name")
    arguments = event.get("arguments", {})
    call_id = event.get("call_id")

    logger.info(f"Function call: {function_name} with args {arguments}")

    # Execute function
    result = None

    if function_name == "send_to_nested":
        result = await execute_nested_team(arguments.get("text"))
    elif function_name == "send_to_claude_code":
        result = await execute_claude_code(arguments.get("text"))
    else:
        result = f"Unknown function: {function_name}"

    # Send result back to OpenAI
    if session_id in sessions:
        openai_client = sessions[session_id]["openai_client"]
        try:
            await openai_client.send_function_result(call_id, result)
        except Exception as e:
            logger.error(f"Error sending function result: {e}")


async def execute_nested_team(text: str) -> str:
    """Execute nested team agent"""
    # TODO: Integrate with existing nested team logic
    logger.info(f"Nested team execution: {text}")
    return f"Nested team executed: {text}"


async def execute_claude_code(text: str) -> str:
    """Execute Claude Code"""
    # TODO: Integrate with existing Claude Code logic
    logger.info(f"Claude Code execution: {text}")
    return f"Claude Code executed: {text}"


@router.delete("/api/realtime/session/{session_id}")
async def close_session(session_id: str):
    """Close session and cleanup"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Close OpenAI connection
    try:
        await session["openai_client"].close()
    except Exception as e:
        logger.error(f"Error closing OpenAI client: {e}")

    # Close frontend connections
    for handler in session["frontend_handlers"]:
        try:
            await handler.close()
        except Exception as e:
            logger.error(f"Error closing frontend handler: {e}")

    # Remove session
    del sessions[session_id]

    logger.info(f"Closed session {session_id}")

    return JSONResponse({"status": "closed"})


def mix_audio_streams(streams: list) -> bytes:
    """Mix multiple audio streams into one"""
    if not streams:
        return b""
    if len(streams) == 1:
        return streams[0]

    try:
        # Convert bytes to numpy arrays
        arrays = [np.frombuffer(s, dtype=np.int16) for s in streams]

        # Find max length and pad shorter arrays
        max_length = max(len(arr) for arr in arrays)
        arrays = [np.pad(arr, (0, max_length - len(arr))) for arr in arrays]

        # Average samples to prevent clipping
        mixed = np.mean(arrays, axis=0).astype(np.int16)

        return mixed.tobytes()
    except Exception as e:
        logger.error(f"Error mixing audio: {e}")
        return streams[0] if streams else b""
