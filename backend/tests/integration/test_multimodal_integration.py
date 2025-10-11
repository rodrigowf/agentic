#!/usr/bin/env python3
"""
Simple integration test for MultimodalToolsLoopingAgent.
Tests that the agent can use a tool that returns an image and describe it.
"""

import asyncio
import os
import sys
from pathlib import Path
from PIL import Image as PILImage, ImageDraw, ImageFont
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from core.multimodal_tools_looping_agent import MultimodalToolsLoopingAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.tools import FunctionTool


def create_test_chart():
    """Create a simple test chart image."""
    workspace = Path(os.getcwd()) / "workspace"
    workspace.mkdir(exist_ok=True)

    # Create a colorful bar chart
    img = PILImage.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)

    # Draw bars with different colors
    bars = [
        (50, 100, 80, 250, 'red', 'Q1'),
        (120, 80, 150, 250, 'blue', 'Q2'),
        (190, 120, 220, 250, 'green', 'Q3'),
        (260, 60, 290, 250, 'orange', 'Q4'),
    ]

    for x1, y1, x2, y2, color, label in bars:
        draw.rectangle([x1, y1, x2, y2], fill=color, outline='black')
        draw.text((x1, y2 + 10), label, fill='black')

    # Title
    draw.text((120, 20), "Quarterly Sales Chart", fill='black')

    # Save
    image_path = workspace / "test_chart.png"
    img.save(image_path)
    print(f"✓ Created test chart: {image_path}")

    return f"Chart saved to {image_path}"


async def main():
    """Run integration test."""
    print("=" * 60)
    print("Multimodal Tools Looping Agent - Integration Test")
    print("=" * 60)

    # 1. Create model client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("✗ OPENAI_API_KEY not set")
        return False

    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=api_key
    )
    print("✓ Model client created (gpt-4o-mini)")

    # 2. Create tool
    test_tool = FunctionTool(
        func=create_test_chart,
        name="create_test_chart",
        description="Create a test quarterly sales bar chart image"
    )
    print("✓ Tool created (create_test_chart)")

    # 3. Create agent
    agent = MultimodalToolsLoopingAgent(
        name="VisionAgent",
        model_client=model_client,
        tools=[test_tool],
        system_message=(
            "You are a helpful assistant with vision capabilities. "
            "Use the create_test_chart tool to get a chart image, then describe "
            "what you see in detail (colors, data, layout). "
            "Say TERMINATE when done."
        ),
        max_consecutive_auto_reply=10
    )
    print("✓ Multimodal agent created")

    # 4. Run agent
    print("\n" + "-" * 60)
    print("Running agent task...")
    print("-" * 60)

    task = "Create the test chart and describe what you see in it."

    multimodal_message_found = False
    assistant_response_found = False
    assistant_text = []

    try:
        async for event in agent.run_stream(task):
            event_type = event.get('type', 'Unknown')
            source = event.get('source', 'Unknown')

            # Track if we got a multimodal message
            if event_type == 'MultiModalMessage':
                multimodal_message_found = True
                print(f"\n✓ MultiModalMessage detected!")
                content = event.get('content', [])
                print(f"  - Content items: {len(content)}")
                if len(content) > 1:
                    print(f"  - Images: {len(content) - 1}")

            # Track assistant responses
            elif event_type == 'TextMessage' and source == 'VisionAgent':
                assistant_response_found = True
                text_content = event.get('content', '')
                if text_content:
                    assistant_text.append(text_content)
                    print(f"\n[Assistant]: {text_content[:100]}...")

            # Show tool calls
            elif event_type == 'ToolCallRequestEvent':
                tool_name = event.get('data', {}).get('name', 'unknown')
                print(f"\n[Tool Call]: {tool_name}")

    except Exception as e:
        print(f"\n✗ Error during agent execution: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Verify results
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    success = True

    if multimodal_message_found:
        print("✓ MultiModalMessage was created")
    else:
        print("✗ MultiModalMessage was NOT created")
        success = False

    if assistant_response_found:
        print("✓ Assistant provided response")
    else:
        print("✗ Assistant did NOT provide response")
        success = False

    # Check if assistant described the chart
    full_response = " ".join(assistant_text).lower()
    keywords = ['chart', 'bar', 'color', 'sales', 'quarterly', 'q1', 'q2', 'q3', 'q4']
    found_keywords = [kw for kw in keywords if kw in full_response]

    if len(found_keywords) >= 3:
        print(f"✓ Assistant described the chart (found keywords: {', '.join(found_keywords)})")
    else:
        print(f"⚠ Assistant response unclear (found keywords: {', '.join(found_keywords)})")
        print(f"  Full response: {full_response[:200]}...")

    print("\n" + "=" * 60)
    if success:
        print("✓ Integration test PASSED")
    else:
        print("✗ Integration test FAILED")
    print("=" * 60)

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
