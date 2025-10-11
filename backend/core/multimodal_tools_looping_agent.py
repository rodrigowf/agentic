import asyncio
import re
import logging
from pathlib import Path
from typing import AsyncIterator, List, Optional
from io import BytesIO
import base64

# Core autogen components
from autogen_core import CancellationToken, Image as AGImage

# AgentChat specific components
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base._chat_agent import Response
from autogen_agentchat.messages import (
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    TextMessage,
    MultiModalMessage,
    ToolCallExecutionEvent
)

# Try to import PIL for image handling
try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

# Default max iterations
DEFAULT_MAX_ITERS = 40

logger = logging.getLogger(__name__)


class MultimodalToolsLoopingAgent(AssistantAgent):
    """
    An AssistantAgent that can interpret images and audio in tool responses using multimodal LLMs.

    This agent extends the LoopingAssistantAgent behavior by:
    1. Detecting image/audio content in tool responses (file paths, base64, URLs)
    2. Converting them to MultiModalMessage objects
    3. Passing them to the LLM for multimodal interpretation

    Supported formats:
    - Image files: .png, .jpg, .jpeg, .gif, .bmp, .webp
    - Base64 encoded images: data:image/...;base64,...
    - File paths to images
    - URLs to images (if content is downloaded)
    """

    # Supported image extensions
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

    # Pattern to detect base64 images in tool responses
    BASE64_IMAGE_PATTERN = re.compile(
        r'data:image/([a-zA-Z]+);base64,([A-Za-z0-9+/=]+)',
        re.IGNORECASE
    )

    # Pattern to detect file paths in tool responses
    FILE_PATH_PATTERN = re.compile(
        r'(?:^|[\s\'\"])((?:[\/~])?(?:[\w\-\.]+\/)*[\w\-\.]+\.(?:png|jpg|jpeg|gif|bmp|webp))(?:[\s\'\"]|$)',
        re.IGNORECASE | re.MULTILINE
    )

    def __init__(self, *args, max_consecutive_auto_reply: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_consecutive_auto_reply = max_consecutive_auto_reply if max_consecutive_auto_reply is not None else DEFAULT_MAX_ITERS

        if PILImage is None:
            logger.warning("PIL (Pillow) not installed. Image handling will be limited.")

    def _detect_and_convert_images(self, content: str) -> List[AGImage]:
        """
        Detect images in tool response content and convert them to AGImage objects.

        Args:
            content: Tool response content (may contain file paths, base64, etc.)

        Returns:
            List of AGImage objects found in the content
        """
        images = []

        # 1. Check for base64 encoded images
        base64_matches = self.BASE64_IMAGE_PATTERN.findall(content)
        for format_type, b64_data in base64_matches:
            try:
                image = AGImage.from_base64(b64_data)
                images.append(image)
                logger.info(f"Detected base64 image (format: {format_type})")
            except Exception as e:
                logger.warning(f"Failed to parse base64 image: {e}")

        # 2. Check for file paths
        file_matches = self.FILE_PATH_PATTERN.findall(content)
        for file_path_str in file_matches:
            try:
                file_path = Path(file_path_str).expanduser().resolve()
                if file_path.exists() and file_path.suffix.lower() in self.IMAGE_EXTENSIONS:
                    image = AGImage.from_file(file_path)
                    images.append(image)
                    logger.info(f"Detected image file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to load image from path {file_path_str}: {e}")

        return images

    def _create_multimodal_message_from_tool_result(
        self,
        tool_result_content: str,
        source: str = "tools"
    ) -> BaseChatMessage:
        """
        Create a MultiModalMessage if images are detected in tool result, otherwise TextMessage.

        Args:
            tool_result_content: The content from tool execution
            source: Message source (default "tools")

        Returns:
            MultiModalMessage if images found, otherwise TextMessage
        """
        images = self._detect_and_convert_images(tool_result_content)

        if images:
            # Create multimodal message with text and images
            content_list = [tool_result_content] + images
            logger.info(f"Creating MultiModalMessage with {len(images)} image(s)")
            return MultiModalMessage(content=content_list, source=source)
        else:
            # No images detected, return regular text message
            return TextMessage(content=tool_result_content, source=source)

    async def run_stream(
        self,
        task: str,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator:
        """
        Run the agent with multimodal tool response handling.

        This method loops through LLM interactions and tool calls, automatically
        detecting and converting images/audio in tool responses to multimodal messages
        that the LLM can interpret directly.
        """
        if cancellation_token is None:
            cancellation_token = CancellationToken()

        # Initialize history with the initial user task
        history: List[BaseChatMessage] = [TextMessage(content=task, source="user")]
        iters = 0

        while True:
            iters += 1
            if iters > self.max_consecutive_auto_reply:
                yield TextMessage(
                    content=f"[SYSTEM] Safety stop: max iterations ({self.max_consecutive_auto_reply}) reached.",
                    source="system"
                ).model_dump()
                break

            last_assistant_text_message_content: str | None = None
            accumulated_assistant_chunks: str = ""
            current_iteration_new_history: List[BaseChatMessage] = []

            try:
                async for evt in super().on_messages_stream(messages=history, cancellation_token=cancellation_token):
                    # Convert event to proper JSON format before yielding
                    if isinstance(evt, (TextMessage, MultiModalMessage, ModelClientStreamingChunkEvent, ToolCallExecutionEvent)):
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

                    # Handle tool call execution - THIS IS WHERE MULTIMODAL MAGIC HAPPENS
                    if isinstance(evt, ToolCallExecutionEvent):
                        for result in evt.content:
                            result_content = str(result.content)

                            # Create multimodal message if images detected, otherwise text message
                            msg = self._create_multimodal_message_from_tool_result(
                                result_content,
                                source="tools"
                            )

                            current_iteration_new_history.append(msg)

                            # Yield the multimodal message so frontend can see it
                            yield msg.model_dump()

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
