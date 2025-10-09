import os
import importlib
import logging
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState
from schemas import AgentConfig
from datetime import datetime, timezone
import asyncio
import json
import openai
import contextvars
from context import CURRENT_AGENT, get_current_agent

# --- Corrected AutoGen v0.4+ Imports ---
# Core components
from autogen_core import CancellationToken, FunctionCall, Image
# Models (including FunctionExecutionResult and ModelInfo)
from autogen_core.models import FunctionExecutionResult, ModelInfo
# AgentChat components
# Agent instantiation now handled via factory
# Corrected message/event imports
from autogen_agentchat.messages import (
    TextMessage,
    ToolCallRequestEvent,
    ToolCallExecutionEvent,
    BaseChatMessage,
    BaseAgentEvent
)
# Model clients
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.tools import FunctionTool
from agent_factory import create_agent_from_config

logger = logging.getLogger(__name__)

# Suppress noisy stack traces from expected cancellations inside autogen
class _DropCancelledErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            msg = ""
        # Drop logs that are just reporting asyncio.CancelledError from normal cancellation flows
        if "CancelledError" in msg:
            return False
        # Also check exception info when available
        exc = getattr(record, 'exc_info', None)
        if exc and isinstance(exc[1], Exception) and exc[1].__class__.__name__ == 'CancelledError':
            return False
        return True

for name in ("autogen_core", "autogen_core.events", "autogen_agentchat"):
    try:
        logging.getLogger(name).addFilter(_DropCancelledErrorFilter())
    except Exception:
        pass

# Helper function for recursive serialization
def _recursive_serialize(obj):
    """Recursively serialize objects to JSON-compatible format"""
    from datetime import datetime, date
    import uuid
    
    if hasattr(obj, 'model_dump'):
        try:
            # Try model_dump first (Pydantic v2)
            dumped = obj.model_dump()
            return _recursive_serialize(dumped)
        except Exception:
            try:
                # Fallback to dict() method (Pydantic v1 or other dict-like objects)
                dumped = obj.dict() if hasattr(obj, 'dict') else str(obj)
                return _recursive_serialize(dumped)
            except Exception:
                return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _recursive_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_recursive_serialize(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif hasattr(obj, '__dict__'):
        # Handle objects with __dict__ attribute
        try:
            return _recursive_serialize(obj.__dict__)
        except Exception:
            return str(obj)
    return str(obj)

# --- WebSocket Event Helper ---
async def send_event_to_websocket(websocket: WebSocket, event_type: str, data: any):
    if websocket.client_state != WebSocketState.CONNECTED:
        logger.warning(f"Attempted to send event '{event_type}' but WebSocket was not connected.")
        return
    try:
        # Always use recursive serialization to handle datetime and complex objects
        event_data = _recursive_serialize(data)

        payload = {
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        # Double-ensure the entire payload is serializable
        serialized_payload = _recursive_serialize(payload)
        await websocket.send_json(serialized_payload)
    except Exception as e:
        logger.error(f"Error sending event '{event_type}' via WebSocket: {e}")
        try:
            error_payload = {
                "type": "error", 
                "data": {"message": str(e)}, 
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await websocket.send_json(error_payload)
        except Exception:
            pass

# --- Main Agent Runner (v0.4+ Style) ---
async def run_agent_ws(agent_cfg: AgentConfig, all_tools: list[FunctionTool], websocket: WebSocket):
    logger.info(f"Starting run_agent_ws for agent: {agent_cfg.name} (v0.4+ style)")
    agent_tools = [t for t in all_tools if t.name in agent_cfg.tools]

    if len(agent_tools) != len(agent_cfg.tools):
        missing = set(agent_cfg.tools) - {t.name for t in agent_tools}
        await send_event_to_websocket(websocket, "warning", {"message": f"Agent '{agent_cfg.name}' configured with tools that couldn't be loaded: {missing}"})

    # --- Model Client Setup (v0.4+) ---
    model_client = None
    prov = agent_cfg.llm.provider.lower()
    model_name = agent_cfg.llm.model
    api_key = None
    try:
        if prov == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment.")
            try:
                model_client = OpenAIChatCompletionClient(model=model_name, api_key=api_key)
            except ValueError as ve:
                if "model_info is required" in str(ve):
                    openai_model_info = ModelInfo(
                        vision=True,
                        function_calling=True,
                        json_output=True,
                        family="openai",
                        structured_output=True
                    )
                    model_client = OpenAIChatCompletionClient(
                        model=model_name,
                        api_key=api_key,
                        base_url="https://api.openai.com/v1",
                        model_info=openai_model_info
                    )
                else:
                    raise ve
        elif prov == 'gemini':
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment.")
            gemini_model_info = ModelInfo(
                vision=True,
                function_calling=True,
                json_output=True,
                family="gemini",
                structured_output=True
            )
            model_client = OpenAIChatCompletionClient(
                model=model_name,
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                model_info=gemini_model_info
            )
        else:
            await send_event_to_websocket(websocket, "error", {"message": f"Unsupported or unavailable LLM provider: {prov}"})
            await websocket.close()
            return
    except Exception as e:
        await send_event_to_websocket(websocket, "error", {"message": f"Error setting up LLM Client: {str(e)}"})
        await websocket.close()
        return

    # --- Agent Instantiation via factory ---
    try:
        assistant = create_agent_from_config(agent_cfg, all_tools, model_client)
        CURRENT_AGENT.set(assistant)

        # Initialize Memory agent if this is the Memory agent
        if agent_cfg.name == "Memory":
            try:
                # Import and call the initialization function
                from tools.memory import initialize_memory_agent
                initialize_memory_agent()
                logger.info("Memory agent initialized with short-term memory injection")
            except Exception as init_error:
                logger.warning(f"Failed to initialize Memory agent: {init_error}")
                # Don't fail the whole agent creation, just log the warning

    except Exception as e:
        await send_event_to_websocket(websocket, "error", {"message": f"Failed to create agent: {e}"})
        await websocket.close()
        if model_client and hasattr(model_client, 'close'):
            await model_client.close()
        return

    # --- Multi-run loop with cancel and incremental user messages ---
    pending_run: str | None = None
    pending_user_messages: list[str] = []

    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            # Determine next task to run:
            if pending_run is not None:
                task_message_content = pending_run
                pending_run = None
            elif pending_user_messages:
                # Incremental turn from queued user messages
                task_message_content = pending_user_messages.pop(0)
            else:
                # Wait for next command
                try:
                    cmd = await websocket.receive_json()
                except WebSocketDisconnect:
                    break
                ctype = (cmd.get("type") or "").lower()
                if ctype == "run":
                    task_message_content = (cmd.get("data") or "").strip()
                    if not task_message_content:
                        # Try default; if not present, inform and continue without error
                        default_prompt = getattr(agent_cfg, 'prompt', None)
                        default_user = (getattr(default_prompt, 'user', None) or '').strip() if default_prompt else ''
                        if default_user:
                            task_message_content = default_user
                        else:
                            await send_event_to_websocket(websocket, "system", {"message": "Run requested without a task. Awaiting non-empty task or user_message."})
                            continue
                elif ctype == "user_message":
                    # Start a turn immediately when idle, but ignore empty/whitespace
                    msg = (cmd.get("data") or "").strip()
                    if not msg:
                        await send_event_to_websocket(websocket, "system", {"message": "Ignored empty user_message."})
                        continue
                    task_message_content = msg
                elif ctype == "cancel":
                    await send_event_to_websocket(websocket, "system", {"message": "No active run to cancel."})
                    continue
                else:
                    await send_event_to_websocket(websocket, "error", {"message": "Unknown command. Use 'run' or 'user_message'."})
                    continue

            await send_event_to_websocket(websocket, "system", {"message": f"Initiating agent run with task: {str(task_message_content)[:100]}..."})

            cancellation_token = CancellationToken()
            message_count = 0
            stream_finished_naturally = False

            # Control listener: cancel, queue run (preemptive), queue user_message (incremental)
            async def control_listener():
                nonlocal pending_run, pending_user_messages
                try:
                    while True:
                        ctrl = await websocket.receive_json()
                        ctype = (ctrl.get("type") or "").lower()
                        if ctype == "cancel":
                            cancellation_token.cancel()
                            await send_event_to_websocket(websocket, "system", {"message": "Cancellation requested."})
                        elif ctype == "run":
                            pending_run = (ctrl.get("data") or "").strip()
                            if not pending_run:
                                pending_run = None
                                await send_event_to_websocket(websocket, "system", {"message": "Ignored empty run request."})
                            else:
                                cancellation_token.cancel()
                                await send_event_to_websocket(websocket, "system", {"message": "New run requested. Current run will stop and restart."})
                        elif ctype == "user_message":
                            # Queue incremental turn without cancelling current run; ignore empty
                            msg = (ctrl.get("data") or "").strip()
                            if msg:
                                pending_user_messages.append(msg)
                                await send_event_to_websocket(websocket, "system", {"message": "User message queued for next turn."})
                            else:
                                await send_event_to_websocket(websocket, "system", {"message": "Ignored empty user_message."})
                        else:
                            # Ignore other messages
                            pass
                except (WebSocketDisconnect, asyncio.CancelledError):
                    # Normal cancellation when stream finishes or WebSocket disconnects
                    pass
                except Exception as e:
                    logger.debug(f"Control listener ended: {e}")

            listener_task = asyncio.create_task(control_listener())

            try:
                stream = assistant.run_stream(task=task_message_content, cancellation_token=cancellation_token)
                async for event in stream:
                    event_type = event.__class__.__name__.lower()
                    # Use recursive serialization for all stream events
                    await send_event_to_websocket(websocket, event_type, event)
                    if isinstance(event, (BaseChatMessage, ToolCallRequestEvent, ToolCallExecutionEvent)):
                        message_count += 1
                stream_finished_naturally = True
            except asyncio.CancelledError:
                logger.info("Agent stream task cancelled.")
                # If we didn’t explicitly cancel via our token, treat this as a natural finish
                try:
                    if not cancellation_token.is_canceled:
                        stream_finished_naturally = True
                except Exception:
                    pass
            except WebSocketDisconnect:
                break
            except Exception as e:
                err_str = str(e)
                if isinstance(e, openai.RateLimitError) or 'RESOURCE_EXHAUSTED' in err_str or 'QuotaFailure' in err_str:
                    await send_event_to_websocket(websocket, "error", {"message": "Quota exceeded, please check your plan or try again later."})
                    break
                if isinstance(e, openai.NotFoundError) or 'model_not_found' in err_str.lower():
                    await send_event_to_websocket(websocket, "error", {"message": "Specified model does not exist or you do not have access to it."})
                    break
                await send_event_to_websocket(websocket, "error", {"message": f"Error during agent run: {str(e)}"})
            finally:
                if not listener_task.done():
                    listener_task.cancel()
                    try:
                        await listener_task
                    except (asyncio.CancelledError, Exception):
                        # Properly handle cancellation and any other exceptions
                        pass
                if stream_finished_naturally:
                    await send_event_to_websocket(websocket, "system", {"message": "Agent run finished."})
                else:
                    await send_event_to_websocket(websocket, "system", {"message": "Agent run interrupted."})
            # Loop continues; queued user messages will start next, else wait for command
    finally:
        CURRENT_AGENT.set(None)
        if model_client and hasattr(model_client, 'close'):
            try:
                await model_client.close()
            except Exception:
                pass
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except Exception:
                pass