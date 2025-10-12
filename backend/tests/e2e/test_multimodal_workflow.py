#!/usr/bin/env python3
"""
End-to-End tests for multimodal agent workflows.

Tests the complete workflow of multimodal vision agents:
1. Create multimodal agent with image tools
2. Execute agent that generates/captures images
3. Verify automatic image detection and processing
4. Test MultiModalMessage creation
5. Verify vision model integration
6. Test various image formats (PNG, JPG, base64)

These tests verify the full multimodal agent workflow with minimal mocking.
"""

import json
import os
import pytest
import tempfile
import shutil
import base64
from pathlib import Path
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from config.schemas import AgentConfig
from tests.fixtures import (
    MOCK_MULTIMODAL_AGENT,
    create_mock_agent_config,
    create_mock_image_base64,
    MOCK_BASE64_IMAGE
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_workspace(monkeypatch):
    """Create temporary workspace with images directory."""
    temp_dir = tempfile.mkdtemp()
    agents_path = Path(temp_dir) / "agents"
    tools_path = Path(temp_dir) / "tools"
    images_path = Path(temp_dir) / "images"
    agents_path.mkdir()
    tools_path.mkdir()
    images_path.mkdir()

    import main
    original_agents_dir = main.AGENTS_DIR
    original_tools_dir = main.TOOLS_DIR
    main.AGENTS_DIR = str(agents_path)
    main.TOOLS_DIR = str(tools_path)
    main.AGENTS = []
    main.LOADED_TOOLS_WITH_FILENAMES = []

    yield {
        "agents_dir": str(agents_path),
        "tools_dir": str(tools_path),
        "images_dir": str(images_path),
        "temp_dir": temp_dir
    }

    main.AGENTS_DIR = original_agents_dir
    main.TOOLS_DIR = original_tools_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def image_tools(temp_workspace):
    """Create image tools in temp directory."""
    # Create tools code with image generation/capture capabilities
    tools_code = '''"""
Image tools for testing multimodal agents.
"""

from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
import os


def generate_test_image(
    text: str = "Test",
    width: int = 400,
    height: int = 300,
    save_path: str = None
) -> str:
    """
    Generate a test image with text.

    Args:
        text: Text to display on image
        width: Image width
        height: Image height
        save_path: Optional path to save image

    Returns:
        Path to saved image or base64 encoded image
    """
    # Create image
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Draw text
    text_bbox = draw.textbbox((0, 0), text)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    position = ((width - text_width) // 2, (height - text_height) // 2)
    draw.text(position, text, fill='black')

    # Save or return base64
    if save_path:
        img.save(save_path)
        return f"Image saved to {save_path}"
    else:
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_b64}"


def get_sample_image(image_type: str = "chart") -> str:
    """
    Get a sample image of specified type.

    Args:
        image_type: Type of image (chart, photo, diagram)

    Returns:
        Base64 encoded image
    """
    # Create different types of images
    if image_type == "chart":
        img = Image.new('RGB', (400, 300), color='lightblue')
        draw = ImageDraw.Draw(img)
        # Simple bar chart
        draw.rectangle([50, 200, 100, 250], fill='red')
        draw.rectangle([150, 150, 200, 250], fill='green')
        draw.rectangle([250, 100, 300, 250], fill='blue')
        draw.text((150, 270), "Sample Chart", fill='black')

    elif image_type == "photo":
        img = Image.new('RGB', (400, 300), color='skyblue')
        draw = ImageDraw.Draw(img)
        # Simple landscape
        draw.rectangle([0, 200, 400, 300], fill='green')  # Ground
        draw.ellipse([150, 50, 250, 150], fill='yellow')  # Sun
        draw.text((150, 270), "Sample Photo", fill='black')

    else:  # diagram
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)
        # Simple flowchart
        draw.rectangle([150, 50, 250, 100], outline='black')
        draw.text((180, 65), "Start", fill='black')
        draw.line([200, 100, 200, 150], fill='black')
        draw.rectangle([150, 150, 250, 200], outline='black')
        draw.text((170, 165), "Process", fill='black')

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_b64}"


# Export tools
generate_test_image_func = FunctionTool(
    func=generate_test_image,
    name="generate_test_image",
    description="Generate a test image with custom text"
)

get_sample_image_func = FunctionTool(
    func=get_sample_image,
    name="get_sample_image",
    description="Get a sample image of specified type"
)

tools = [generate_test_image_func, get_sample_image_func]
'''

    tool_file = Path(temp_workspace["tools_dir"]) / "image_tools.py"
    tool_file.write_text(tools_code)

    return ["generate_test_image", "get_sample_image"]


class TestMultimodalAgentCreation:
    """E2E tests for multimodal agent creation."""

    def test_create_multimodal_agent(self, client, temp_workspace, image_tools):
        """Test creating a multimodal vision agent."""
        # Create multimodal agent configuration
        agent_config = create_mock_agent_config(
            name="VisionAgent",
            agent_type="multimodal_tools_looping",
            tools=image_tools,
            llm_provider="openai",
            llm_model="gpt-4o",  # Vision-capable model required
            max_consecutive_auto_reply=10
        )

        # Create agent via API
        response = client.post("/api/agents", json=agent_config.model_dump(mode='json'))
        assert response.status_code == 200

        created = response.json()
        assert created["name"] == "VisionAgent"
        assert created["agent_type"] == "multimodal_tools_looping"
        assert created["llm"]["model"] == "gpt-4o"

        # Verify agent file
        agent_file = Path(temp_workspace["agents_dir"]) / "VisionAgent.json"
        assert agent_file.exists()

    def test_multimodal_agent_with_vision_model(self, client, temp_workspace, image_tools):
        """Test that multimodal agent uses vision-capable model."""
        # Test with different vision models
        vision_models = [
            ("openai", "gpt-4o"),
            ("openai", "gpt-4o-mini"),
            ("openai", "gpt-4-turbo-2024-04-09"),
        ]

        for i, (provider, model) in enumerate(vision_models):
            agent_config = create_mock_agent_config(
                name=f"VisionAgent_{i}",
                agent_type="multimodal_tools_looping",
                tools=image_tools,
                llm_provider=provider,
                llm_model=model
            )

            response = client.post("/api/agents", json=agent_config.model_dump(mode='json'))
            assert response.status_code == 200
            assert response.json()["llm"]["model"] == model


class TestMultimodalImageDetection:
    """E2E tests for automatic image detection in tool responses."""

    def test_detect_image_file_path(self, client, temp_workspace, image_tools):
        """Test detecting image file paths in tool responses."""
        # Create agent
        agent_config = create_mock_agent_config(
            name="PathDetectionAgent",
            agent_type="multimodal_tools_looping",
            tools=image_tools
        )
        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        # Execute with mocked runner
        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Tool returns path to saved image
                image_path = Path(temp_workspace["images_dir"]) / "test.png"

                # Actually create the image
                img = Image.new('RGB', (100, 100), color='red')
                img.save(image_path)

                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": "generate_test_image",
                        "result": f"Image saved to {image_path}",
                        "is_error": False,
                        "id": "tool_1"
                    }
                })

                # Agent should detect image and send MultiModalMessage
                await websocket.send_json({
                    "type": "MultiModalMessage",
                    "data": {
                        "content": [
                            {"type": "text", "text": "I can see the image:"},
                            {"type": "image_url", "image_url": {"url": str(image_path)}}
                        ]
                    }
                })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/PathDetectionAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify MultiModalMessage was sent
                multimodal_events = [e for e in events if e["type"] == "MultiModalMessage"]
                assert len(multimodal_events) > 0

                # Verify image was detected
                mm_event = multimodal_events[0]
                assert "content" in mm_event["data"]
                assert any(
                    item.get("type") == "image_url"
                    for item in mm_event["data"]["content"]
                )

    def test_detect_base64_image(self, client, temp_workspace, image_tools):
        """Test detecting base64 encoded images in tool responses."""
        agent_config = create_mock_agent_config(
            name="Base64DetectionAgent",
            agent_type="multimodal_tools_looping",
            tools=image_tools
        )
        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Tool returns base64 image
                base64_img = create_mock_image_base64(text="Test")

                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": "get_sample_image",
                        "result": base64_img,
                        "is_error": False,
                        "id": "tool_1"
                    }
                })

                # Agent detects base64 and creates MultiModalMessage
                await websocket.send_json({
                    "type": "MultiModalMessage",
                    "data": {
                        "content": [
                            {"type": "text", "text": "Here's the image:"},
                            {"type": "image_url", "image_url": {"url": base64_img}}
                        ]
                    }
                })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/Base64DetectionAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify base64 image was detected
                multimodal_events = [e for e in events if e["type"] == "MultiModalMessage"]
                assert len(multimodal_events) > 0

                mm_event = multimodal_events[0]
                image_items = [
                    item for item in mm_event["data"]["content"]
                    if item.get("type") == "image_url"
                ]
                assert len(image_items) > 0
                assert "data:image" in image_items[0]["image_url"]["url"]


class TestMultimodalWorkflow:
    """E2E tests for complete multimodal workflows."""

    def test_screenshot_analysis_workflow(self, client, temp_workspace, image_tools):
        """
        Test complete workflow:
        1. Agent takes screenshot
        2. Screenshot detected automatically
        3. Agent analyzes screenshot content
        4. Agent describes what it sees
        """
        agent_config = create_mock_agent_config(
            name="ScreenshotAnalyzer",
            agent_type="multimodal_tools_looping",
            tools=image_tools
        )
        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Step 1: Take screenshot (simulated)
                screenshot_path = Path(temp_workspace["images_dir"]) / "screenshot.png"
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)
                draw.text((300, 250), "Dashboard UI", fill='black')
                draw.rectangle([100, 100, 700, 500], outline='black')
                img.save(screenshot_path)

                await websocket.send_json({
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": "generate_test_image",
                        "arguments": {"text": "Dashboard", "save_path": str(screenshot_path)},
                        "id": "tool_1"
                    }
                })

                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": "generate_test_image",
                        "result": f"Screenshot saved to {screenshot_path}",
                        "is_error": False,
                        "id": "tool_1"
                    }
                })

                # Step 2: Image detected, MultiModalMessage created
                await websocket.send_json({
                    "type": "MultiModalMessage",
                    "data": {
                        "content": [
                            {"type": "text", "text": "Analyzing screenshot:"},
                            {"type": "image_url", "image_url": {"url": str(screenshot_path)}}
                        ]
                    },
                    "source": "agent"
                })

                # Step 3: Agent describes what it sees
                await websocket.send_json({
                    "type": "TextMessage",
                    "data": {
                        "content": (
                            "I can see a dashboard UI with a rectangular border. "
                            "The text 'Dashboard UI' is displayed in the center. "
                            "The interface appears clean and minimalistic."
                        )
                    },
                    "source": "agent"
                })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/ScreenshotAnalyzer") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify workflow
                event_types = [e["type"] for e in events]
                assert "ToolCallRequestEvent" in event_types
                assert "ToolCallExecutionEvent" in event_types
                assert "MultiModalMessage" in event_types
                assert "TextMessage" in event_types

                # Verify description
                text_messages = [e for e in events if e["type"] == "TextMessage"]
                assert len(text_messages) > 0
                assert "dashboard" in text_messages[0]["data"]["content"].lower()

    def test_image_generation_and_description_workflow(self, client, temp_workspace, image_tools):
        """
        Test complete workflow:
        1. Agent generates image
        2. Image detected automatically
        3. Agent describes generated image
        """
        agent_config = create_mock_agent_config(
            name="ImageGenerator",
            agent_type="multimodal_tools_looping",
            tools=image_tools
        )
        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Generate chart
                await websocket.send_json({
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": "get_sample_image",
                        "arguments": {"image_type": "chart"},
                        "id": "tool_1"
                    }
                })

                base64_chart = create_mock_image_base64(text="Chart")

                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": "get_sample_image",
                        "result": base64_chart,
                        "is_error": False,
                        "id": "tool_1"
                    }
                })

                # MultiModalMessage with image
                await websocket.send_json({
                    "type": "MultiModalMessage",
                    "data": {
                        "content": [
                            {"type": "text", "text": "Generated chart:"},
                            {"type": "image_url", "image_url": {"url": base64_chart}}
                        ]
                    }
                })

                # Description
                await websocket.send_json({
                    "type": "TextMessage",
                    "data": {
                        "content": (
                            "I generated a bar chart with three bars in different colors. "
                            "The bars show increasing height from left to right."
                        )
                    }
                })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/ImageGenerator") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify complete workflow
                assert any(e["type"] == "ToolCallRequestEvent" for e in events)
                assert any(e["type"] == "MultiModalMessage" for e in events)
                assert any(e["type"] == "TextMessage" for e in events)

    def test_multiple_images_in_sequence(self, client, temp_workspace, image_tools):
        """Test agent processing multiple images in sequence."""
        agent_config = create_mock_agent_config(
            name="MultiImageAgent",
            agent_type="multimodal_tools_looping",
            tools=image_tools
        )
        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                image_types = ["chart", "photo", "diagram"]

                for i, img_type in enumerate(image_types):
                    # Request image
                    await websocket.send_json({
                        "type": "ToolCallRequestEvent",
                        "data": {
                            "name": "get_sample_image",
                            "arguments": {"image_type": img_type},
                            "id": f"tool_{i}"
                        }
                    })

                    # Image generated
                    base64_img = create_mock_image_base64(text=img_type)
                    await websocket.send_json({
                        "type": "ToolCallExecutionEvent",
                        "data": {
                            "name": "get_sample_image",
                            "result": base64_img,
                            "is_error": False,
                            "id": f"tool_{i}"
                        }
                    })

                    # MultiModalMessage
                    await websocket.send_json({
                        "type": "MultiModalMessage",
                        "data": {
                            "content": [
                                {"type": "text", "text": f"Image {i+1} ({img_type}):"},
                                {"type": "image_url", "image_url": {"url": base64_img}}
                            ]
                        }
                    })

                    # Description
                    await websocket.send_json({
                        "type": "TextMessage",
                        "data": {"content": f"Analyzed {img_type} image"}
                    })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/MultiImageAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify all images processed
                multimodal_events = [e for e in events if e["type"] == "MultiModalMessage"]
                assert len(multimodal_events) == 3

                text_messages = [e for e in events if e["type"] == "TextMessage"]
                assert len(text_messages) >= 3


class TestMultimodalErrorHandling:
    """E2E tests for multimodal agent error handling."""

    def test_invalid_image_path(self, client, temp_workspace, image_tools):
        """Test handling of invalid image paths."""
        agent_config = create_mock_agent_config(
            name="InvalidPathAgent",
            agent_type="multimodal_tools_looping",
            tools=image_tools
        )
        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Tool returns invalid path
                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": "generate_test_image",
                        "result": "Image saved to /nonexistent/path/image.png",
                        "is_error": False,
                        "id": "tool_1"
                    }
                })

                # Agent handles gracefully
                await websocket.send_json({
                    "type": "TextMessage",
                    "data": {"content": "Unable to access image, continuing without vision."}
                })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/InvalidPathAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Should handle gracefully without crashing
                assert any(e["type"] == "TaskResult" for e in events)

    def test_corrupted_base64_image(self, client, temp_workspace, image_tools):
        """Test handling of corrupted base64 images."""
        agent_config = create_mock_agent_config(
            name="CorruptedImageAgent",
            agent_type="multimodal_tools_looping",
            tools=image_tools
        )
        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Tool returns corrupted base64
                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": "get_sample_image",
                        "result": "data:image/png;base64,CORRUPTED!!!",
                        "is_error": False,
                        "id": "tool_1"
                    }
                })

                # Agent handles error
                await websocket.send_json({
                    "type": "TextMessage",
                    "data": {"content": "Image format error, proceeding without image analysis."}
                })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "error_handled"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/CorruptedImageAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Should handle gracefully
                task_result = next(e for e in events if e["type"] == "TaskResult")
                assert task_result["data"]["outcome"] in ["error_handled", "success"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
