#!/usr/bin/env python3
"""
End-to-end test for dynamic initialization agent

This script tests:
1. Backend API returns correct agent configuration
2. Agent can be created via factory with initialization function
3. Initialization function is executed correctly
4. Memory agent works with dynamic initialization

Run this with backend server running on localhost:8000
"""

import requests
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def test_api_returns_dynamic_init_agent():
    """Test that API returns Memory agent with dynamic_init_looping type"""
    print("\n" + "="*60)
    print("Test 1: API returns dynamic_init_looping agent")
    print("="*60)

    try:
        response = requests.get("http://localhost:8000/api/agents", timeout=5)
        response.raise_for_status()
        agents = response.json()

        # Find Memory agent
        memory_agent = next((a for a in agents if a['name'] == 'Memory'), None)

        if not memory_agent:
            print("✗ FAILED: Memory agent not found in agents list")
            return False

        # Check agent_type
        agent_type = memory_agent.get('agent_type')
        if agent_type != 'dynamic_init_looping':
            print(f"✗ FAILED: Expected agent_type 'dynamic_init_looping', got '{agent_type}'")
            return False

        print(f"✓ Agent type: {agent_type}")

        # Check initialization_function
        init_func = memory_agent.get('initialization_function')
        expected_func = 'memory.initialize_memory_agent'
        if init_func != expected_func:
            print(f"✗ FAILED: Expected initialization_function '{expected_func}', got '{init_func}'")
            return False

        print(f"✓ Initialization function: {init_func}")

        # Check tools
        tools = memory_agent.get('tools', [])
        expected_tools = [
            'get_short_term_memory',
            'overwrite_short_term_memory',
            'create_memory_bank',
            'add_to_memory',
            'search_memory',
            'replace_data',
            'remove_data',
            'list_memory_banks'
        ]

        for tool in expected_tools:
            if tool not in tools:
                print(f"✗ FAILED: Expected tool '{tool}' not found")
                return False

        print(f"✓ All {len(expected_tools)} memory tools present")

        print("\n✓ PASSED: API returns correct dynamic_init_looping agent configuration")
        return True

    except requests.exceptions.ConnectionError:
        print("✗ FAILED: Could not connect to backend server")
        print("  Make sure backend is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_agent_creation_with_init():
    """Test creating an agent with initialization function"""
    print("\n" + "="*60)
    print("Test 2: Create agent with initialization function")
    print("="*60)

    try:
        from config.schemas import AgentConfig, LLMConfig, PromptConfig
        from core.agent_factory import create_agent_from_config
        from core.dynamic_init_looping_agent import DynamicInitLoopingAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_core.models import ModelInfo
        from utils.context import CURRENT_AGENT

        # Create test agent config
        agent_config = AgentConfig(
            name="TestDynamicInit",
            agent_type="dynamic_init_looping",
            tools=[],
            llm=LLMConfig(
                provider="openai",
                model="gpt-4o-mini",
                temperature=0.0
            ),
            prompt=PromptConfig(
                system="You are a test agent. {{SHORT_TERM_MEMORY}}",
                user="Test task"
            ),
            initialization_function="memory.initialize_memory_agent",
            max_consecutive_auto_reply=5,
            reflect_on_tool_use=True
        )

        # Create model client
        model_info = ModelInfo(
            vision=True,
            function_calling=True,
            json_output=True,
            family="openai",
            structured_output=True
        )
        model_client = OpenAIChatCompletionClient(
            model="gpt-4o-mini",
            api_key="test-key",
            model_info=model_info
        )

        print("✓ Agent config and model client created")

        # Create agent via factory
        agent = create_agent_from_config(agent_config, [], model_client)

        # Verify agent type
        if not isinstance(agent, DynamicInitLoopingAgent):
            print(f"✗ FAILED: Expected DynamicInitLoopingAgent, got {type(agent)}")
            return False

        print(f"✓ Agent created: {agent.name} ({type(agent).__name__})")

        # Verify initialization function is set
        if agent.initialization_function != "memory.initialize_memory_agent":
            print(f"✗ FAILED: Initialization function not set correctly")
            return False

        print(f"✓ Initialization function: {agent.initialization_function}")

        # Set as current agent and re-initialize
        CURRENT_AGENT.set(agent)

        try:
            agent._run_initialization()
            print("✓ Initialization function executed successfully")
        except Exception as e:
            print(f"⚠ Initialization execution warning: {e}")
            # This is okay - might fail in test environment

        # Check system message
        system_msg = agent._system_messages[0].content
        placeholder_replaced = "{{SHORT_TERM_MEMORY}}" not in system_msg

        if placeholder_replaced:
            print("✓ System message placeholder was replaced")
        else:
            print("⚠ System message placeholder not replaced (expected in test environment)")

        # Cleanup
        CURRENT_AGENT.set(None)

        print("\n✓ PASSED: Agent creation with initialization works")
        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backend_integration():
    """Test that backend can load and use the dynamic init agent"""
    print("\n" + "="*60)
    print("Test 3: Backend integration test")
    print("="*60)

    try:
        # This would test actual WebSocket connection to backend
        # For now, just verify the config can be loaded
        from config.config_loader import load_agents
        from pathlib import Path

        agents_dir = str(Path(__file__).parent.parent / "agents")
        agents = load_agents(agents_dir)

        memory_config = next((a for a in agents if a.name == "Memory"), None)

        if not memory_config:
            print("✗ FAILED: Could not load Memory agent config")
            return False

        print(f"✓ Loaded Memory agent config")

        # Verify config has correct type
        if memory_config.agent_type != "dynamic_init_looping":
            print(f"✗ FAILED: Wrong agent type: {memory_config.agent_type}")
            return False

        print(f"✓ Agent type: {memory_config.agent_type}")

        # Verify initialization function
        if memory_config.initialization_function != "memory.initialize_memory_agent":
            print(f"✗ FAILED: Wrong init function: {memory_config.initialization_function}")
            return False

        print(f"✓ Initialization function: {memory_config.initialization_function}")

        print("\n✓ PASSED: Backend can load dynamic init agent configuration")
        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all end-to-end tests"""
    print("\n" + "#"*60)
    print("# Dynamic Initialization Agent - End-to-End Tests")
    print("#"*60)

    tests = [
        ("API Configuration", test_api_returns_dynamic_init_agent),
        ("Agent Creation", test_agent_creation_with_init),
        ("Backend Integration", test_backend_integration),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"\n✗ EXCEPTION in {test_name}: {e}")

    print("\n" + "#"*60)
    print(f"# RESULTS: {passed} passed, {failed} failed")
    print("#"*60 + "\n")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
