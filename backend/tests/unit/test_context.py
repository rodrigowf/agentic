"""
Unit tests for utils/context.py

Tests agent context management using contextvars for thread-safe agent access.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock

from utils.context import CURRENT_AGENT, get_current_agent
from config.schemas import AgentConfig, LLMConfig, PromptConfig


# ============================================================================
# Test get_current_agent
# ============================================================================


def test_get_current_agent_returns_none_by_default():
    """Test that get_current_agent returns None when no agent is set."""
    # Reset context
    CURRENT_AGENT.set(None)

    agent = get_current_agent()

    assert agent is None


def test_get_current_agent_returns_set_agent():
    """Test that get_current_agent returns the agent that was set."""
    mock_agent = MagicMock()
    mock_agent.name = "TestAgent"

    CURRENT_AGENT.set(mock_agent)

    agent = get_current_agent()

    assert agent is mock_agent
    assert agent.name == "TestAgent"


def test_get_current_agent_with_agent_config():
    """Test get_current_agent with real AgentConfig instance."""
    agent_config = AgentConfig(
        name="RealAgent",
        agent_type="looping",
        tools=["tool1"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="System", user="User")
    )

    CURRENT_AGENT.set(agent_config)

    retrieved = get_current_agent()

    assert retrieved is agent_config
    assert retrieved.name == "RealAgent"
    assert retrieved.agent_type == "looping"


# ============================================================================
# Test Context Isolation
# ============================================================================


def test_context_isolation_between_sequential_sets():
    """Test that context can be changed multiple times sequentially."""
    agent1 = MagicMock()
    agent1.name = "Agent1"

    agent2 = MagicMock()
    agent2.name = "Agent2"

    # Set first agent
    CURRENT_AGENT.set(agent1)
    assert get_current_agent().name == "Agent1"

    # Set second agent
    CURRENT_AGENT.set(agent2)
    assert get_current_agent().name == "Agent2"

    # Set back to None
    CURRENT_AGENT.set(None)
    assert get_current_agent() is None


def test_context_isolation_with_multiple_agents():
    """Test context isolation with multiple different agents."""
    agents = []
    for i in range(5):
        agent = MagicMock()
        agent.name = f"Agent{i}"
        agent.id = i
        agents.append(agent)

    # Set and verify each agent
    for agent in agents:
        CURRENT_AGENT.set(agent)
        retrieved = get_current_agent()
        assert retrieved.name == agent.name
        assert retrieved.id == agent.id


# ============================================================================
# Test Thread Safety
# ============================================================================


def test_context_is_thread_local():
    """Test that context is isolated between threads."""
    results = []

    def thread_function(thread_id):
        """Function to run in each thread."""
        # Create thread-specific agent
        agent = MagicMock()
        agent.name = f"Agent-Thread-{thread_id}"
        agent.thread_id = thread_id

        # Set in this thread's context
        CURRENT_AGENT.set(agent)

        # Small delay to ensure threads overlap
        time.sleep(0.01)

        # Retrieve from context
        retrieved = get_current_agent()

        # Verify it's the correct agent for this thread
        results.append({
            "thread_id": thread_id,
            "set_name": agent.name,
            "retrieved_name": retrieved.name if retrieved else None,
            "match": retrieved is agent if retrieved else False
        })

    # Run in multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=thread_function, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify all threads got their own agent
    assert len(results) == 5
    for result in results:
        assert result["match"] is True
        assert f"Thread-{result['thread_id']}" in result["retrieved_name"]


def test_context_with_thread_pool_executor():
    """Test context isolation using ThreadPoolExecutor."""

    def process_with_agent(agent_id):
        """Process function that uses agent context."""
        agent = MagicMock()
        agent.id = agent_id
        agent.name = f"Agent-{agent_id}"

        CURRENT_AGENT.set(agent)

        # Simulate some work
        time.sleep(0.01)

        # Retrieve and verify
        retrieved = get_current_agent()
        return {
            "agent_id": agent_id,
            "retrieved_id": retrieved.id if retrieved else None,
            "match": retrieved.id == agent_id if retrieved else False
        }

    # Run with thread pool
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_with_agent, i) for i in range(20)]
        results = [future.result() for future in as_completed(futures)]

    # Verify all had correct context
    assert len(results) == 20
    assert all(r["match"] for r in results)


def test_main_thread_context_not_affected_by_child_threads():
    """Test that child threads don't affect main thread context."""
    # Set agent in main thread
    main_agent = MagicMock()
    main_agent.name = "MainAgent"
    CURRENT_AGENT.set(main_agent)

    # Verify main thread context
    assert get_current_agent().name == "MainAgent"

    def child_thread_function():
        """Function that sets different agent in child thread."""
        child_agent = MagicMock()
        child_agent.name = "ChildAgent"
        CURRENT_AGENT.set(child_agent)

        # Verify child has its own context
        assert get_current_agent().name == "ChildAgent"

    # Run child thread
    thread = threading.Thread(target=child_thread_function)
    thread.start()
    thread.join()

    # Verify main thread context unchanged
    assert get_current_agent().name == "MainAgent"


# ============================================================================
# Test Context with Real Agent Operations
# ============================================================================


def test_context_with_agent_config_operations():
    """Test context with real AgentConfig operations."""
    agent = AgentConfig(
        name="OperationAgent",
        agent_type="looping",
        tools=["tool1", "tool2"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.7),
        prompt=PromptConfig(system="System prompt", user="User prompt"),
        max_consecutive_auto_reply=10,
        tool_call_loop=True
    )

    CURRENT_AGENT.set(agent)

    # Retrieve and perform operations
    retrieved = get_current_agent()

    assert retrieved.name == "OperationAgent"
    assert len(retrieved.tools) == 2
    assert retrieved.llm.temperature == 0.7
    assert retrieved.max_consecutive_auto_reply == 10


def test_context_preserves_agent_state():
    """Test that context preserves agent state and attributes."""
    agent = MagicMock()
    agent.name = "StatefulAgent"
    agent.counter = 0
    agent.data = {"key": "value"}

    CURRENT_AGENT.set(agent)

    # Modify agent through context
    retrieved = get_current_agent()
    retrieved.counter += 1
    retrieved.data["new_key"] = "new_value"

    # Verify modifications persist
    agent_again = get_current_agent()
    assert agent_again.counter == 1
    assert agent_again.data["new_key"] == "new_value"


# ============================================================================
# Test Context Reset
# ============================================================================


def test_context_can_be_reset():
    """Test that context can be reset to None."""
    agent = MagicMock()
    agent.name = "TemporaryAgent"

    CURRENT_AGENT.set(agent)
    assert get_current_agent() is not None

    CURRENT_AGENT.set(None)
    assert get_current_agent() is None


def test_context_reset_in_finally_block():
    """Test common pattern of resetting context in finally block."""
    original = get_current_agent()  # May be None

    temp_agent = MagicMock()
    temp_agent.name = "TempAgent"

    try:
        CURRENT_AGENT.set(temp_agent)
        assert get_current_agent().name == "TempAgent"

        # Simulate some work
        _ = get_current_agent()

    finally:
        CURRENT_AGENT.set(original)

    # Context restored
    assert get_current_agent() is original


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_context_with_none_agent():
    """Test that None can be explicitly set as agent."""
    CURRENT_AGENT.set(None)

    agent = get_current_agent()

    assert agent is None


def test_context_multiple_gets_without_set():
    """Test multiple get calls without setting return default."""
    CURRENT_AGENT.set(None)

    for _ in range(5):
        agent = get_current_agent()
        assert agent is None


def test_context_with_agent_having_none_attributes():
    """Test context with agent that has None attributes."""
    agent = MagicMock()
    agent.name = None
    agent.llm = None
    agent.prompt = None

    CURRENT_AGENT.set(agent)

    retrieved = get_current_agent()

    assert retrieved.name is None
    assert retrieved.llm is None
    assert retrieved.prompt is None


def test_context_with_different_object_types():
    """Test that context can hold different types of objects."""
    # Mock agent
    mock_agent = MagicMock()
    mock_agent.type = "mock"

    CURRENT_AGENT.set(mock_agent)
    assert get_current_agent().type == "mock"

    # AgentConfig
    config_agent = AgentConfig(
        name="ConfigAgent",
        agent_type="looping",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    CURRENT_AGENT.set(config_agent)
    assert get_current_agent().name == "ConfigAgent"

    # String (unusual but valid)
    CURRENT_AGENT.set("StringAgent")
    assert get_current_agent() == "StringAgent"

    # Dict (unusual but valid)
    CURRENT_AGENT.set({"name": "DictAgent"})
    assert get_current_agent()["name"] == "DictAgent"


# ============================================================================
# Test Concurrent Access Patterns
# ============================================================================


def test_concurrent_set_and_get_operations():
    """Test concurrent set and get operations from multiple threads."""
    iterations = 100
    num_threads = 10

    def thread_worker(worker_id):
        """Worker that repeatedly sets and gets agent."""
        mismatches = []

        for i in range(iterations):
            agent = MagicMock()
            agent.worker_id = worker_id
            agent.iteration = i

            CURRENT_AGENT.set(agent)

            # Immediate get should return same agent
            retrieved = get_current_agent()

            if retrieved.worker_id != worker_id or retrieved.iteration != i:
                mismatches.append({
                    "expected_worker": worker_id,
                    "expected_iter": i,
                    "got_worker": retrieved.worker_id,
                    "got_iter": retrieved.iteration
                })

        return mismatches

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(thread_worker, i) for i in range(num_threads)]
        all_mismatches = []

        for future in as_completed(futures):
            mismatches = future.result()
            all_mismatches.extend(mismatches)

    # Should have no mismatches - each thread maintains its own context
    assert len(all_mismatches) == 0


def test_context_in_nested_function_calls():
    """Test that context is maintained through nested function calls."""
    agent = MagicMock()
    agent.name = "NestedAgent"

    def level_1():
        """First level function."""
        return level_2()

    def level_2():
        """Second level function."""
        return level_3()

    def level_3():
        """Third level function."""
        return get_current_agent()

    CURRENT_AGENT.set(agent)

    # Call through nested functions
    retrieved = level_1()

    assert retrieved is agent
    assert retrieved.name == "NestedAgent"


# ============================================================================
# Test Integration with Tool Execution Pattern
# ============================================================================


def test_context_in_tool_execution_pattern():
    """Test common pattern of using context during tool execution."""

    def simulate_tool_execution(tool_name):
        """Simulate a tool that needs to access current agent."""
        agent = get_current_agent()

        if agent is None:
            return f"Error: {tool_name} - No agent in context"

        return f"{tool_name} executed by {agent.name}"

    # Set agent
    agent = MagicMock()
    agent.name = "ToolAgent"
    CURRENT_AGENT.set(agent)

    # Execute tools
    result1 = simulate_tool_execution("web_search")
    result2 = simulate_tool_execution("memory_save")

    assert "web_search executed by ToolAgent" == result1
    assert "memory_save executed by ToolAgent" == result2


def test_context_cleanup_pattern():
    """Test context cleanup pattern used in agent execution."""
    original_agent = get_current_agent()

    def execute_with_agent(agent_config):
        """Execute with temporary agent context."""
        previous = get_current_agent()

        try:
            CURRENT_AGENT.set(agent_config)

            # Simulate work
            current = get_current_agent()
            return current.name

        finally:
            # Restore previous context
            CURRENT_AGENT.set(previous)

    # Create test agents
    agent1 = MagicMock()
    agent1.name = "Agent1"

    agent2 = MagicMock()
    agent2.name = "Agent2"

    # Execute with agent1
    CURRENT_AGENT.set(agent1)
    result = execute_with_agent(agent2)

    # Verify agent2 was used
    assert result == "Agent2"

    # Verify agent1 was restored
    assert get_current_agent().name == "Agent1"


# ============================================================================
# Pytest Fixtures for Test Isolation
# ============================================================================


@pytest.fixture(autouse=True)
def reset_context():
    """Reset context before and after each test."""
    # Reset before test
    CURRENT_AGENT.set(None)

    yield

    # Reset after test
    CURRENT_AGENT.set(None)


# ============================================================================
# Pytest Markers
# ============================================================================


pytestmark = pytest.mark.unit
