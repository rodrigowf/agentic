"""
Unit tests for config/config_loader.py

Tests agent and tool loading, validation, error handling, and caching behavior.
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from autogen_core.tools import FunctionTool

from config.config_loader import (
    load_tools,
    save_tool,
    load_agents,
    save_agent,
    get_tool_infos,
    _get_tool_schema,
)
from config.schemas import AgentConfig, LLMConfig, PromptConfig, ToolInfo
from tests.fixtures import (
    MOCK_LOOPING_AGENT,
    MOCK_NESTED_AGENT,
    agent_config_to_dict,
)


# ============================================================================
# Test _get_tool_schema
# ============================================================================


def test_get_tool_schema_with_openai_schema():
    """Test _get_tool_schema when tool has openai_schema attribute."""
    mock_tool = MagicMock(spec=FunctionTool)
    mock_tool.openai_schema = {
        "type": "function",
        "function": {
            "name": "test_tool",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}
        }
    }

    schema = _get_tool_schema(mock_tool)

    assert "type" in schema
    assert schema["type"] == "function"


def test_get_tool_schema_without_openai_schema():
    """Test _get_tool_schema fallback when tool lacks openai_schema."""
    mock_tool = MagicMock(spec=FunctionTool)
    del mock_tool.openai_schema  # Ensure attribute doesn't exist

    schema = _get_tool_schema(mock_tool)

    # Should return basic fallback
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"


# ============================================================================
# Test load_tools
# ============================================================================


def test_load_tools_empty_directory(tmp_path):
    """Test load_tools with empty directory."""
    tools_dir = tmp_path / "empty_tools"
    tools_dir.mkdir()

    tools = load_tools(str(tools_dir))

    assert tools == []


def test_load_tools_creates_directory_if_not_exists(tmp_path):
    """Test load_tools creates directory if it doesn't exist."""
    tools_dir = tmp_path / "nonexistent_tools"

    tools = load_tools(str(tools_dir))

    assert tools_dir.exists()
    assert tools == []


def test_load_tools_skips_init_file(tmp_path):
    """Test that __init__.py files are skipped."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create __init__.py
    init_file = tools_dir / "__init__.py"
    init_file.write_text("# Init file")

    tools = load_tools(str(tools_dir))

    assert tools == []


def test_load_tools_loads_valid_tool(tmp_path):
    """Test loading a valid tool from Python file."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create a simple tool file
    tool_file = tools_dir / "simple_tool.py"
    tool_file.write_text("""
from autogen_core.tools import FunctionTool

def my_function(query: str) -> str:
    return f"Result for {query}"

my_tool = FunctionTool(
    func=my_function,
    name="my_tool",
    description="A simple test tool"
)
""")

    tools = load_tools(str(tools_dir))

    assert len(tools) == 1
    tool, filename = tools[0]
    assert isinstance(tool, FunctionTool)
    assert filename == "simple_tool.py"
    assert tool.name == "my_tool"


def test_load_tools_handles_multiple_tools_in_file(tmp_path):
    """Test loading multiple FunctionTool instances from a single file."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    tool_file = tools_dir / "multi_tool.py"
    tool_file.write_text("""
from autogen_core.tools import FunctionTool

def func1(x: str) -> str:
    return f"Func1: {x}"

def func2(y: int) -> int:
    return y * 2

tool1 = FunctionTool(func=func1, name="tool1", description="Tool 1")
tool2 = FunctionTool(func=func2, name="tool2", description="Tool 2")
""")

    tools = load_tools(str(tools_dir))

    assert len(tools) == 2
    assert all(isinstance(t[0], FunctionTool) for t in tools)
    assert all(t[1] == "multi_tool.py" for t in tools)


def test_load_tools_skips_invalid_python_file(tmp_path):
    """Test that invalid Python files are skipped with warning."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create invalid Python file
    invalid_file = tools_dir / "invalid.py"
    invalid_file.write_text("This is not valid Python syntax!!!@#$")

    # Should not raise, just skip the file
    tools = load_tools(str(tools_dir))

    assert tools == []


def test_load_tools_skips_file_without_function_tools(tmp_path):
    """Test that Python files without FunctionTool instances are skipped."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    tool_file = tools_dir / "no_tools.py"
    tool_file.write_text("""
def some_function():
    return "I'm not a FunctionTool"

SOME_CONSTANT = 42
""")

    tools = load_tools(str(tools_dir))

    assert tools == []


def test_load_tools_handles_non_python_files(tmp_path):
    """Test that non-Python files are skipped."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create non-Python files
    (tools_dir / "readme.txt").write_text("Not a Python file")
    (tools_dir / "config.json").write_text("{}")

    tools = load_tools(str(tools_dir))

    assert tools == []


# ============================================================================
# Test save_tool
# ============================================================================


def test_save_tool_creates_directory(tmp_path):
    """Test that save_tool creates directory if it doesn't exist."""
    tools_dir = tmp_path / "new_tools"

    save_tool(str(tools_dir), "test.py", b"# Test content")

    assert tools_dir.exists()
    assert (tools_dir / "test.py").exists()


def test_save_tool_writes_content(tmp_path):
    """Test that save_tool writes content correctly."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    content = b"# Test tool\nprint('Hello')"
    save_tool(str(tools_dir), "test.py", content)

    saved_file = tools_dir / "test.py"
    assert saved_file.read_bytes() == content


def test_save_tool_overwrites_existing_file(tmp_path):
    """Test that save_tool overwrites existing files."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    tool_file = tools_dir / "test.py"
    tool_file.write_text("Old content")

    new_content = b"New content"
    save_tool(str(tools_dir), "test.py", new_content)

    assert tool_file.read_bytes() == new_content


# ============================================================================
# Test load_agents
# ============================================================================


def test_load_agents_empty_directory(tmp_path):
    """Test load_agents with empty directory."""
    agents_dir = tmp_path / "empty_agents"
    agents_dir.mkdir()

    agents = load_agents(str(agents_dir))

    assert agents == []


def test_load_agents_creates_directory_if_not_exists(tmp_path):
    """Test load_agents creates directory if it doesn't exist."""
    agents_dir = tmp_path / "nonexistent_agents"

    agents = load_agents(str(agents_dir))

    assert agents_dir.exists()
    assert agents == []


def test_load_agents_loads_valid_agent(tmp_path):
    """Test loading a valid agent configuration."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Create valid agent JSON
    agent_config = {
        "name": "TestAgent",
        "agent_type": "looping",
        "tools": ["web_search"],
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.0,
            "max_tokens": None
        },
        "prompt": {
            "system": "You are a test agent.",
            "user": "Test task"
        },
        "tool_call_loop": True
    }

    agent_file = agents_dir / "TestAgent.json"
    agent_file.write_text(json.dumps(agent_config))

    agents = load_agents(str(agents_dir))

    assert len(agents) == 1
    assert isinstance(agents[0], AgentConfig)
    assert agents[0].name == "TestAgent"
    assert agents[0].agent_type == "looping"


def test_load_agents_skips_non_json_files(tmp_path):
    """Test that non-JSON files are skipped."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    (agents_dir / "readme.txt").write_text("Not a JSON file")
    (agents_dir / "config.py").write_text("# Python file")

    agents = load_agents(str(agents_dir))

    assert agents == []


def test_load_agents_skips_invalid_json(tmp_path):
    """Test that invalid JSON files are skipped with warning."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    invalid_file = agents_dir / "invalid.json"
    invalid_file.write_text("{ This is not valid JSON }")

    agents = load_agents(str(agents_dir))

    assert agents == []


def test_load_agents_skips_invalid_schema(tmp_path):
    """Test that files with invalid agent schema are skipped."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Missing required fields
    invalid_config = {
        "name": "InvalidAgent"
        # Missing agent_type, tools, etc.
    }

    agent_file = agents_dir / "InvalidAgent.json"
    agent_file.write_text(json.dumps(invalid_config))

    agents = load_agents(str(agents_dir))

    assert agents == []


def test_load_agents_expands_nested_team_sub_agents(tmp_path):
    """Test that nested team sub-agents are expanded from filenames."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Create sub-agent files
    sub_agent_1 = {
        "name": "SubAgent1",
        "agent_type": "looping",
        "tools": ["tool1"],
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0},
        "prompt": {"system": "Sub 1", "user": "Task 1"},
        "tool_call_loop": True
    }
    (agents_dir / "SubAgent1.json").write_text(json.dumps(sub_agent_1))

    sub_agent_2 = {
        "name": "SubAgent2",
        "agent_type": "looping",
        "tools": ["tool2"],
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0},
        "prompt": {"system": "Sub 2", "user": "Task 2"},
        "tool_call_loop": True
    }
    (agents_dir / "SubAgent2.json").write_text(json.dumps(sub_agent_2))

    # Create nested team that references sub-agents by name
    nested_config = {
        "name": "NestedTeam",
        "agent_type": "nested_team",
        "tools": [],
        "llm": {"provider": "openai", "model": "gpt-4-turbo-2024-04-09", "temperature": 0.0},
        "prompt": {"system": "", "user": ""},
        "sub_agents": ["SubAgent1", "SubAgent2"],  # String references
        "mode": "selector",
        "tool_call_loop": False
    }
    (agents_dir / "NestedTeam.json").write_text(json.dumps(nested_config))

    agents = load_agents(str(agents_dir))

    # Should load all 3 agents
    assert len(agents) == 3

    # Find nested team
    nested = next(a for a in agents if a.name == "NestedTeam")
    assert nested.agent_type == "nested_team"
    assert len(nested.sub_agents) == 2

    # Verify sub-agents are expanded to full AgentConfig objects
    assert all(isinstance(sub, AgentConfig) for sub in nested.sub_agents)
    assert nested.sub_agents[0].name == "SubAgent1"
    assert nested.sub_agents[1].name == "SubAgent2"


def test_load_agents_handles_missing_sub_agent_file(tmp_path):
    """Test that missing sub-agent files are handled gracefully."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Create nested team referencing non-existent sub-agent
    nested_config = {
        "name": "NestedTeam",
        "agent_type": "nested_team",
        "tools": [],
        "llm": {"provider": "openai", "model": "gpt-4-turbo-2024-04-09", "temperature": 0.0},
        "prompt": {"system": "", "user": ""},
        "sub_agents": ["NonExistentAgent"],
        "mode": "selector",
        "tool_call_loop": False
    }
    (agents_dir / "NestedTeam.json").write_text(json.dumps(nested_config))

    agents = load_agents(str(agents_dir))

    # Should still load the nested team, but sub_agents list will be empty or incomplete
    assert len(agents) == 1
    assert agents[0].name == "NestedTeam"


def test_load_agents_handles_dict_sub_agents(tmp_path):
    """Test that sub-agents can be provided as dicts instead of filenames."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Create nested team with inline sub-agent dict
    nested_config = {
        "name": "NestedTeam",
        "agent_type": "nested_team",
        "tools": [],
        "llm": {"provider": "openai", "model": "gpt-4-turbo-2024-04-09", "temperature": 0.0},
        "prompt": {"system": "", "user": ""},
        "sub_agents": [
            {
                "name": "InlineAgent",
                "agent_type": "looping",
                "tools": ["tool1"],
                "llm": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0},
                "prompt": {"system": "Inline", "user": "Task"},
                "tool_call_loop": True
            }
        ],
        "mode": "selector",
        "tool_call_loop": False
    }
    (agents_dir / "NestedTeam.json").write_text(json.dumps(nested_config))

    agents = load_agents(str(agents_dir))

    assert len(agents) == 1
    nested = agents[0]
    assert len(nested.sub_agents) == 1
    assert nested.sub_agents[0].name == "InlineAgent"


# ============================================================================
# Test save_agent
# ============================================================================


def test_save_agent_writes_json(tmp_path):
    """Test that save_agent writes valid JSON."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    agent = MOCK_LOOPING_AGENT
    save_agent(agent, str(agents_dir))

    agent_file = agents_dir / f"{agent.name}.json"
    assert agent_file.exists()

    # Verify JSON is valid
    with open(agent_file) as f:
        data = json.load(f)

    assert data["name"] == agent.name
    assert data["agent_type"] == agent.agent_type


def test_save_agent_nested_team_saves_sub_agent_names(tmp_path):
    """Test that nested team agents save sub-agent names, not full configs."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    agent = MOCK_NESTED_AGENT
    save_agent(agent, str(agents_dir))

    agent_file = agents_dir / f"{agent.name}.json"

    with open(agent_file) as f:
        data = json.load(f)

    # sub_agents should be list of names (strings), not dicts
    assert "sub_agents" in data
    assert isinstance(data["sub_agents"], list)
    if len(data["sub_agents"]) > 0:
        # Should be string names
        assert all(isinstance(name, str) for name in data["sub_agents"])


def test_save_agent_overwrites_existing_file(tmp_path):
    """Test that save_agent overwrites existing agent files."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    agent = MOCK_LOOPING_AGENT

    # Save first time
    save_agent(agent, str(agents_dir))

    # Modify and save again
    agent.description = "Updated description"
    save_agent(agent, str(agents_dir))

    # Load and verify
    agent_file = agents_dir / f"{agent.name}.json"
    with open(agent_file) as f:
        data = json.load(f)

    assert data["description"] == "Updated description"


# ============================================================================
# Test get_tool_infos
# ============================================================================


def test_get_tool_infos_empty_list():
    """Test get_tool_infos with empty tool list."""
    infos = get_tool_infos([])

    assert infos == []


def test_get_tool_infos_converts_tools_to_info():
    """Test that get_tool_infos converts FunctionTools to ToolInfo objects."""
    # Create mock tools
    def mock_func(x: str) -> str:
        return f"Result: {x}"

    tool1 = FunctionTool(func=mock_func, name="tool1", description="Tool 1")
    tool2 = FunctionTool(func=mock_func, name="tool2", description="Tool 2")

    loaded_tools = [(tool1, "tool1.py"), (tool2, "tool2.py")]

    infos = get_tool_infos(loaded_tools)

    assert len(infos) == 2
    assert all(isinstance(info, ToolInfo) for info in infos)
    assert infos[0].name == "tool1"
    assert infos[0].filename == "tool1.py"
    assert infos[1].name == "tool2"
    assert infos[1].filename == "tool2.py"


def test_get_tool_infos_includes_schema():
    """Test that get_tool_infos includes tool schema."""
    def mock_func(x: str) -> str:
        return f"Result: {x}"

    tool = FunctionTool(func=mock_func, name="test_tool", description="Test")
    loaded_tools = [(tool, "test.py")]

    infos = get_tool_infos(loaded_tools)

    assert len(infos) == 1
    assert "parameters" in infos[0].parameters


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_load_agents_handles_circular_references(tmp_path):
    """Test that circular sub-agent references don't cause infinite loops."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # This test documents current behavior - circular refs aren't explicitly prevented
    # but won't cause infinite loops since we only expand one level

    agent_a = {
        "name": "AgentA",
        "agent_type": "nested_team",
        "tools": [],
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0},
        "prompt": {"system": "", "user": ""},
        "sub_agents": ["AgentB"],
        "mode": "selector",
        "tool_call_loop": False
    }
    (agents_dir / "AgentA.json").write_text(json.dumps(agent_a))

    agent_b = {
        "name": "AgentB",
        "agent_type": "nested_team",
        "tools": [],
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0},
        "prompt": {"system": "", "user": ""},
        "sub_agents": ["AgentA"],  # Circular reference
        "mode": "selector",
        "tool_call_loop": False
    }
    (agents_dir / "AgentB.json").write_text(json.dumps(agent_b))

    # Should not hang or crash
    agents = load_agents(str(agents_dir))

    # Should load both agents
    assert len(agents) == 2


def test_load_tools_with_import_error(tmp_path):
    """Test that tools with import errors are skipped."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    tool_file = tools_dir / "bad_import.py"
    tool_file.write_text("""
from nonexistent_module import something

def my_function():
    return "Won't work"
""")

    # Should not raise, just skip
    tools = load_tools(str(tools_dir))

    assert tools == []


def test_load_agents_loads_multiple_agents(tmp_path):
    """Test loading multiple agent configurations."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Create multiple agents
    for i in range(3):
        agent_config = {
            "name": f"Agent{i}",
            "agent_type": "looping",
            "tools": [f"tool{i}"],
            "llm": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.0},
            "prompt": {"system": f"Agent {i}", "user": f"Task {i}"},
            "tool_call_loop": True
        }
        (agents_dir / f"Agent{i}.json").write_text(json.dumps(agent_config))

    agents = load_agents(str(agents_dir))

    assert len(agents) == 3
    assert set(a.name for a in agents) == {"Agent0", "Agent1", "Agent2"}


# ============================================================================
# Integration Tests
# ============================================================================


def test_save_and_load_agent_roundtrip(tmp_path):
    """Test that saving and loading an agent preserves configuration."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    original = MOCK_LOOPING_AGENT

    # Save
    save_agent(original, str(agents_dir))

    # Load
    loaded_agents = load_agents(str(agents_dir))

    assert len(loaded_agents) == 1
    loaded = loaded_agents[0]

    # Verify key fields match
    assert loaded.name == original.name
    assert loaded.agent_type == original.agent_type
    assert loaded.tools == original.tools
    assert loaded.llm.provider == original.llm.provider
    assert loaded.llm.model == original.llm.model


def test_load_and_get_tool_info_workflow(tmp_path):
    """Test complete workflow: load tools and convert to ToolInfo."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create tool file
    tool_file = tools_dir / "workflow_tool.py"
    tool_file.write_text("""
from autogen_core.tools import FunctionTool

def my_workflow_tool(query: str) -> str:
    return f"Workflow result: {query}"

workflow_tool = FunctionTool(
    func=my_workflow_tool,
    name="workflow_tool",
    description="A workflow test tool"
)
""")

    # Load tools
    loaded_tools = load_tools(str(tools_dir))

    # Convert to tool infos
    tool_infos = get_tool_infos(loaded_tools)

    assert len(tool_infos) == 1
    assert tool_infos[0].name == "workflow_tool"
    assert tool_infos[0].description == "A workflow test tool"
    assert tool_infos[0].filename == "workflow_tool.py"


# ============================================================================
# Pytest Markers
# ============================================================================


pytestmark = pytest.mark.unit
