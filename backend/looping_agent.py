from autogen_core import CancellationToken
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage, BaseChatMessage, ToolCallExecutionEvent
from typing import AsyncIterator

class LoopingAssistantAgent(AssistantAgent):
    async def run_stream(
        self,
        task: str,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator:
        # Simplified loop without token isolation
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        history: list[BaseChatMessage] = [TextMessage(content=task, source="user")]
        MAX_ITERS = 20
        iters = 0

        while True:
            iters += 1
            if iters > MAX_ITERS:
                yield TextMessage(content="[SYSTEM] Safety stop: max iterations reached.", source="system")
                break

            last_assistant_msg = None
            # Collect tool results to append to history
            tool_results_to_append = []

            async for evt in self.on_messages_stream(messages=history, cancellation_token=cancellation_token):
                yield evt
                # After tool execution, convert result to TextMessage for context
                if isinstance(evt, ToolCallExecutionEvent):
                    for result in evt.content:
                        msg = TextMessage(content=result.content, source="tools")
                        history.append(msg)
                # Track assistant text messages
                if isinstance(evt, TextMessage):
                    history.append(evt)
                    last_assistant_msg = evt

            # If assistant signaled termination, stop
            if last_assistant_msg and "TERMINATE" in last_assistant_msg.content:
                break
            # Else continue for next iteration
        # end while
