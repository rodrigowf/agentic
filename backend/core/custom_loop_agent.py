"""
Module: custom_loop_agent

Provides a CustomLoopAgent that processes model output through a configurable
output handler function. The handler can save files, take screenshots, run code,
etc., and return feedback (text + images) to the model for iterative refinement.

This is useful for:
- HTML generation with visual feedback
- Code execution with output verification
- Document generation with preview
- Any task requiring iterative output refinement
"""

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator, Callable, Dict, List, Optional, Any

from autogen_core import CancellationToken, Image as AGImage
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base._chat_agent import Response
from autogen_agentchat.messages import (
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    TextMessage,
    MultiModalMessage,
)

from handlers import OutputHandlerResult, load_handler

logger = logging.getLogger(__name__)

# Default max iterations
DEFAULT_MAX_ITERATIONS = 5


class CustomLoopAgent(AssistantAgent):
    """
    An agent that processes its output through a custom handler each iteration.

    The handler receives the model's text output and can:
    - Save files (HTML, code, documents, etc.)
    - Run external tools (screenshot, code execution, etc.)
    - Return feedback text and images to the model

    The loop continues until:
    - The handler returns should_continue=False (e.g., "DONE" signal detected)
    - Max iterations reached
    - Cancellation requested

    Attributes:
        output_handler: Function to process each model output
        output_handler_config: Configuration passed to the handler
        max_iterations: Maximum number of iterations before stopping
    """

    def __init__(
        self,
        *args,
        output_handler: Optional[str] = None,
        output_handler_config: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize the CustomLoopAgent.

        Args:
            output_handler: Handler function path (e.g., 'html_display.process_output')
            output_handler_config: Configuration dict passed to the handler
            max_iterations: Maximum iterations before stopping (default: 5)
            *args, **kwargs: Arguments passed to AssistantAgent
        """
        super().__init__(*args, **kwargs)

        self.output_handler_path = output_handler
        self.output_handler_config = output_handler_config or {}
        self.max_iterations = max_iterations if max_iterations is not None else DEFAULT_MAX_ITERATIONS

        # Load the handler function
        self._handler_func: Optional[Callable] = None
        if output_handler:
            try:
                self._handler_func = load_handler(output_handler)
                logger.info(f"Loaded output handler: {output_handler}")
            except Exception as e:
                logger.error(f"Failed to load output handler '{output_handler}': {e}")
                raise

    def _load_image_as_agimage(self, image_path: str) -> Optional[AGImage]:
        """Load an image file as an AGImage object for multimodal input."""
        try:
            path = Path(image_path)
            if path.exists():
                return AGImage.from_file(path)
            else:
                logger.warning(f"Image file not found: {image_path}")
                return None
        except Exception as e:
            logger.warning(f"Failed to load image {image_path}: {e}")
            return None

    def _create_feedback_message(
        self,
        result: OutputHandlerResult,
        source: str = "system"
    ) -> BaseChatMessage:
        """
        Create a feedback message from handler result.

        If images are present, creates a MultiModalMessage.
        Otherwise, creates a TextMessage.
        """
        # Load images
        images = []
        for img_path in result.feedback_images:
            img = self._load_image_as_agimage(img_path)
            if img:
                images.append(img)

        feedback_text = result.feedback_text or ""

        if images:
            # Create multimodal message with text and images
            content_list = [feedback_text] + images
            logger.info(f"Creating feedback with {len(images)} image(s)")
            return MultiModalMessage(content=content_list, source=source)
        else:
            return TextMessage(content=feedback_text, source=source)

    async def run_stream(
        self,
        task: str,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator:
        """
        Run the agent with output handler processing.

        Each iteration:
        1. Get model output
        2. Pass output to handler
        3. If handler says stop -> break
        4. Else -> add feedback to history and continue
        """
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        if not self._handler_func:
            yield TextMessage(
                content="[SYSTEM] No output handler configured for this agent.",
                source="system"
            ).model_dump()
            return

        # Initialize history with the user task
        history: List[BaseChatMessage] = [TextMessage(content=task, source="user")]
        iteration = 0

        # Context passed to handler
        handler_context = {
            "agent_name": self.name,
            "output_dir": self.output_handler_config.get("output_dir", "data/workspace/html_outputs"),
        }

        while True:
            iteration += 1

            if iteration > self.max_iterations:
                yield TextMessage(
                    content=f"[SYSTEM] Max iterations ({self.max_iterations}) reached. Stopping.",
                    source="system"
                ).model_dump()
                break

            logger.info(f"[{self.name}] Iteration {iteration}/{self.max_iterations}")

            # Collect the model's complete output this iteration
            accumulated_output = ""
            current_iteration_messages: List[BaseChatMessage] = []

            try:
                async for evt in super().on_messages_stream(
                    messages=history,
                    cancellation_token=cancellation_token
                ):
                    # Yield streaming events to frontend
                    if isinstance(evt, ModelClientStreamingChunkEvent):
                        if evt.content:
                            accumulated_output += evt.content
                        yield evt.model_dump()

                    elif isinstance(evt, Response):
                        if evt.chat_message:
                            # Capture the final response content
                            # Use the final message content, which may be more complete than streaming chunks
                            msg_content = evt.chat_message.content
                            if msg_content:
                                # Handle both string and list content (for multimodal)
                                if isinstance(msg_content, str):
                                    # Only use Response content if we didn't accumulate via streaming
                                    if not accumulated_output.strip():
                                        accumulated_output = msg_content
                                elif isinstance(msg_content, list):
                                    # Extract text from multimodal content list
                                    text_parts = [str(item) for item in msg_content if isinstance(item, str)]
                                    if text_parts and not accumulated_output.strip():
                                        accumulated_output = "\n".join(text_parts)
                            current_iteration_messages.append(evt.chat_message)
                            yield evt.chat_message.model_dump()
                        else:
                            yield evt.model_dump() if hasattr(evt, 'model_dump') else {}

                    elif isinstance(evt, (TextMessage, MultiModalMessage)):
                        yield evt.model_dump()

                    else:
                        yield evt.model_dump() if hasattr(evt, 'model_dump') else evt.__dict__

                logger.info(f"[{self.name}] Iteration {iteration} output length: {len(accumulated_output)}")

            except asyncio.CancelledError:
                yield TextMessage(
                    content="[SYSTEM] Operation cancelled.",
                    source="system"
                ).model_dump()
                raise

            # Add assistant messages to history
            history.extend(current_iteration_messages)

            # Process output through handler
            if not accumulated_output.strip():
                logger.warning(f"[{self.name}] Empty output at iteration {iteration}")
                # Give the model another chance
                feedback_msg = TextMessage(
                    content="Your output was empty. Please provide the requested output.",
                    source="system"
                )
                history.append(feedback_msg)
                yield feedback_msg.model_dump()
                await asyncio.sleep(0.1)
                continue

            try:
                logger.info(f"[{self.name}] Processing output through handler...")
                handler_result = self._handler_func(
                    output=accumulated_output,
                    iteration=iteration,
                    config=self.output_handler_config,
                    context=handler_context
                )
            except Exception as e:
                logger.error(f"[{self.name}] Handler error: {e}")
                yield TextMessage(
                    content=f"[SYSTEM] Handler error: {e}",
                    source="system"
                ).model_dump()
                break

            # Check if we should stop
            if not handler_result.should_continue:
                logger.info(f"[{self.name}] Handler signaled completion")
                if handler_result.feedback_text:
                    yield TextMessage(
                        content=handler_result.feedback_text,
                        source="system"
                    ).model_dump()
                break

            # Create feedback message and add to history
            if handler_result.feedback_text or handler_result.feedback_images:
                feedback_msg = self._create_feedback_message(handler_result, source="system")
                history.append(feedback_msg)
                yield feedback_msg.model_dump()

            # Log saved file info
            if handler_result.saved_file:
                logger.info(f"[{self.name}] Saved: {handler_result.saved_file}")

            await asyncio.sleep(0.1)

        logger.info(f"[{self.name}] Completed after {iteration} iteration(s)")
