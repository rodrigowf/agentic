"""
Simple Pipecat WebSocket Implementation - Direct OpenAI Connection with Full Archie Integration

This bypasses Pipecat's transport layer entirely and directly connects:
Frontend WebSocket ←→ This Handler ←→ OpenAI Realtime API WebSocket

Features:
- Full Archie system prompt with agent injection
- Function tools: send_to_nested, send_to_claude_code, pause, reset
- Integration with nested team and Claude Code WebSockets
- Event recording to conversation database
"""

import asyncio
import logging
import os
import json
import websockets
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Optional, Any
from datetime import datetime, timezone

# Import conversation store
try:
    from ..utils.voice_conversation_store import store as conversation_store
except ImportError:
    from utils.voice_conversation_store import store as conversation_store

# Import config loader for agent loading
try:
    from ..config.config_loader import load_agents
except ImportError:
    from config.config_loader import load_agents

logger = logging.getLogger(__name__)
router = APIRouter()

# Archie system prompt (from realtime_voice.py)
VOICE_SYSTEM_PROMPT = (
    "You are Archie, the realtime voice interface for a multi‑agent team and self-editing Claude Code instance. "
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

# Function tool definitions for OpenAI Realtime API
FUNCTION_TOOLS = [
    {
        "type": "function",
        "name": "send_to_nested",
        "description": "Forward a task or question to the multi-agent nested team for research, analysis, or execution. Use this when the user requests work that requires agents with specialized capabilities (research, file management, engineering, database operations, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The task or question to send to the nested team"
                }
            },
            "required": ["text"]
        }
    },
    {
        "type": "function",
        "name": "send_to_claude_code",
        "description": "Send self-editing instructions to Claude Code for modifying this application's codebase. Use this when the user asks to change, add, fix, or improve code in the application itself.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The self-editing instruction for Claude Code"
                }
            },
            "required": ["text"]
        }
    },
    {
        "type": "function",
        "name": "pause",
        "description": "Pause the execution of the nested team. Use only when explicitly requested by the user or when a [TEAM CONTROL] message instructs you to pause.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "reset",
        "description": "Reset the state of the nested team. Use only when explicitly requested by the user or when a [TEAM CONTROL] message instructs you to reset.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# Active sessions: conversation_id -> session_state
sessions: Dict[str, dict] = {}

def _inject_available_agents(instructions: str, agent_name: str) -> str:
    """
    Inject available agents from the nested team into the voice system prompt.
    Replaces {{AVAILABLE_AGENTS}} placeholder with formatted list of agents.

    This loads our AutoGen-based agentic system agents (NOT Pipecat agents).
    """
    try:
        # Load all agents from our agentic system
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
            # Sub-agents can be either strings or AgentConfig objects
            if hasattr(sub_agent, 'name'):
                sub_agent_name = sub_agent.name
                description = sub_agent.description or "No description available"
                agent_descriptions.append(f"- **{sub_agent_name}**: {description}")
            else:
                # If it's a string, find the configuration
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

        # Replace placeholder
        updated_instructions = instructions.replace("{{AVAILABLE_AGENTS}}", agents_text)
        logger.info(f"[Archie] Injected {len(agent_descriptions)} agent descriptions into voice prompt")

        return updated_instructions

    except Exception as e:
        logger.error(f"[Archie] Error injecting available agents: {e}")
        return instructions.replace("{{AVAILABLE_AGENTS}}", "(Error loading agents information)")


@router.websocket("/realtime/pipecat-simple/ws/{conversation_id}")
async def pipecat_simple_websocket(websocket: WebSocket, conversation_id: str):
    """
    Simple WebSocket endpoint with full Archie integration

    This directly proxies between frontend and OpenAI while providing:
    - Full Archie system prompt with agent descriptions
    - Function tools for nested team and Claude Code control
    - Event forwarding from nested team and Claude Code
    """
    await websocket.accept()

    # Get query params
    voice = websocket.query_params.get("voice", "alloy")
    agent_name = websocket.query_params.get("agent_name", "MainConversation")

    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        await websocket.close(code=1008, reason="OPENAI_API_KEY not configured")
        return

    logger.info(f"[Archie] Starting session for conversation: {conversation_id}, agent: {agent_name}")

    # Ensure conversation exists
    existing_conv = conversation_store.get_conversation(conversation_id)
    if not existing_conv:
        now = datetime.now(timezone.utc).isoformat()
        with conversation_store._connection() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, name, created_at, updated_at, voice_model, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, f"Archie {conversation_id[:8]}", now, now, voice, "{}")
            )
        logger.info(f"[Archie] Created conversation: {conversation_id}")

    # Prepare system prompt with agent injection
    system_prompt = _inject_available_agents(VOICE_SYSTEM_PROMPT, agent_name)

    # WebSocket connections
    openai_ws = None
    nested_ws = None
    claude_code_ws = None

    # State for tracking
    session_state = {
        "conversation_id": conversation_id,
        "agent_name": agent_name,
        "nested_running": False,
        "claude_code_running": False
    }
    sessions[conversation_id] = session_state

    try:
        # Connect to OpenAI Realtime API
        openai_url = f"wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "OpenAI-Beta": "realtime=v1"
        }

        logger.info(f"[Archie] Connecting to OpenAI Realtime API...")
        openai_ws = await websockets.connect(openai_url, additional_headers=headers)
        logger.info(f"[Archie] ✓ Connected to OpenAI")

        # Send session configuration with Archie prompt and tools
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": system_prompt,
                "voice": voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 800
                },
                "tools": FUNCTION_TOOLS,
                "tool_choice": "auto",
                "temperature": 0.7,
                "max_response_output_tokens": 4096
            }
        }

        await openai_ws.send(json.dumps(session_config))
        logger.info(f"[Archie] ✓ Sent session configuration with {len(FUNCTION_TOOLS)} tools")

        # Helper function to send [TEAM] or [CODE] messages to OpenAI for narration
        async def forward_to_voice(source: str, message: str):
            """Forward a system message to OpenAI voice model"""
            try:
                # Send as conversation item (user role but system context)
                event = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": message
                            }
                        ]
                    }
                }
                await openai_ws.send(json.dumps(event))

                # Trigger response
                response_event = {"type": "response.create"}
                await openai_ws.send(json.dumps(response_event))

                logger.debug(f"[Archie] Forwarded to voice: {message[:100]}")
            except Exception as e:
                logger.error(f"[Archie] Failed to forward to voice: {e}")

        # Function call handlers
        async def handle_send_to_nested(text: str) -> str:
            """Send task to nested team"""
            nonlocal nested_ws
            logger.info(f"[Archie] send_to_nested called: {text[:100]}")

            try:
                # Connect to nested team if not already connected
                if nested_ws is None:
                    nested_url = f"ws://localhost:8000/api/runs/{agent_name}"
                    logger.info(f"[Archie] Connecting to nested team: {nested_url}")
                    nested_ws = await websockets.connect(nested_url)
                    logger.info(f"[Archie] ✓ Connected to nested team")

                    # Start listening for nested events
                    asyncio.create_task(listen_to_nested())

                # Send message to nested team
                await nested_ws.send(json.dumps({"type": "user_message", "data": text}))
                session_state["nested_running"] = True

                # Record event
                conversation_store.append_event(
                    conversation_id,
                    {"text": text},
                    source="controller",
                    event_type="tool_send_to_nested"
                )

                return "Task sent to nested team. Monitoring for updates..."

            except Exception as e:
                logger.error(f"[Archie] send_to_nested error: {e}")
                import traceback
                traceback.print_exc()
                return f"Error sending to nested team: {str(e)}"

        async def handle_send_to_claude_code(text: str) -> str:
            """Send instruction to Claude Code"""
            nonlocal claude_code_ws
            logger.info(f"[Archie] send_to_claude_code called: {text[:100]}")

            try:
                # Connect to Claude Code if not already connected
                if claude_code_ws is None:
                    claude_url = f"ws://localhost:8000/api/runs/ClaudeCode"
                    logger.info(f"[Archie] Connecting to Claude Code: {claude_url}")
                    claude_code_ws = await websockets.connect(claude_url)
                    logger.info(f"[Archie] ✓ Connected to Claude Code")

                    # Start listening for Claude Code events
                    asyncio.create_task(listen_to_claude_code())

                # Send message to Claude Code
                await claude_code_ws.send(json.dumps({"type": "user_message", "data": text}))
                session_state["claude_code_running"] = True

                # Record event
                conversation_store.append_event(
                    conversation_id,
                    {"text": text},
                    source="controller",
                    event_type="tool_send_to_claude_code"
                )

                return "Instruction sent to Claude Code. Monitoring for updates..."

            except Exception as e:
                logger.error(f"[Archie] send_to_claude_code error: {e}")
                return f"Error sending to Claude Code: {str(e)}"

        async def handle_pause() -> str:
            """Pause nested team"""
            logger.info(f"[Archie] pause called")
            # TODO: Implement pause mechanism
            return "Pause requested (not yet implemented)"

        async def handle_reset() -> str:
            """Reset nested team"""
            logger.info(f"[Archie] reset called")
            # TODO: Implement reset mechanism
            return "Reset requested (not yet implemented)"

        # Nested team event listener
        async def listen_to_nested():
            """Listen for events from nested team and forward to voice"""
            nonlocal nested_ws
            try:
                async for message in nested_ws:
                    try:
                        event = json.loads(message)
                        event_type = event.get("type", "")

                        # Record event to database
                        conversation_store.append_event(
                            conversation_id,
                            event,
                            source="nested",
                            event_type=event_type
                        )

                        # Forward significant events to voice
                        if event_type == "TextMessage":
                            data = event.get("data", {})
                            content = data.get("content", "")
                            source = data.get("source", "unknown")
                            await forward_to_voice("nested", f"[TEAM {source}] {content}")

                        elif event_type == "ToolCallExecutionEvent":
                            data = event.get("data", {})
                            tool_name = data.get("name", "tool")
                            result = data.get("result", "")
                            await forward_to_voice("nested", f"[TEAM Tool] {tool_name} completed")

                        elif event_type == "RUN_FINISHED":
                            await forward_to_voice("nested", "[RUN_FINISHED]")
                            session_state["nested_running"] = False

                        # Also forward to frontend
                        await websocket.send_text(json.dumps({
                            "type": "nested_event",
                            "event": event
                        }))

                    except json.JSONDecodeError:
                        logger.warning(f"[Archie] Failed to parse nested message")
                    except Exception as e:
                        logger.error(f"[Archie] Error processing nested event: {e}")

            except Exception as e:
                logger.error(f"[Archie] Nested listener error: {e}")
            finally:
                logger.info(f"[Archie] Nested listener stopped")

        # Claude Code event listener
        async def listen_to_claude_code():
            """Listen for events from Claude Code and forward to voice"""
            nonlocal claude_code_ws
            try:
                async for message in claude_code_ws:
                    try:
                        event = json.loads(message)
                        event_type = event.get("type", "")

                        # Record event to database
                        conversation_store.append_event(
                            conversation_id,
                            event,
                            source="claude_code",
                            event_type=event_type
                        )

                        # Forward significant events to voice
                        if event_type == "ToolCallRequestEvent":
                            data = event.get("data", {})
                            tool_name = data.get("name", "tool")
                            await forward_to_voice("claude_code", f"[CODE ClaudeCode] Using {tool_name}")

                        elif event_type == "TaskResult":
                            data = event.get("data", {})
                            outcome = data.get("outcome", "completed")
                            await forward_to_voice("claude_code", f"[CODE RESULT] {outcome}")
                            session_state["claude_code_running"] = False

                        # Also forward to frontend
                        await websocket.send_text(json.dumps({
                            "type": "claude_code_event",
                            "event": event
                        }))

                    except json.JSONDecodeError:
                        logger.warning(f"[Archie] Failed to parse Claude Code message")
                    except Exception as e:
                        logger.error(f"[Archie] Error processing Claude Code event: {e}")

            except Exception as e:
                logger.error(f"[Archie] Claude Code listener error: {e}")
            finally:
                logger.info(f"[Archie] Claude Code listener stopped")

        # Frontend to OpenAI proxy
        async def frontend_to_openai():
            """Forward audio from frontend to OpenAI"""
            try:
                while True:
                    data = await websocket.receive()

                    if 'bytes' in data:
                        # Binary audio data - send to OpenAI as audio append event
                        audio_bytes = data['bytes']
                        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                        event = {
                            "type": "input_audio_buffer.append",
                            "audio": audio_b64
                        }
                        await openai_ws.send(json.dumps(event))

                    elif 'text' in data:
                        # Text message - could be control messages
                        await openai_ws.send(data['text'])

            except WebSocketDisconnect:
                logger.info("[Archie] Frontend disconnected")
            except Exception as e:
                logger.error(f"[Archie] Error in frontend_to_openai: {e}")

        # OpenAI to frontend proxy with function call handling
        async def openai_to_frontend():
            """Forward responses from OpenAI to frontend and handle function calls"""
            try:
                async for message in openai_ws:
                    try:
                        event = json.loads(message)
                        event_type = event.get('type', '')

                        # Handle function calls
                        if event_type == 'response.function_call_arguments.done':
                            call_id = event.get('call_id', '')
                            function_name = event.get('name', '')
                            arguments_str = event.get('arguments', '{}')

                            logger.info(f"[Archie] Function call: {function_name}")

                            try:
                                args = json.loads(arguments_str)
                            except json.JSONDecodeError:
                                args = {}

                            # Execute function
                            result = ""
                            if function_name == "send_to_nested":
                                result = await handle_send_to_nested(args.get("text", ""))
                            elif function_name == "send_to_claude_code":
                                result = await handle_send_to_claude_code(args.get("text", ""))
                            elif function_name == "pause":
                                result = await handle_pause()
                            elif function_name == "reset":
                                result = await handle_reset()
                            else:
                                result = f"Unknown function: {function_name}"

                            # Send function result back to OpenAI
                            function_result = {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": call_id,
                                    "output": result
                                }
                            }
                            await openai_ws.send(json.dumps(function_result))

                            # Trigger response after function result
                            response_event = {"type": "response.create"}
                            await openai_ws.send(json.dumps(response_event))

                        # Handle audio responses
                        elif event_type == 'response.audio.delta':
                            audio_b64 = event.get('delta', '')
                            if audio_b64:
                                audio_bytes = base64.b64decode(audio_b64)
                                await websocket.send_bytes(audio_bytes)

                        # Handle transcriptions
                        elif event_type == 'conversation.item.input_audio_transcription.completed':
                            transcript = event.get('transcript', '')
                            if transcript:
                                await websocket.send_text(json.dumps({
                                    "type": "transcription",
                                    "text": transcript,
                                    "source": "user"
                                }))

                        # Handle text responses
                        elif event_type == 'response.text.delta':
                            text = event.get('delta', '')
                            if text:
                                await websocket.send_text(json.dumps({
                                    "type": "text",
                                    "text": text,
                                    "source": "assistant"
                                }))

                        # Handle errors
                        elif event_type in ['error', 'response.error']:
                            error = event.get('error', {})
                            logger.error(f"[Archie] OpenAI error: {error}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "error": error
                            }))

                        # Log interesting events
                        if event_type in ['session.created', 'session.updated', 'response.done', 'response.function_call_arguments.done']:
                            logger.info(f"[Archie] OpenAI event: {event_type}")

                    except json.JSONDecodeError:
                        logger.warning(f"[Archie] Failed to parse OpenAI message: {message[:100]}")
                    except Exception as e:
                        logger.error(f"[Archie] Error processing OpenAI message: {e}")

            except Exception as e:
                logger.error(f"[Archie] Error in openai_to_frontend: {e}")

        # Run both proxy tasks concurrently
        await asyncio.gather(
            frontend_to_openai(),
            openai_to_frontend()
        )

    except Exception as e:
        logger.error(f"[Archie] Error in session: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if openai_ws:
            await openai_ws.close()
        if nested_ws:
            await nested_ws.close()
        if claude_code_ws:
            await claude_code_ws.close()

        sessions.pop(conversation_id, None)
        logger.info(f"[Archie] Session ended for conversation: {conversation_id}")
