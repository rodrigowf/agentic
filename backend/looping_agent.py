import asyncio
import pprint
from typing import AsyncIterator, List, Sequence

# Core autogen components
from autogen_core import CancellationToken

# AgentChat specific components
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base._chat_agent import Response # Import Response
from autogen_agentchat.messages import (
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    TextMessage,
    ToolCallExecutionEvent
)

# Default max iterations
MAX_ITERS = 20

class LoopingAssistantAgent(AssistantAgent):
    """
    An AssistantAgent that overrides run_stream to loop its core logic
    (calling the LLM, handling tools) until its own output contains "TERMINATE".
    """
    async def run_stream(
        self,
        task: str,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator:
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        # Initialize history with the initial user task
        history: List[BaseChatMessage] = [TextMessage(content=task, source="user")]
        iters = 0

        while True:
            iters += 1
            if iters > MAX_ITERS:
                yield TextMessage(content=f"[SYSTEM] Safety stop: max iterations ({MAX_ITERS}) reached.", source="system").model_dump()
                break

            last_assistant_text_message_content: str | None = None
            accumulated_assistant_chunks: str = ""
            current_iteration_new_history: List[BaseChatMessage] = []

            try:
                async for evt in super().on_messages_stream(messages=history, cancellation_token=cancellation_token):
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
                        for result in evt.content:
                            msg = TextMessage(content=str(result.content), source="tools")
                            current_iteration_new_history.append(msg)
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
