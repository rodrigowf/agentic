"""
Mock agent configurations for testing.

This module provides mock agent configurations that match the AgentConfig schema.
These can be used across different test files for consistent testing.
"""

from typing import Dict, Any, Optional, List
from config.schemas import AgentConfig, LLMConfig, PromptConfig


# ============================================================================
# Mock LLM Configurations
# ============================================================================

MOCK_OPENAI_LLM = LLMConfig(
    provider="openai",
    model="gpt-4o-mini",
    temperature=0.0,
    max_tokens=None
)

MOCK_OPENAI_VISION_LLM = LLMConfig(
    provider="openai",
    model="gpt-4o",
    temperature=0.0,
    max_tokens=None
)

MOCK_ANTHROPIC_LLM = LLMConfig(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    temperature=0.0,
    max_tokens=4096
)

MOCK_GOOGLE_LLM = LLMConfig(
    provider="google",
    model="gemini-1.5-pro",
    temperature=0.0,
    max_tokens=None
)


# ============================================================================
# Mock Prompt Configurations
# ============================================================================

MOCK_BASIC_PROMPT = PromptConfig(
    system="You are a helpful AI assistant.",
    user="Help the user with their task."
)

MOCK_RESEARCH_PROMPT = PromptConfig(
    system="You are a professional web researcher. Use tools to gather information and say TERMINATE when done.",
    user="Research the topic provided by the user."
)

MOCK_VISION_PROMPT = PromptConfig(
    system="You are an AI assistant with vision capabilities. Describe images in detail and say TERMINATE when done.",
    user="Analyze the images provided and describe what you see."
)

MOCK_DEVELOPER_PROMPT = PromptConfig(
    system="You are a software developer. Write code and use tools to solve problems. Say TERMINATE when done.",
    user="Develop the requested feature."
)

MOCK_MEMORY_PROMPT = PromptConfig(
    system="You are a memory manager. Your short-term memory: {{SHORT_TERM_MEMORY}}. Use tools to manage memories.",
    user="Manage user's information and memories."
)


# ============================================================================
# Mock Agent Configurations
# ============================================================================

MOCK_LOOPING_AGENT = AgentConfig(
    name="TestLoopingAgent",
    agent_type="looping",
    tools=["web_search", "fetch_web_content"],
    llm=MOCK_OPENAI_LLM,
    prompt=MOCK_BASIC_PROMPT,
    code_executor=None,
    model_client_stream=False,
    sources=None,
    description="A test looping agent that searches the web",
    system_message=None,
    max_consecutive_auto_reply=10,
    reflect_on_tool_use=True,
    terminate_on_text=False,
    tool_call_loop=True,
    sub_agents=None,
    mode=None,
    orchestrator_prompt=None,
    include_inner_dialog=True
)

# Note: sub_agents should be List[AgentConfig] per schema, but JSON files use strings
# For testing, we create minimal AgentConfig objects for sub-agents
_MOCK_MANAGER_AGENT = AgentConfig(
    name="Manager",
    agent_type="looping",
    tools=[],
    llm=MOCK_OPENAI_LLM,
    prompt=MOCK_BASIC_PROMPT,
    max_consecutive_auto_reply=5
)

_MOCK_RESEARCHER_SUB_AGENT = AgentConfig(
    name="Researcher",
    agent_type="looping",
    tools=["web_search"],
    llm=MOCK_OPENAI_LLM,
    prompt=MOCK_RESEARCH_PROMPT,
    max_consecutive_auto_reply=10
)

_MOCK_DEVELOPER_SUB_AGENT = AgentConfig(
    name="Developer",
    agent_type="looping",
    tools=[],
    llm=MOCK_OPENAI_LLM,
    prompt=MOCK_DEVELOPER_PROMPT,
    max_consecutive_auto_reply=10
)

MOCK_NESTED_AGENT = AgentConfig(
    name="TestNestedTeam",
    agent_type="nested_team",
    tools=[],
    llm=MOCK_OPENAI_LLM,
    prompt=PromptConfig(system="", user=""),
    code_executor={"type": ""},
    model_client_stream=False,
    sources=[],
    description="A test nested team agent with coordinated sub-agents",
    system_message="",
    max_consecutive_auto_reply=20,
    reflect_on_tool_use=True,
    terminate_on_text=False,
    tool_call_loop=False,
    sub_agents=[_MOCK_MANAGER_AGENT, _MOCK_RESEARCHER_SUB_AGENT, _MOCK_DEVELOPER_SUB_AGENT],
    mode="selector",
    orchestrator_prompt="__function__",
    orchestrator_agent_name="Manager",
    orchestrator_pattern="NEXT AGENT: <Name>",
    include_inner_dialog=True
)

MOCK_MULTIMODAL_AGENT = AgentConfig(
    name="TestMultimodalAgent",
    agent_type="multimodal_tools_looping",
    tools=["take_screenshot", "generate_test_image", "get_sample_image"],
    llm=MOCK_OPENAI_VISION_LLM,
    prompt=MOCK_VISION_PROMPT,
    code_executor=None,
    model_client_stream=False,
    sources=None,
    description="A test multimodal agent with vision capabilities",
    system_message=None,
    max_consecutive_auto_reply=7,
    reflect_on_tool_use=True,
    terminate_on_text=False,
    tool_call_loop=True,
    sub_agents=None,
    mode=None,
    orchestrator_prompt=None,
    include_inner_dialog=True
)

MOCK_CODE_EXECUTOR_AGENT = AgentConfig(
    name="TestCodeExecutor",
    agent_type="looping_code_executor",
    tools=["execute_python"],
    llm=MOCK_OPENAI_LLM,
    prompt=MOCK_DEVELOPER_PROMPT,
    code_executor={"type": "local"},
    model_client_stream=True,
    sources=[],
    description="A test code executor agent that can run Python code",
    system_message="You can execute Python code to solve problems.",
    max_consecutive_auto_reply=10,
    reflect_on_tool_use=True,
    terminate_on_text=False,
    tool_call_loop=True,
    sub_agents=None,
    mode=None,
    orchestrator_prompt=None,
    include_inner_dialog=True
)

MOCK_RESEARCHER_AGENT = AgentConfig(
    name="TestResearcher",
    agent_type="looping",
    tools=["arxiv_search", "fetch_web_content", "web_search", "wikipedia_search"],
    llm=MOCK_OPENAI_LLM,
    prompt=MOCK_RESEARCH_PROMPT,
    code_executor=None,
    model_client_stream=False,
    sources=None,
    description="A test researcher agent specializing in web research",
    system_message=None,
    max_consecutive_auto_reply=20,
    reflect_on_tool_use=True,
    terminate_on_text=False,
    tool_call_loop=True,
    sub_agents=None,
    mode=None,
    orchestrator_prompt=None,
    include_inner_dialog=True
)

MOCK_MEMORY_AGENT = AgentConfig(
    name="TestMemoryAgent",
    agent_type="looping",
    tools=[
        "get_short_term_memory",
        "overwrite_short_term_memory",
        "create_memory_bank",
        "add_to_memory",
        "search_memory",
        "list_memory_banks"
    ],
    llm=MOCK_OPENAI_LLM,
    prompt=MOCK_MEMORY_PROMPT,
    code_executor=None,
    model_client_stream=False,
    sources=None,
    description="A test memory agent with short-term and long-term memory capabilities",
    system_message=None,
    max_consecutive_auto_reply=10,
    reflect_on_tool_use=True,
    terminate_on_text=False,
    tool_call_loop=True,
    sub_agents=None,
    mode=None,
    orchestrator_prompt=None,
    include_inner_dialog=True
)


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_agent_config(
    name: str = "TestAgent",
    agent_type: str = "looping",
    tools: Optional[List[str]] = None,
    llm: Optional[LLMConfig] = None,
    prompt: Optional[PromptConfig] = None,
    sub_agents: Optional[List[str]] = None,
    **kwargs
) -> AgentConfig:
    """
    Create a custom mock agent configuration with specified parameters.

    Args:
        name: Agent name
        agent_type: Type of agent (looping, nested_team, multimodal_tools_looping, etc.)
        tools: List of tool names
        llm: LLM configuration (defaults to MOCK_OPENAI_LLM)
        prompt: Prompt configuration (defaults to MOCK_BASIC_PROMPT)
        sub_agents: List of sub-agent names (for nested teams)
        **kwargs: Additional fields to override

    Returns:
        AgentConfig instance

    Example:
        >>> agent = create_mock_agent_config(
        ...     name="CustomAgent",
        ...     tools=["custom_tool"],
        ...     max_consecutive_auto_reply=15
        ... )
    """
    if tools is None:
        tools = []

    if llm is None:
        llm = MOCK_OPENAI_LLM

    if prompt is None:
        prompt = MOCK_BASIC_PROMPT

    # Default configuration
    config_dict = {
        "name": name,
        "agent_type": agent_type,
        "tools": tools,
        "llm": llm,
        "prompt": prompt,
        "code_executor": None,
        "model_client_stream": False,
        "sources": None,
        "description": f"Test {agent_type} agent",
        "system_message": None,
        "max_consecutive_auto_reply": 10,
        "reflect_on_tool_use": True,
        "terminate_on_text": False,
        "tool_call_loop": agent_type != "nested_team",
        "sub_agents": sub_agents,
        "mode": "selector" if agent_type == "nested_team" else None,
        "orchestrator_prompt": "__function__" if agent_type == "nested_team" else None,
        "include_inner_dialog": True
    }

    # Override with provided kwargs
    config_dict.update(kwargs)

    return AgentConfig(**config_dict)


def agent_config_to_dict(config: AgentConfig) -> Dict[str, Any]:
    """
    Convert AgentConfig to dictionary format (for JSON serialization).

    Args:
        config: AgentConfig instance

    Returns:
        Dictionary representation of the config

    Example:
        >>> config_dict = agent_config_to_dict(MOCK_LOOPING_AGENT)
        >>> assert "name" in config_dict
    """
    return config.model_dump()


def create_minimal_agent_dict(
    name: str = "MinimalAgent",
    agent_type: str = "looping"
) -> Dict[str, Any]:
    """
    Create a minimal agent configuration dictionary with only required fields.
    Useful for testing validation and default values.

    Args:
        name: Agent name
        agent_type: Agent type

    Returns:
        Minimal agent configuration dictionary

    Example:
        >>> minimal = create_minimal_agent_dict("TestAgent")
        >>> AgentConfig(**minimal)  # Should create valid config with defaults
    """
    return {
        "name": name,
        "agent_type": agent_type,
        "tools": [],
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.0
        },
        "prompt": {
            "system": "You are a helpful assistant.",
            "user": "Help the user."
        }
    }


# ============================================================================
# Export All
# ============================================================================

__all__ = [
    # LLM configs
    "MOCK_OPENAI_LLM",
    "MOCK_OPENAI_VISION_LLM",
    "MOCK_ANTHROPIC_LLM",
    "MOCK_GOOGLE_LLM",

    # Prompt configs
    "MOCK_BASIC_PROMPT",
    "MOCK_RESEARCH_PROMPT",
    "MOCK_VISION_PROMPT",
    "MOCK_DEVELOPER_PROMPT",
    "MOCK_MEMORY_PROMPT",

    # Agent configs
    "MOCK_LOOPING_AGENT",
    "MOCK_NESTED_AGENT",
    "MOCK_MULTIMODAL_AGENT",
    "MOCK_CODE_EXECUTOR_AGENT",
    "MOCK_RESEARCHER_AGENT",
    "MOCK_MEMORY_AGENT",

    # Helper functions
    "create_mock_agent_config",
    "agent_config_to_dict",
    "create_minimal_agent_dict",
]
