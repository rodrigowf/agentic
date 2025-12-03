"""
backend/api/realtime_voice_pipecat.py
Pipecat-based voice controller for OpenAI Realtime API

This replaces the custom WebRTC implementation with Pipecat framework.
Uses Daily transport for WebRTC and OpenAI Realtime API for voice.
"""

import asyncio
import logging
import os
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import uuid

# Pipecat imports (using correct paths from example)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.daily.transport import DailyTransport, DailyParams
from pipecat.services.openai_realtime_beta import (
    OpenAIRealtimeBetaLLMService,
    SessionProperties,
    InputAudioTranscription,
    TurnDetection,
    InputAudioNoiseReduction
)
from pipecat.processors.aggregators.llm_response import LLMUserResponseAggregator, LLMAssistantResponseAggregator
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.frames.frames import (
    Frame,
    TextFrame,
    TranscriptionMessage,
    FunctionCallFromLLM,
    FunctionCallResultFrame,
    EndFrame
)

# Import conversation store for event persistence
try:
    from ..utils.voice_conversation_store import store as conversation_store
except ImportError:
    from utils.voice_conversation_store import store as conversation_store

logger = logging.getLogger(__name__)
router = APIRouter()

# Active sessions
# Structure: {session_id: {"task": PipelineTask, "runner": PipelineRunner, "conversation_id": str}}
sessions: Dict[str, dict] = {}


class VoiceFunctionHandler:
    """Handles function calls from OpenAI Realtime API"""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.nested_ws = None  # Will be set externally
        self.claude_code_ws = None  # Will be set externally

    async def send_to_nested(self, text: str) -> str:
        """Send task to nested team agents"""
        logger.info(f"[Function] send_to_nested: {text}")

        # Record event
        try:
            conversation_store.append_event(
                self.conversation_id,
                {"type": "tool_send_to_nested", "text": text},
                source="controller"
            )
        except Exception as e:
            logger.error(f"Failed to record event: {e}")

        # TODO: Integrate with existing nested team WebSocket
        # For now, return placeholder
        return f"Nested team will execute: {text}"

    async def send_to_claude_code(self, text: str) -> str:
        """Send instruction to Claude Code"""
        logger.info(f"[Function] send_to_claude_code: {text}")

        # Record event
        try:
            conversation_store.append_event(
                self.conversation_id,
                {"type": "tool_send_to_claude_code", "text": text},
                source="controller"
            )
        except Exception as e:
            logger.error(f"Failed to record event: {e}")

        # TODO: Integrate with existing Claude Code controller
        # For now, return placeholder
        return f"Claude Code will execute: {text}"

    async def pause(self) -> str:
        """Pause nested team execution"""
        logger.info("[Function] pause")

        # Record event
        try:
            conversation_store.append_event(
                self.conversation_id,
                {"type": "tool_pause"},
                source="controller"
            )
        except Exception as e:
            logger.error(f"Failed to record event: {e}")

        # TODO: Send pause to nested WebSocket
        return "Nested team paused"

    async def reset(self) -> str:
        """Reset nested team conversation"""
        logger.info("[Function] reset")

        # Record event
        try:
            conversation_store.append_event(
                self.conversation_id,
                {"type": "tool_reset"},
                source="controller"
            )
        except Exception as e:
            logger.error(f"Failed to record event: {e}")

        # TODO: Send reset to nested WebSocket
        return "Nested team reset"

    async def pause_claude_code(self) -> str:
        """Pause Claude Code execution"""
        logger.info("[Function] pause_claude_code")

        # Record event
        try:
            conversation_store.append_event(
                self.conversation_id,
                {"type": "tool_pause_claude_code"},
                source="controller"
            )
        except Exception as e:
            logger.error(f"Failed to record event: {e}")

        # TODO: Send pause to Claude Code WebSocket
        return "Claude Code paused"


class EventRecordingProcessor(FrameProcessor):
    """Pipecat processor to record events to conversation store"""

    def __init__(self, conversation_id: str):
        super().__init__()
        self.conversation_id = conversation_id

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames and record to conversation store"""
        try:
            # Record transcription messages
            if isinstance(frame, TranscriptionMessage):
                conversation_store.append_event(
                    self.conversation_id,
                    {
                        "type": "transcription",
                        "text": frame.text,
                        "user_id": getattr(frame, "user_id", "user"),
                        "timestamp": getattr(frame, "timestamp", None)
                    },
                    source="voice"
                )

            # Record function call frames
            elif isinstance(frame, FunctionCallFromLLM):
                conversation_store.append_event(
                    self.conversation_id,
                    {
                        "type": "function_call",
                        "name": frame.function_name,
                        "arguments": frame.arguments
                    },
                    source="voice"
                )

            # Record text frames (assistant messages)
            elif isinstance(frame, TextFrame):
                conversation_store.append_event(
                    self.conversation_id,
                    {
                        "type": "text_message",
                        "text": frame.text
                    },
                    source="voice"
                )

        except Exception as e:
            logger.error(f"Failed to record frame: {e}")

        # Pass frame through
        await self.push_frame(frame, direction)


@router.post("/api/realtime/pipecat/session")
async def create_pipecat_session(request: Request):
    """
    Create new voice session with Pipecat + Daily + OpenAI Realtime

    Body:
        conversation_id: str - Conversation ID for event persistence
        voice: str - OpenAI voice (alloy, echo, fable, onyx, nova, shimmer)
        agent_name: str - Agent name (for logging)
        system_prompt: str - System prompt for OpenAI
    """
    body = await request.json()
    conversation_id = body.get("conversation_id")
    voice = body.get("voice", "alloy")
    agent_name = body.get("agent_name", "MainConversation")
    system_prompt = body.get("system_prompt", "")

    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id is required")

    session_id = str(uuid.uuid4())

    try:
        # Get Daily API key
        daily_api_key = os.getenv("DAILY_API_KEY")
        if not daily_api_key:
            raise HTTPException(
                status_code=500,
                detail="DAILY_API_KEY not configured. Set DAILY_API_KEY in .env file."
            )

        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

        # Create Daily room
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.daily.co/v1/rooms",
                headers={
                    "Authorization": f"Bearer {daily_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "properties": {
                        "exp": int(asyncio.get_event_loop().time()) + 3600,  # 1 hour expiry
                        "enable_chat": False,
                        "enable_screenshare": False,
                        "enable_recording": False
                    }
                }
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create Daily room: {resp.status} {error_text}"
                    )
                room_data = await resp.json()
                room_url = room_data["url"]
                room_name = room_data["name"]

        logger.info(f"Created Daily room: {room_url}")

        # Create Daily token for bot
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.daily.co/v1/meeting-tokens",
                headers={
                    "Authorization": f"Bearer {daily_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "properties": {
                        "room_name": room_name,
                        "is_owner": True
                    }
                }
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create Daily token: {resp.status} {error_text}"
                    )
                token_data = await resp.json()
                bot_token = token_data["token"]

        logger.info(f"Created Daily bot token")

        # Create function handler
        function_handler = VoiceFunctionHandler(conversation_id)

        # Define tools for OpenAI
        tools = [
            {
                "type": "function",
                "name": "send_to_nested",
                "description": "Send a user message to the nested agents team (MainConversation) via WebSocket.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The user message to send."}
                    },
                    "required": ["text"]
                }
            },
            {
                "type": "function",
                "name": "send_to_claude_code",
                "description": "Send a self-editing instruction to Claude Code to modify the codebase.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The instruction for Claude Code."}
                    },
                    "required": ["text"]
                }
            },
            {
                "type": "function",
                "name": "pause",
                "description": "Pause the current nested conversation when the user explicitly asks.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "type": "function",
                "name": "reset",
                "description": "Reset the nested team conversation state when the user explicitly asks.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "type": "function",
                "name": "pause_claude_code",
                "description": "Pause/interrupt the currently running Claude Code task.",
                "parameters": {"type": "object", "properties": {}}
            }
        ]

        # Register function handlers
        function_map = {
            "send_to_nested": function_handler.send_to_nested,
            "send_to_claude_code": function_handler.send_to_claude_code,
            "pause": function_handler.pause,
            "reset": function_handler.reset,
            "pause_claude_code": function_handler.pause_claude_code
        }

        # Create Daily transport
        transport = DailyTransport(
            room_url,
            bot_token,
            "Archie Bot",
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                transcription_enabled=True,
                vad_enabled=True,
                vad_analyzer="silero",  # Voice Activity Detection
                vad_audio_passthrough=True
            )
        )

        # Create session properties for OpenAI Realtime
        session_properties = SessionProperties(
            input_audio_transcription=InputAudioTranscription(),
            turn_detection=TurnDetection.server_vad(),  # Server-side voice activity detection
            input_audio_noise_reduction=InputAudioNoiseReduction(type="near_field"),
            voice=voice,
            instructions=system_prompt or "You are Archie, a helpful voice assistant.",
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
            max_response_output_tokens=4096
        )

        # Create OpenAI Realtime LLM service
        llm = OpenAIRealtimeBetaLLMService(
            api_key=openai_api_key,
            session_properties=session_properties,
            start_audio_paused=False
        )

        # Register function handlers with LLM
        for func_name, func in function_map.items():
            llm.register_function(func_name, func)

        # Create context aggregators
        context_aggregator = llm.create_context_aggregator()

        # Create event recording processor
        event_recorder = EventRecordingProcessor(conversation_id)

        # Build pipeline
        pipeline = Pipeline([
            transport.input(),              # Audio from Daily (users)
            context_aggregator.user(),      # Track user context
            llm,                            # OpenAI Realtime API
            event_recorder,                 # Record events to DB
            transport.output(),             # Audio to Daily (users)
            context_aggregator.assistant()  # Track assistant context
        ])

        # Create pipeline task
        task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

        # Create pipeline runner
        runner = PipelineRunner()

        # Store session
        sessions[session_id] = {
            "task": task,
            "runner": runner,
            "conversation_id": conversation_id,
            "room_url": room_url,
            "room_name": room_name,
            "function_handler": function_handler,
            "transport": transport
        }

        # Run pipeline in background
        asyncio.create_task(runner.run(task))

        logger.info(f"Created Pipecat session: {session_id}")

        # Record session start
        conversation_store.append_event(
            conversation_id,
            {
                "type": "session_started",
                "session_id": session_id,
                "voice": voice,
                "agent_name": agent_name,
                "room_url": room_url
            },
            source="controller"
        )

        return JSONResponse({
            "session_id": session_id,
            "room_url": room_url,
            "room_name": room_name,
            "status": "connected"
        })

    except Exception as e:
        logger.error(f"Failed to create Pipecat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/realtime/pipecat/session/{session_id}")
async def close_pipecat_session(session_id: str):
    """Close Pipecat session and cleanup"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    try:
        # Stop pipeline
        task = session["task"]
        await task.queue_frame(EndFrame())

        # Wait for pipeline to finish (with timeout)
        try:
            await asyncio.wait_for(task.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"Pipeline did not finish gracefully for session {session_id}")

        # Record session stop
        conversation_store.append_event(
            session["conversation_id"],
            {"type": "session_stopped", "session_id": session_id},
            source="controller"
        )

        # Remove session
        del sessions[session_id]

        logger.info(f"Closed Pipecat session: {session_id}")

        return JSONResponse({"status": "closed"})

    except Exception as e:
        logger.error(f"Error closing Pipecat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/realtime/pipecat/sessions")
async def list_pipecat_sessions():
    """List active Pipecat sessions"""
    return JSONResponse({
        "sessions": [
            {
                "session_id": session_id,
                "conversation_id": session["conversation_id"],
                "room_url": session["room_url"]
            }
            for session_id, session in sessions.items()
        ]
    })
