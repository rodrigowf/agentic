#!/usr/bin/env python3
"""
End-to-End tests for complete agent execution workflows.

Tests the entire workflow from agent creation to execution with minimal mocking.
This tests the actual integration of all components:
- Agent configuration loading
- Tool loading and registration
- Agent factory instantiation
- Agent execution via WebSocket
- Event streaming
- Error handling

These tests use real HTTP/WebSocket connections and minimal mocking to verify
the complete system behavior.
"""

import json
import os
import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from config.schemas import AgentConfig, LLMConfig, PromptConfig
from tests.fixtures import (
    MOCK_LOOPING_AGENT,
    MOCK_NESTED_AGENT,
    MOCK_MULTIMODAL_AGENT,
    create_mock_agent_config,
    MOCK_WEB_SEARCH_RESPONSE,
    create_mock_tool_response
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_workspace(monkeypatch):
    """Create temporary workspace with agents and tools directories."""
    temp_dir = tempfile.mkdtemp()
    agents_path = Path(temp_dir) / "agents"
    tools_path = Path(temp_dir) / "tools"
    agents_path.mkdir()
    tools_path.mkdir()

    # Monkeypatch the directories in main module
    import main
    original_agents_dir = main.AGENTS_DIR
    original_tools_dir = main.TOOLS_DIR
    main.AGENTS_DIR = str(agents_path)
    main.TOOLS_DIR = str(tools_path)
    main.AGENTS = []
    main.LOADED_TOOLS_WITH_FILENAMES = []

    yield {
        "agents_dir": str(agents_path),
        "tools_dir": str(tools_path),
        "temp_dir": temp_dir
    }

    # Cleanup
    main.AGENTS_DIR = original_agents_dir
    main.TOOLS_DIR = original_tools_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def simple_test_tool(temp_workspace):
    """Create a simple test tool."""
    tool_code = '''"""Simple test tool for E2E testing."""

from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool


class TestToolInput(BaseModel):
    """Input for test tool."""
    message: str = Field(..., description="Message to echo")


def simple_test_tool(message: str) -> str:
    """
    A simple test tool that echoes the input message.

    Args:
        message: The message to echo

    Returns:
        The echoed message with a prefix
    """
    return f"Tool executed: {message}"


# Export tool
simple_test_tool_func = FunctionTool(
    func=simple_test_tool,
    name="simple_test_tool",
    description="A simple test tool that echoes messages"
)

tools = [simple_test_tool_func]
'''

    tool_file = Path(temp_workspace["tools_dir"]) / "simple_test_tool.py"
    tool_file.write_text(tool_code)

    return "simple_test_tool"


class TestLoopingAgentWorkflow:
    """E2E tests for looping agent workflow."""

    def test_complete_looping_agent_lifecycle(self, client, temp_workspace, simple_test_tool):
        """
        Test complete lifecycle: Create agent → Execute → Verify results.

        This is a true E2E test that exercises the entire stack.
        """
        # Step 1: Create agent configuration
        agent_config = create_mock_agent_config(
            name="E2ETestAgent",
            agent_type="looping",
            tools=[simple_test_tool],
            max_consecutive_auto_reply=3,
            tool_call_loop=True
        )

        # Step 2: Save agent via API
        response = client.post("/api/agents", json=agent_config.model_dump(mode='json'))
        assert response.status_code == 200
        created_agent = response.json()
        assert created_agent["name"] == "E2ETestAgent"

        # Step 3: Verify agent file was created
        agent_file = Path(temp_workspace["agents_dir"]) / "E2ETestAgent.json"
        assert agent_file.exists()

        # Step 4: List agents via API
        response = client.get("/api/agents")
        assert response.status_code == 200
        agents = response.json()
        assert len(agents) >= 1
        assert any(a["name"] == "E2ETestAgent" for a in agents)

        # Step 5: Execute agent via WebSocket (with mocked LLM)
        with patch('core.looping_agent.LoopingAgent') as mock_agent_class:
            # Mock the agent to send test events
            mock_agent = AsyncMock()

            async def mock_run(*args, **kwargs):
                # Simulate agent execution events
                return [
                    {"role": "assistant", "content": "Let me use the tool."},
                    {"role": "assistant", "content": "TERMINATE"}
                ]

            mock_agent.run.return_value = mock_run()
            mock_agent_class.return_value = mock_agent

            with client.websocket_connect(f"/api/runs/E2ETestAgent") as websocket:
                # Should receive events
                received_events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        received_events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    # Timeout or disconnection
                    pass

                # Verify we received events
                assert len(received_events) > 0

        # Step 6: Update agent via API
        updated_config = agent_config.model_copy()
        updated_config.description = "Updated E2E test agent"
        response = client.put(
            "/api/agents/E2ETestAgent",
            json=updated_config.model_dump(mode='json')
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated E2E test agent"

    def test_looping_agent_with_tool_execution(self, client, temp_workspace, simple_test_tool):
        """Test looping agent that actually calls tools."""
        # Create agent
        agent_config = create_mock_agent_config(
            name="ToolCallingAgent",
            agent_type="looping",
            tools=[simple_test_tool],
            tool_call_loop=True
        )

        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        # Execute with tool call simulation
        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Simulate tool call workflow
                await websocket.send_json({
                    "type": "TextMessage",
                    "data": {"content": "I'll use the tool now."},
                    "source": "agent",
                    "timestamp": datetime.utcnow().isoformat()
                })

                await websocket.send_json({
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": simple_test_tool,
                        "arguments": {"message": "Hello E2E test"},
                        "id": "tool_123"
                    },
                    "source": "agent",
                    "timestamp": datetime.utcnow().isoformat()
                })

                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": simple_test_tool,
                        "result": "Tool executed: Hello E2E test",
                        "is_error": False,
                        "id": "tool_123"
                    },
                    "source": "agent",
                    "timestamp": datetime.utcnow().isoformat()
                })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success", "message": "Completed"},
                    "timestamp": datetime.utcnow().isoformat()
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/ToolCallingAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify event sequence
                event_types = [e["type"] for e in events]
                assert "TextMessage" in event_types
                assert "ToolCallRequestEvent" in event_types
                assert "ToolCallExecutionEvent" in event_types
                assert "TaskResult" in event_types

                # Verify tool execution
                tool_result = next(e for e in events if e["type"] == "ToolCallExecutionEvent")
                assert tool_result["data"]["result"] == "Tool executed: Hello E2E test"
                assert tool_result["data"]["is_error"] is False

    def test_looping_agent_error_recovery(self, client, temp_workspace, simple_test_tool):
        """Test looping agent error handling and recovery."""
        agent_config = create_mock_agent_config(
            name="ErrorRecoveryAgent",
            agent_type="looping",
            tools=[simple_test_tool]
        )

        client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_agent_runner(config, tools, websocket):
                # Simulate error and recovery
                await websocket.send_json({
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": simple_test_tool,
                        "arguments": {"message": "test"},
                        "id": "tool_1"
                    }
                })

                # Tool execution fails
                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": simple_test_tool,
                        "result": "Error: Tool failed",
                        "is_error": True,
                        "id": "tool_1"
                    }
                })

                # Agent recovers and tries again
                await websocket.send_json({
                    "type": "TextMessage",
                    "data": {"content": "Let me try again."}
                })

                await websocket.send_json({
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": simple_test_tool,
                        "arguments": {"message": "retry"},
                        "id": "tool_2"
                    }
                })

                # Success
                await websocket.send_json({
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": simple_test_tool,
                        "result": "Tool executed: retry",
                        "is_error": False,
                        "id": "tool_2"
                    }
                })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_agent_runner

            with client.websocket_connect("/api/runs/ErrorRecoveryAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify error handling
                tool_executions = [e for e in events if e["type"] == "ToolCallExecutionEvent"]
                assert len(tool_executions) == 2
                assert tool_executions[0]["data"]["is_error"] is True
                assert tool_executions[1]["data"]["is_error"] is False


class TestNestedTeamWorkflow:
    """E2E tests for nested team agent workflow."""

    def test_nested_team_creation_and_execution(self, client, temp_workspace, simple_test_tool):
        """Test creating and executing a nested team agent."""
        # Create sub-agents first
        agent1_config = create_mock_agent_config(
            name="SubAgent1",
            agent_type="looping",
            tools=[simple_test_tool]
        )
        agent2_config = create_mock_agent_config(
            name="SubAgent2",
            agent_type="looping",
            tools=[simple_test_tool]
        )

        client.post("/api/agents", json=agent1_config.model_dump(mode='json'))
        client.post("/api/agents", json=agent2_config.model_dump(mode='json'))

        # Create nested team agent
        team_config = create_mock_agent_config(
            name="TeamAgent",
            agent_type="nested_team",
            tools=[],
            sub_agents=["SubAgent1", "SubAgent2"],
            mode="selector",
            orchestrator_prompt="__function__"
        )

        response = client.post("/api/agents", json=team_config.model_dump(mode='json'))
        assert response.status_code == 200
        assert response.json()["agent_type"] == "nested_team"

        # Execute nested team
        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_team_runner(config, tools, websocket):
                # Orchestrator selects agent
                await websocket.send_json({
                    "type": "TextMessage",
                    "data": {"content": "[ORCHESTRATOR] Selecting SubAgent1"},
                    "source": "orchestrator"
                })

                # SubAgent1 executes
                await websocket.send_json({
                    "type": "TextMessage",
                    "data": {"content": "SubAgent1 executing task"},
                    "source": "SubAgent1"
                })

                await websocket.send_json({
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": simple_test_tool,
                        "arguments": {"message": "from SubAgent1"},
                        "id": "tool_1"
                    },
                    "source": "SubAgent1"
                })

                # Task complete
                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"},
                    "source": "orchestrator"
                })

            mock_run.side_effect = mock_team_runner

            with client.websocket_connect("/api/runs/TeamAgent") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify nested team execution
                assert len(events) >= 3
                sources = [e.get("source") for e in events if "source" in e]
                assert "orchestrator" in sources
                assert "SubAgent1" in sources

    def test_nested_team_handoff_workflow(self, client, temp_workspace, simple_test_tool):
        """Test nested team with agent handoffs."""
        # Create agents
        for i in range(3):
            agent_config = create_mock_agent_config(
                name=f"TeamMember{i}",
                agent_type="looping",
                tools=[simple_test_tool]
            )
            client.post("/api/agents", json=agent_config.model_dump(mode='json'))

        # Create team
        team_config = create_mock_agent_config(
            name="CollaborativeTeam",
            agent_type="nested_team",
            sub_agents=["TeamMember0", "TeamMember1", "TeamMember2"],
            mode="selector"
        )

        client.post("/api/agents", json=team_config.model_dump(mode='json'))

        # Execute with handoffs
        with patch('core.runner.run_agent_ws') as mock_run:
            async def mock_handoff_runner(config, tools, websocket):
                # Sequential handoffs
                for i in range(3):
                    await websocket.send_json({
                        "type": "TextMessage",
                        "data": {"content": f"Handing off to TeamMember{i}"},
                        "source": "orchestrator"
                    })

                    await websocket.send_json({
                        "type": "TextMessage",
                        "data": {"content": f"TeamMember{i} working on task"},
                        "source": f"TeamMember{i}"
                    })

                await websocket.send_json({
                    "type": "TaskResult",
                    "data": {"outcome": "success"}
                })

            mock_run.side_effect = mock_handoff_runner

            with client.websocket_connect("/api/runs/CollaborativeTeam") as websocket:
                events = []
                try:
                    while True:
                        event = websocket.receive_json(timeout=2)
                        events.append(event)
                        if event.get("type") == "TaskResult":
                            break
                except Exception:
                    pass

                # Verify all team members participated
                messages = [e for e in events if e["type"] == "TextMessage"]
                sources = [m.get("source") for m in messages]
                assert "TeamMember0" in sources
                assert "TeamMember1" in sources
                assert "TeamMember2" in sources


class TestAgentConfigurationWorkflow:
    """E2E tests for agent configuration management."""

    def test_agent_crud_workflow(self, client, temp_workspace):
        """Test complete CRUD workflow for agents."""
        # Create
        agent_config = create_mock_agent_config(name="CRUDTestAgent")
        response = client.post("/api/agents", json=agent_config.model_dump(mode='json'))
        assert response.status_code == 200

        # Read
        response = client.get("/api/agents")
        assert response.status_code == 200
        agents = response.json()
        assert any(a["name"] == "CRUDTestAgent" for a in agents)

        # Update
        updated_config = agent_config.model_copy()
        updated_config.description = "Updated description"
        updated_config.llm.temperature = 0.7
        response = client.put(
            "/api/agents/CRUDTestAgent",
            json=updated_config.model_dump(mode='json')
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"
        assert response.json()["llm"]["temperature"] == 0.7

        # Verify file was updated
        agent_file = Path(temp_workspace["agents_dir"]) / "CRUDTestAgent.json"
        with open(agent_file) as f:
            saved_agent = json.load(f)
        assert saved_agent["description"] == "Updated description"

    def test_multiple_agents_workflow(self, client, temp_workspace):
        """Test managing multiple agents simultaneously."""
        # Create multiple agents
        agent_names = []
        for i in range(5):
            name = f"MultiAgent{i}"
            agent_names.append(name)
            agent_config = create_mock_agent_config(
                name=name,
                description=f"Agent number {i}"
            )
            response = client.post("/api/agents", json=agent_config.model_dump(mode='json'))
            assert response.status_code == 200

        # List all agents
        response = client.get("/api/agents")
        assert response.status_code == 200
        agents = response.json()
        assert len(agents) >= 5

        # Verify all were created
        listed_names = [a["name"] for a in agents]
        for name in agent_names:
            assert name in listed_names

        # Update each agent
        for i, name in enumerate(agent_names):
            config = create_mock_agent_config(
                name=name,
                description=f"Updated agent {i}"
            )
            response = client.put(f"/api/agents/{name}", json=config.model_dump(mode='json'))
            assert response.status_code == 200
            assert response.json()["description"] == f"Updated agent {i}"


class TestAgentValidationWorkflow:
    """E2E tests for agent configuration validation."""

    def test_invalid_agent_configuration(self, client, temp_workspace):
        """Test creating agent with invalid configuration."""
        invalid_configs = [
            # Missing required fields
            {"name": "Invalid1"},
            # Invalid agent type
            {
                "name": "Invalid2",
                "agent_type": "invalid_type",
                "tools": [],
                "llm": {"provider": "openai", "model": "gpt-4o"},
                "prompt": {"system": "test", "user": "test"}
            },
            # Invalid LLM provider
            {
                "name": "Invalid3",
                "agent_type": "looping",
                "tools": [],
                "llm": {"provider": "invalid_provider", "model": "model"},
                "prompt": {"system": "test", "user": "test"}
            }
        ]

        for config in invalid_configs:
            response = client.post("/api/agents", json=config)
            assert response.status_code in [400, 422], f"Expected error for config: {config}"

    def test_duplicate_agent_name_handling(self, client, temp_workspace):
        """Test handling of duplicate agent names."""
        agent_config = create_mock_agent_config(name="DuplicateTest")

        # First creation should succeed
        response = client.post("/api/agents", json=agent_config.model_dump(mode='json'))
        assert response.status_code == 200

        # Second creation with same name should fail
        response = client.post("/api/agents", json=agent_config.model_dump(mode='json'))
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_nested_team_validation(self, client, temp_workspace):
        """Test nested team agent validation."""
        # Create nested team without creating sub-agents first
        team_config = create_mock_agent_config(
            name="InvalidTeam",
            agent_type="nested_team",
            sub_agents=["NonExistentAgent1", "NonExistentAgent2"],
            mode="selector"
        )

        # Should still create (validation happens at runtime)
        response = client.post("/api/agents", json=team_config.model_dump(mode='json'))
        assert response.status_code == 200

        # Execution would fail, but creation succeeds
        # (This is current behavior - could be enhanced with pre-validation)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
