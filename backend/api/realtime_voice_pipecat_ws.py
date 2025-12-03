"""
backend/api/realtime_voice_pipecat_ws.py
Pipecat-based voice controller using FastAPI WebSocket (self-hosted, no Daily)

This is fully self-hosted - no external service dependencies except OpenAI.
Uses FastAPI WebSocket for audio transport instead of Daily/WebRTC.
"""

import asyncio
import logging
import os
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse
import uuid

# Pipecat imports (using correct paths)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport, FastAPIWebsocketParams
from pipecat.services.openai_realtime_beta import (
    OpenAIRealtimeBetaLLMService,
    SessionProperties,
    InputAudioTranscription,
    TurnDetection,
    InputAudioNoiseReduction
)
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
                        "text": frame.content,
                        "role": frame.role,
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


@router.websocket("/realtime/pipecat/ws/{conversation_id}")
async def pipecat_websocket(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for Pipecat voice sessions (self-hosted, no Daily)

    Full path: /api/realtime/pipecat/ws/{conversation_id}
    (Note: router is included with prefix='/api' in main.py)

    Path params:
        conversation_id: str - Conversation ID for event persistence

    Query params (optional):
        voice: str - OpenAI voice (alloy, echo, fable, onyx, nova, shimmer)
        agent_name: str - Agent name (for logging)
    """
    await websocket.accept()

    # Get query params
    voice = websocket.query_params.get("voice", "alloy")
    agent_name = websocket.query_params.get("agent_name", "MainConversation")
    system_prompt = websocket.query_params.get("system_prompt", "")

    session_id = str(uuid.uuid4())

    try:
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            await websocket.close(code=1008, reason="OPENAI_API_KEY not configured")
            return

        logger.info(f"Creating Pipecat WebSocket session: {session_id} for conversation: {conversation_id}")

        # Ensure conversation exists in database (create if doesn't exist)
        existing_conv = conversation_store.get_conversation(conversation_id)
        if not existing_conv:
            # Conversation doesn't exist, create it with the specific ID
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            with conversation_store._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO conversations (id, name, created_at, updated_at, voice_model, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id,
                        f"Pipecat Session {conversation_id[:8]}",
                        now,
                        now,
                        voice,
                        "{}"  # Empty JSON object for metadata
                    )
                )
            logger.info(f"Created new conversation: {conversation_id}")
        else:
            logger.info(f"Using existing conversation: {conversation_id}")

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

        # Create FastAPI WebSocket transport (NO DAILY NEEDED!)
        # Note: OpenAI Realtime API has built-in VAD, so we don't need client-side VAD
        transport = FastAPIWebsocketTransport(
            websocket,
            FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                audio_in_sample_rate=24000,  # OpenAI Realtime uses 24kHz
                audio_out_sample_rate=24000,
                audio_in_channels=1,  # Mono
                audio_out_channels=1,
                add_wav_header=False  # Send raw PCM16
            )
        )

        # Create session properties for OpenAI Realtime
        session_properties = SessionProperties(
            input_audio_transcription=InputAudioTranscription(),
            turn_detection=TurnDetection(),  # Server-side voice activity detection (default)
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
            session_properties=session_properties
        )

        # Register function handlers with LLM
        for func_name, func in function_map.items():
            llm.register_function(func_name, func)

        # Create event recording processor
        event_recorder = EventRecordingProcessor(conversation_id)

        # Build pipeline (simplified - no context aggregator needed)
        pipeline = Pipeline([
            transport.input(),              # Audio from WebSocket
            llm,                            # OpenAI Realtime API
            event_recorder,                 # Record events to DB
            transport.output()              # Audio to WebSocket
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
            "function_handler": function_handler,
            "transport": transport
        }

        logger.info(f"Starting Pipecat pipeline for session: {session_id}")

        # Record session start
        conversation_store.append_event(
            conversation_id,
            {
                "type": "session_started",
                "session_id": session_id,
                "voice": voice,
                "agent_name": agent_name,
                "transport": "websocket"
            },
            source="controller"
        )

        # Run pipeline (blocking)
        await runner.run(task)

        logger.info(f"Pipecat pipeline finished for session: {session_id}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"Error in Pipecat WebSocket session: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass
    finally:
        # Cleanup session
        if session_id in sessions:
            # Record session stop
            try:
                conversation_store.append_event(
                    conversation_id,
                    {"type": "session_stopped", "session_id": session_id},
                    source="controller"
                )
            except Exception as e:
                logger.error(f"Failed to record session stop: {e}")

            # Remove session
            del sessions[session_id]
            logger.info(f"Cleaned up session: {session_id}")


@router.get("/api/realtime/pipecat/sessions")
async def list_pipecat_sessions():
    """List active Pipecat sessions"""
    return JSONResponse({
        "sessions": [
            {
                "session_id": session_id,
                "conversation_id": session["conversation_id"]
            }
            for session_id, session in sessions.items()
        ]
    })


@router.post("/api/realtime/pipecat/sessions/{session_id}/stop")
async def stop_pipecat_session(session_id: str):
    """Stop a running Pipecat session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    try:
        # Send end frame to pipeline
        task = session["task"]
        await task.queue_frame(EndFrame())

        # Wait for pipeline to finish (with timeout)
        try:
            await asyncio.wait_for(task.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"Pipeline did not finish gracefully for session {session_id}")

        return JSONResponse({"status": "stopped", "session_id": session_id})

    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
