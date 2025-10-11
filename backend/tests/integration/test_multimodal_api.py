#!/usr/bin/env python3
"""
API-level test for MultimodalToolsLoopingAgent.
Tests the full stack: config loading, agent factory, tool loading, and execution.
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
from config.schemas import AgentConfig
from core.agent_factory import create_agent_from_config
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def test_full_stack():
    """Test the complete API stack with multimodal agent."""
    print("=" * 70)
    print("Multimodal Agent - Full Stack API Test")
    print("=" * 70)

    # 1. Load agent configuration
    print("\n[1/5] Loading agent configuration...")
    try:
        agents_dir = str(Path(__file__).parent / "agents")
        all_agents = load_agents(agents_dir)

        # Find MultimodalVisionAgent
        agent_cfg = None
        for agent in all_agents:
            if agent.name == "MultimodalVisionAgent":
                agent_cfg = agent
                break

        if not agent_cfg:
            print("✗ MultimodalVisionAgent not found")
            return False

        print(f"✓ Loaded agent: {agent_cfg.name}")
        print(f"  - Type: {agent_cfg.agent_type}")
        print(f"  - Model: {agent_cfg.llm.model}")
        print(f"  - Tools: {', '.join(agent_cfg.tools or [])}")
    except Exception as e:
        print(f"✗ Failed to load agent config: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. Load tools
    print("\n[2/5] Loading tools...")
    try:
        tools_dir = str(Path(__file__).parent / "tools")
        loaded_tools = load_tools(tools_dir)
        all_tools = [tool for tool, _ in loaded_tools]
        print(f"✓ Loaded {len(all_tools)} tools")

        # Find our image tools
        image_tool_names = {'take_screenshot', 'generate_test_image', 'get_sample_image'}
        found_tools = [t.name for t in all_tools if t.name in image_tool_names]
        print(f"  - Image tools found: {', '.join(found_tools)}")

        if not found_tools:
            print("⚠ Warning: No image tools found")
    except Exception as e:
        print(f"✗ Failed to load tools: {e}")
        return False

    # 3. Create model client
    print("\n[3/5] Creating model client...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("✗ OPENAI_API_KEY not set")
        return False

    try:
        model_client = OpenAIChatCompletionClient(
            model=agent_cfg.llm.model,
            api_key=api_key
        )
        print(f"✓ Model client created: {agent_cfg.llm.model}")
    except Exception as e:
        print(f"✗ Failed to create model client: {e}")
        return False

    # 4. Create agent via factory
    print("\n[4/5] Creating agent via factory...")
    try:
        agent = create_agent_from_config(agent_cfg, all_tools, model_client)
        print(f"✓ Agent created: {type(agent).__name__}")

        # Verify it's the right type
        from core.multimodal_tools_looping_agent import MultimodalToolsLoopingAgent
        if isinstance(agent, MultimodalToolsLoopingAgent):
            print("  - Confirmed: MultimodalToolsLoopingAgent instance")
        else:
            print(f"  ⚠ Warning: Got {type(agent).__name__} instead of MultimodalToolsLoopingAgent")
    except Exception as e:
        print(f"✗ Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Run agent
    print("\n[5/5] Running agent...")
    print("-" * 70)

    task = "Generate a test image with the text 'Hello Vision World' and describe what you see."

    events_received = 0
    multimodal_messages = 0
    tool_calls = 0
    assistant_messages = 0

    try:
        async for event in agent.run_stream(task):
            events_received += 1
            event_type = event.get('type', 'Unknown')
            source = event.get('source', 'Unknown')

            # Count event types
            if event_type == 'MultiModalMessage':
                multimodal_messages += 1
                content = event.get('content', [])
                print(f"\n✓ MultiModalMessage received!")
                print(f"  - Content items: {len(content)}")
                if len(content) > 1:
                    print(f"  - Images: {len(content) - 1}")

            elif event_type == 'ToolCallRequestEvent':
                tool_calls += 1
                tool_name = event.get('data', {}).get('name', 'unknown')
                print(f"\n[Tool]: {tool_name}")

            elif event_type == 'TextMessage' and source in ['VisionAgent', 'MultimodalVisionAgent']:
                assistant_messages += 1
                content = event.get('content', '')
                if content:
                    preview = content[:80] + "..." if len(content) > 80 else content
                    print(f"\n[Assistant]: {preview}")

    except Exception as e:
        print(f"\n✗ Error during agent execution: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Results
    print("\n" + "=" * 70)
    print("Test Results:")
    print("=" * 70)

    success = True

    print(f"\nEvents received: {events_received}")
    print(f"  - Tool calls: {tool_calls}")
    print(f"  - MultiModalMessages: {multimodal_messages}")
    print(f"  - Assistant messages: {assistant_messages}")

    if events_received == 0:
        print("\n✗ FAILED: No events received")
        success = False
    else:
        print("\n✓ Events received")

    if tool_calls == 0:
        print("✗ FAILED: No tool calls")
        success = False
    else:
        print("✓ Tool calls executed")

    if multimodal_messages == 0:
        print("✗ FAILED: No MultiModalMessages created")
        success = False
    else:
        print("✓ MultiModalMessages created")

    if assistant_messages == 0:
        print("✗ FAILED: No assistant responses")
        success = False
    else:
        print("✓ Assistant responses received")

    print("\n" + "=" * 70)
    if success:
        print("✓✓✓ FULL STACK TEST PASSED ✓✓✓")
    else:
        print("✗✗✗ FULL STACK TEST FAILED ✗✗✗")
    print("=" * 70)

    return success


if __name__ == "__main__":
    result = asyncio.run(test_full_stack())
    sys.exit(0 if result else 1)
