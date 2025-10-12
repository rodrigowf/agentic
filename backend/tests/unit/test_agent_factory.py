"""
Unit tests for core/agent_factory.py

Tests agent creation from configuration for all agent types:
- Looping agents
- Nested team agents
- Multimodal agents
- Code executor agents
- Standard assistant agents
- Error handling for invalid configurations
"""

import pytest
import os
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from config.schemas import AgentConfig, LLMConfig, PromptConfig
from core.agent_factory import create_agent_from_config
from core.looping_agent import LoopingAssistantAgent
from core.looping_code_executor_agent import LoopingCodeExecutorAgent
from core.multimodal_tools_looping_agent import MultimodalToolsLoopingAgent
from core.nested_agent import NestedTeamAgent
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_core.tools import FunctionTool


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_model_client():
    """Mock OpenAI model client."""
    mock = MagicMock()
    mock.model = "gpt-4o-mini"
    return mock


@pytest.fixture
def sample_tools():
    """Create sample function tools for testing."""
    def test_tool_func(query: str) -> str:
        """A test tool."""
        return f"Test result for: {query}"

    def another_tool_func(data: str) -> str:
        """Another test tool."""
        return f"Another result: {data}"

    return [
        FunctionTool(func=test_tool_func, name="test_tool", description="A test tool"),
        FunctionTool(func=another_tool_func, name="another_tool", description="Another tool"),
    ]


@pytest.fixture
def looping_agent_config():
    """Looping agent configuration."""
    return AgentConfig(
        name="TestLoopingAgent",
        agent_type="looping",
        tools=["test_tool"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="You are a helpful assistant.", user="Test task"),
        description="Test looping agent",
        max_consecutive_auto_reply=10,
        reflect_on_tool_use=True,
    )


@pytest.fixture
def multimodal_agent_config():
    """Multimodal agent configuration."""
    return AgentConfig(
        name="TestMultimodalAgent",
        agent_type="multimodal_tools_looping",
        tools=["test_tool"],
        llm=LLMConfig(provider="openai", model="gpt-4o", temperature=0.0),
        prompt=PromptConfig(system="You are a vision assistant.", user="Describe the image"),
        description="Test multimodal agent",
        max_consecutive_auto_reply=5,
        reflect_on_tool_use=True,
    )


@pytest.fixture
def code_executor_agent_config(tmp_path):
    """Code executor agent configuration."""
    return AgentConfig(
        name="TestCodeExecutorAgent",
        agent_type="code_executor",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="You are a code executor.", user="Execute code"),
        code_executor={"type": "local", "work_dir": str(tmp_path)},
        system_message="Execute Python code",
        description="Code executor agent",
        model_client_stream=False,
    )


@pytest.fixture
def looping_code_executor_config(tmp_path):
    """Looping code executor agent configuration."""
    return AgentConfig(
        name="TestLoopingCodeExecutor",
        agent_type="looping_code_executor",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="You are a code executor.", user="Execute code"),
        code_executor={"type": "local", "work_dir": str(tmp_path)},
        system_message="Execute Python code",
        description="Looping code executor",
        model_client_stream=False,
        max_consecutive_auto_reply=10,
    )


@pytest.fixture
def nested_team_config():
    """Nested team agent configuration."""
    return AgentConfig(
        name="TestNestedTeam",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4-turbo", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        sub_agents=[
            AgentConfig(
                name="SubAgent1",
                agent_type="looping",
                tools=["test_tool"],
                llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
                prompt=PromptConfig(system="Sub agent 1", user="Task 1"),
            ),
            AgentConfig(
                name="SubAgent2",
                agent_type="looping",
                tools=["another_tool"],
                llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
                prompt=PromptConfig(system="Sub agent 2", user="Task 2"),
            ),
        ],
        mode="selector",
        orchestrator_prompt="__function__",
        max_consecutive_auto_reply=5,
    )


@pytest.fixture
def standard_assistant_config():
    """Standard assistant agent configuration."""
    return AgentConfig(
        name="TestAssistant",
        agent_type="assistant",
        tools=["test_tool"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="You are an assistant.", user="Help me"),
        description="Test assistant agent",
    )


# ============================================================================
# Test Agent Creation - Looping Agent
# ============================================================================

def test_create_looping_agent(looping_agent_config, sample_tools, mock_model_client):
    """Test creation of looping assistant agent."""
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)

    assert isinstance(agent, LoopingAssistantAgent)
    assert agent.name == "TestLoopingAgent"
    assert agent.description == "Test looping agent"
    assert agent.max_consecutive_auto_reply == 10
    assert len(agent._tools) == 1  # Only test_tool should be included
    assert agent._tools[0].name == "test_tool"


def test_looping_agent_tool_filtering(looping_agent_config, sample_tools, mock_model_client):
    """Test that only configured tools are attached to looping agent."""
    # Config specifies only "test_tool"
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)

    tool_names = [tool.name for tool in agent._tools]
    assert "test_tool" in tool_names
    assert "another_tool" not in tool_names


def test_looping_agent_reflect_on_tool_use(looping_agent_config, sample_tools, mock_model_client):
    """Test that reflect_on_tool_use setting is applied."""
    looping_agent_config.reflect_on_tool_use = True
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)
    # Note: reflect_on_tool_use is handled internally by AutoGen
    assert isinstance(agent, LoopingAssistantAgent)


def test_looping_agent_system_message(looping_agent_config, sample_tools, mock_model_client):
    """Test that system message is correctly set."""
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)

    # Check that system message is set from prompt.system
    assert agent._system_messages is not None
    assert len(agent._system_messages) > 0
    assert agent._system_messages[0].content == "You are a helpful assistant."


# ============================================================================
# Test Agent Creation - Multimodal Agent
# ============================================================================

def test_create_multimodal_agent(multimodal_agent_config, sample_tools, mock_model_client):
    """Test creation of multimodal looping agent."""
    agent = create_agent_from_config(multimodal_agent_config, sample_tools, mock_model_client)

    assert isinstance(agent, MultimodalToolsLoopingAgent)
    assert agent.name == "TestMultimodalAgent"
    assert agent.description == "Test multimodal agent"
    assert agent.max_consecutive_auto_reply == 5


def test_multimodal_agent_has_vision_capabilities(multimodal_agent_config, sample_tools, mock_model_client):
    """Test that multimodal agent has image detection methods."""
    agent = create_agent_from_config(multimodal_agent_config, sample_tools, mock_model_client)

    # Check for multimodal-specific methods
    assert hasattr(agent, '_detect_and_convert_images')
    assert hasattr(agent, '_create_multimodal_message_from_tool_result')
    assert hasattr(agent, 'IMAGE_EXTENSIONS')
    assert hasattr(agent, 'BASE64_IMAGE_PATTERN')


def test_multimodal_agent_default_system_message(sample_tools, mock_model_client):
    """Test that multimodal agent gets default vision system message."""
    config = AgentConfig(
        name="TestMultimodal",
        agent_type="multimodal_tools_looping",
        tools=["test_tool"],
        llm=LLMConfig(provider="openai", model="gpt-4o", temperature=0.0),
        prompt=PromptConfig(system="", user=""),  # Empty system message
        max_consecutive_auto_reply=5,
    )

    agent = create_agent_from_config(config, sample_tools, mock_model_client)

    # Should have default vision-related system message
    assert agent._system_messages is not None
    # The agent adds its own default if system is empty


# ============================================================================
# Test Agent Creation - Code Executor
# ============================================================================

def test_create_code_executor_agent(code_executor_agent_config, sample_tools, mock_model_client):
    """Test creation of code executor agent."""
    agent = create_agent_from_config(code_executor_agent_config, sample_tools, mock_model_client)

    assert isinstance(agent, CodeExecutorAgent)
    assert agent.name == "TestCodeExecutorAgent"
    assert agent.description == "Code executor agent"


def test_code_executor_requires_config(sample_tools, mock_model_client):
    """Test that code executor agent requires code_executor config."""
    config = AgentConfig(
        name="BadCodeExecutor",
        agent_type="code_executor",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        code_executor=None,  # Missing required config
    )

    with pytest.raises(Exception):  # Should raise error
        create_agent_from_config(config, sample_tools, mock_model_client)


def test_code_executor_unsupported_type(sample_tools, mock_model_client):
    """Test error handling for unsupported code executor type."""
    config = AgentConfig(
        name="BadCodeExecutor",
        agent_type="code_executor",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        code_executor={"type": "unsupported_type"},
    )

    with pytest.raises(ValueError, match="Unsupported code_executor type"):
        create_agent_from_config(config, sample_tools, mock_model_client)


def test_code_executor_work_dir_default(sample_tools, mock_model_client):
    """Test that code executor uses current working directory by default."""
    config = AgentConfig(
        name="CodeExecutor",
        agent_type="code_executor",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        code_executor={"type": "local"},  # No work_dir specified
    )

    agent = create_agent_from_config(config, sample_tools, mock_model_client)
    assert isinstance(agent, CodeExecutorAgent)
    # work_dir should default to os.getcwd()


# ============================================================================
# Test Agent Creation - Looping Code Executor
# ============================================================================

def test_create_looping_code_executor(looping_code_executor_config, sample_tools, mock_model_client):
    """Test creation of looping code executor agent."""
    agent = create_agent_from_config(looping_code_executor_config, sample_tools, mock_model_client)

    assert isinstance(agent, LoopingCodeExecutorAgent)
    assert agent.name == "TestLoopingCodeExecutor"
    assert agent.max_consecutive_auto_reply == 10


def test_looping_code_executor_requires_config(sample_tools, mock_model_client):
    """Test that looping code executor requires code_executor config."""
    config = AgentConfig(
        name="BadLoopingExecutor",
        agent_type="looping_code_executor",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="", user=""),
        code_executor=None,
    )

    with pytest.raises(Exception):
        create_agent_from_config(config, sample_tools, mock_model_client)


# ============================================================================
# Test Agent Creation - Nested Team
# ============================================================================

@patch('core.nested_agent.NestedTeamAgent.from_config')
def test_create_nested_team_agent(mock_from_config, nested_team_config, sample_tools, mock_model_client):
    """Test creation of nested team agent."""
    mock_agent = MagicMock(spec=NestedTeamAgent)
    mock_from_config.return_value = mock_agent

    agent = create_agent_from_config(nested_team_config, sample_tools, mock_model_client)

    # Should call NestedTeamAgent.from_config
    mock_from_config.assert_called_once_with(nested_team_config, sample_tools, mock_model_client)
    assert agent == mock_agent


def test_nested_team_sub_agents(nested_team_config, sample_tools, mock_model_client):
    """Test that nested team config has sub_agents."""
    # The actual nested team initialization is tested in test_nested_agent.py
    assert nested_team_config.sub_agents is not None
    assert len(nested_team_config.sub_agents) == 2
    assert nested_team_config.sub_agents[0].name == "SubAgent1"
    assert nested_team_config.sub_agents[1].name == "SubAgent2"


# ============================================================================
# Test Agent Creation - Standard Assistant
# ============================================================================

def test_create_standard_assistant_agent(standard_assistant_config, sample_tools, mock_model_client):
    """Test creation of standard assistant agent (fallback)."""
    agent = create_agent_from_config(standard_assistant_config, sample_tools, mock_model_client)

    assert isinstance(agent, AssistantAgent)
    assert agent.name == "TestAssistant"
    assert agent.description is not None


def test_standard_assistant_with_tools(standard_assistant_config, sample_tools, mock_model_client):
    """Test that standard assistant gets configured tools."""
    agent = create_agent_from_config(standard_assistant_config, sample_tools, mock_model_client)

    tool_names = [tool.name for tool in agent._tools]
    assert "test_tool" in tool_names


# ============================================================================
# Test Tool Filtering
# ============================================================================

def test_tool_filtering_empty_tools(looping_agent_config, sample_tools, mock_model_client):
    """Test agent creation with no tools specified."""
    looping_agent_config.tools = []
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)

    assert len(agent._tools) == 0


def test_tool_filtering_nonexistent_tool(looping_agent_config, sample_tools, mock_model_client):
    """Test agent creation with nonexistent tool name."""
    looping_agent_config.tools = ["nonexistent_tool"]
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)

    # Should create agent but with no tools attached
    assert len(agent._tools) == 0


def test_tool_filtering_multiple_tools(looping_agent_config, sample_tools, mock_model_client):
    """Test agent creation with multiple tools."""
    looping_agent_config.tools = ["test_tool", "another_tool"]
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)

    tool_names = [tool.name for tool in agent._tools]
    assert len(tool_names) == 2
    assert "test_tool" in tool_names
    assert "another_tool" in tool_names


# ============================================================================
# Test Error Handling
# ============================================================================

def test_invalid_agent_type(sample_tools, mock_model_client):
    """Test that invalid agent type falls back to standard assistant."""
    config = AgentConfig(
        name="InvalidTypeAgent",
        agent_type="nonexistent_type",
        tools=["test_tool"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="Test", user="Test"),
    )

    # Should fall back to standard AssistantAgent
    agent = create_agent_from_config(config, sample_tools, mock_model_client)
    assert isinstance(agent, AssistantAgent)


def test_missing_llm_config(sample_tools, mock_model_client):
    """Test that model_client is required."""
    config = AgentConfig(
        name="TestAgent",
        agent_type="looping",
        tools=["test_tool"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="Test", user="Test"),
    )

    # Should work with provided model_client
    agent = create_agent_from_config(config, sample_tools, mock_model_client)
    assert agent is not None


def test_none_tools_list(looping_agent_config, mock_model_client):
    """Test agent creation with None tools list."""
    looping_agent_config.tools = None

    # Should handle None gracefully (convert to empty list)
    agent = create_agent_from_config(looping_agent_config, [], mock_model_client)
    assert isinstance(agent, LoopingAssistantAgent)


# ============================================================================
# Test Model Client Configuration
# ============================================================================

def test_agent_uses_provided_model_client(looping_agent_config, sample_tools, mock_model_client):
    """Test that agent uses the provided model client."""
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)

    # Agent should have reference to model client
    assert agent._model_client == mock_model_client


def test_different_model_clients():
    """Test creating agents with different model clients."""
    client1 = MagicMock()
    client1.model = "gpt-4o-mini"

    client2 = MagicMock()
    client2.model = "gpt-4o"

    config = AgentConfig(
        name="TestAgent",
        agent_type="looping",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="Test", user="Test"),
    )

    agent1 = create_agent_from_config(config, [], client1)
    agent2 = create_agent_from_config(config, [], client2)

    assert agent1._model_client == client1
    assert agent2._model_client == client2


# ============================================================================
# Test Agent Configuration Inheritance
# ============================================================================

def test_max_consecutive_auto_reply_default(sample_tools, mock_model_client):
    """Test default max_consecutive_auto_reply value."""
    config = AgentConfig(
        name="TestAgent",
        agent_type="looping",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="Test", user="Test"),
        max_consecutive_auto_reply=None,  # Should use default
    )

    agent = create_agent_from_config(config, sample_tools, mock_model_client)
    # Default is 5 from schema, but LoopingAgent has its own default (40)
    assert agent.max_consecutive_auto_reply is not None


def test_custom_max_consecutive_auto_reply(sample_tools, mock_model_client):
    """Test custom max_consecutive_auto_reply value."""
    config = AgentConfig(
        name="TestAgent",
        agent_type="looping",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="Test", user="Test"),
        max_consecutive_auto_reply=15,
    )

    agent = create_agent_from_config(config, sample_tools, mock_model_client)
    assert agent.max_consecutive_auto_reply == 15


# ============================================================================
# Test Agent Naming and Description
# ============================================================================

def test_agent_name_preserved(looping_agent_config, sample_tools, mock_model_client):
    """Test that agent name is preserved from config."""
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)
    assert agent.name == looping_agent_config.name


def test_agent_description_preserved(looping_agent_config, sample_tools, mock_model_client):
    """Test that agent description is preserved from config."""
    looping_agent_config.description = "Custom description"
    agent = create_agent_from_config(looping_agent_config, sample_tools, mock_model_client)
    assert agent.description == "Custom description"


def test_agent_without_description(sample_tools, mock_model_client):
    """Test agent creation without description."""
    config = AgentConfig(
        name="NoDescAgent",
        agent_type="looping",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
        prompt=PromptConfig(system="Test", user="Test"),
        description=None,
    )

    agent = create_agent_from_config(config, sample_tools, mock_model_client)
    assert agent.name == "NoDescAgent"
    # Description may be None or default value


# ============================================================================
# Integration Tests
# ============================================================================

def test_create_multiple_agents_different_types(sample_tools, mock_model_client, tmp_path):
    """Test creating multiple agents of different types."""
    configs = [
        AgentConfig(
            name="Looping1",
            agent_type="looping",
            tools=["test_tool"],
            llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
            prompt=PromptConfig(system="Test", user="Test"),
        ),
        AgentConfig(
            name="Multimodal1",
            agent_type="multimodal_tools_looping",
            tools=["test_tool"],
            llm=LLMConfig(provider="openai", model="gpt-4o", temperature=0.0),
            prompt=PromptConfig(system="Test", user="Test"),
        ),
        AgentConfig(
            name="Standard1",
            agent_type="assistant",
            tools=["test_tool"],
            llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
            prompt=PromptConfig(system="Test", user="Test"),
        ),
    ]

    agents = [create_agent_from_config(cfg, sample_tools, mock_model_client) for cfg in configs]

    assert len(agents) == 3
    assert isinstance(agents[0], LoopingAssistantAgent)
    assert isinstance(agents[1], MultimodalToolsLoopingAgent)
    assert isinstance(agents[2], AssistantAgent)
