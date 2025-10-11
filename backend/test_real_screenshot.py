#!/usr/bin/env python3
"""
Test real screenshot functionality with multimodal agent.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config.config_loader import load_agents, load_tools
from core.agent_factory import create_agent_from_config
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def test_real_screenshot():
    """Test real screenshot with multimodal agent."""
    print("=" * 70)
    print("Real Screenshot Test with Multimodal Agent")
    print("=" * 70)

    # 1. Load agent
    print("\n[1/4] Loading MultimodalVisionAgent...")
    agents_dir = str(Path(__file__).parent / "agents")
    all_agents = load_agents(agents_dir)

    agent_cfg = None
    for agent in all_agents:
        if agent.name == "MultimodalVisionAgent":
            agent_cfg = agent
            break

    if not agent_cfg:
        print("✗ MultimodalVisionAgent not found")
        return False

    print(f"✓ Loaded agent: {agent_cfg.name}")

    # 2. Load tools
    print("\n[2/4] Loading tools...")
    tools_dir = str(Path(__file__).parent / "tools")
    loaded_tools = load_tools(tools_dir)
    all_tools = [tool for tool, _ in loaded_tools]

    screenshot_tool = None
    for tool in all_tools:
        if tool.name == "take_screenshot":
            screenshot_tool = tool
            break

    if not screenshot_tool:
        print("✗ take_screenshot tool not found")
        return False

    print(f"✓ Found take_screenshot tool")

    # 3. Create agent
    print("\n[3/4] Creating agent with model...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("✗ OPENAI_API_KEY not set")
        return False

    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",  # Use mini for faster response
        api_key=api_key
    )

    agent = create_agent_from_config(agent_cfg, all_tools, model_client)
    print(f"✓ Created agent with gpt-4o")

    # 4. Run agent with screenshot task
    print("\n[4/4] Taking screenshot and asking agent to describe it...")
    print("-" * 70)

    task = "Take a screenshot of my current desktop and describe in detail what you see. Include any visible windows, applications, text, colors, and layout."

    screenshot_taken = False
    multimodal_message = False
    description = []

    try:
        async for event in agent.run_stream(task):
            event_type = event.get('type', 'Unknown')
            source = event.get('source', 'Unknown')

            if event_type == 'ToolCallRequestEvent':
                tool_name = event.get('data', {}).get('name', 'unknown')
                if tool_name == 'take_screenshot':
                    print("\n✓ Agent is taking screenshot...")
                    screenshot_taken = True

            elif event_type == 'MultiModalMessage':
                multimodal_message = True
                content = event.get('content', [])
                print(f"\n✓ MultiModalMessage created with {len(content)} items")
                if len(content) > 1:
                    print(f"  → Screenshot image included")

            elif event_type == 'TextMessage' and source == 'MultimodalVisionAgent':
                text = event.get('content', '')
                if text and 'TERMINATE' not in text:
                    description.append(text)
                    print(f"\n[Agent Description]:")
                    print(f"{text[:200]}..." if len(text) > 200 else text)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Results
    print("\n" + "=" * 70)
    print("Test Results:")
    print("=" * 70)

    success = True

    if screenshot_taken:
        print("✓ Screenshot was taken")
    else:
        print("✗ Screenshot was NOT taken")
        success = False

    if multimodal_message:
        print("✓ MultiModalMessage was created")
    else:
        print("✗ MultiModalMessage was NOT created")
        success = False

    if description:
        print("✓ Agent provided description")
        full_desc = " ".join(description)

        # Check for visual elements
        visual_keywords = ['window', 'screen', 'desktop', 'application', 'browser',
                          'terminal', 'text', 'icon', 'menu', 'bar', 'color',
                          'background', 'foreground', 'visible', 'display']
        found = [kw for kw in visual_keywords if kw.lower() in full_desc.lower()]

        if len(found) >= 3:
            print(f"✓ Description contains visual elements: {', '.join(found[:5])}")
        else:
            print(f"⚠ Description may be incomplete (keywords: {', '.join(found)})")
    else:
        print("✗ Agent did NOT provide description")
        success = False

    # Check screenshot file exists
    screenshots_dir = Path(os.getcwd()) / "workspace" / "screenshots"
    if screenshots_dir.exists():
        screenshots = list(screenshots_dir.glob("*.png"))
        if screenshots:
            latest = max(screenshots, key=lambda p: p.stat().st_mtime)
            size_kb = latest.stat().st_size / 1024
            print(f"✓ Screenshot file created: {latest.name} ({size_kb:.1f} KB)")
        else:
            print("⚠ No screenshot files found in workspace/screenshots/")
    else:
        print("⚠ Screenshots directory not created")

    print("\n" + "=" * 70)
    if success:
        print("✓✓✓ REAL SCREENSHOT TEST PASSED ✓✓✓")
        print("\nThe agent successfully:")
        print("  1. Took a real screenshot of your desktop")
        print("  2. Received the image via MultiModalMessage")
        print("  3. 'Saw' and described the actual screen content")
    else:
        print("✗✗✗ REAL SCREENSHOT TEST FAILED ✗✗✗")
    print("=" * 70)

    return success


if __name__ == "__main__":
    result = asyncio.run(test_real_screenshot())
    sys.exit(0 if result else 1)
