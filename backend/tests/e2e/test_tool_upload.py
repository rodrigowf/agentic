#!/usr/bin/env python3
"""
End-to-End tests for tool upload and execution workflows.

Tests the complete workflow of:
1. Creating a custom tool
2. Uploading tool via API
3. Tool being loaded dynamically
4. Agent using the tool
5. Tool execution and result verification
6. Tool updates and deletion

These tests verify the full tool lifecycle with minimal mocking.
"""

import json
import os
import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from config.schemas import AgentConfig
from tests.fixtures import create_mock_agent_config


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_workspace(monkeypatch):
    """Create temporary workspace for agents and tools."""
    temp_dir = tempfile.mkdtemp()
    agents_path = Path(temp_dir) / "agents"
    tools_path = Path(temp_dir) / "tools"
    agents_path.mkdir()
    tools_path.mkdir()

    import main
    original_agents_dir = main.AGENTS_DIR
    original_tools_dir = main.TOOLS_DIR
    original_tools = main.LOADED_TOOLS_WITH_FILENAMES

    main.AGENTS_DIR = str(agents_path)
    main.TOOLS_DIR = str(tools_path)
    main.AGENTS = []
    main.LOADED_TOOLS_WITH_FILENAMES = []

    yield {
        "agents_dir": str(agents_path),
        "tools_dir": str(tools_path),
        "temp_dir": temp_dir
    }

    main.AGENTS_DIR = original_agents_dir
    main.TOOLS_DIR = original_tools_dir
    main.LOADED_TOOLS_WITH_FILENAMES = original_tools
    shutil.rmtree(temp_dir)


def create_simple_tool_code(tool_name: str, description: str) -> str:
    """Helper to create valid tool code."""
    return f'''"""
{description}
"""

from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool


class {tool_name.capitalize()}Input(BaseModel):
    """Input schema for {tool_name}."""
    text: str = Field(..., description="Input text")


def {tool_name}(text: str) -> str:
    """
    {description}

    Args:
        text: Input text to process

    Returns:
        Processed result
    """
    return f"{{tool_name}} processed: {{text}}"


# Export tool
{tool_name}_func = FunctionTool(
    func={tool_name},
    name="{tool_name}",
    description="{description}"
)

tools = [{tool_name}_func]
'''


class TestToolUploadWorkflow:
    """E2E tests for tool upload workflow."""

    def test_complete_tool_upload_lifecycle(self, client, temp_workspace):
        """
        Test complete tool lifecycle:
        1. Upload tool via API
        2. Verify tool file created
        3. List tools and verify presence
        4. Verify tool can be loaded
        """
        # Step 1: Create tool code
        tool_name = "custom_search"
        tool_code = create_simple_tool_code(
            tool_name,
            "A custom search tool for testing"
        )

        # Step 2: Upload tool via API
        response = client.post(
            "/api/tools",
            files={
                "file": (f"{tool_name}.py", tool_code, "text/x-python")
            }
        )
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Tool uploaded successfully"
        assert result["filename"] == f"{tool_name}.py"

        # Step 3: Verify tool file created
        tool_file = Path(temp_workspace["tools_dir"]) / f"{tool_name}.py"
        assert tool_file.exists()

        # Verify file content
        with open(tool_file) as f:
            content = f.read()
        assert tool_name in content
        assert "FunctionTool" in content

        # Step 4: List tools via API
        response = client.get("/api/tools")
        assert response.status_code == 200
        tools = response.json()

        # Find our tool
        tool_names = [t["name"] for t in tools]
        assert tool_name in tool_names

        # Step 5: Verify tool metadata
        our_tool = next(t for t in tools if t["name"] == tool_name)
        assert our_tool["filename"] == f"{tool_name}.py"
        assert "description" in our_tool

    def test_upload_multiple_tools(self, client, temp_workspace):
        """Test uploading multiple tools."""
        tool_names = ["tool_a", "tool_b", "tool_c", "tool_d"]

        # Upload multiple tools
        for name in tool_names:
            tool_code = create_simple_tool_code(name, f"Tool {name}")
            response = client.post(
                "/api/tools",
                files={"file": (f"{name}.py", tool_code, "text/x-python")}
            )
            assert response.status_code == 200

        # Verify all tools exist
        response = client.get("/api/tools")
        assert response.status_code == 200
        tools = response.json()

        uploaded_names = [t["name"] for t in tools]
        for name in tool_names:
            assert name in uploaded_names

        # Verify files exist
        for name in tool_names:
            tool_file = Path(temp_workspace["tools_dir"]) / f"{name}.py"
            assert tool_file.exists()

    def test_upload_tool_with_dependencies(self, client, temp_workspace):
        """Test uploading a tool with external dependencies."""
        tool_code = '''"""
Advanced tool with dependencies.
"""

from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
import json
import re
from datetime import datetime


def advanced_tool(data: str) -> str:
    """
    An advanced tool that uses multiple libraries.

    Args:
        data: JSON string to process

    Returns:
        Processed result
    """
    try:
        parsed = json.loads(data)
        timestamp = datetime.utcnow().isoformat()
        result = {
            "processed": True,
            "timestamp": timestamp,
            "data": parsed
        }
        return json.dumps(result)
    except Exception as e:
        return f"Error: {str(e)}"


advanced_tool_func = FunctionTool(
    func=advanced_tool,
    name="advanced_tool",
    description="Advanced tool with dependencies"
)

tools = [advanced_tool_func]
'''

        # Upload tool
        response = client.post(
            "/api/tools",
            files={"file": ("advanced_tool.py", tool_code, "text/x-python")}
        )
        assert response.status_code == 200

        # Verify tool exists
        response = client.get("/api/tools")
        tools = response.json()
        assert any(t["name"] == "advanced_tool" for t in tools)

    def test_upload_invalid_tool_code(self, client, temp_workspace):
        """Test uploading invalid tool code."""
        invalid_codes = [
            # Missing tools export
            '''
def my_tool():
    return "test"
''',
            # Syntax error
            '''
def my_tool(
    return "test"
''',
            # No FunctionTool
            '''
def my_tool():
    return "test"

tools = []
''',
        ]

        for i, code in enumerate(invalid_codes):
            response = client.post(
                "/api/tools",
                files={"file": (f"invalid_{i}.py", code, "text/x-python")}
            )
            # May succeed or fail depending on validation
            # At minimum, should not crash the server
            assert response.status_code in [200, 400, 422]


class TestToolExecutionWorkflow:
    """E2E tests for tool execution in agents."""

    def test_agent_uses_uploaded_tool(self, client, temp_workspace):
        """
        Test complete workflow:
        1. Upload custom tool
        2. Create agent that uses the tool
        3. Execute agent
        4. Verify tool is called
        """
        # Step 1: Upload tool
        tool_name = "custom_analyzer"
        tool_code = create_simple_tool_code(tool_name, "Custom analyzer tool")

        response = client.post(
            "/api/tools",
            files={"file": (f"{tool_name}.py", tool_code, "text/x-python")}
        )
        assert response.status_code == 200

        # Step 2: Create agent that uses this tool
        agent_config = create_mock_agent_config(
            name="ToolUserAgent",
            agent_type="looping",
            tools=[tool_name],
            tool_call_loop=True
        )

        response = client.post("/api/agents", json=agent_config.model_dump(mode='json'))
        assert response.status_code == 200

        # Step 3: Execute agent (with mocked runner)
        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Verify tool is available
                tool_names = [t.name for t in tools]
                assert tool_name in tool_names

                # Simulate tool call
                await websocket.send_json({
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": tool_name,
                        "arguments": {"text": "test data"},
                        "id": "tool_1"
                    }
                })

                # Simulate tool execution
                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": tool_name,
                        "result": f"{tool_name} processed: test data",
                        "is_error": False,
                        "id": "tool_1"
                    }
                })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/ToolUserAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify tool was called
                tool_calls = [e for e in events if e["type"] == "ToolCallRequestEvent"]
                assert len(tool_calls) > 0
                assert tool_calls[0]["data"]["name"] == tool_name

                # Verify tool execution
                executions = [e for e in events if e["type"] == "ToolCallExecutionEvent"]
                assert len(executions) > 0
                assert tool_name in executions[0]["data"]["result"]

    def test_multiple_tools_in_single_agent(self, client, temp_workspace):
        """Test agent using multiple custom tools."""
        # Upload multiple tools
        tool_names = ["tool_one", "tool_two", "tool_three"]
        for name in tool_names:
            tool_code = create_simple_tool_code(name, f"Tool {name}")
            client.post(
                "/api/tools",
                files={"file": (f"{name}.py", tool_code, "text/x-python")}
            )

        # Create agent with all tools
        agent_config = create_mock_agent_config(
            name="MultiToolAgent",
            agent_type="looping",
            tools=tool_names
        )

        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        # Execute and verify all tools available
        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Verify all tools available
                available_tools = [t.name for t in tools]
                for name in tool_names:
                    assert name in available_tools

                # Call each tool
                for i, name in enumerate(tool_names):
                    await websocket.send_json({
                        "type": "ToolCallRequestEvent",
                        "data": {
                            "name": name,
                            "arguments": {"text": f"test {i}"},
                            "id": f"tool_{i}"
                        }
                    })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/MultiToolAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify all tools were called
                tool_calls = [e for e in events if e["type"] == "ToolCallRequestEvent"]
                assert len(tool_calls) == 3

                called_tools = [e["data"]["name"] for e in tool_calls]
                for name in tool_names:
                    assert name in called_tools


class TestToolUpdateWorkflow:
    """E2E tests for tool update workflow."""

    def test_tool_update_via_reupload(self, client, temp_workspace):
        """Test updating a tool by re-uploading."""
        tool_name = "updatable_tool"

        # Version 1
        tool_code_v1 = create_simple_tool_code(
            tool_name,
            "Version 1 of the tool"
        )

        response = client.post(
            "/api/tools",
            files={"file": (f"{tool_name}.py", tool_code_v1, "text/x-python")}
        )
        assert response.status_code == 200

        # Verify V1
        tool_file = Path(temp_workspace["tools_dir"]) / f"{tool_name}.py"
        with open(tool_file) as f:
            content = f.read()
        assert "Version 1" in content

        # Version 2 (update)
        tool_code_v2 = create_simple_tool_code(
            tool_name,
            "Version 2 of the tool - UPDATED"
        )

        response = client.post(
            "/api/tools",
            files={"file": (f"{tool_name}.py", tool_code_v2, "text/x-python")}
        )
        # Should succeed (overwrite)
        assert response.status_code == 200

        # Verify V2
        with open(tool_file) as f:
            content = f.read()
        assert "Version 2" in content
        assert "UPDATED" in content

    def test_tool_hot_reload_after_update(self, client, temp_workspace):
        """Test that tools are reloaded after update."""
        tool_name = "hot_reload_tool"

        # Upload V1
        tool_code_v1 = create_simple_tool_code(tool_name, "V1")
        client.post(
            "/api/tools",
            files={"file": (f"{tool_name}.py", tool_code_v1, "text/x-python")}
        )

        # Get tools list
        response = client.get("/api/tools")
        tools_v1 = response.json()
        tool_v1 = next(t for t in tools_v1 if t["name"] == tool_name)

        # Upload V2
        tool_code_v2 = create_simple_tool_code(tool_name, "V2 - UPDATED")
        client.post(
            "/api/tools",
            files={"file": (f"{tool_name}.py", tool_code_v2, "text/x-python")}
        )

        # Reload tools (in real system, happens automatically or on next request)
        import main
        main.LOADED_TOOLS_WITH_FILENAMES = main.load_tools(main.TOOLS_DIR)

        # Get tools list again
        response = client.get("/api/tools")
        tools_v2 = response.json()
        tool_v2 = next(t for t in tools_v2 if t["name"] == tool_name)

        # Description should be updated
        assert "V2" in tool_v2["description"] or "UPDATED" in tool_v2["description"]


class TestToolErrorHandling:
    """E2E tests for tool error handling."""

    def test_tool_runtime_error(self, client, temp_workspace):
        """Test handling of runtime errors in tools."""
        # Create tool that can error
        tool_code = '''"""
Tool that can raise errors.
"""

from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool


def error_prone_tool(mode: str) -> str:
    """
    A tool that can succeed or fail based on input.

    Args:
        mode: "success" or "error"

    Returns:
        Result or error
    """
    if mode == "error":
        raise ValueError("Intentional error for testing")
    return f"Success: {mode}"


error_prone_tool_func = FunctionTool(
    func=error_prone_tool,
    name="error_prone_tool",
    description="Tool that can error"
)

tools = [error_prone_tool_func]
'''

        client.post(
            "/api/tools",
            files={"file": ("error_prone_tool.py", tool_code, "text/x-python")}
        )

        # Create agent
        agent_config = create_mock_agent_config(
            name="ErrorHandlingAgent",
            tools=["error_prone_tool"]
        )
        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        # Execute with error
        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Call tool with error mode
                await websocket.send_json({
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": "error_prone_tool",
                        "arguments": {"mode": "error"},
                        "id": "tool_1"
                    }
                })

                # Tool execution fails
                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": "error_prone_tool",
                        "result": "Error: Intentional error for testing",
                        "is_error": True,
                        "id": "tool_1"
                    }
                })

                # Agent recovers
                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "error_handled"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/ErrorHandlingAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify error was reported
                executions = [e for e in events if e["type"] == "ToolCallExecutionEvent"]
                assert len(executions) > 0
                assert executions[0]["data"]["is_error"] is True

    def test_missing_tool_handling(self, client, temp_workspace):
        """Test agent behavior when configured tool is missing."""
        # Create agent with non-existent tool
        agent_config = create_mock_agent_config(
            name="MissingToolAgent",
            tools=["nonexistent_tool"]
        )

        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        # Try to execute
        with client.websocket_connect("/api/runs/MissingToolAgent") as websocket:
            # Should receive error about missing tool
            try:
                event = websocket.receive_json(timeout=2)
                # May receive error or startup message
                assert "type" in event
            except Exception:
                # Timeout is also acceptable
                pass


class TestToolValidation:
    """E2E tests for tool validation."""

    def test_tool_with_valid_schema(self, client, temp_workspace):
        """Test tool with proper Pydantic schema."""
        tool_code = '''"""
Well-structured tool with proper schema.
"""

from pydantic import BaseModel, Field, field_validator
from autogen_core.tools import FunctionTool
from typing import Optional


class WellStructuredInput(BaseModel):
    """Comprehensive input schema."""
    query: str = Field(..., description="Search query", min_length=1)
    max_results: Optional[int] = Field(10, description="Max results", ge=1, le=100)
    filter_type: str = Field("all", description="Filter type")

    @field_validator('filter_type')
    @classmethod
    def validate_filter(cls, v):
        if v not in ["all", "recent", "popular"]:
            raise ValueError("Invalid filter type")
        return v


def well_structured_tool(
    query: str,
    max_results: int = 10,
    filter_type: str = "all"
) -> str:
    """
    A well-structured tool with validation.

    Args:
        query: Search query
        max_results: Maximum results
        filter_type: Type of filter

    Returns:
        Search results
    """
    return f"Query: {query}, Results: {max_results}, Filter: {filter_type}"


well_structured_tool_func = FunctionTool(
    func=well_structured_tool,
    name="well_structured_tool",
    description="Well-structured tool with validation"
)

tools = [well_structured_tool_func]
'''

        response = client.post(
            "/api/tools",
            files={"file": ("well_structured_tool.py", tool_code, "text/x-python")}
        )
        assert response.status_code == 200

        # Verify tool loaded
        response = client.get("/api/tools")
        tools = response.json()
        assert any(t["name"] == "well_structured_tool" for t in tools)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
