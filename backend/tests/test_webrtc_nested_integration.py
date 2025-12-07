"""
Tests for WebRTC + Nested Agents Integration

Tests the integration between the WebRTC voice bridge and nested agents/Claude Code.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.realtime_voice_webrtc import BridgeSession, REALTIME_TOOLS


class TestToolDefinitions:
    """Test that tool definitions are properly configured."""

    def test_realtime_tools_count(self):
        """Verify we have 5 tools defined."""
        assert len(REALTIME_TOOLS) == 5

    def test_realtime_tools_names(self):
        """Verify all expected tool names are present."""
        tool_names = {tool["name"] for tool in REALTIME_TOOLS}
        expected = {"send_to_nested", "send_to_claude_code", "pause", "reset", "pause_claude_code"}
        assert tool_names == expected

    def test_tool_structure(self):
        """Verify each tool has the required structure."""
        for tool in REALTIME_TOOLS:
            assert tool["type"] == "function"
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert tool["parameters"]["type"] == "object"


class TestBridgeSessionInit:
    """Test BridgeSession initialization with new attributes."""

    def test_bridge_session_has_websocket_attrs(self):
        """Verify new WebSocket attributes are initialized."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Check WebSocket attributes
        assert session.nested_ws is None
        assert session.claude_code_ws is None
        assert session.nested_ws_task is None
        assert session.claude_code_ws_task is None
        assert session.aiohttp_session is None
        assert session.backend_base_url == "ws://localhost:8000"


@pytest.mark.asyncio
class TestToolExecution:
    """Test tool execution methods."""

    async def test_execute_tool_send_to_nested(self):
        """Test send_to_nested tool execution."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Mock the WebSocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        session.nested_ws = mock_ws

        # Execute tool
        result = await session.execute_tool_call("call-123", "send_to_nested", {"text": "Hello"})

        # Verify
        assert result["success"] is True
        mock_ws.send_json.assert_called_once_with({
            "type": "user_message",
            "data": "Hello"
        })

    async def test_execute_tool_send_to_nested_no_connection(self):
        """Test send_to_nested fails gracefully without WebSocket."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # No WebSocket connected
        result = await session.execute_tool_call("call-123", "send_to_nested", {"text": "Hello"})

        # Verify failure
        assert result["success"] is False
        assert "not connected" in result["error"]

    async def test_execute_tool_send_to_claude_code(self):
        """Test send_to_claude_code tool execution."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Mock the WebSocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        session.claude_code_ws = mock_ws

        # Execute tool
        result = await session.execute_tool_call("call-123", "send_to_claude_code", {"text": "Fix bug"})

        # Verify
        assert result["success"] is True
        mock_ws.send_json.assert_called_once_with({
            "type": "user_message",
            "data": "Fix bug"
        })

    async def test_execute_tool_pause(self):
        """Test pause tool execution."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Mock the WebSocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        session.nested_ws = mock_ws

        # Execute tool
        result = await session.execute_tool_call("call-123", "pause", {})

        # Verify
        assert result["success"] is True
        mock_ws.send_json.assert_called_once_with({
            "type": "control",
            "action": "pause"
        })

    async def test_execute_tool_reset(self):
        """Test reset tool execution."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Mock the WebSocket
        mock_ws = AsyncMock()
        mock_ws.closed = False
        session.nested_ws = mock_ws

        # Execute tool
        result = await session.execute_tool_call("call-123", "reset", {})

        # Verify
        assert result["success"] is True
        mock_ws.send_json.assert_called_once_with({
            "type": "control",
            "action": "reset"
        })

    async def test_execute_unknown_tool(self):
        """Test handling of unknown tool."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Execute unknown tool
        result = await session.execute_tool_call("call-123", "unknown_tool", {})

        # Verify failure
        assert result["success"] is False
        assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
class TestEventForwarding:
    """Test event forwarding from nested agents to voice."""

    async def test_handle_nested_message_text(self):
        """Test forwarding text messages from nested agents."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Mock OpenAI client
        mock_client = AsyncMock()
        session.openai_client = mock_client

        # Test event
        event = {
            "type": "TextMessage",
            "data": {
                "source": "Engineer",
                "content": "I'm working on the feature"
            }
        }

        # Handle event
        await session._handle_nested_message(event)

        # Verify forwarded to voice
        mock_client.forward_message_to_voice.assert_called_once()
        call_args = mock_client.forward_message_to_voice.call_args
        assert call_args[0][0] == "system"
        assert "[TEAM Engineer]" in call_args[0][1]
        assert "I'm working on the feature" in call_args[0][1]

    async def test_handle_nested_message_tool_result(self):
        """Test forwarding tool execution results."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Mock OpenAI client
        mock_client = AsyncMock()
        session.openai_client = mock_client

        # Test event
        event = {
            "type": "ToolCallExecutionEvent",
            "data": {
                "name": "create_file",
                "result": "File created at src/App.js"
            }
        }

        # Handle event
        await session._handle_nested_message(event)

        # Verify forwarded to voice
        mock_client.forward_message_to_voice.assert_called_once()
        call_args = mock_client.forward_message_to_voice.call_args
        assert call_args[0][0] == "system"
        assert "[TEAM create_file]" in call_args[0][1]

    async def test_handle_nested_message_task_result(self):
        """Test forwarding task completion."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Mock OpenAI client
        mock_client = AsyncMock()
        session.openai_client = mock_client

        # Test event
        event = {
            "type": "TaskResult",
            "data": {
                "outcome": "success",
                "message": "Feature implemented successfully"
            }
        }

        # Handle event
        await session._handle_nested_message(event)

        # Verify forwarded to voice
        mock_client.forward_message_to_voice.assert_called_once()
        call_args = mock_client.forward_message_to_voice.call_args
        assert call_args[0][0] == "system"
        assert "[TEAM] Task success" in call_args[0][1]

    async def test_handle_claude_code_message(self):
        """Test forwarding Claude Code events."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Mock OpenAI client
        mock_client = AsyncMock()
        session.openai_client = mock_client

        # Test event
        event = {
            "type": "TextMessage",
            "data": {
                "content": "Modifying src/App.js..."
            }
        }

        # Handle event
        await session._handle_claude_code_message(event)

        # Verify forwarded to voice
        mock_client.forward_message_to_voice.assert_called_once()
        call_args = mock_client.forward_message_to_voice.call_args
        assert call_args[0][0] == "system"
        assert "[CODE ClaudeCode]" in call_args[0][1]


@pytest.mark.asyncio
class TestSessionLifecycle:
    """Test session startup and cleanup."""

    async def test_close_cleanup_websockets(self):
        """Test that close() properly cleans up WebSocket connections."""
        session = BridgeSession(
            conversation_id="test-conv-123",
            voice="alloy",
            agent_name="TestAgent",
            system_prompt="Test prompt",
        )

        # Mock WebSocket tasks - need to be actual tasks for cancel/await
        async def mock_task():
            try:
                await asyncio.sleep(10)  # Long sleep to ensure it gets cancelled
            except asyncio.CancelledError:
                pass

        mock_nested_task = asyncio.create_task(mock_task())
        mock_claude_task = asyncio.create_task(mock_task())
        session.nested_ws_task = mock_nested_task
        session.claude_code_ws_task = mock_claude_task

        # Mock WebSocket connections
        mock_nested_ws = AsyncMock()
        mock_nested_ws.closed = False
        mock_claude_ws = AsyncMock()
        mock_claude_ws.closed = False
        session.nested_ws = mock_nested_ws
        session.claude_code_ws = mock_claude_ws

        # Mock aiohttp session
        mock_aiohttp_session = AsyncMock()
        session.aiohttp_session = mock_aiohttp_session

        # Mock other connections
        session.browser_audio_task = None
        session.browser_pc = None
        session.openai_client = None

        # Close session
        await session.close()

        # Verify tasks were cleaned up (either cancelled or done)
        assert mock_nested_task.done()
        assert mock_claude_task.done()

        # Verify WebSockets were closed
        mock_nested_ws.close.assert_called_once()
        mock_claude_ws.close.assert_called_once()

        # Verify aiohttp session was closed
        mock_aiohttp_session.close.assert_called_once()

        # Verify attributes were set to None
        assert session.nested_ws_task is None
        assert session.claude_code_ws_task is None
        assert session.nested_ws is None
        assert session.claude_code_ws is None
        assert session.aiohttp_session is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
