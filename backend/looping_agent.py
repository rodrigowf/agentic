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
        """
        Runs the agent's logic in a loop until the termination condition ("TERMINATE" in output) is met.
        Streams all events generated during the process.
        """
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        # Initialize history with the initial user task
        history: List[BaseChatMessage] = [TextMessage(content=task, source="user")]
        iters = 0

        while True:
            iters += 1
            if iters > MAX_ITERS:
                yield TextMessage(content=f"[SYSTEM] Safety stop: max iterations ({MAX_ITERS}) reached.", source="system")
                break

            # --- Variables to capture the final assistant message of THIS iteration ---
            # Stores content if a complete TextMessage from assistant is received
            last_assistant_text_message_content: str | None = None
            # Accumulates content from streaming chunks potentially from the assistant
            accumulated_assistant_chunks: str = ""
            # Stores messages generated within this iteration to be added to history *after* the iteration
            current_iteration_new_history: List[BaseChatMessage] = []

            try:
                # --- Execute one agent turn using the parent's on_messages_stream ---
                # This handles LLM calls, tool requests, and tool execution based on the current history
                async for evt in super().on_messages_stream(messages=history, cancellation_token=cancellation_token):
                    yield evt  # Yield the event immediately to the caller

                    # --- Process event for history update and termination check ---

                    # 1. Tool Execution Results: Add to history for the *next* turn
                    if isinstance(evt, ToolCallExecutionEvent):
                        # Convert tool results to TextMessages for history context
                        for result in evt.content:
                            # Use str(result.content) for safety, assuming it's the tool output string
                            msg = TextMessage(content=str(result.content), source="tools") # Source 'tools' as per convention
                            current_iteration_new_history.append(msg)
                        # Reset assistant message trackers, as assistant will generate a new response after tools
                        accumulated_assistant_chunks = ""
                        last_assistant_text_message_content = None

                    # 2. Assistant's Complete TextMessage: Capture content, mark for history
                    elif isinstance(evt, Response) and evt.chat_message.source == self.name:
                        if evt.chat_message.content:
                            last_assistant_text_message_content = evt.chat_message.content
                            current_iteration_new_history.append(evt.chat_message) # Add the complete message itself
                            accumulated_assistant_chunks = "" # Clear chunk buffer, complete message received

                    # 3. Assistant's Streaming Chunks: Accumulate content
                    # Assuming chunks after tool calls / before final TextMessage are assistant's response
                    elif isinstance(evt, ModelClientStreamingChunkEvent):
                         if evt.content:
                             accumulated_assistant_chunks += evt.content
                    
                    # Note: ToolCallRequestEvent is typically handled internally by on_messages_stream
                    # leading to ToolCallExecutionEvent, so we don't need to handle it explicitly here for history/termination.

            except asyncio.CancelledError:
                yield TextMessage(content="[SYSTEM] Operation cancelled.", source="system")
                # Re-raise to ensure cancellation propagates if needed
                raise

            # --- Post-Iteration Processing ---

            # Determine the final assistant content produced in *this* iteration
            final_content_this_iteration = last_assistant_text_message_content if last_assistant_text_message_content is not None else accumulated_assistant_chunks

            # If we only got chunks (no final TextMessage), add the accumulated message to history
            if accumulated_assistant_chunks and last_assistant_text_message_content is None:
                 chunk_message = TextMessage(content=accumulated_assistant_chunks, source=self.name)
                 # Avoid adding duplicate if the last message in new_history is already this chunk message
                 # (This is unlikely given the flow, but safer)
                 if not current_iteration_new_history or current_iteration_new_history[-1] != chunk_message:
                    current_iteration_new_history.append(chunk_message)

            # Append all messages generated/processed in this iteration to the main history for the *next* iteration
            history.extend(current_iteration_new_history)

            # Optional: Debugging print for the final content checked
            if final_content_this_iteration:
                 pprint.pprint(f"LoopingAgent - Iteration {iters} - Final Assistant Content: '{final_content_this_iteration}'", indent=2)

            # --- Check Termination Condition ---
            if final_content_this_iteration and "TERMINATE" in final_content_this_iteration:
                pprint.pprint(f"LoopingAgent - Iteration {iters} - Termination condition 'TERMINATE' found.")
                break # Exit the while loop

            # Small delay to prevent overly tight loops in case of immediate responses without termination
            await asyncio.sleep(0.1)
            # --- End of While Loop ---

        pprint.pprint(f"LoopingAgent - Loop finished after {iters} iterations.")
