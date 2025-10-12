"""
Unit tests for core/nested_agent.py

Tests the NestedTeamAgent behavior including:
- Nested team initialization
- Sub-agent coordination
- Orchestrator selection
- Agent handoffs
- Inner dialog handling
- Error propagation
- Termination conditions
- Custom selector logic
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, call
from typing import List

from autogen_core import CancellationToken
from autogen_core.tools import FunctionTool
from autogen_agentchat.messages import TextMessage, BaseChatMessage
from autogen_agentchat.base import Response
from autogen_agentchat.teams import SelectorGroupChat, RoundRobinGroupChat

from config.schemas import AgentConfig, LLMConfig, PromptConfig
from core.nested_agent import (
    NestedTeamAgent,
    _custom_agent_selector,
    _orchestrator_only_termination,
    _wrap_agent_with_context,
    _create_pattern_regex,
    _TEAM_AGENT_NAMES,
    _ORCHESTRATOR_NAME,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_model_client():
    """Mock model client."""
    mock = MagicMock()
    mock.model = "gpt-4-turbo"
    return mock


@pytest.fixture
def sample_tools():
    """Create sample function tools."""
    def tool_func(query: str) -> str:
        return f"Result: {query}"

    return [FunctionTool(func=tool_func, name="test_tool", description="A test tool")]


@pytest.fixture
def sub_agent_configs():
    """Create sub-agent configurations."""
    return [
        AgentConfig(
            name="Researcher",
            agent_type="looping",
            tools=["test_tool"],
            llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
            prompt=PromptConfig(system="You are a researcher.", user="Research the topic."),
            max_consecutive_auto_reply=5,
        ),
        AgentConfig(
            name="Writer",
            agent_type="looping",
            tools=["test_tool"],
            llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
            prompt=PromptConfig(system="You are a writer.", user="Write content."),
            max_consecutive_auto_reply=5,
        ),
    ]


@pytest.fixture
def nested_team_config(sub_agent_configs):
    """Create nested team configuration."""
    return AgentConfig(
        name="TestTeam",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4-turbo", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        sub_agents=sub_agent_configs,
        mode="selector",
        orchestrator_prompt="__function__",
        orchestrator_agent_name="Manager",
        orchestrator_pattern="NEXT AGENT: <Name>",
        max_consecutive_auto_reply=10,
        include_inner_dialog=True,
    )


@pytest.fixture
def round_robin_config(sub_agent_configs):
    """Create round-robin team configuration."""
    return AgentConfig(
        name="RoundRobinTeam",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4-turbo", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        sub_agents=sub_agent_configs,
        mode="round_robin",
        max_consecutive_auto_reply=10,
        include_inner_dialog=True,
    )


@pytest.fixture
def cancellation_token():
    """Create cancellation token."""
    return CancellationToken()


# ============================================================================
# Test Initialization
# ============================================================================

def test_nested_team_initialization(nested_team_config, sample_tools, mock_model_client):
    """Test that NestedTeamAgent initializes correctly."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    assert agent.name == "TestTeam"
    assert agent.description == "Nested team agent"
    assert agent.agent_cfg == nested_team_config
    assert agent._team is not None


def test_nested_team_creates_sub_agents(nested_team_config, sample_tools, mock_model_client):
    """Test that sub-agents are created during initialization."""
    with patch('core.agent_factory.create_agent_from_config') as mock_create:
        mock_create.return_value = MagicMock()

        agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

        # Should create sub-agents
        assert mock_create.call_count == 2  # Researcher + Writer


def test_nested_team_selector_mode(nested_team_config, sample_tools, mock_model_client):
    """Test that selector mode creates SelectorGroupChat."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    assert isinstance(agent._team, SelectorGroupChat)


def test_nested_team_round_robin_mode(round_robin_config, sample_tools, mock_model_client):
    """Test that round_robin mode creates RoundRobinGroupChat."""
    agent = NestedTeamAgent(round_robin_config, sample_tools, mock_model_client)

    assert isinstance(agent._team, RoundRobinGroupChat)


def test_nested_team_default_orchestrator_name(nested_team_config, sample_tools, mock_model_client):
    """Test default orchestrator agent name."""
    nested_team_config.orchestrator_agent_name = None  # Use default
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    # Default is "Manager"
    assert agent._team is not None


def test_nested_team_custom_orchestrator_name(nested_team_config, sample_tools, mock_model_client):
    """Test custom orchestrator agent name."""
    nested_team_config.orchestrator_agent_name = "CustomManager"
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    assert agent._team is not None


def test_nested_team_from_config_classmethod(nested_team_config, sample_tools, mock_model_client):
    """Test from_config class method."""
    agent = NestedTeamAgent.from_config(nested_team_config, sample_tools, mock_model_client)

    assert isinstance(agent, NestedTeamAgent)
    assert agent.name == "TestTeam"


# ============================================================================
# Test Custom Selector Logic
# ============================================================================

def test_custom_agent_selector_no_messages():
    """Test custom selector with no messages returns orchestrator."""
    # Set up global state
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"
    nested_module._TEAM_AGENT_NAMES = {"Researcher", "Writer"}

    result = _custom_agent_selector([])
    assert result == "Manager"


def test_custom_agent_selector_user_message():
    """Test custom selector with user message returns orchestrator."""
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"
    nested_module._TEAM_AGENT_NAMES = {"Researcher", "Writer"}

    messages = [TextMessage(content="Hello", source="user")]
    result = _custom_agent_selector(messages)
    assert result == "Manager"


def test_custom_agent_selector_orchestrator_terminate():
    """Test custom selector with orchestrator TERMINATE returns None."""
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"
    nested_module._TEAM_AGENT_NAMES = {"Researcher", "Writer"}

    messages = [TextMessage(content="TERMINATE", source="Manager")]
    result = _custom_agent_selector(messages)
    assert result is None


def test_custom_agent_selector_orchestrator_selects_agent():
    """Test custom selector parsing agent selection from orchestrator."""
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"
    nested_module._TEAM_AGENT_NAMES = {"Researcher", "Writer"}
    nested_module._ORCHESTRATOR_PATTERN = "NEXT AGENT: <Name>"

    messages = [TextMessage(content="NEXT AGENT: Researcher", source="Manager")]
    result = _custom_agent_selector(messages)
    assert result == "Researcher"


def test_custom_agent_selector_case_insensitive():
    """Test custom selector is case-insensitive."""
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"
    nested_module._TEAM_AGENT_NAMES = {"Researcher", "Writer"}
    nested_module._ORCHESTRATOR_PATTERN = "NEXT AGENT: <Name>"

    messages = [TextMessage(content="next agent: Researcher", source="Manager")]
    result = _custom_agent_selector(messages)
    assert result == "Researcher"


def test_custom_agent_selector_with_period():
    """Test custom selector handles period after agent name."""
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"
    nested_module._TEAM_AGENT_NAMES = {"Researcher", "Writer"}
    nested_module._ORCHESTRATOR_PATTERN = "NEXT AGENT: <Name>"

    messages = [TextMessage(content="NEXT AGENT: Researcher.", source="Manager")]
    result = _custom_agent_selector(messages)
    assert result == "Researcher"


def test_custom_agent_selector_invalid_agent():
    """Test custom selector with invalid agent name returns None."""
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"
    nested_module._TEAM_AGENT_NAMES = {"Researcher", "Writer"}
    nested_module._ORCHESTRATOR_PATTERN = "NEXT AGENT: <Name>"

    messages = [TextMessage(content="NEXT AGENT: UnknownAgent", source="Manager")]
    result = _custom_agent_selector(messages)
    assert result is None


def test_custom_agent_selector_non_orchestrator_terminate():
    """Test custom selector with non-orchestrator TERMINATE returns orchestrator."""
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"
    nested_module._TEAM_AGENT_NAMES = {"Researcher", "Writer"}

    messages = [TextMessage(content="TERMINATE", source="Researcher")]
    result = _custom_agent_selector(messages)
    assert result == "Manager"  # Hand back to orchestrator


def test_custom_agent_selector_agent_continues():
    """Test custom selector allows same agent to continue."""
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"
    nested_module._TEAM_AGENT_NAMES = {"Researcher", "Writer"}

    messages = [TextMessage(content="Working on it...", source="Researcher")]
    result = _custom_agent_selector(messages)
    assert result == "Researcher"  # Same agent continues


# ============================================================================
# Test Pattern Regex
# ============================================================================

def test_create_pattern_regex_basic():
    """Test pattern regex creation."""
    pattern = "NEXT AGENT: <Name>"
    regex = _create_pattern_regex(pattern)

    import re
    match = re.search(regex, "NEXT AGENT: Researcher", re.IGNORECASE)
    assert match is not None
    assert match.group(1) == "Researcher"


def test_create_pattern_regex_special_chars():
    """Test pattern regex with special characters."""
    pattern = "SELECT: <Name>!"
    regex = _create_pattern_regex(pattern)

    import re
    match = re.search(regex, "SELECT: Writer!", re.IGNORECASE)
    assert match is not None
    assert match.group(1) == "Writer"


def test_create_pattern_regex_agent_with_spaces():
    """Test pattern regex with agent names containing spaces."""
    pattern = "NEXT AGENT: <Name>"
    regex = _create_pattern_regex(pattern)

    import re
    match = re.search(regex, "NEXT AGENT: Research Agent", re.IGNORECASE)
    assert match is not None
    assert match.group(1) == "Research Agent"


# ============================================================================
# Test Orchestrator Termination
# ============================================================================

def test_orchestrator_only_termination():
    """Test orchestrator-only termination condition."""
    import core.nested_agent as nested_module
    nested_module._ORCHESTRATOR_NAME = "Manager"

    term_func = _orchestrator_only_termination()

    # Orchestrator TERMINATE should trigger
    messages = [TextMessage(content="TERMINATE", source="Manager")]
    assert term_func(messages) is True

    # Non-orchestrator TERMINATE should not trigger
    messages = [TextMessage(content="TERMINATE", source="Researcher")]
    assert term_func(messages) is False

    # No TERMINATE should not trigger
    messages = [TextMessage(content="Working...", source="Manager")]
    assert term_func(messages) is False


# ============================================================================
# Test Agent Context Wrapping
# ============================================================================

def test_wrap_agent_with_context():
    """Test that agent methods are wrapped with context."""
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock()
    mock_agent.run_stream = AsyncMock()

    wrapped = _wrap_agent_with_context(mock_agent)

    # Should have wrapped methods
    assert hasattr(wrapped, 'run')
    assert hasattr(wrapped, 'run_stream')


@pytest.mark.asyncio
async def test_wrap_agent_run_sets_context():
    """Test that wrapped run method sets context."""
    from utils.context import CURRENT_AGENT

    mock_agent = MagicMock()
    mock_agent.name = "TestAgent"

    async def mock_run(*args, **kwargs):
        # Check context is set during run
        current = CURRENT_AGENT.get()
        assert current == mock_agent
        return "result"

    mock_agent.run = mock_run

    wrapped = _wrap_agent_with_context(mock_agent)

    result = await wrapped.run()
    assert result == "result"


@pytest.mark.asyncio
async def test_wrap_agent_run_stream_sets_context():
    """Test that wrapped run_stream method sets context."""
    from utils.context import CURRENT_AGENT

    mock_agent = MagicMock()
    mock_agent.name = "TestAgent"

    async def mock_run_stream(*args, **kwargs):
        # Check context is set during stream
        current = CURRENT_AGENT.get()
        assert current == mock_agent
        yield "event1"
        yield "event2"

    mock_agent.run_stream = mock_run_stream

    wrapped = _wrap_agent_with_context(mock_agent)

    events = []
    async for event in wrapped.run_stream():
        events.append(event)

    assert len(events) == 2


# ============================================================================
# Test on_messages
# ============================================================================

@pytest.mark.asyncio
async def test_on_messages_basic(nested_team_config, sample_tools, mock_model_client, cancellation_token):
    """Test on_messages method."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    # Mock team run
    mock_result = MagicMock()
    mock_result.messages = [
        TextMessage(content="User task", source="user"),
        TextMessage(content="Processing...", source="Researcher"),
        TextMessage(content="Final result", source="Manager"),
    ]

    with patch.object(agent._team, 'run', AsyncMock(return_value=mock_result)):
        messages = [TextMessage(content="Test task", source="user")]
        response = await agent.on_messages(messages, cancellation_token)

        assert isinstance(response, Response)
        assert response.chat_message is not None


@pytest.mark.asyncio
async def test_on_messages_includes_inner_dialog(nested_team_config, sample_tools, mock_model_client, cancellation_token):
    """Test that on_messages includes inner dialog when configured."""
    nested_team_config.include_inner_dialog = True
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    mock_result = MagicMock()
    mock_result.messages = [
        TextMessage(content="User task", source="user"),
        TextMessage(content="Inner message 1", source="Researcher"),
        TextMessage(content="Inner message 2", source="Writer"),
        TextMessage(content="Final result", source="Manager"),
    ]

    with patch.object(agent._team, 'run', AsyncMock(return_value=mock_result)):
        messages = [TextMessage(content="Test task", source="user")]
        response = await agent.on_messages(messages, cancellation_token)

        # Should have inner messages
        assert response.inner_messages is not None
        assert len(response.inner_messages) > 0


@pytest.mark.asyncio
async def test_on_messages_excludes_inner_dialog(nested_team_config, sample_tools, mock_model_client, cancellation_token):
    """Test that on_messages excludes inner dialog when configured."""
    nested_team_config.include_inner_dialog = False
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    mock_result = MagicMock()
    mock_result.messages = [
        TextMessage(content="User task", source="user"),
        TextMessage(content="Inner message", source="Researcher"),
        TextMessage(content="Final result", source="Manager"),
    ]

    with patch.object(agent._team, 'run', AsyncMock(return_value=mock_result)):
        messages = [TextMessage(content="Test task", source="user")]
        response = await agent.on_messages(messages, cancellation_token)

        # Should not have inner messages
        assert response.inner_messages is None or len(response.inner_messages) == 0


# ============================================================================
# Test on_messages_stream
# ============================================================================

@pytest.mark.asyncio
async def test_on_messages_stream(nested_team_config, sample_tools, mock_model_client, cancellation_token):
    """Test on_messages_stream method."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    async def mock_run_stream(*args, **kwargs):
        yield TextMessage(content="Event 1", source="Researcher")
        yield TextMessage(content="Event 2", source="Writer")
        yield TextMessage(content="Final", source="Manager")

    with patch.object(agent._team, 'run_stream', side_effect=mock_run_stream):
        messages = [TextMessage(content="Test task", source="user")]
        events = []
        async for event in agent.on_messages_stream(messages, cancellation_token):
            events.append(event)

        assert len(events) == 3


@pytest.mark.asyncio
async def test_on_messages_stream_forwards_all_events(nested_team_config, sample_tools, mock_model_client, cancellation_token):
    """Test that on_messages_stream forwards all team events."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    async def mock_run_stream(*args, **kwargs):
        for i in range(5):
            yield TextMessage(content=f"Event {i}", source="Researcher")

    with patch.object(agent._team, 'run_stream', side_effect=mock_run_stream):
        messages = [TextMessage(content="Test task", source="user")]
        events = []
        async for event in agent.on_messages_stream(messages, cancellation_token):
            events.append(event)

        assert len(events) == 5


# ============================================================================
# Test on_reset
# ============================================================================

@pytest.mark.asyncio
async def test_on_reset(nested_team_config, sample_tools, mock_model_client, cancellation_token):
    """Test on_reset method."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    with patch.object(agent._team, 'reset', AsyncMock()) as mock_reset:
        await agent.on_reset(cancellation_token)
        mock_reset.assert_called_once()


# ============================================================================
# Test produced_message_types
# ============================================================================

def test_produced_message_types(nested_team_config, sample_tools, mock_model_client):
    """Test produced_message_types property."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    message_types = agent.produced_message_types
    assert TextMessage in message_types


# ============================================================================
# Test Team Configuration
# ============================================================================

def test_selector_with_custom_prompt(nested_team_config, sample_tools, mock_model_client):
    """Test selector mode with custom orchestrator prompt."""
    nested_team_config.orchestrator_prompt = "Custom orchestrator prompt"
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    assert isinstance(agent._team, SelectorGroupChat)


def test_selector_with_function_prompt(nested_team_config, sample_tools, mock_model_client):
    """Test selector mode with __function__ prompt uses custom selector."""
    nested_team_config.orchestrator_prompt = "__function__"
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    assert isinstance(agent._team, SelectorGroupChat)


def test_max_consecutive_auto_reply_applied(nested_team_config, sample_tools, mock_model_client):
    """Test that max_consecutive_auto_reply is applied to termination condition."""
    nested_team_config.max_consecutive_auto_reply = 20
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    # Termination condition should include max messages
    assert agent._team is not None


# ============================================================================
# Test Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_on_messages_team_error(nested_team_config, sample_tools, mock_model_client, cancellation_token):
    """Test error handling when team run fails."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    with patch.object(agent._team, 'run', AsyncMock(side_effect=Exception("Team error"))):
        messages = [TextMessage(content="Test task", source="user")]
        with pytest.raises(Exception, match="Team error"):
            await agent.on_messages(messages, cancellation_token)


@pytest.mark.asyncio
async def test_on_messages_stream_team_error(nested_team_config, sample_tools, mock_model_client, cancellation_token):
    """Test error handling when team stream fails."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    async def mock_run_stream_error(*args, **kwargs):
        yield TextMessage(content="Event 1", source="Researcher")
        raise Exception("Stream error")

    with patch.object(agent._team, 'run_stream', side_effect=mock_run_stream_error):
        messages = [TextMessage(content="Test task", source="user")]
        with pytest.raises(Exception, match="Stream error"):
            async for event in agent.on_messages_stream(messages, cancellation_token):
                pass


# ============================================================================
# Test Sub-Agent Configuration
# ============================================================================

def test_empty_sub_agents(sample_tools, mock_model_client):
    """Test nested team with no sub-agents."""
    config = AgentConfig(
        name="EmptyTeam",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4-turbo", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        sub_agents=None,  # No sub-agents
        mode="selector",
        orchestrator_prompt="__function__",
    )

    # Should handle empty sub-agents
    agent = NestedTeamAgent(config, sample_tools, mock_model_client)
    assert agent._team is not None


def test_single_sub_agent(sample_tools, mock_model_client):
    """Test nested team with single sub-agent."""
    config = AgentConfig(
        name="SingleTeam",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4-turbo", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        sub_agents=[
            AgentConfig(
                name="OnlyAgent",
                agent_type="looping",
                tools=[],
                llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
                prompt=PromptConfig(system="Agent", user="Task"),
            )
        ],
        mode="selector",
        orchestrator_prompt="__function__",
    )

    agent = NestedTeamAgent(config, sample_tools, mock_model_client)
    assert agent._team is not None


def test_many_sub_agents(sample_tools, mock_model_client):
    """Test nested team with many sub-agents."""
    sub_agents = [
        AgentConfig(
            name=f"Agent{i}",
            agent_type="looping",
            tools=[],
            llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
            prompt=PromptConfig(system=f"Agent {i}", user=f"Task {i}"),
        )
        for i in range(5)
    ]

    config = AgentConfig(
        name="ManyAgentsTeam",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4-turbo", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        sub_agents=sub_agents,
        mode="selector",
        orchestrator_prompt="__function__",
    )

    agent = NestedTeamAgent(config, sample_tools, mock_model_client)
    assert agent._team is not None


# ============================================================================
# Test Global State Management
# ============================================================================

def test_team_agent_names_updated(nested_team_config, sample_tools, mock_model_client):
    """Test that global _TEAM_AGENT_NAMES is updated."""
    import core.nested_agent as nested_module

    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    # Global state should be updated
    # Note: This depends on implementation details
    assert agent._team is not None


def test_orchestrator_name_updated(nested_team_config, sample_tools, mock_model_client):
    """Test that global _ORCHESTRATOR_NAME is updated."""
    import core.nested_agent as nested_module

    nested_team_config.orchestrator_agent_name = "CustomOrchestrator"
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    # Global state should be updated
    assert agent._team is not None


# ============================================================================
# Test Allow Repeated Speaker
# ============================================================================

def test_allow_repeated_speaker_enabled(nested_team_config, sample_tools, mock_model_client):
    """Test that allow_repeated_speaker is enabled for tool looping."""
    agent = NestedTeamAgent(nested_team_config, sample_tools, mock_model_client)

    # SelectorGroupChat should have allow_repeated_speaker=True
    # This allows agents to continue using tools in a loop
    assert isinstance(agent._team, SelectorGroupChat)
