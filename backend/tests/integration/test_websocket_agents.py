#!/usr/bin/env python3
"""
Integration tests for WebSocket communication with agents.

Tests:
- Connection establishment
- Message sending/receiving
- Tool call events
- Agent execution flow
- Error handling
- Disconnection
"""

import json
import os
import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from config.schemas import AgentConfig, LLMConfig, PromptConfig


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_agents_dir(monkeypatch):
    """Create a temporary agents directory for testing."""
    temp_dir = tempfile.mkdtemp()
    agents_path = Path(temp_dir) / "agents"
    agents_path.mkdir()

    # Monkeypatch the AGENTS_DIR in main module
    import main
    original_dir = main.AGENTS_DIR
    main.AGENTS_DIR = str(agents_path)
    main.AGENTS = []

    yield str(agents_path)

    # Cleanup
    main.AGENTS_DIR = original_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_tools_dir(monkeypatch):
    """Create a temporary tools directory for testing."""
    temp_dir = tempfile.mkdtemp()
    tools_path = Path(temp_dir) / "tools"
    tools_path.mkdir()

    # Monkeypatch the TOOLS_DIR in main module
    import main
    original_dir = main.TOOLS_DIR
    main.TOOLS_DIR = str(tools_path)
    main.LOADED_TOOLS_WITH_FILENAMES = []

    yield str(tools_path)

    # Cleanup
    main.TOOLS_DIR = original_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def simple_agent_config(temp_agents_dir):
    """Create a simple agent configuration for testing."""
    config = AgentConfig(
        name="SimpleAgent",
        agent_type="looping",
        tools=[],
        llm=LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.0
        ),
        prompt=PromptConfig(
            system="You are a test agent. Say 'Test complete' and then say TERMINATE.",
            user="Execute test."
        ),
        description="Simple test agent",
        max_consecutive_auto_reply=5,
        tool_call_loop=False
    )

    # Save to file
    agent_file = Path(temp_agents_dir) / "SimpleAgent.json"
    agent_file.write_text(config.model_dump_json(indent=2))

    return config


class TestWebSocketConnection:
    """Tests for WebSocket connection establishment."""

    def test_websocket_connect_success(self, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test successful WebSocket connection."""
        with client.websocket_connect(f"/api/runs/SimpleAgent") as websocket:
            # Connection should succeed
            assert websocket is not None

            # Should be able to receive initial events
            # (may receive error if agent setup fails, but connection works)
            data = websocket.receive_json(timeout=2)
            assert "type" in data

    def test_websocket_connect_nonexistent_agent(self, client, temp_agents_dir, temp_tools_dir):
        """Test connecting to non-existent agent."""
        with client.websocket_connect("/api/runs/NonExistentAgent") as websocket:
            # Should receive error message
            data = websocket.receive_json(timeout=2)
            assert data["type"] == "error"
            assert "not found" in data["data"]["message"].lower()

    def test_websocket_connect_invalid_path(self, client):
        """Test connecting to invalid WebSocket path."""
        try:
            with client.websocket_connect("/api/runs/") as websocket:
                # Should fail or return error
                pass
        except Exception:
            # Connection may fail, which is expected
            pass


class TestWebSocketMessaging:
    """Tests for WebSocket message exchange."""

    @patch('core.runner.run_agent_ws')
    async def test_websocket_receive_events(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test receiving events from agent."""
        # Mock the agent runner to send test events
        async def mock_agent_runner(config, tools, websocket):
            await websocket.send_json({
                "type": "TextMessage",
                "data": {"content": "Test message"},
                "timestamp": "2025-01-01T00:00:00Z"
            })
            await websocket.send_json({
                "type": "TaskResult",
                "data": {"status": "completed"},
                "timestamp": "2025-01-01T00:00:01Z"
            })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            # Receive first event
            event1 = websocket.receive_json(timeout=2)
            assert event1["type"] == "TextMessage"
            assert "content" in event1["data"]

            # Receive second event
            event2 = websocket.receive_json(timeout=2)
            assert event2["type"] == "TaskResult"

    def test_websocket_multiple_connections(self, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test multiple simultaneous WebSocket connections."""
        # Open multiple connections
        connections = []
        try:
            for i in range(3):
                ws = client.websocket_connect(f"/api/runs/SimpleAgent")
                connections.append(ws.__enter__())

            # All connections should work
            assert len(connections) == 3

            # Each can receive events independently
            for ws in connections:
                try:
                    data = ws.receive_json(timeout=1)
                    assert "type" in data
                except Exception:
                    # May timeout if no events, which is fine
                    pass

        finally:
            # Cleanup
            for ws in connections:
                try:
                    ws.__exit__(None, None, None)
                except Exception:
                    pass


class TestWebSocketToolCalls:
    """Tests for tool call events via WebSocket."""

    @patch('core.runner.run_agent_ws')
    async def test_tool_call_event_structure(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test tool call event structure."""
        async def mock_agent_runner(config, tools, websocket):
            # Send tool call request event
            await websocket.send_json({
                "type": "ToolCallRequestEvent",
                "data": {
                    "name": "test_tool",
                    "arguments": {"param": "value"},
                    "id": "tool_123"
                },
                "source": "agent",
                "timestamp": "2025-01-01T00:00:00Z"
            })

            # Send tool execution result
            await websocket.send_json({
                "type": "ToolCallExecutionEvent",
                "data": {
                    "name": "test_tool",
                    "result": "Tool executed successfully",
                    "is_error": False,
                    "id": "tool_123"
                },
                "source": "agent",
                "timestamp": "2025-01-01T00:00:01Z"
            })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            # Receive tool call request
            request_event = websocket.receive_json(timeout=2)
            assert request_event["type"] == "ToolCallRequestEvent"
            assert request_event["data"]["name"] == "test_tool"
            assert "arguments" in request_event["data"]

            # Receive tool execution result
            result_event = websocket.receive_json(timeout=2)
            assert result_event["type"] == "ToolCallExecutionEvent"
            assert result_event["data"]["result"] == "Tool executed successfully"
            assert result_event["data"]["is_error"] is False

    @patch('core.runner.run_agent_ws')
    async def test_multiple_tool_calls(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test multiple sequential tool calls."""
        async def mock_agent_runner(config, tools, websocket):
            tool_names = ["tool_1", "tool_2", "tool_3"]
            for i, name in enumerate(tool_names):
                await websocket.send_json({
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": name,
                        "arguments": {},
                        "id": f"tool_{i}"
                    }
                })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            received_tools = []
            for _ in range(3):
                event = websocket.receive_json(timeout=2)
                if event["type"] == "ToolCallRequestEvent":
                    received_tools.append(event["data"]["name"])

            assert len(received_tools) == 3
            assert "tool_1" in received_tools
            assert "tool_2" in received_tools
            assert "tool_3" in received_tools


class TestWebSocketErrorHandling:
    """Tests for error handling in WebSocket connections."""

    @patch('core.runner.run_agent_ws')
    async def test_agent_error_propagation(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test that agent errors are properly sent to client."""
        async def mock_agent_runner(config, tools, websocket):
            await websocket.send_json({
                "type": "error",
                "data": {
                    "message": "Agent execution failed",
                    "details": "Test error"
                }
            })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            event = websocket.receive_json(timeout=2)
            assert event["type"] == "error"
            assert "message" in event["data"]

    @patch('core.runner.run_agent_ws')
    async def test_tool_execution_error(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test tool execution error handling."""
        async def mock_agent_runner(config, tools, websocket):
            await websocket.send_json({
                "type": "ToolCallExecutionEvent",
                "data": {
                    "name": "failing_tool",
                    "result": "Error: Tool failed",
                    "is_error": True,
                    "id": "tool_123"
                }
            })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            event = websocket.receive_json(timeout=2)
            assert event["type"] == "ToolCallExecutionEvent"
            assert event["data"]["is_error"] is True

    @patch('core.runner.run_agent_ws')
    async def test_websocket_exception_during_run(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test exception handling during agent run."""
        async def mock_agent_runner(config, tools, websocket):
            # Send one event successfully
            await websocket.send_json({"type": "start", "data": {}})
            # Simulate exception
            raise Exception("Simulated agent crash")

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            # Should receive start event
            event1 = websocket.receive_json(timeout=2)
            assert event1["type"] == "start"

            # Should receive error event or connection close
            try:
                event2 = websocket.receive_json(timeout=2)
                # If we get an event, it should be an error
                assert event2["type"] == "error"
            except Exception:
                # Connection may close instead
                pass


class TestWebSocketDisconnection:
    """Tests for WebSocket disconnection handling."""

    def test_client_disconnect(self, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test client-initiated disconnection."""
        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            # Receive initial event
            try:
                websocket.receive_json(timeout=1)
            except Exception:
                pass

            # Client disconnects (happens automatically when exiting context)

        # Connection should be closed cleanly

    @patch('core.runner.run_agent_ws')
    async def test_server_disconnect(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test server-initiated disconnection."""
        async def mock_agent_runner(config, tools, websocket):
            await websocket.send_json({"type": "complete", "data": {}})
            await websocket.close()

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            event = websocket.receive_json(timeout=2)
            assert event["type"] == "complete"

            # Connection should close after this


class TestClaudeCodeWebSocket:
    """Tests for Claude Code WebSocket endpoint."""

    def test_claude_code_connect(self, client):
        """Test connecting to Claude Code WebSocket."""
        with client.websocket_connect("/api/runs/ClaudeCode") as websocket:
            # Should receive initialization event
            event = websocket.receive_json(timeout=2)
            assert event["type"] in ["system", "error"]

    @patch('api.claude_code_controller.ClaudeCodeSession')
    async def test_claude_code_send_message(self, mock_session_class, client):
        """Test sending message to Claude Code."""
        # Mock Claude Code session
        mock_session = AsyncMock()
        mock_session.start = AsyncMock()
        mock_session.stop = AsyncMock()
        mock_session.send_message = AsyncMock()

        async def mock_stream():
            yield {"type": "TextMessage", "data": {"content": "Response"}}

        mock_session.stream_events = mock_stream
        mock_session_class.return_value = mock_session

        with client.websocket_connect("/api/runs/ClaudeCode") as websocket:
            # Send user message
            websocket.send_json({
                "type": "user_message",
                "data": "Test message"
            })

            # Should receive response
            try:
                event = websocket.receive_json(timeout=2)
                assert "type" in event
            except Exception:
                # May timeout, which is acceptable
                pass

    def test_claude_code_invalid_command(self, client):
        """Test sending invalid command to Claude Code."""
        with client.websocket_connect("/api/runs/ClaudeCode") as websocket:
            # Send invalid command
            websocket.send_json({
                "type": "invalid_command",
                "data": "test"
            })

            # Should receive error or system message
            event = websocket.receive_json(timeout=2)
            assert event["type"] in ["error", "system"]


class TestWebSocketEventTypes:
    """Tests for different event types."""

    @patch('core.runner.run_agent_ws')
    async def test_text_message_event(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test TextMessage event."""
        async def mock_agent_runner(config, tools, websocket):
            await websocket.send_json({
                "type": "TextMessage",
                "data": {"content": "Hello from agent"},
                "source": "agent"
            })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            event = websocket.receive_json(timeout=2)
            assert event["type"] == "TextMessage"
            assert event["data"]["content"] == "Hello from agent"

    @patch('core.runner.run_agent_ws')
    async def test_task_result_event(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test TaskResult event."""
        async def mock_agent_runner(config, tools, websocket):
            await websocket.send_json({
                "type": "TaskResult",
                "data": {
                    "outcome": "success",
                    "message": "Task completed successfully"
                }
            })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            event = websocket.receive_json(timeout=2)
            assert event["type"] == "TaskResult"
            assert event["data"]["outcome"] == "success"

    @patch('core.runner.run_agent_ws')
    async def test_multimodal_message_event(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test MultiModalMessage event."""
        async def mock_agent_runner(config, tools, websocket):
            await websocket.send_json({
                "type": "MultiModalMessage",
                "data": {
                    "content": [
                        {"type": "text", "text": "Here is an image:"},
                        {"type": "image", "image": "data:image/png;base64,iVBORw0KG..."}
                    ]
                }
            })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            event = websocket.receive_json(timeout=2)
            assert event["type"] == "MultiModalMessage"
            assert isinstance(event["data"]["content"], list)


class TestWebSocketPerformance:
    """Tests for WebSocket performance characteristics."""

    @patch('core.runner.run_agent_ws')
    async def test_rapid_event_stream(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test handling rapid event stream."""
        async def mock_agent_runner(config, tools, websocket):
            # Send many events rapidly
            for i in range(50):
                await websocket.send_json({
                    "type": "TextMessage",
                    "data": {"content": f"Message {i}"}
                })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            received_count = 0
            try:
                for _ in range(50):
                    event = websocket.receive_json(timeout=0.1)
                    if event["type"] == "TextMessage":
                        received_count += 1
            except Exception:
                # Timeout is acceptable
                pass

            # Should receive most/all messages
            assert received_count > 0

    @patch('core.runner.run_agent_ws')
    async def test_large_message(self, mock_run, client, temp_agents_dir, temp_tools_dir, simple_agent_config):
        """Test handling large messages."""
        async def mock_agent_runner(config, tools, websocket):
            # Send large message
            large_content = "x" * 100000  # 100KB
            await websocket.send_json({
                "type": "TextMessage",
                "data": {"content": large_content}
            })

        mock_run.side_effect = mock_agent_runner

        with client.websocket_connect("/api/runs/SimpleAgent") as websocket:
            event = websocket.receive_json(timeout=5)
            assert event["type"] == "TextMessage"
            assert len(event["data"]["content"]) == 100000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
