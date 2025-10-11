"""
End-to-end tests for MultimodalToolsLoopingAgent.

These tests verify that the agent can:
1. Detect images in tool responses (file paths, base64)
2. Convert them to MultiModalMessage objects
3. Pass them to the LLM for interpretation
4. Complete tasks that require image understanding
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from io import BytesIO
import base64

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from PIL import Image as PILImage, ImageDraw, ImageFont

# Import our modules
from core.multimodal_tools_looping_agent import MultimodalToolsLoopingAgent
from autogen_core import CancellationToken, Image as AGImage
from autogen_agentchat.messages import MultiModalMessage, TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.tools import FunctionTool


# Mock model client for unit tests
class MockModelClient:
    """Mock model client that doesn't require API keys."""
    def __init__(self):
        self.model_info = {"function_calling": True}


# Test fixtures
@pytest.fixture
def workspace_dir(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def test_image_path(workspace_dir):
    """Create a test image file."""
    img = PILImage.new('RGB', (200, 100), color='blue')
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()

    draw.text((50, 40), "TEST IMAGE", fill='white', font=font)

    image_path = workspace_dir / "test_image.png"
    img.save(image_path)
    return image_path


@pytest.fixture
def model_client():
    """Create a model client for testing."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    return OpenAIChatCompletionClient(
        model="gpt-4o-mini",  # Use mini for faster/cheaper tests
        api_key=api_key
    )


# Unit Tests for Image Detection

def test_detect_file_path_in_text():
    """Test that the agent can detect image file paths in text."""
    agent = MultimodalToolsLoopingAgent(
        name="TestAgent",
        model_client=MockModelClient(),
        tools=[]
    )

    # Test various file path formats
    test_cases = [
        ("Image saved to /home/user/image.png", 1),
        ("Screenshot at ./workspace/screenshot.jpg", 1),
        ("Files: image1.png and image2.jpeg", 2),
        ("No images here!", 0),
        ("Path: /tmp/test.txt", 0),  # Not an image extension
    ]

    for text, expected_count in test_cases:
        matches = agent.FILE_PATH_PATTERN.findall(text)
        assert len(matches) == expected_count, f"Failed for: {text}"


def test_detect_base64_image_in_text():
    """Test that the agent can detect base64 encoded images."""
    agent = MultimodalToolsLoopingAgent(
        name="TestAgent",
        model_client=MockModelClient(),
        tools=[]
    )

    # Create a small base64 image
    img = PILImage.new('RGB', (10, 10), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

    text_with_base64 = f"Image: data:image/png;base64,{b64_data}"

    matches = agent.BASE64_IMAGE_PATTERN.findall(text_with_base64)
    assert len(matches) == 1
    assert matches[0][0].lower() == 'png'


def test_convert_images_from_file_path(test_image_path):
    """Test converting actual image files to AGImage objects."""
    agent = MultimodalToolsLoopingAgent(
        name="TestAgent",
        model_client=MockModelClient(),
        tools=[]
    )

    text = f"Image saved to {test_image_path}"
    images = agent._detect_and_convert_images(text)

    assert len(images) == 1
    assert isinstance(images[0], AGImage)


def test_convert_images_from_base64():
    """Test converting base64 images to AGImage objects."""
    agent = MultimodalToolsLoopingAgent(
        name="TestAgent",
        model_client=MockModelClient(),
        tools=[]
    )

    # Create a small test image
    img = PILImage.new('RGB', (10, 10), color='green')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

    text = f"data:image/png;base64,{b64_data}"
    images = agent._detect_and_convert_images(text)

    assert len(images) == 1
    assert isinstance(images[0], AGImage)


def test_create_multimodal_message_with_images(test_image_path):
    """Test creating MultiModalMessage when images are detected."""
    agent = MultimodalToolsLoopingAgent(
        name="TestAgent",
        model_client=MockModelClient(),
        tools=[]
    )

    tool_result = f"Screenshot saved to {test_image_path}"
    message = agent._create_multimodal_message_from_tool_result(tool_result)

    assert isinstance(message, MultiModalMessage)
    assert len(message.content) == 2  # Text + 1 image
    assert isinstance(message.content[0], str)
    assert isinstance(message.content[1], AGImage)


def test_create_text_message_when_no_images():
    """Test creating TextMessage when no images are detected."""
    agent = MultimodalToolsLoopingAgent(
        name="TestAgent",
        model_client=MockModelClient(),
        tools=[]
    )

    tool_result = "Operation completed successfully. No images."
    message = agent._create_multimodal_message_from_tool_result(tool_result)

    assert isinstance(message, TextMessage)
    assert message.content == tool_result


# Integration Tests

@pytest.mark.asyncio
async def test_agent_with_image_tool(model_client, workspace_dir):
    """
    Test that the agent can use a tool that returns an image path
    and then analyze that image.
    """

    # Create a test tool that returns an image
    def get_test_chart():
        """Generate a simple chart image."""
        img = PILImage.new('RGB', (300, 200), color='white')
        draw = ImageDraw.Draw(img)

        # Draw simple bars
        draw.rectangle([50, 150, 80, 180], fill='red', outline='black')
        draw.rectangle([100, 120, 130, 180], fill='blue', outline='black')
        draw.rectangle([150, 100, 180, 180], fill='green', outline='black')

        draw.text((100, 20), "Sales Chart", fill='black')

        image_path = workspace_dir / "chart.png"
        img.save(image_path)
        return f"Chart saved to {image_path}"

    test_tool = FunctionTool(
        func=get_test_chart,
        name="get_test_chart",
        description="Get a test sales chart image"
    )

    # Create agent
    agent = MultimodalToolsLoopingAgent(
        name="VisionAgent",
        model_client=model_client,
        tools=[test_tool],
        system_message="You are a helpful assistant with vision. Use the get_test_chart tool to get an image, then describe what you see. Say TERMINATE when done.",
        max_consecutive_auto_reply=10
    )

    # Run agent
    task = "Get the test chart and describe what you see in it."
    results = []

    async for event in agent.run_stream(task):
        results.append(event)

    # Verify we got events
    assert len(results) > 0

    # Check for MultiModalMessage in results
    multimodal_messages = [
        r for r in results
        if r.get('type') == 'MultiModalMessage'
    ]

    assert len(multimodal_messages) > 0, "No MultiModalMessage events found"

    # Verify final result contains image description
    text_messages = [
        r for r in results
        if r.get('type') == 'TextMessage' and r.get('source') == 'VisionAgent'
    ]

    # The agent should describe the chart
    final_text = " ".join([m.get('content', '') for m in text_messages])
    # Should mention something about the chart or bars
    assert any(keyword in final_text.lower() for keyword in ['chart', 'bar', 'color', 'red', 'blue', 'green'])


@pytest.mark.asyncio
async def test_agent_multiple_images(model_client, workspace_dir):
    """
    Test that the agent can handle multiple images in a single tool response.
    """

    def get_multiple_images():
        """Generate multiple test images."""
        paths = []
        for i, color in enumerate(['red', 'green', 'blue']):
            img = PILImage.new('RGB', (100, 100), color=color)
            draw = ImageDraw.Draw(img)
            draw.text((30, 40), color.upper(), fill='white')

            image_path = workspace_dir / f"image_{i}.png"
            img.save(image_path)
            paths.append(str(image_path))

        return f"Generated images:\n" + "\n".join(paths)

    test_tool = FunctionTool(
        func=get_multiple_images,
        name="get_multiple_images",
        description="Get multiple colored test images"
    )

    agent = MultimodalToolsLoopingAgent(
        name="VisionAgent",
        model_client=model_client,
        tools=[test_tool],
        system_message="You are a helpful assistant with vision. Use tools and describe what you see. Say TERMINATE when done.",
        max_consecutive_auto_reply=10
    )

    task = "Get multiple images and tell me what colors you see."
    results = []

    async for event in agent.run_stream(task):
        results.append(event)

    # Check for MultiModalMessage with multiple images
    multimodal_messages = [
        r for r in results
        if r.get('type') == 'MultiModalMessage'
    ]

    assert len(multimodal_messages) > 0

    # Verify agent mentions the colors
    text_messages = [
        r for r in results
        if r.get('type') == 'TextMessage' and r.get('source') == 'VisionAgent'
    ]

    final_text = " ".join([m.get('content', '') for m in text_messages]).lower()
    assert 'red' in final_text or 'green' in final_text or 'blue' in final_text


@pytest.mark.asyncio
async def test_agent_handles_no_images_gracefully(model_client):
    """
    Test that the agent works normally when tools don't return images.
    """

    def get_text_data():
        """Return plain text data."""
        return "Here is some text data: Revenue: $1000, Expenses: $500, Profit: $500"

    test_tool = FunctionTool(
        func=get_text_data,
        name="get_text_data",
        description="Get text financial data"
    )

    agent = MultimodalToolsLoopingAgent(
        name="VisionAgent",
        model_client=model_client,
        tools=[test_tool],
        system_message="You are a helpful assistant. Use tools to answer questions. Say TERMINATE when done.",
        max_consecutive_auto_reply=10
    )

    task = "Get the text data and tell me the profit."
    results = []

    async for event in agent.run_stream(task):
        results.append(event)

    # Should work like a normal agent (no MultiModalMessage)
    assert len(results) > 0

    # Verify agent mentions the profit
    text_messages = [
        r for r in results
        if r.get('type') == 'TextMessage' and r.get('source') == 'VisionAgent'
    ]

    final_text = " ".join([m.get('content', '') for m in text_messages]).lower()
    assert '500' in final_text or 'profit' in final_text


# Performance and Edge Cases

def test_handle_invalid_image_path():
    """Test that invalid image paths don't crash the agent."""
    agent = MultimodalToolsLoopingAgent(
        name="TestAgent",
        model_client=MockModelClient(),
        tools=[]
    )

    text = "Image at /nonexistent/path/image.png"
    images = agent._detect_and_convert_images(text)

    # Should return empty list, not crash
    assert images == []


def test_handle_corrupted_base64():
    """Test that corrupted base64 data doesn't crash the agent."""
    agent = MultimodalToolsLoopingAgent(
        name="TestAgent",
        model_client=MockModelClient(),
        tools=[]
    )

    text = "data:image/png;base64,CORRUPTED_DATA!!!"
    images = agent._detect_and_convert_images(text)

    # Should return empty list, not crash
    assert images == []


def test_max_iterations_safety(model_client):
    """Test that max_consecutive_auto_reply prevents infinite loops."""
    agent = MultimodalToolsLoopingAgent(
        name="TestAgent",
        model_client=model_client,
        tools=[],
        system_message="Never say TERMINATE",
        max_consecutive_auto_reply=3
    )

    # This should stop after 3 iterations
    results = []

    async def run_test():
        async for event in agent.run_stream("Keep going forever"):
            results.append(event)

    asyncio.run(run_test())

    # Should have safety stop message
    safety_messages = [
        r for r in results
        if 'Safety stop' in r.get('content', '')
    ]

    assert len(safety_messages) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
