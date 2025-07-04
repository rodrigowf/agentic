import asyncio
import json
import logging
import pprint
from typing import AsyncIterator, List, Sequence, Optional, Tuple

# Core autogen components
from autogen_core import CancellationToken, FunctionCall
from autogen_core import Image as AGImage  # added to detect Image outputs
from autogen_core.models import FunctionExecutionResult as CoreFunctionExecutionResult  # added for fake tool result construction

# AgentChat specific components
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base._chat_agent import Response # Import Response
from autogen_agentchat.messages import (
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    TextMessage,
    ToolCallExecutionEvent,
    MultiModalMessage,  # added for multimodal support
    FunctionExecutionResult,  # added for overriding tool execution
)
from autogen_core.models import FunctionExecutionResult as CoreFunctionExecutionResult  # for creating fake execution results

logger = logging.getLogger(__name__)

# Default max iterations
DEFAULT_MAX_ITERS = 40 # Renamed from MAX_ITERS

class LoopingAssistantAgent(AssistantAgent):
    """
    An AssistantAgent that overrides run_stream to loop its core logic
    (calling the LLM, handling tools) until its own output contains "TERMINATE".
    """
    def __init__(self, *args, max_consecutive_auto_reply: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_consecutive_auto_reply = max_consecutive_auto_reply if max_consecutive_auto_reply is not None else DEFAULT_MAX_ITERS

    @classmethod
    async def _execute_tool_call(
        cls, 
        tool_call: FunctionCall, 
        workbench,  # Workbench type
        handoff_tools,  # List[BaseTool[Any, Any]]
        agent_name: str,
        cancellation_token: CancellationToken
    ) -> Tuple[FunctionCall, FunctionExecutionResult]:
        """
        Override the base _execute_tool_call method to preserve AGImage objects
        instead of converting them to text with result.to_text().
        """
        arguments = tool_call.arguments
        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        # Call the tool through the workbench
        result = await workbench.call_tool(
            name=tool_call.name,
            arguments=arguments,
            cancellation_token=cancellation_token,
        )
        
        logger.info(f"Tool {tool_call.name} result type: {type(result)}")
        logger.info(f"Tool {tool_call.name} result.content type: {type(result.content) if hasattr(result, 'content') else 'no content attr'}")
        logger.info(f"Tool {tool_call.name} result.content value: {result.content if hasattr(result, 'content') else 'no content'}")
        
        # Check if the result contains AGImage objects
        if hasattr(result, 'content') and isinstance(result.content, AGImage):
            # Preserve the AGImage object instead of converting to text
            content = result.content
            logger.info(f"✅ Preserving AGImage object from tool {tool_call.name}")
        elif hasattr(result, 'content') and isinstance(result.content, list):
            # Check if it's a list containing AGImage objects
            has_images = any(isinstance(item, AGImage) for item in result.content)
            if has_images:
                content = result.content
                logger.info(f"✅ Preserving AGImage objects in list from tool {tool_call.name}")
            else:
                content = result.to_text()
                logger.info(f"❌ Converting non-image list to text from tool {tool_call.name}")
        else:
            # Default behavior for non-image results
            content = result.to_text()
            logger.info(f"❌ Converting non-image result to text from tool {tool_call.name}")

        execution_result = FunctionExecutionResult(
            content=content,
            call_id=tool_call.id,
            is_error=result.is_error,
            name=tool_call.name,
        )
        
        logger.info(f"Final FunctionExecutionResult content type: {type(execution_result.content)}")
        logger.info(f"Final FunctionExecutionResult content: {execution_result.content}")

        return (tool_call, execution_result)



    async def on_messages_stream(
        self, 
        messages: Sequence[BaseChatMessage], 
        cancellation_token: CancellationToken
    ) -> AsyncIterator:
        """Override to intercept and handle image tool results properly."""
        async for evt in super().on_messages_stream(messages=messages, cancellation_token=cancellation_token):
            # Intercept ToolCallExecutionEvent to handle images
            if isinstance(evt, ToolCallExecutionEvent):
                logger.info(f"🔍 Intercepting ToolCallExecutionEvent with {len(evt.content)} results")
                
                # Check if any tool results contain AGImage objects
                has_images = False
                for result in evt.content:
                    if isinstance(result.content, AGImage):
                        has_images = True
                        logger.info(f"✅ Found AGImage in tool result: {result.name}")
                        break
                    elif isinstance(result.content, list) and any(isinstance(item, AGImage) for item in result.content):
                        has_images = True
                        logger.info(f"✅ Found AGImage list in tool result: {result.name}")
                        break
                
                if has_images:
                    # Add a MultiModalMessage to the conversation history for images
                    for result in evt.content:
                        if isinstance(result.content, AGImage):
                            # Single image
                            multimodal_msg = MultiModalMessage(
                                content=[result.content], 
                                source="tools"
                            )
                            messages = list(messages) + [multimodal_msg]
                            logger.info(f"📷 Added single AGImage to conversation history from {result.name}")
                        elif isinstance(result.content, list) and any(isinstance(item, AGImage) for item in result.content):
                            # List of images
                            images = [item for item in result.content if isinstance(item, AGImage)]
                            if images:
                                multimodal_msg = MultiModalMessage(
                                    content=images, 
                                    source="tools"
                                )
                                messages = list(messages) + [multimodal_msg]
                                logger.info(f"📷 Added {len(images)} AGImages to conversation history from {result.name}")
            
            yield evt

    async def run_stream(
        self,
        task: BaseChatMessage | str,  # support multimodal initial task
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        # Initialize history with the initial user task, supporting multimodal
        if isinstance(task, BaseChatMessage):
            history: List[BaseChatMessage] = [task]
        else:
            history = [TextMessage(content=str(task), source="user")]
        iters = 0

        while True:
            iters += 1
            if iters > self.max_consecutive_auto_reply: # Changed from MAX_ITERS to self.max_consecutive_auto_reply
                yield TextMessage(content=f"[SYSTEM] Safety stop: max iterations ({self.max_consecutive_auto_reply}) reached.", source="system").model_dump()
                break

            last_assistant_text_message_content: str | None = None
            accumulated_assistant_chunks: str = ""
            current_iteration_new_history: List[BaseChatMessage] = []

            try:
                async for evt in self.on_messages_stream(messages=history, cancellation_token=cancellation_token):
                    # Convert event to proper JSON format before yielding
                    if isinstance(evt, (TextMessage, ModelClientStreamingChunkEvent, ToolCallExecutionEvent)):
                        yield evt.model_dump()
                    elif isinstance(evt, Response):
                        if evt.chat_message and evt.chat_message.source == self.name:
                            if evt.chat_message.content:
                                last_assistant_text_message_content = evt.chat_message.content
                                current_iteration_new_history.append(evt.chat_message)
                                accumulated_assistant_chunks = ""
                        yield evt.chat_message.model_dump() if evt.chat_message else evt.model_dump()
                    else:
                        # For any other event types, try model_dump() or convert to dict
                        yield evt.model_dump() if hasattr(evt, 'model_dump') else evt.__dict__

                    if isinstance(evt, ToolCallExecutionEvent):
                        # Tool execution events now handled in our overridden on_messages_stream
                        accumulated_assistant_chunks = ""
                        last_assistant_text_message_content = None
                    elif isinstance(evt, ModelClientStreamingChunkEvent):
                        if evt.content:
                            accumulated_assistant_chunks += evt.content

            except asyncio.CancelledError:
                yield TextMessage(content="[SYSTEM] Operation cancelled.", source="system").model_dump()
                raise

            final_content_this_iteration = (
                last_assistant_text_message_content 
                if last_assistant_text_message_content is not None 
                else accumulated_assistant_chunks
            )

            if accumulated_assistant_chunks and last_assistant_text_message_content is None:
                chunk_message = TextMessage(content=accumulated_assistant_chunks, source=self.name)
                if not current_iteration_new_history or current_iteration_new_history[-1] != chunk_message:
                    current_iteration_new_history.append(chunk_message)

            history.extend(current_iteration_new_history)

            if final_content_this_iteration and "TERMINATE" in final_content_this_iteration:
                break

            await asyncio.sleep(0.1)
