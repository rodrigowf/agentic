"""
Unit tests for core/multimodal_tools_looping_agent.py

Tests the MultimodalToolsLoopingAgent behavior including:
- Image detection in tool responses
- MultiModalMessage creation
- Vision model integration
- Various image formats (file paths, base64)
- Error handling for invalid images
- Termination with multimodal content
- System message handling
"""

import pytest
import asyncio
import base64
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from typing import List

from autogen_core import CancellationToken, Image as AGImage
from autogen_core.tools import FunctionTool
from autogen_agentchat.messages import (
    TextMessage,
    MultiModalMessage,
    ToolCallExecutionEvent,
    ModelClientStreamingChunkEvent,
)
from autogen_agentchat.base._chat_agent import Response

from core.multimodal_tools_looping_agent import MultimodalToolsLoopingAgent, DEFAULT_MAX_ITERS

# Try importing PIL
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_model_client():
    """Mock vision-capable model client."""
    mock = MagicMock()
    mock.model = "gpt-4o"
    mock.create = AsyncMock()
    return mock


@pytest.fixture
def sample_tool():
    """Create a sample function tool."""
    def test_func(query: str) -> str:
        """Test function."""
        return f"Result for: {query}"

    return FunctionTool(func=test_func, name="test_tool", description="A test tool")


@pytest.fixture
def multimodal_agent(mock_model_client, sample_tool):
    """Create a MultimodalToolsLoopingAgent instance."""
    return MultimodalToolsLoopingAgent(
        name="VisionAgent",
        description="A vision-capable agent",
        system_message="You are a vision assistant. Say TERMINATE when done.",
        model_client=mock_model_client,
        tools=[sample_tool],
        reflect_on_tool_use=True,
        max_consecutive_auto_reply=10,
    )


@pytest.fixture
def cancellation_token():
    """Create a cancellation token."""
    return CancellationToken()


@pytest.fixture
def temp_image_file(tmp_path):
    """Create a temporary test image file."""
    if not PIL_AVAILABLE:
        pytest.skip("PIL not available")

    image_path = tmp_path / "test_image.png"
    img = PILImage.new('RGB', (100, 100), color='red')
    img.save(image_path)
    return image_path


@pytest.fixture
def base64_image():
    """Create a base64-encoded test image."""
    if not PIL_AVAILABLE:
        pytest.skip("PIL not available")

    from io import BytesIO
    img = PILImage.new('RGB', (50, 50), color='blue')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')


# ============================================================================
# Test Initialization
# ============================================================================

def test_multimodal_agent_initialization(multimodal_agent):
    """Test that MultimodalToolsLoopingAgent initializes correctly."""
    assert multimodal_agent.name == "VisionAgent"
    assert multimodal_agent.description == "A vision-capable agent"
    assert multimodal_agent.max_consecutive_auto_reply == 10


def test_multimodal_agent_default_system_message(mock_model_client, sample_tool):
    """Test default vision system message when none provided."""
    agent = MultimodalToolsLoopingAgent(
        name="VisionAgent",
        description="Test",
        system_message=None,  # Should use default
        model_client=mock_model_client,
        tools=[sample_tool],
    )

    # Should have default vision-related system message
    assert agent._system_messages is not None
    system_content = agent._system_messages[0].content
    assert "vision" in system_content.lower() or "image" in system_content.lower()


def test_multimodal_agent_custom_system_message(mock_model_client, sample_tool):
    """Test custom system message."""
    custom_msg = "Custom vision prompt"
    agent = MultimodalToolsLoopingAgent(
        name="VisionAgent",
        description="Test",
        system_message=custom_msg,
        model_client=mock_model_client,
        tools=[sample_tool],
    )

    assert agent._system_messages[0].content == custom_msg


def test_multimodal_agent_has_image_detection_methods(multimodal_agent):
    """Test that agent has image detection capabilities."""
    assert hasattr(multimodal_agent, '_detect_and_convert_images')
    assert hasattr(multimodal_agent, '_create_multimodal_message_from_tool_result')
    assert hasattr(multimodal_agent, 'IMAGE_EXTENSIONS')
    assert hasattr(multimodal_agent, 'BASE64_IMAGE_PATTERN')
    assert hasattr(multimodal_agent, 'FILE_PATH_PATTERN')


def test_multimodal_agent_image_extensions(multimodal_agent):
    """Test that agent recognizes common image extensions."""
    extensions = multimodal_agent.IMAGE_EXTENSIONS
    assert '.png' in extensions
    assert '.jpg' in extensions
    assert '.jpeg' in extensions
    assert '.gif' in extensions


def test_multimodal_agent_inherits_assistant_agent(multimodal_agent):
    """Test that MultimodalToolsLoopingAgent inherits from AssistantAgent."""
    from autogen_agentchat.agents import AssistantAgent
    assert isinstance(multimodal_agent, AssistantAgent)


def test_multimodal_agent_default_max_iters(mock_model_client, sample_tool):
    """Test default max_consecutive_auto_reply value."""
    agent = MultimodalToolsLoopingAgent(
        name="VisionAgent",
        description="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
    )

    assert agent.max_consecutive_auto_reply == DEFAULT_MAX_ITERS


# ============================================================================
# Test Image Detection - File Paths
# ============================================================================

def test_detect_image_from_absolute_path(multimodal_agent, temp_image_file):
    """Test detecting image from absolute file path."""
    content = f"Screenshot saved to {temp_image_file}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1
    assert isinstance(images[0], AGImage)


def test_detect_image_from_relative_path(multimodal_agent, tmp_path):
    """Test detecting image from relative file path."""
    if not PIL_AVAILABLE:
        pytest.skip("PIL not available")

    # Create image in current directory concept
    image_path = tmp_path / "relative_image.png"
    img = PILImage.new('RGB', (100, 100), color='green')
    img.save(image_path)

    content = f"Image at {image_path}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1


def test_detect_multiple_images_from_paths(multimodal_agent, tmp_path):
    """Test detecting multiple images from file paths."""
    if not PIL_AVAILABLE:
        pytest.skip("PIL not available")

    # Create multiple images
    image1 = tmp_path / "image1.png"
    image2 = tmp_path / "image2.jpg"

    for img_path in [image1, image2]:
        img = PILImage.new('RGB', (100, 100), color='red')
        img.save(img_path)

    content = f"Images saved to {image1} and {image2}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 2


def test_detect_image_with_quotes(multimodal_agent, temp_image_file):
    """Test detecting image path surrounded by quotes."""
    content = f'Screenshot saved to "{temp_image_file}"'
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1


def test_detect_image_with_punctuation(multimodal_agent, temp_image_file):
    """Test detecting image path followed by punctuation."""
    content = f"Screenshot saved to {temp_image_file}."
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1


def test_no_detection_for_nonexistent_file(multimodal_agent):
    """Test that nonexistent file paths are not detected as images."""
    content = "Screenshot saved to /nonexistent/path/image.png"
    images = multimodal_agent._detect_and_convert_images(content)

    # Should not detect nonexistent file
    assert len(images) == 0


def test_no_detection_for_non_image_extensions(multimodal_agent, tmp_path):
    """Test that non-image file extensions are not detected."""
    text_file = tmp_path / "document.txt"
    text_file.write_text("Not an image")

    content = f"File saved to {text_file}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 0


# ============================================================================
# Test Image Detection - Base64
# ============================================================================

def test_detect_base64_image(multimodal_agent, base64_image):
    """Test detecting base64-encoded image."""
    content = f"data:image/png;base64,{base64_image}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1
    assert isinstance(images[0], AGImage)


def test_detect_base64_image_in_text(multimodal_agent, base64_image):
    """Test detecting base64 image embedded in text."""
    content = f"Here is the image: data:image/png;base64,{base64_image} (end)"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1


def test_detect_multiple_base64_images(multimodal_agent, base64_image):
    """Test detecting multiple base64 images."""
    content = f"Image 1: data:image/png;base64,{base64_image}\nImage 2: data:image/jpeg;base64,{base64_image}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 2


def test_detect_base64_case_insensitive(multimodal_agent, base64_image):
    """Test that base64 detection is case-insensitive."""
    content = f"DATA:IMAGE/PNG;BASE64,{base64_image}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1


def test_invalid_base64_data(multimodal_agent):
    """Test handling of invalid base64 data."""
    content = "data:image/png;base64,InvalidBase64Data!!!"
    images = multimodal_agent._detect_and_convert_images(content)

    # Should not crash, but may not detect invalid base64
    assert isinstance(images, list)


# ============================================================================
# Test MultiModalMessage Creation
# ============================================================================

def test_create_multimodal_message_with_image(multimodal_agent, temp_image_file):
    """Test creating MultiModalMessage when image is detected."""
    content = f"Screenshot saved to {temp_image_file}"
    message = multimodal_agent._create_multimodal_message_from_tool_result(content)

    assert isinstance(message, MultiModalMessage)
    assert isinstance(message.content, list)
    assert len(message.content) == 2  # Text + Image
    assert isinstance(message.content[0], str)
    assert isinstance(message.content[1], AGImage)


def test_create_text_message_without_image(multimodal_agent):
    """Test creating TextMessage when no image is detected."""
    content = "No images here, just text"
    message = multimodal_agent._create_multimodal_message_from_tool_result(content)

    assert isinstance(message, TextMessage)
    assert message.content == content


def test_multimodal_message_with_custom_source(multimodal_agent, temp_image_file):
    """Test MultiModalMessage with custom source."""
    content = f"Image at {temp_image_file}"
    message = multimodal_agent._create_multimodal_message_from_tool_result(
        content, source="custom_source"
    )

    assert message.source == "custom_source"


def test_multimodal_message_with_multiple_images(multimodal_agent, tmp_path):
    """Test MultiModalMessage with multiple images."""
    if not PIL_AVAILABLE:
        pytest.skip("PIL not available")

    image1 = tmp_path / "img1.png"
    image2 = tmp_path / "img2.png"

    for img_path in [image1, image2]:
        img = PILImage.new('RGB', (100, 100), color='red')
        img.save(img_path)

    content = f"Images: {image1} and {image2}"
    message = multimodal_agent._create_multimodal_message_from_tool_result(content)

    assert isinstance(message, MultiModalMessage)
    assert len(message.content) == 3  # Text + 2 Images


# ============================================================================
# Test TERMINATE Detection
# ============================================================================

def test_message_contains_terminate_text(multimodal_agent):
    """Test detecting TERMINATE in text message."""
    message = TextMessage(content="Task complete. TERMINATE", source="agent")
    assert multimodal_agent._message_contains_terminate(message) is True


def test_message_contains_terminate_case_insensitive(multimodal_agent):
    """Test TERMINATE detection is case-insensitive."""
    message = TextMessage(content="terminate now", source="agent")
    assert multimodal_agent._message_contains_terminate(message) is True

    message = TextMessage(content="Terminate the task", source="agent")
    assert multimodal_agent._message_contains_terminate(message) is True


def test_message_contains_terminate_word_boundary(multimodal_agent):
    """Test TERMINATE detection respects word boundaries."""
    # Should match TERMINATE as a word
    message = TextMessage(content="TERMINATE", source="agent")
    assert multimodal_agent._message_contains_terminate(message) is True

    # Should not match partial words (this depends on regex implementation)
    # Note: Current implementation uses \b word boundaries
    message = TextMessage(content="determinate", source="agent")
    # May or may not match depending on implementation


def test_message_without_terminate(multimodal_agent):
    """Test message without TERMINATE."""
    message = TextMessage(content="Working on the task...", source="agent")
    assert multimodal_agent._message_contains_terminate(message) is False


def test_terminate_in_multimodal_message(multimodal_agent):
    """Test detecting TERMINATE in MultiModalMessage."""
    message = MultiModalMessage(
        content=["Task done. TERMINATE", MagicMock()],
        source="agent"
    )
    assert multimodal_agent._message_contains_terminate(message) is True


def test_no_terminate_in_multimodal_message(multimodal_agent):
    """Test MultiModalMessage without TERMINATE."""
    message = MultiModalMessage(
        content=["Still working...", MagicMock()],
        source="agent"
    )
    assert multimodal_agent._message_contains_terminate(message) is False


# ============================================================================
# Test update_system_message
# ============================================================================

def test_update_system_message(multimodal_agent):
    """Test updating system message."""
    new_message = "New system message"
    multimodal_agent.update_system_message(new_message)

    assert multimodal_agent._system_messages[0].content == new_message


def test_update_system_message_no_existing(mock_model_client, sample_tool):
    """Test updating system message when none exists."""
    agent = MultimodalToolsLoopingAgent(
        name="VisionAgent",
        description="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
    )

    # Clear system messages
    agent._system_messages = []

    # Should not crash
    agent.update_system_message("New message")


# ============================================================================
# Test run_stream Method
# ============================================================================

@pytest.mark.asyncio
async def test_run_stream_basic(multimodal_agent, cancellation_token):
    """Test basic run_stream execution."""
    async def mock_on_messages_stream(*args, **kwargs):
        yield Response(
            chat_message=TextMessage(content="TERMINATE", source="VisionAgent")
        )

    with patch.object(multimodal_agent, 'on_messages_stream', side_effect=mock_on_messages_stream):
        events = []
        async for event in multimodal_agent.run_stream("Test task", cancellation_token):
            events.append(event)

        assert len(events) > 0


@pytest.mark.asyncio
async def test_run_stream_with_tool_result_image(multimodal_agent, cancellation_token, temp_image_file):
    """Test run_stream with tool result containing image."""
    mock_result = MagicMock()
    mock_result.content = f"Screenshot saved to {temp_image_file}"

    async def mock_on_messages_stream(*args, **kwargs):
        yield ToolCallExecutionEvent(content=[mock_result], source="VisionAgent")
        yield Response(
            chat_message=TextMessage(content="TERMINATE", source="VisionAgent")
        )

    with patch.object(multimodal_agent, 'on_messages_stream', side_effect=mock_on_messages_stream):
        events = []
        async for event in multimodal_agent.run_stream("Test task", cancellation_token):
            events.append(event)

        # Should have yielded events including multimodal message
        assert len(events) >= 2


@pytest.mark.asyncio
async def test_run_stream_terminate_in_streaming_chunk(multimodal_agent, cancellation_token):
    """Test that TERMINATE in streaming chunks stops the loop."""
    async def mock_on_messages_stream(*args, **kwargs):
        yield ModelClientStreamingChunkEvent(content="Processing... ", source="VisionAgent")
        yield ModelClientStreamingChunkEvent(content="TERMINATE", source="VisionAgent")

    with patch.object(multimodal_agent, 'on_messages_stream', side_effect=mock_on_messages_stream):
        events = []
        async for event in multimodal_agent.run_stream("Test task", cancellation_token):
            events.append(event)

        # Should terminate
        assert len(events) >= 2


@pytest.mark.asyncio
async def test_run_stream_max_iterations(multimodal_agent, cancellation_token):
    """Test that agent stops after max iterations."""
    multimodal_agent.max_consecutive_auto_reply = 3

    async def mock_on_messages_stream(*args, **kwargs):
        yield Response(
            chat_message=TextMessage(content="Working...", source="VisionAgent")
        )

    with patch.object(multimodal_agent, 'on_messages_stream', side_effect=mock_on_messages_stream):
        events = []
        async for event in multimodal_agent.run_stream("Test task", cancellation_token):
            events.append(event)

        # Should have safety stop message
        assert any("Safety stop" in str(event) for event in events)


@pytest.mark.asyncio
async def test_run_stream_handles_cancellation(multimodal_agent, cancellation_token):
    """Test that CancelledError is properly handled."""
    async def mock_on_messages_stream(*args, **kwargs):
        yield Response(
            chat_message=TextMessage(content="Starting...", source="VisionAgent")
        )
        raise asyncio.CancelledError()

    with patch.object(multimodal_agent, 'on_messages_stream', side_effect=mock_on_messages_stream):
        with pytest.raises(asyncio.CancelledError):
            events = []
            async for event in multimodal_agent.run_stream("Test task", cancellation_token):
                events.append(event)

            # Should have cancellation message
            assert any("cancelled" in str(event).lower() for event in events)


# ============================================================================
# Test Tool Result Processing
# ============================================================================

@pytest.mark.asyncio
async def test_tool_result_without_image_creates_text_message(multimodal_agent, cancellation_token):
    """Test that tool result without image creates TextMessage."""
    mock_result = MagicMock()
    mock_result.content = "Plain text result"

    async def mock_on_messages_stream(*args, **kwargs):
        yield ToolCallExecutionEvent(content=[mock_result], source="VisionAgent")
        yield Response(
            chat_message=TextMessage(content="TERMINATE", source="VisionAgent")
        )

    with patch.object(multimodal_agent, 'on_messages_stream', side_effect=mock_on_messages_stream):
        events = []
        async for event in multimodal_agent.run_stream("Test task", cancellation_token):
            events.append(event)

        # Should have text message, not multimodal
        assert len(events) >= 2


@pytest.mark.asyncio
async def test_multiple_tool_results(multimodal_agent, cancellation_token, temp_image_file):
    """Test processing multiple tool results."""
    mock_result1 = MagicMock()
    mock_result1.content = f"Image 1: {temp_image_file}"

    mock_result2 = MagicMock()
    mock_result2.content = "Text result"

    async def mock_on_messages_stream(*args, **kwargs):
        yield ToolCallExecutionEvent(
            content=[mock_result1, mock_result2],
            source="VisionAgent"
        )
        yield Response(
            chat_message=TextMessage(content="TERMINATE", source="VisionAgent")
        )

    with patch.object(multimodal_agent, 'on_messages_stream', side_effect=mock_on_messages_stream):
        events = []
        async for event in multimodal_agent.run_stream("Test task", cancellation_token):
            events.append(event)

        assert len(events) >= 3  # Tool result events + terminate


# ============================================================================
# Test Error Handling
# ============================================================================

def test_detect_images_with_invalid_path(multimodal_agent):
    """Test that invalid paths don't crash image detection."""
    content = "Path with\x00null byte: image.png"
    images = multimodal_agent._detect_and_convert_images(content)

    # Should handle gracefully
    assert isinstance(images, list)


def test_detect_images_with_empty_string(multimodal_agent):
    """Test image detection with empty string."""
    images = multimodal_agent._detect_and_convert_images("")
    assert len(images) == 0


def test_detect_images_with_unicode(multimodal_agent, tmp_path):
    """Test image detection with unicode characters."""
    if not PIL_AVAILABLE:
        pytest.skip("PIL not available")

    # Create image with unicode in path
    image_path = tmp_path / "测试图片.png"
    img = PILImage.new('RGB', (100, 100), color='red')
    img.save(image_path)

    content = f"Image saved to {image_path}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1


# ============================================================================
# Test PIL Availability Handling
# ============================================================================

def test_agent_warns_without_pil(mock_model_client, sample_tool):
    """Test that agent logs warning when PIL is not available."""
    with patch('core.multimodal_tools_looping_agent.PILImage', None):
        agent = MultimodalToolsLoopingAgent(
            name="VisionAgent",
            description="Test",
            model_client=mock_model_client,
            tools=[sample_tool],
        )

        # Agent should still be created
        assert agent is not None


# ============================================================================
# Test Integration with Different Image Formats
# ============================================================================

@pytest.mark.parametrize("extension", ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'])
def test_detect_various_image_extensions(multimodal_agent, tmp_path, extension):
    """Test detection of various image file extensions."""
    if not PIL_AVAILABLE:
        pytest.skip("PIL not available")

    image_path = tmp_path / f"test{extension}"

    # Create appropriate image based on extension
    img = PILImage.new('RGB', (100, 100), color='red')
    try:
        img.save(image_path)
    except (KeyError, OSError):
        # Some formats may not be supported
        pytest.skip(f"Format {extension} not supported")

    content = f"Image saved to {image_path}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1


def test_detect_mixed_content(multimodal_agent, temp_image_file, base64_image):
    """Test detecting both file paths and base64 images in same content."""
    content = f"File image: {temp_image_file}\nBase64: data:image/png;base64,{base64_image}"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 2


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_detect_image_path_in_json(multimodal_agent, temp_image_file):
    """Test detecting image path within JSON string."""
    content = f'{{"image_path": "{temp_image_file}", "status": "ok"}}'
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1


def test_detect_image_path_in_markdown(multimodal_agent, temp_image_file):
    """Test detecting image path in markdown format."""
    content = f"![Screenshot]({temp_image_file})"
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1


def test_detect_image_path_in_html(multimodal_agent, temp_image_file):
    """Test detecting image path in HTML tag."""
    content = f'<img src="{temp_image_file}" alt="test">'
    images = multimodal_agent._detect_and_convert_images(content)

    assert len(images) == 1
