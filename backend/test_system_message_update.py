#!/usr/bin/env python3
"""
Test that system message can be customized and updated in MultimodalToolsLoopingAgent.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from core.multimodal_tools_looping_agent import MultimodalToolsLoopingAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient


def test_system_message():
    """Test system message customization."""
    print("=" * 70)
    print("System Message Customization Test")
    print("=" * 70)

    # Create a mock model client
    class MockModelClient:
        def __init__(self):
            self.model_info = {"function_calling": True}

    model_client = MockModelClient()

    # Test 1: Default system message
    print("\n[Test 1] Creating agent with default system message...")
    agent1 = MultimodalToolsLoopingAgent(
        name="VisionAgent1",
        model_client=model_client,
        tools=[]
    )

    if hasattr(agent1, '_system_messages') and agent1._system_messages:
        default_msg = agent1._system_messages[0].content
        print(f"✓ Default system message set:")
        print(f"  '{default_msg[:80]}...'")
        assert "vision capabilities" in default_msg.lower()
        print("✓ Contains vision-related content")
    else:
        print("✗ No system messages found")
        return False

    # Test 2: Custom system message
    print("\n[Test 2] Creating agent with custom system message...")
    custom_message = "You are a specialized screenshot analyzer. Focus on UI elements and layout."
    agent2 = MultimodalToolsLoopingAgent(
        name="VisionAgent2",
        model_client=model_client,
        tools=[],
        system_message=custom_message
    )

    if hasattr(agent2, '_system_messages') and agent2._system_messages:
        actual_msg = agent2._system_messages[0].content
        print(f"✓ Custom system message set:")
        print(f"  '{actual_msg}'")
        assert actual_msg == custom_message
        print("✓ Message matches custom input")
    else:
        print("✗ No system messages found")
        return False

    # Test 3: Update system message
    print("\n[Test 3] Updating system message dynamically...")
    updated_message = "You are now a color analysis expert. Focus on color schemes and palettes."
    agent2.update_system_message(updated_message)

    if hasattr(agent2, '_system_messages') and agent2._system_messages:
        new_msg = agent2._system_messages[0].content
        print(f"✓ System message updated:")
        print(f"  '{new_msg}'")
        assert new_msg == updated_message
        print("✓ Message successfully updated")
    else:
        print("✗ Could not update system message")
        return False

    # Test 4: Via agent_factory
    print("\n[Test 4] Testing with agent_factory...")
    from config.schemas import AgentConfig, LLMConfig, PromptConfig

    config = AgentConfig(
        name="TestVisionAgent",
        agent_type="multimodal_tools_looping",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o"),
        prompt=PromptConfig(
            system="Custom prompt from config: Analyze images for accessibility issues.",
            user="Test task"
        ),
        max_consecutive_auto_reply=10,
        reflect_on_tool_use=True
    )

    from core.agent_factory import create_agent_from_config
    agent3 = create_agent_from_config(config, [], model_client)

    if hasattr(agent3, '_system_messages') and agent3._system_messages:
        config_msg = agent3._system_messages[0].content
        print(f"✓ Agent created from config with system message:")
        print(f"  '{config_msg[:80]}...'")
        assert "accessibility" in config_msg.lower()
        print("✓ Contains config-specified content")
    else:
        print("✗ No system messages in config-created agent")
        return False

    print("\n" + "=" * 70)
    print("✓✓✓ ALL SYSTEM MESSAGE TESTS PASSED ✓✓✓")
    print("=" * 70)
    print("\nSummary:")
    print("  ✓ Default system message works")
    print("  ✓ Custom system message in __init__ works")
    print("  ✓ update_system_message() method works")
    print("  ✓ Agent factory respects prompt.system config")
    return True


if __name__ == "__main__":
    try:
        result = test_system_message()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
