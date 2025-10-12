"""
Unit tests for core/looping_agent.py

Tests the LoopingAssistantAgent behavior including:
- Agent initialization
- Configuration parameters
- Method signatures
- Tool assignment
- System message handling

Note: Full streaming behavior is tested in integration tests since it
requires complex integration with the AutoGen framework.
"""

import pytest
import asyncio
import inspect
from unittest.mock import MagicMock

from autogen_core import CancellationToken
from autogen_core.tools import FunctionTool
from autogen_agentchat.messages import TextMessage, BaseChatMessage

from core.looping_agent import LoopingAssistantAgent, DEFAULT_MAX_ITERS


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_model_client():
    """Mock model client for testing."""
    mock = MagicMock()
    mock.model = "gpt-4o-mini"
    return mock


@pytest.fixture
def sample_tool():
    """Create a sample function tool."""
    def test_func(query: str) -> str:
        """Test function."""
        return f"Result for: {query}"

    return FunctionTool(func=test_func, name="test_tool", description="A test tool")


@pytest.fixture
def looping_agent(mock_model_client, sample_tool):
    """Create a LoopingAssistantAgent instance."""
    return LoopingAssistantAgent(
        name="TestAgent",
        description="A test looping agent",
        system_message="You are a helpful assistant. Say TERMINATE when done.",
        model_client=mock_model_client,
        tools=[sample_tool],
        reflect_on_tool_use=True,
        max_consecutive_auto_reply=10,
    )


@pytest.fixture
def cancellation_token():
    """Create a cancellation token."""
    return CancellationToken()


# ============================================================================
# Test Initialization
# ============================================================================

def test_looping_agent_initialization(looping_agent, sample_tool):
    """Test that LoopingAssistantAgent initializes correctly."""
    assert looping_agent.name == "TestAgent"
    assert looping_agent.description == "A test looping agent"
    assert looping_agent.max_consecutive_auto_reply == 10
    assert len(looping_agent._tools) == 1
    assert looping_agent._tools[0].name == "test_tool"


def test_looping_agent_default_max_iters(mock_model_client, sample_tool):
    """Test default max_consecutive_auto_reply value."""
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
    )

    assert agent.max_consecutive_auto_reply == DEFAULT_MAX_ITERS


def test_looping_agent_custom_max_iters(mock_model_client, sample_tool):
    """Test custom max_consecutive_auto_reply value."""
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
        max_consecutive_auto_reply=25,
    )

    assert agent.max_consecutive_auto_reply == 25


def test_looping_agent_zero_max_iters(mock_model_client, sample_tool):
    """Test agent with max_consecutive_auto_reply set to 0."""
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
        max_consecutive_auto_reply=0,
    )

    assert agent.max_consecutive_auto_reply == 0


def test_looping_agent_system_message(looping_agent):
    """Test that system message is correctly set."""
    assert looping_agent._system_messages is not None
    assert len(looping_agent._system_messages) > 0
    assert "helpful assistant" in looping_agent._system_messages[0].content.lower()


def test_looping_agent_inherits_assistant_agent(looping_agent):
    """Test that LoopingAssistantAgent inherits from AssistantAgent."""
    from autogen_agentchat.agents import AssistantAgent
    assert isinstance(looping_agent, AssistantAgent)


def test_looping_agent_with_no_tools(mock_model_client):
    """Test creating agent with no tools."""
    agent = LoopingAssistantAgent(
        name="NoToolsAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[],
    )

    assert len(agent._tools) == 0


def test_looping_agent_with_multiple_tools(mock_model_client):
    """Test creating agent with multiple tools."""
    def tool1_func(x: str) -> str:
        return f"Tool1: {x}"

    def tool2_func(y: str) -> str:
        return f"Tool2: {y}"

    tools = [
        FunctionTool(func=tool1_func, name="tool1", description="First tool"),
        FunctionTool(func=tool2_func, name="tool2", description="Second tool"),
    ]

    agent = LoopingAssistantAgent(
        name="MultiToolAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=tools,
    )

    assert len(agent._tools) == 2
    assert agent._tools[0].name == "tool1"
    assert agent._tools[1].name == "tool2"


# ============================================================================
# Test Method Signatures
# ============================================================================

def test_run_stream_method_exists(looping_agent):
    """Test that run_stream method exists and is async."""
    assert hasattr(looping_agent, 'run_stream')
    assert asyncio.iscoroutinefunction(looping_agent.run_stream)


def test_run_stream_accepts_task_parameter(looping_agent):
    """Test that run_stream accepts task parameter."""
    sig = inspect.signature(looping_agent.run_stream)
    assert 'task' in sig.parameters


def test_run_stream_accepts_cancellation_token(looping_agent):
    """Test that run_stream accepts cancellation_token parameter."""
    sig = inspect.signature(looping_agent.run_stream)
    assert 'cancellation_token' in sig.parameters


def test_run_stream_returns_async_iterator(looping_agent):
    """Test that run_stream returns an async iterator."""
    sig = inspect.signature(looping_agent.run_stream)
    # Check return annotation exists
    assert sig.return_annotation is not inspect.Signature.empty


# ============================================================================
# Test Reflection on Tool Use
# ============================================================================

def test_reflect_on_tool_use_enabled(mock_model_client, sample_tool):
    """Test agent with reflection on tool use enabled."""
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
        reflect_on_tool_use=True,
    )

    # reflect_on_tool_use is passed to parent AssistantAgent
    assert agent is not None


def test_reflect_on_tool_use_disabled(mock_model_client, sample_tool):
    """Test agent with reflection on tool use disabled."""
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
        reflect_on_tool_use=False,
    )

    assert agent is not None


# ============================================================================
# Test Configuration
# ============================================================================

def test_agent_name_property(looping_agent):
    """Test that agent name is accessible."""
    assert looping_agent.name == "TestAgent"


def test_agent_description_property(looping_agent):
    """Test that agent description is accessible."""
    assert looping_agent.description == "A test looping agent"


def test_agent_model_client_property(looping_agent, mock_model_client):
    """Test that agent has model client."""
    assert looping_agent._model_client == mock_model_client


def test_agent_tools_property(looping_agent):
    """Test that agent tools are accessible."""
    assert hasattr(looping_agent, '_tools')
    assert isinstance(looping_agent._tools, list)


def test_agent_system_messages_property(looping_agent):
    """Test that agent system messages are accessible."""
    assert hasattr(looping_agent, '_system_messages')
    assert isinstance(looping_agent._system_messages, list)


# ============================================================================
# Test Edge Cases
# ============================================================================

def test_agent_with_none_max_reply(mock_model_client, sample_tool):
    """Test agent initialization with None max_consecutive_auto_reply."""
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
        max_consecutive_auto_reply=None,  # Should use default
    )

    assert agent.max_consecutive_auto_reply == DEFAULT_MAX_ITERS


def test_agent_with_large_max_reply(mock_model_client, sample_tool):
    """Test agent with very large max_consecutive_auto_reply."""
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
        max_consecutive_auto_reply=1000,
    )

    assert agent.max_consecutive_auto_reply == 1000


def test_agent_with_empty_system_message(mock_model_client, sample_tool):
    """Test agent with empty system message."""
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="",
        model_client=mock_model_client,
        tools=[sample_tool],
    )

    assert agent._system_messages is not None


def test_agent_with_long_system_message(mock_model_client, sample_tool):
    """Test agent with very long system message."""
    long_message = "x" * 10000
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message=long_message,
        model_client=mock_model_client,
        tools=[sample_tool],
    )

    assert agent._system_messages[0].content == long_message


def test_agent_with_none_description(mock_model_client, sample_tool):
    """Test agent with None description."""
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description=None,
        system_message="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
    )

    assert agent.name == "TestAgent"


def test_agent_with_unicode_name(mock_model_client, sample_tool):
    """Test agent with unicode characters in name."""
    agent = LoopingAssistantAgent(
        name="测试Agent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[sample_tool],
    )

    assert agent.name == "测试Agent"


# ============================================================================
# Test Constants
# ============================================================================

def test_default_max_iters_constant():
    """Test that DEFAULT_MAX_ITERS constant is defined."""
    assert DEFAULT_MAX_ITERS is not None
    assert isinstance(DEFAULT_MAX_ITERS, int)
    assert DEFAULT_MAX_ITERS > 0


def test_default_max_iters_value():
    """Test that DEFAULT_MAX_ITERS has expected value."""
    assert DEFAULT_MAX_ITERS == 40


# ============================================================================
# Test Tool Assignment
# ============================================================================

def test_tools_are_function_tools(looping_agent):
    """Test that assigned tools are FunctionTool instances."""
    for tool in looping_agent._tools:
        assert isinstance(tool, FunctionTool)


def test_tool_names_preserved(mock_model_client):
    """Test that tool names are preserved."""
    def my_tool(x: str) -> str:
        return x

    tool = FunctionTool(func=my_tool, name="custom_name", description="Test")
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[tool],
    )

    assert agent._tools[0].name == "custom_name"


def test_tool_descriptions_preserved(mock_model_client):
    """Test that tool descriptions are preserved."""
    def my_tool(x: str) -> str:
        return x

    tool = FunctionTool(func=my_tool, name="tool", description="Custom description")
    agent = LoopingAssistantAgent(
        name="TestAgent",
        description="Test",
        system_message="Test",
        model_client=mock_model_client,
        tools=[tool],
    )

    assert agent._tools[0].description == "Custom description"


# ============================================================================
# Test Model Client
# ============================================================================

def test_model_client_is_stored(looping_agent, mock_model_client):
    """Test that model client is stored in agent."""
    assert looping_agent._model_client == mock_model_client


def test_different_model_clients():
    """Test creating agents with different model clients."""
    client1 = MagicMock()
    client1.model = "model1"

    client2 = MagicMock()
    client2.model = "model2"

    agent1 = LoopingAssistantAgent(
        name="Agent1",
        description="Test",
        system_message="Test",
        model_client=client1,
        tools=[],
    )

    agent2 = LoopingAssistantAgent(
        name="Agent2",
        description="Test",
        system_message="Test",
        model_client=client2,
        tools=[],
    )

    assert agent1._model_client == client1
    assert agent2._model_client == client2


# ============================================================================
# Test Instance Creation
# ============================================================================

def test_multiple_agent_instances(mock_model_client, sample_tool):
    """Test creating multiple independent agent instances."""
    agent1 = LoopingAssistantAgent(
        name="Agent1",
        description="First agent",
        system_message="System 1",
        model_client=mock_model_client,
        tools=[sample_tool],
        max_consecutive_auto_reply=5,
    )

    agent2 = LoopingAssistantAgent(
        name="Agent2",
        description="Second agent",
        system_message="System 2",
        model_client=mock_model_client,
        tools=[],
        max_consecutive_auto_reply=15,
    )

    # Verify independence
    assert agent1.name != agent2.name
    assert agent1.description != agent2.description
    assert agent1.max_consecutive_auto_reply != agent2.max_consecutive_auto_reply
    assert len(agent1._tools) != len(agent2._tools)
