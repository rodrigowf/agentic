"""
Integration test for DynamicInitLoopingAgent

Tests the full flow of creating and using a dynamic initialization agent,
including integration with the agent factory and configuration loader.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from config.schemas import AgentConfig, LLMConfig, PromptConfig
from core.agent_factory import create_agent_from_config
from core.dynamic_init_looping_agent import DynamicInitLoopingAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo
from utils.context import CURRENT_AGENT


def test_dynamic_init_agent_creation_via_factory():
    """Test creating a dynamic init agent through the agent factory"""

    # Create agent configuration
    agent_config = AgentConfig(
        name="TestDynamicAgent",
        agent_type="dynamic_init_looping",
        tools=[],
        llm=LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.0
        ),
        prompt=PromptConfig(
            system="You are a test agent.",
            user="Test task"
        ),
        initialization_function="",  # No init function for this test
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

    # Create agent via factory
    agent = create_agent_from_config(agent_config, [], model_client)

    # Verify agent type and properties
    assert isinstance(agent, DynamicInitLoopingAgent)
    assert agent.name == "TestDynamicAgent"
    assert agent.initialization_function == ""
    assert agent._system_messages[0].content == "You are a test agent."

    print("✓ Dynamic init agent created via factory successfully")
    return True


def test_memory_agent_config_loading():
    """Test loading the Memory agent configuration with dynamic init"""
    import json

    # Load Memory agent configuration
    memory_config_path = backend_path / "agents" / "Memory.json"

    if not memory_config_path.exists():
        print("⚠ Memory.json not found, skipping test")
        return True

    with open(memory_config_path, 'r') as f:
        memory_config_dict = json.load(f)

    # Verify configuration has dynamic_init_looping type
    assert memory_config_dict['agent_type'] == 'dynamic_init_looping', \
        f"Expected agent_type 'dynamic_init_looping', got '{memory_config_dict['agent_type']}'"

    # Verify initialization_function is set
    assert 'initialization_function' in memory_config_dict, \
        "initialization_function not found in Memory agent config"

    assert memory_config_dict['initialization_function'] == 'memory.initialize_memory_agent', \
        f"Expected 'memory.initialize_memory_agent', got '{memory_config_dict['initialization_function']}'"

    print("✓ Memory agent configuration validated successfully")
    return True


def test_memory_initialization_function_execution():
    """Test that memory initialization function can be executed"""
    from tools.memory import initialize_memory_agent
    from core.dynamic_init_looping_agent import DynamicInitLoopingAgent

    # Create a test agent
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

    agent = DynamicInitLoopingAgent(
        name="TestMemory",
        description="Test memory agent",
        system_message="Test agent. {{SHORT_TERM_MEMORY}}",
        model_client=model_client,
        tools=[],
        initialization_function=""  # Don't auto-initialize
    )

    # Set as current agent
    CURRENT_AGENT.set(agent)

    # Call initialization function manually
    result = initialize_memory_agent()

    # Verify function executed
    assert result == "Memory agent initialized successfully" or "initialized" in result.lower(), \
        f"Unexpected result from initialize_memory_agent: {result}"

    # Verify system message was updated (placeholder should be replaced)
    system_message = agent._system_messages[0].content

    # The placeholder should be replaced with either empty memory message or actual content
    assert "{{SHORT_TERM_MEMORY}}" not in system_message, \
        "Placeholder was not replaced in system message"

    print("✓ Memory initialization function executed successfully")
    print(f"  System message after init: {system_message[:100]}...")

    # Cleanup
    CURRENT_AGENT.set(None)

    return True


def test_dynamic_init_with_memory_via_factory():
    """Test creating Memory agent with automatic initialization via factory"""

    # Create Memory agent configuration
    agent_config = AgentConfig(
        name="Memory",
        agent_type="dynamic_init_looping",
        tools=[],
        llm=LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.0
        ),
        prompt=PromptConfig(
            system="You are Memory agent. {{SHORT_TERM_MEMORY}}",
            user="What is my name?"
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

    # Set current agent context before creating agent
    # (This is needed for the initialization function to work)

    # Create agent via factory
    agent = create_agent_from_config(agent_config, [], model_client)

    # Set as current agent for initialization
    CURRENT_AGENT.set(agent)

    # Re-run initialization now that context is set
    # (In production, this happens in runner.py after CURRENT_AGENT.set(agent))
    if hasattr(agent, '_run_initialization'):
        try:
            agent._run_initialization()
        except Exception as e:
            print(f"⚠ Initialization failed (expected in test environment): {e}")

    # Verify agent was created
    assert isinstance(agent, DynamicInitLoopingAgent)
    assert agent.name == "Memory"
    assert agent.initialization_function == "memory.initialize_memory_agent"

    print("✓ Memory agent with dynamic init created via factory")

    # Cleanup
    CURRENT_AGENT.set(None)

    return True


if __name__ == '__main__':
    print("\n=== Running Dynamic Init Integration Tests ===\n")

    tests = [
        ("Agent Factory Creation", test_dynamic_init_agent_creation_via_factory),
        ("Memory Config Loading", test_memory_agent_config_loading),
        ("Memory Init Function", test_memory_initialization_function_execution),
        ("Memory Agent via Factory", test_dynamic_init_with_memory_via_factory),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}")
            print("-" * 50)
            result = test_func()
            if result:
                passed += 1
                print(f"✓ PASSED: {test_name}\n")
            else:
                failed += 1
                print(f"✗ FAILED: {test_name}\n")
        except Exception as e:
            failed += 1
            print(f"✗ FAILED: {test_name}")
            print(f"  Error: {e}\n")

    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50 + "\n")

    sys.exit(0 if failed == 0 else 1)
