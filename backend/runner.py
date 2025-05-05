import os
import importlib
import logging
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState
from schemas import AgentConfig
from datetime import datetime
import asyncio
import json
import openai

# --- Corrected AutoGen v0.4+ Imports ---
# Core components
from autogen_core import CancellationToken, FunctionCall, Image
# Models (including FunctionExecutionResult and ModelInfo)
from autogen_core.models import FunctionExecutionResult, ModelInfo
# AgentChat components
from looping_agent import LoopingAssistantAgent
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
# Tools
from autogen_core.tools import FunctionTool

logger = logging.getLogger(__name__)

# Helper function for recursive serialization
def _recursive_serialize(obj):
    """Recursively serialize objects to JSON-compatible format"""
    if hasattr(obj, 'model_dump'):
        try:
            return obj.model_dump()
        except Exception:
            # Fallback for older pydantic versions or other model_dump implementations
            return obj.dict() if hasattr(obj, 'dict') else str(obj)
    elif isinstance(obj, dict):
        return {k: _recursive_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_recursive_serialize(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    # Handle any other types by converting to string
    return str(obj)

# --- WebSocket Event Helper ---
async def send_event_to_websocket(websocket: WebSocket, event_type: str, data: any):
    if websocket.client_state != WebSocketState.CONNECTED:
        logger.warning(f"Attempted to send event '{event_type}' but WebSocket was not connected.")
        return
    try:
        # Serialize data into JSON-compatible structure
        if isinstance(data, dict):
            event_data = data
        elif hasattr(data, 'model_dump'):
            event_data = data.model_dump()
        else:
            event_data = _recursive_serialize(data)

        payload = {
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await websocket.send_json(payload)
        logger.debug(f"Sent event '{event_type}' with payload")
    except Exception as e:
        logger.error(f"Error sending event '{event_type}' via WebSocket: {e}")
        # Fallback minimal payload
        try:
            error_payload = {"type": "error", "data": {"message": str(e)}, "timestamp": datetime.utcnow().isoformat() + "Z"}
            await websocket.send_json(error_payload)
        except Exception:
            pass

# --- Main Agent Runner (v0.4+ Style) ---
async def run_agent_ws(agent_cfg: AgentConfig, all_tools: list[FunctionTool], websocket: WebSocket):
    logger.info(f"Starting run_agent_ws for agent: {agent_cfg.name} (v0.4+ style)")
    agent_tools = [t for t in all_tools if t.name in agent_cfg.tools]
    logger.info(f"Filtered tools for agent '{agent_cfg.name}': {[t.name for t in agent_tools]}")

    if len(agent_tools) != len(agent_cfg.tools):
        missing = set(agent_cfg.tools) - {t.name for t in agent_tools}
        warning_msg = f"Agent '{agent_cfg.name}' configured with tools that couldn't be loaded: {missing}"
        logger.warning(warning_msg)
        await send_event_to_websocket(websocket, "warning", {"message": warning_msg})

    # --- Model Client Setup (v0.4+) ---
    model_client = None
    prov = agent_cfg.llm.provider.lower()
    model_name = agent_cfg.llm.model
    api_key = None
    logger.info(f"Attempting to create model client for provider: {prov}, model: {model_name}")
    try:
        if prov == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment.")
            try:
                # First attempt: Initialize directly (works for known models)
                model_client = OpenAIChatCompletionClient(model=model_name, api_key=api_key)
                logger.info(f"Using OpenAIChatCompletionClient for known OpenAI model.")
            except ValueError as ve:
                # Second attempt: If model_info is required (unknown/new model)
                if "model_info is required" in str(ve):
                    logger.warning(f"Model '{model_name}' not recognized by autogen_ext, providing default model_info.")
                    # Define default model_info assuming modern capabilities
                    # Adjust these based on actual o4-mini capabilities if needed
                    openai_model_info = ModelInfo(
                        vision=True,
                        function_calling=True,
                        json_output=True,
                        family="openai", # Specify family as openai
                        structured_output=True
                    )
                    openai_base_url = "https://api.openai.com/v1" # Standard OpenAI base URL
                    model_client = OpenAIChatCompletionClient(
                        model=model_name,
                        api_key=api_key,
                        base_url=openai_base_url,
                        model_info=openai_model_info
                    )
                    logger.info(f"Using OpenAIChatCompletionClient with explicit model_info for OpenAI model.")
                else:
                    # Re-raise other ValueErrors
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
            gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"  # remove trailing slash
            logger.info(f"Using OpenAIChatCompletionClient for Gemini model via compatible endpoint: {gemini_base_url}")
            model_client = OpenAIChatCompletionClient(
                model=model_name,
                api_key=api_key,
                base_url=gemini_base_url,
                model_info=gemini_model_info
            )

        else:
            error_msg = f"Unsupported or unavailable LLM provider: {prov}"
            logger.error(error_msg)
            await send_event_to_websocket(websocket, "error", {"message": error_msg})
            await websocket.close()
            return

        if model_client is None:
             raise ValueError(f"Failed to initialize model client for provider: {prov}")

        logger.info(f"Successfully created model client for {prov}")

    except Exception as e:
        logger.exception(f"Error setting up LLM Client for agent '{agent_cfg.name}': {e}")
        await send_event_to_websocket(websocket, "error", {"message": f"Error setting up LLM Client: {str(e)}"})
        await websocket.close()
        return

    # --- Agent Instantiation (v0.4+) ---
    logger.info(f"Instantiating LoopingAssistantAgent: {agent_cfg.name}")
    try:
        assistant = LoopingAssistantAgent(
            name=agent_cfg.name,
            system_message=agent_cfg.prompt.system,
            model_client=model_client,
            tools=agent_tools,
            reflect_on_tool_use=agent_cfg.reflect_on_tool_use,
        )
        logger.info(f"Agent '{agent_cfg.name}' instantiated successfully using LoopingAssistantAgent.")

    except Exception as e:
        logger.exception(f"Error creating agent instance '{agent_cfg.name}': {e}")
        await send_event_to_websocket(websocket, "error", {"message": f"Error creating agent instance: {str(e)}"})
        await websocket.close()
        if model_client and hasattr(model_client, 'close'):
            await model_client.close()
        return

    # --- Run Interaction using LoopingAssistantAgent.run_stream ---
    cancellation_token = CancellationToken()
    message_count = 0 # Initialize message counter
    stream_finished_naturally = False
    error_occurred = False  # flag to skip final messaging on errors

    try:
        logger.info(f"Waiting for initial 'run' message from client for agent '{agent_cfg.name}'")
        initial_message_data = await websocket.receive_json()
        logger.info(f"Received initial message: {initial_message_data}")

        if initial_message_data.get("type") != "run":
            error_msg = "Expected 'run' message type to start agent"
            logger.error(error_msg)
            await send_event_to_websocket(websocket, "error", {"message": error_msg})
            await websocket.close()
            return

        task_message_content = initial_message_data.get("data")
        if not task_message_content:
            task_message_content = agent_cfg.prompt.user
            if not task_message_content:
                error_msg = "No task message provided in 'run' message and agent config's 'prompt.user' is also empty."
                logger.error(error_msg)
                await send_event_to_websocket(websocket, "error", {"message": error_msg})
                await websocket.close()
                return
            else:
                logger.info(f"Using default task from agent config: {task_message_content[:100]}...")
        else:
            logger.info(f"Using task from client message: {task_message_content[:100]}...")

        await send_event_to_websocket(websocket, "system", {"message": f"Initiating agent run with task: {task_message_content[:100]}..."})

        # Use assistant.run_stream with the task content
        stream = assistant.run_stream(task=task_message_content, cancellation_token=cancellation_token)

        # Initialize message count (run_stream doesn't start with the task message in the count)
        message_count = 0

        async for event in stream:
            event_type = event.__class__.__name__.lower()
            await send_event_to_websocket(websocket, event_type, event)

            # Increment message count for relevant events
            if isinstance(event, (BaseChatMessage, ToolCallRequestEvent, ToolCallExecutionEvent)):
                message_count += 1

        # If the loop finishes without exceptions, the stream ended naturally.
        stream_finished_naturally = True

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client during run for agent '{agent_cfg.name}'.")
        cancellation_token.cancel()
    except asyncio.CancelledError:
        # This might still happen if the websocket disconnects or another external cancellation occurs
        logger.info(f"Agent run for '{agent_cfg.name}' was cancelled externally.")
        await send_event_to_websocket(websocket, "system", {"message": "Agent run cancelled externally."})
    except Exception as e:
        # Quota error detection for both OpenAI and Gemini
        err_str = str(e)
        if isinstance(e, openai.RateLimitError) or 'RESOURCE_EXHAUSTED' in err_str or 'QuotaFailure' in err_str:
            logger.error(f"Quota exceeded for agent '{agent_cfg.name}': {e}")
            await send_event_to_websocket(websocket, "error", {"message": "Quota exceeded, please check your plan or try again later."})
            await websocket.close()
            return
        # Handle model not found errors
        if isinstance(e, openai.NotFoundError) or 'model_not_found' in err_str.lower():
            logger.error(f"Model not found or unauthorized for agent '{agent_cfg.name}': {e}")
            await send_event_to_websocket(websocket, "error", {"message": "Specified model does not exist or you do not have access to it."})
            await websocket.close()
            return
        # Fallback for other exceptions
        logger.exception(f"Error during agent run/streaming for '{agent_cfg.name}': {e}.")
        try:
            await send_event_to_websocket(websocket, "error", {"message": f"Error during agent run: {str(e)}"})
        except Exception as send_err:
            logger.error(f"Failed to send error details over WebSocket after run error: {send_err}")
    finally:
        if not error_occurred:
            if stream_finished_naturally:
                 logger.info(f"Agent stream finished naturally for '{agent_cfg.name}'. Total messages/tool events processed by runner: {message_count}")
                 await send_event_to_websocket(websocket, "system", {"message": "Agent run finished."})
            else:
                 # Log if the stream ended due to cancellation/error
                 logger.info(f"Agent stream processing stopped for '{agent_cfg.name}'. Total messages/tool events processed before stop: {message_count}")

        logger.info(f"Agent run processing finished or errored for {agent_cfg.name}.")
        if model_client and hasattr(model_client, 'close'):
            try:
                await model_client.close()
                logger.info(f"Closed model client for agent '{agent_cfg.name}'.")
            except Exception as close_err:
                logger.error(f"Error closing model client for agent '{agent_cfg.name}': {close_err}")