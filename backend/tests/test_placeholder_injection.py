#!/usr/bin/env python3
"""
Test script to verify {{AVAILABLE_AGENTS}} placeholder injection in nested_team agents.
This simulates the nested_team agent initialization without requiring API keys.
"""

import sys
sys.path.insert(0, '.')

from config.config_loader import load_agents, load_tools
from config.schemas import AgentConfig
from core.agent_factory import create_agent_from_config
from unittest.mock import MagicMock

def test_placeholder_injection():
    """Test that nested_team agent injects agent descriptions into Manager's system prompt"""

    print("=" * 80)
    print("Testing {{AVAILABLE_AGENTS}} Placeholder Injection")
    print("=" * 80)

    # Load all agent configs
    all_agents = load_agents('agents')
    print(f"\n✅ Loaded {len(all_agents)} agent configs")

    # Find MainConversation
    main_conv = None
    for cfg in all_agents:
        if cfg.name == 'MainConversation':
            main_conv = cfg
            break

    if not main_conv:
        print("\n❌ ERROR: MainConversation not found!")
        return False

    print(f"✅ Found MainConversation with sub-agents: {[a.name for a in main_conv.sub_agents]}")

    # Load tools
    tools_list = load_tools('tools')
    tools = [t[0] for t in tools_list]
    print(f"✅ Loaded {len(tools)} tools")

    # Create a mock model client (don't need real API)
    mock_model_client = MagicMock()

    try:
        # Create the nested team agent (this should trigger placeholder injection)
        print("\n🔄 Creating nested team agent...")
        nested_agent = create_agent_from_config(main_conv, tools, mock_model_client)
        print(f"✅ Created nested team agent: {nested_agent.name}")

        # Find the Manager agent in the team
        manager_agent = None
        for agent in nested_agent._team._participants:
            if agent.name == 'Manager':
                manager_agent = agent
                break

        if not manager_agent:
            print("\n❌ ERROR: Manager agent not found in team!")
            return False

        print(f"✅ Found Manager agent in team")

        # Get the system message
        if not manager_agent._system_messages:
            print("\n❌ ERROR: Manager has no system messages!")
            return False

        system_msg = manager_agent._system_messages[0].content

        # Check if placeholder was replaced
        print("\n" + "=" * 80)
        print("Manager System Message (first 1500 chars):")
        print("=" * 80)
        print(system_msg[:1500])
        print("...")
        print("=" * 80)

        # Verify placeholder was replaced
        if '{{AVAILABLE_AGENTS}}' in system_msg:
            print("\n❌ FAILURE: Placeholder was NOT replaced!")
            return False
        else:
            print("\n✅ SUCCESS: Placeholder was replaced!")

        # Check that expected agents are listed
        expected_agents = ['Memory', 'FileManager', 'Database', 'Researcher', 'Engineer']
        missing_agents = []
        for agent_name in expected_agents:
            if agent_name not in system_msg:
                missing_agents.append(agent_name)

        if missing_agents:
            print(f"⚠️  WARNING: Some agents not found in system message: {missing_agents}")
        else:
            print(f"✅ All expected agents found in system message: {expected_agents}")

        # Check format
        if 'The agents involved in this conversation besides you are:' in system_msg:
            print("✅ Correct formatting used")
        else:
            print("⚠️  WARNING: Expected formatting not found")

        return True

    except Exception as e:
        print(f"\n❌ ERROR during agent creation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_placeholder_injection()

    print("\n" + "=" * 80)
    if success:
        print("✅ TEST PASSED: Placeholder injection working correctly!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("❌ TEST FAILED: Placeholder injection not working!")
        print("=" * 80)
        sys.exit(1)
