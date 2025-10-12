"""
Unit tests for config/schemas.py

Tests Pydantic data models for agent configuration and data validation.
"""

import pytest
from pydantic import ValidationError

from config.schemas import (
    BaseSchema,
    ToolInfo,
    LLMConfig,
    PromptConfig,
    AgentConfig,
    GenerateToolRequest,
    BaseChatMessage,
)
from tests.fixtures import (
    MOCK_OPENAI_LLM,
    MOCK_ANTHROPIC_LLM,
    MOCK_GOOGLE_LLM,
    MOCK_BASIC_PROMPT,
    MOCK_LOOPING_AGENT,
    MOCK_NESTED_AGENT,
    MOCK_MULTIMODAL_AGENT,
)


# ============================================================================
# Test BaseSchema
# ============================================================================


def test_base_schema_strips_whitespace():
    """Test that BaseSchema strips whitespace from string fields."""

    class TestSchema(BaseSchema):
        name: str
        value: str

    schema = TestSchema(name="  test  ", value="  value  ")

    assert schema.name == "test"
    assert schema.value == "value"


def test_base_schema_forbids_extra_fields():
    """Test that BaseSchema forbids extra fields."""

    class TestSchema(BaseSchema):
        name: str

    with pytest.raises(ValidationError) as exc_info:
        TestSchema(name="test", extra_field="not allowed")

    assert "extra_field" in str(exc_info.value)


# ============================================================================
# Test ToolInfo
# ============================================================================


def test_tool_info_required_fields():
    """Test that ToolInfo requires name, description, and parameters."""
    tool = ToolInfo(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {}}
    )

    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert tool.parameters["type"] == "object"


def test_tool_info_optional_filename():
    """Test that filename is optional."""
    tool = ToolInfo(
        name="test_tool",
        description="A test tool",
        parameters={}
    )

    assert tool.filename is None


def test_tool_info_with_filename():
    """Test that filename can be set."""
    tool = ToolInfo(
        name="test_tool",
        description="A test tool",
        parameters={},
        filename="test_tool.py"
    )

    assert tool.filename == "test_tool.py"


def test_tool_info_validation_errors():
    """Test that ToolInfo validates required fields."""
    with pytest.raises(ValidationError):
        ToolInfo(name="test")  # Missing description and parameters


# ============================================================================
# Test LLMConfig
# ============================================================================


def test_llm_config_required_fields():
    """Test that LLMConfig requires provider and model."""
    llm = LLMConfig(provider="openai", model="gpt-4o-mini")

    assert llm.provider == "openai"
    assert llm.model == "gpt-4o-mini"


def test_llm_config_default_temperature():
    """Test that temperature defaults to 0.0."""
    llm = LLMConfig(provider="openai", model="gpt-4o-mini")

    assert llm.temperature == 0.0


def test_llm_config_default_max_tokens():
    """Test that max_tokens defaults to None."""
    llm = LLMConfig(provider="openai", model="gpt-4o-mini")

    assert llm.max_tokens is None


def test_llm_config_custom_temperature():
    """Test setting custom temperature."""
    llm = LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.7)

    assert llm.temperature == 0.7


def test_llm_config_custom_max_tokens():
    """Test setting custom max_tokens."""
    llm = LLMConfig(provider="openai", model="gpt-4o-mini", max_tokens=2000)

    assert llm.max_tokens == 2000


def test_llm_config_openai():
    """Test OpenAI LLM configuration."""
    llm = MOCK_OPENAI_LLM

    assert llm.provider == "openai"
    assert llm.model == "gpt-4o-mini"


def test_llm_config_anthropic():
    """Test Anthropic LLM configuration."""
    llm = MOCK_ANTHROPIC_LLM

    assert llm.provider == "anthropic"
    assert "claude" in llm.model.lower()


def test_llm_config_google():
    """Test Google LLM configuration."""
    llm = MOCK_GOOGLE_LLM

    assert llm.provider == "google"
    assert "gemini" in llm.model.lower()


def test_llm_config_validation_errors():
    """Test that LLMConfig validates required fields."""
    with pytest.raises(ValidationError):
        LLMConfig(provider="openai")  # Missing model


# ============================================================================
# Test PromptConfig
# ============================================================================


def test_prompt_config_required_fields():
    """Test that PromptConfig requires system and user."""
    prompt = PromptConfig(system="System prompt", user="User prompt")

    assert prompt.system == "System prompt"
    assert prompt.user == "User prompt"


def test_prompt_config_empty_strings():
    """Test that PromptConfig allows empty strings."""
    prompt = PromptConfig(system="", user="")

    assert prompt.system == ""
    assert prompt.user == ""


def test_prompt_config_strips_whitespace():
    """Test that PromptConfig strips leading/trailing whitespace."""
    prompt = PromptConfig(
        system="  System prompt  ",
        user="  User prompt  "
    )

    assert prompt.system == "System prompt"
    assert prompt.user == "User prompt"


def test_prompt_config_validation_errors():
    """Test that PromptConfig validates required fields."""
    with pytest.raises(ValidationError):
        PromptConfig(system="System")  # Missing user


# ============================================================================
# Test AgentConfig
# ============================================================================


def test_agent_config_minimal_looping_agent():
    """Test creating minimal looping agent configuration."""
    agent = AgentConfig(
        name="MinimalAgent",
        agent_type="looping",
        tools=["tool1"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="System", user="User")
    )

    assert agent.name == "MinimalAgent"
    assert agent.agent_type == "looping"
    assert agent.tools == ["tool1"]


def test_agent_config_default_agent_type():
    """Test that agent_type defaults to 'assistant'."""
    agent = AgentConfig(
        name="DefaultAgent",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    assert agent.agent_type == "assistant"


def test_agent_config_default_max_consecutive_auto_reply():
    """Test that max_consecutive_auto_reply defaults to 5."""
    agent = AgentConfig(
        name="Agent",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    assert agent.max_consecutive_auto_reply == 5


def test_agent_config_default_reflect_on_tool_use():
    """Test that reflect_on_tool_use defaults to True."""
    agent = AgentConfig(
        name="Agent",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    assert agent.reflect_on_tool_use is True


def test_agent_config_default_terminate_on_text():
    """Test that terminate_on_text defaults to False."""
    agent = AgentConfig(
        name="Agent",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    assert agent.terminate_on_text is False


def test_agent_config_default_tool_call_loop():
    """Test that tool_call_loop defaults to False."""
    agent = AgentConfig(
        name="Agent",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    assert agent.tool_call_loop is False


def test_agent_config_default_include_inner_dialog():
    """Test that include_inner_dialog defaults to True."""
    agent = AgentConfig(
        name="Agent",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    assert agent.include_inner_dialog is True


def test_agent_config_looping_agent():
    """Test looping agent configuration."""
    agent = MOCK_LOOPING_AGENT

    assert agent.agent_type == "looping"
    assert agent.tool_call_loop is True
    assert len(agent.tools) > 0


def test_agent_config_nested_team_agent():
    """Test nested team agent configuration."""
    agent = MOCK_NESTED_AGENT

    assert agent.agent_type == "nested_team"
    assert agent.mode == "selector"
    assert agent.sub_agents is not None
    assert len(agent.sub_agents) > 0


def test_agent_config_multimodal_agent():
    """Test multimodal agent configuration."""
    agent = MOCK_MULTIMODAL_AGENT

    assert agent.agent_type == "multimodal_tools_looping"
    assert agent.llm.model == "gpt-4o"  # Vision model


def test_agent_config_code_executor_fields():
    """Test code executor specific fields."""
    agent = AgentConfig(
        name="CodeAgent",
        agent_type="code_executor",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user=""),
        code_executor={"type": "local"},
        model_client_stream=True,
        sources=["source1.py", "source2.py"]
    )

    assert agent.code_executor == {"type": "local"}
    assert agent.model_client_stream is True
    assert agent.sources == ["source1.py", "source2.py"]


def test_agent_config_nested_team_fields():
    """Test nested team specific fields."""
    sub_agent = AgentConfig(
        name="SubAgent",
        agent_type="looping",
        tools=["tool1"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    agent = AgentConfig(
        name="TeamAgent",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4-turbo-2024-04-09"),
        prompt=PromptConfig(system="", user=""),
        sub_agents=[sub_agent],
        mode="selector",
        orchestrator_prompt="__function__",
        orchestrator_agent_name="Manager",
        orchestrator_pattern="NEXT AGENT: <Name>"
    )

    assert agent.sub_agents[0].name == "SubAgent"
    assert agent.mode == "selector"
    assert agent.orchestrator_prompt == "__function__"
    assert agent.orchestrator_agent_name == "Manager"
    assert agent.orchestrator_pattern == "NEXT AGENT: <Name>"


def test_agent_config_optional_fields_none():
    """Test that optional fields can be None."""
    agent = AgentConfig(
        name="Agent",
        tools=[],
        llm=None,
        prompt=None,
        code_executor=None,
        sources=None,
        description=None,
        system_message=None,
        sub_agents=None,
        mode=None,
        orchestrator_prompt=None
    )

    assert agent.llm is None
    assert agent.prompt is None
    assert agent.code_executor is None
    assert agent.sources is None
    assert agent.description is None
    assert agent.system_message is None
    assert agent.sub_agents is None
    assert agent.mode is None
    assert agent.orchestrator_prompt is None


def test_agent_config_model_dump():
    """Test serialization with model_dump."""
    agent = AgentConfig(
        name="TestAgent",
        agent_type="looping",
        tools=["tool1"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="System", user="User")
    )

    data = agent.model_dump()

    assert isinstance(data, dict)
    assert data["name"] == "TestAgent"
    assert data["agent_type"] == "looping"
    assert data["tools"] == ["tool1"]
    assert data["llm"]["provider"] == "openai"


def test_agent_config_model_dump_json():
    """Test JSON serialization with model_dump_json."""
    agent = AgentConfig(
        name="TestAgent",
        agent_type="looping",
        tools=["tool1"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="System", user="User")
    )

    json_str = agent.model_dump_json()

    assert isinstance(json_str, str)
    assert "TestAgent" in json_str
    assert "looping" in json_str


def test_agent_config_recursive_sub_agents():
    """Test that sub_agents can contain nested AgentConfig objects."""
    sub_sub_agent = AgentConfig(
        name="SubSubAgent",
        agent_type="looping",
        tools=["tool1"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    sub_agent = AgentConfig(
        name="SubAgent",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user=""),
        sub_agents=[sub_sub_agent]
    )

    top_agent = AgentConfig(
        name="TopAgent",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user=""),
        sub_agents=[sub_agent]
    )

    assert top_agent.sub_agents[0].name == "SubAgent"
    assert top_agent.sub_agents[0].sub_agents[0].name == "SubSubAgent"


def test_agent_config_validation_requires_name():
    """Test that name is required."""
    with pytest.raises(ValidationError) as exc_info:
        AgentConfig(
            tools=[],
            llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
            prompt=PromptConfig(system="", user="")
        )

    assert "name" in str(exc_info.value)


def test_agent_config_validation_requires_tools():
    """Test that tools is required."""
    with pytest.raises(ValidationError) as exc_info:
        AgentConfig(
            name="Agent",
            llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
            prompt=PromptConfig(system="", user="")
        )

    assert "tools" in str(exc_info.value)


# ============================================================================
# Test GenerateToolRequest
# ============================================================================


def test_generate_tool_request_required_fields():
    """Test that GenerateToolRequest requires prompt."""
    request = GenerateToolRequest(prompt="Generate a tool that does X")

    assert request.prompt == "Generate a tool that does X"


def test_generate_tool_request_validation_error():
    """Test that GenerateToolRequest validates required fields."""
    with pytest.raises(ValidationError):
        GenerateToolRequest()  # Missing prompt


# ============================================================================
# Test BaseChatMessage
# ============================================================================


def test_base_chat_message_required_fields():
    """Test that BaseChatMessage requires content and source."""
    message = BaseChatMessage(content="Hello", source="user")

    assert message.content == "Hello"
    assert message.source == "user"


def test_base_chat_message_default_type():
    """Test that type defaults to 'TextMessage'."""
    message = BaseChatMessage(content="Hello", source="user")

    assert message.type == "TextMessage"


def test_base_chat_message_default_models_usage():
    """Test that models_usage defaults to None."""
    message = BaseChatMessage(content="Hello", source="user")

    assert message.models_usage is None


def test_base_chat_message_default_metadata():
    """Test that metadata defaults to empty dict."""
    message = BaseChatMessage(content="Hello", source="user")

    assert message.metadata == {}


def test_base_chat_message_custom_metadata():
    """Test setting custom metadata."""
    message = BaseChatMessage(
        content="Hello",
        source="user",
        metadata={"key": "value"}
    )

    assert message.metadata == {"key": "value"}


def test_base_chat_message_custom_models_usage():
    """Test setting custom models_usage."""
    message = BaseChatMessage(
        content="Hello",
        source="assistant",
        models_usage={"prompt_tokens": 10, "completion_tokens": 5}
    )

    assert message.models_usage["prompt_tokens"] == 10


def test_base_chat_message_model_dump():
    """Test BaseChatMessage serialization."""
    message = BaseChatMessage(
        content="Hello",
        source="user",
        metadata={"key": "value"},
        models_usage={"tokens": 10}
    )

    data = message.model_dump()

    assert data["content"] == "Hello"
    assert data["source"] == "user"
    assert data["metadata"] == {"key": "value"}
    assert data["models_usage"] == {"tokens": 10}
    assert data["type"] == "TextMessage"


def test_base_chat_message_allows_extra_fields():
    """Test that BaseChatMessage allows extra fields (Config: extra = 'allow')."""
    message = BaseChatMessage(
        content="Hello",
        source="user",
        extra_field="allowed"
    )

    # Should not raise ValidationError
    assert message.content == "Hello"


def test_base_chat_message_validation_errors():
    """Test that BaseChatMessage validates required fields."""
    with pytest.raises(ValidationError):
        BaseChatMessage(content="Hello")  # Missing source


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_agent_config_with_all_nested_models():
    """Test creating a complete agent config with all nested models."""
    agent = AgentConfig(
        name="CompleteAgent",
        agent_type="looping",
        tools=["tool1", "tool2"],
        llm=LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=2000
        ),
        prompt=PromptConfig(
            system="You are a helpful assistant.",
            user="Complete the task."
        ),
        code_executor={"type": "local"},
        model_client_stream=True,
        sources=["source.py"],
        description="A complete agent",
        system_message="System message",
        max_consecutive_auto_reply=10,
        reflect_on_tool_use=True,
        terminate_on_text=False,
        tool_call_loop=True,
        include_inner_dialog=True
    )

    # Verify all fields
    assert agent.name == "CompleteAgent"
    assert agent.llm.temperature == 0.7
    assert agent.prompt.system == "You are a helpful assistant."
    assert agent.max_consecutive_auto_reply == 10
    assert agent.tool_call_loop is True


def test_nested_agent_config_serialization_roundtrip():
    """Test that nested agent can be serialized and deserialized."""
    sub_agent = AgentConfig(
        name="SubAgent",
        agent_type="looping",
        tools=["tool1"],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="Sub", user="Task")
    )

    nested_agent = AgentConfig(
        name="NestedAgent",
        agent_type="nested_team",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4-turbo-2024-04-09"),
        prompt=PromptConfig(system="", user=""),
        sub_agents=[sub_agent],
        mode="selector"
    )

    # Serialize
    data = nested_agent.model_dump()

    # Deserialize
    restored = AgentConfig(**data)

    assert restored.name == "NestedAgent"
    assert restored.sub_agents[0].name == "SubAgent"


def test_all_agent_types():
    """Test that all agent types can be created."""
    agent_types = [
        "assistant",
        "looping",
        "nested_team",
        "code_executor",
        "looping_code_executor",
        "multimodal_tools_looping"
    ]

    for agent_type in agent_types:
        agent = AgentConfig(
            name=f"{agent_type}_agent",
            agent_type=agent_type,
            tools=[],
            llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
            prompt=PromptConfig(system="", user="")
        )

        assert agent.agent_type == agent_type


# ============================================================================
# Edge Cases
# ============================================================================


def test_agent_config_empty_tools_list():
    """Test that tools can be an empty list."""
    agent = AgentConfig(
        name="Agent",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user="")
    )

    assert agent.tools == []


def test_llm_config_temperature_boundaries():
    """Test temperature boundary values."""
    # Zero temperature
    llm = LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0)
    assert llm.temperature == 0.0

    # High temperature
    llm = LLMConfig(provider="openai", model="gpt-4o-mini", temperature=2.0)
    assert llm.temperature == 2.0


def test_agent_config_max_consecutive_auto_reply_zero():
    """Test that max_consecutive_auto_reply can be set to 0."""
    agent = AgentConfig(
        name="Agent",
        tools=[],
        llm=LLMConfig(provider="openai", model="gpt-4o-mini"),
        prompt=PromptConfig(system="", user=""),
        max_consecutive_auto_reply=0
    )

    assert agent.max_consecutive_auto_reply == 0


def test_tool_info_empty_parameters():
    """Test that parameters can be an empty dict."""
    tool = ToolInfo(
        name="test_tool",
        description="Test",
        parameters={}
    )

    assert tool.parameters == {}


# ============================================================================
# Pytest Markers
# ============================================================================


pytestmark = pytest.mark.unit
