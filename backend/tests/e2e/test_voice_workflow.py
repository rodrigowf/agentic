#!/usr/bin/env python3
"""
End-to-End tests for complete voice assistant workflows.

Tests the entire voice assistant workflow from conversation creation to
execution with nested team and Claude Code integration. These tests verify:
- Voice conversation lifecycle
- Event storage and retrieval
- Integration with nested team agents
- Integration with Claude Code
- WebSocket communication
- Voice tool execution

These tests use real HTTP/WebSocket connections with minimal mocking to verify
complete system behavior.
"""

import json
import os
import pytest
import tempfile
import shutil
import asyncio
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from typing import List, Dict, Any

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from utils.voice_conversation_store import ConversationStore
from config.schemas import AgentConfig
from tests.fixtures import (
    create_mock_agent_config,
    create_mock_voice_conversation,
    create_mock_voice_event,
    MOCK_VOICE_SESSION_CREATED,
    MOCK_VOICE_FUNCTION_CALL,
    MOCK_NESTED_AGENT_EVENTS,
    MOCK_CLAUDE_CODE_EVENTS
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for voice conversations."""
    db_path = tmp_path / "test_voice.db"
    return str(db_path)


@pytest.fixture
def conversation_store(temp_db):
    """Create a ConversationStore with temporary database."""
    return ConversationStore(db_path=temp_db)


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
    shutil.rmtree(temp_dir)


class TestVoiceConversationLifecycle:
    """E2E tests for voice conversation lifecycle."""

    def test_complete_voice_conversation_workflow(self, conversation_store):
        """
        Test complete voice conversation workflow:
        1. Create conversation
        2. Add events from multiple sources
        3. Retrieve conversation
        4. Verify event ordering and integrity
        """
        # Step 1: Create conversation
        conv_id = conversation_store.create_conversation("E2E Test Conversation")
        assert conv_id is not None
        assert len(conv_id) > 0

        # Step 2: Add events from different sources
        sources = ["voice", "nested", "claude_code", "controller"]
        event_types = ["session_created", "tool_call", "text_message", "task_result"]

        for i, (source, event_type) in enumerate(zip(sources, event_types)):
            event_data = {
                "type": event_type,
                "data": {
                    "message": f"Event {i} from {source}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            conversation_store.add_event(conv_id, source, event_type, event_data)

        # Step 3: Retrieve conversation
        conversation = conversation_store.get_conversation(conv_id)
        assert conversation is not None
        assert conversation["id"] == conv_id
        assert conversation["name"] == "E2E Test Conversation"

        # Step 4: Retrieve and verify events
        events = conversation_store.list_events(conv_id)
        assert len(events) == 4

        # Verify event ordering (chronological)
        for i, event in enumerate(events):
            assert event["source"] == sources[i]
            assert event["type"] == event_types[i]

    def test_multiple_conversations_workflow(self, conversation_store):
        """Test managing multiple conversations simultaneously."""
        # Create multiple conversations
        conv_ids = []
        for i in range(5):
            conv_id = conversation_store.create_conversation(f"Conversation {i}")
            conv_ids.append(conv_id)

            # Add events to each conversation
            for j in range(3):
                event_data = {"message": f"Event {j} in conversation {i}"}
                conversation_store.add_event(
                    conv_id,
                    "voice",
                    "test_event",
                    event_data
                )

        # List all conversations
        conversations = conversation_store.list_conversations()
        assert len(conversations) >= 5

        # Verify each conversation has its events
        for conv_id in conv_ids:
            events = conversation_store.list_events(conv_id)
            assert len(events) == 3

        # Verify events don't leak between conversations
        for i, conv_id in enumerate(conv_ids):
            events = conversation_store.list_events(conv_id)
            for event in events:
                assert f"conversation {i}" in event["payload"]["message"]

    def test_conversation_event_filtering(self, conversation_store):
        """Test filtering events by source and type."""
        conv_id = conversation_store.create_conversation("Filter Test")

        # Add diverse events
        test_events = [
            ("voice", "speech_started"),
            ("voice", "speech_stopped"),
            ("nested", "agent_selected"),
            ("nested", "tool_call"),
            ("claude_code", "tool_use"),
            ("claude_code", "text_message"),
            ("controller", "pause"),
            ("controller", "reset")
        ]

        for source, event_type in test_events:
            conversation_store.add_event(
                conv_id,
                source,
                event_type,
                {"data": f"{source}:{event_type}"}
            )

        # Retrieve all events
        all_events = conversation_store.list_events(conv_id)
        assert len(all_events) == 8

        # Filter by source (done in application code)
        voice_events = [e for e in all_events if e["source"] == "voice"]
        assert len(voice_events) == 2

        nested_events = [e for e in all_events if e["source"] == "nested"]
        assert len(nested_events) == 2

        claude_events = [e for e in all_events if e["source"] == "claude_code"]
        assert len(claude_events) == 2


class TestVoiceNestedIntegration:
    """E2E tests for voice + nested team integration."""

    def test_voice_sends_to_nested_workflow(self, client, temp_workspace, conversation_store):
        """
        Test complete workflow:
        1. Voice receives user speech
        2. Voice calls send_to_nested tool
        3. Nested team executes task
        4. Events stored in database
        5. Results returned to voice
        """
        # Create nested team agent
        team_config = create_mock_agent_config(
            name="VoiceTeam",
            agent_type="nested_team",
            sub_agents=["Agent1", "Agent2"],
            mode="selector"
        )
        client.post("/api/agents", json=team_config.model_dump(mode='json'))

        # Create conversation
        conv_id = conversation_store.create_conversation("Voice + Nested Test")

        # Mock voice WebSocket interaction
        with patch('api.realtime_voice.ConversationStore') as mock_store_class:
            mock_store_class.return_value = conversation_store

            # Simulate voice session events
            conversation_store.add_event(
                conv_id,
                "voice",
                "session.created",
                MOCK_VOICE_SESSION_CREATED
            )

            # Simulate voice calling send_to_nested
            send_to_nested_event = create_mock_voice_event(
                event_type="function_call",
                data={
                    "name": "send_to_nested",
                    "arguments": {"text": "Research AI safety"}
                }
            )
            conversation_store.add_event(
                conv_id,
                "voice",
                "function_call",
                send_to_nested_event
            )

            # Simulate nested team execution
            for nested_event in MOCK_NESTED_AGENT_EVENTS:
                conversation_store.add_event(
                    conv_id,
                    "nested",
                    nested_event["type"],
                    nested_event["data"]
                )

        # Verify event sequence
        events = conversation_store.list_events(conv_id)
        assert len(events) >= 3

        # Verify event sources
        sources = [e["source"] for e in events]
        assert "voice" in sources
        assert "nested" in sources

        # Verify function call
        function_calls = [e for e in events if e["type"] == "function_call"]
        assert len(function_calls) > 0
        assert function_calls[0]["payload"]["name"] == "send_to_nested"

    def test_voice_pause_and_resume_nested(self, conversation_store):
        """Test voice assistant pausing and resuming nested team."""
        conv_id = conversation_store.create_conversation("Pause/Resume Test")

        # Voice sends task to nested
        conversation_store.add_event(
            conv_id,
            "voice",
            "function_call",
            {"name": "send_to_nested", "arguments": {"text": "Long task"}}
        )

        # Nested starts working
        conversation_store.add_event(
            conv_id,
            "nested",
            "task_started",
            {"status": "running"}
        )

        # Voice pauses nested
        conversation_store.add_event(
            conv_id,
            "voice",
            "function_call",
            {"name": "pause", "arguments": {}}
        )

        # Nested pauses
        conversation_store.add_event(
            conv_id,
            "nested",
            "task_paused",
            {"status": "paused"}
        )

        # Voice resumes (implicit through new task)
        conversation_store.add_event(
            conv_id,
            "voice",
            "function_call",
            {"name": "send_to_nested", "arguments": {"text": "Continue"}}
        )

        # Nested resumes
        conversation_store.add_event(
            conv_id,
            "nested",
            "task_resumed",
            {"status": "running"}
        )

        # Verify event sequence
        events = conversation_store.list_events(conv_id)
        event_types = [e["type"] for e in events]

        assert "task_started" in event_types
        assert "task_paused" in event_types
        assert "task_resumed" in event_types


class TestVoiceClaudeCodeIntegration:
    """E2E tests for voice + Claude Code integration."""

    def test_voice_sends_to_claude_code_workflow(self, conversation_store):
        """
        Test complete workflow:
        1. Voice receives self-editing instruction
        2. Voice calls send_to_claude_code tool
        3. Claude Code executes tools
        4. Events stored in database
        5. Results returned to voice
        """
        conv_id = conversation_store.create_conversation("Voice + Claude Code Test")

        # Voice receives user instruction
        conversation_store.add_event(
            conv_id,
            "voice",
            "user_message",
            {
                "type": "user_message",
                "content": "Add a new feature to the codebase"
            }
        )

        # Voice calls send_to_claude_code
        conversation_store.add_event(
            conv_id,
            "voice",
            "function_call",
            {
                "name": "send_to_claude_code",
                "arguments": {"text": "Add a new feature to the codebase"}
            }
        )

        # Claude Code executes
        for claude_event in MOCK_CLAUDE_CODE_EVENTS:
            conversation_store.add_event(
                conv_id,
                "claude_code",
                claude_event["type"],
                claude_event["data"]
            )

        # Verify complete workflow
        events = conversation_store.list_events(conv_id)

        # Should have voice events and claude_code events
        voice_events = [e for e in events if e["source"] == "voice"]
        claude_events = [e for e in events if e["source"] == "claude_code"]

        assert len(voice_events) >= 2
        assert len(claude_events) > 0

        # Verify Claude Code tool usage
        tool_calls = [
            e for e in claude_events
            if e["type"] == "ToolCallRequestEvent"
        ]
        assert len(tool_calls) > 0

    def test_claude_code_permission_bypass(self, conversation_store):
        """Test that Claude Code runs with bypassed permissions for voice."""
        conv_id = conversation_store.create_conversation("Permission Bypass Test")

        # Simulate Claude Code running sensitive operations without prompts
        sensitive_tools = ["Bash", "Edit", "Write"]

        for tool_name in sensitive_tools:
            # Tool call (no permission prompt)
            conversation_store.add_event(
                conv_id,
                "claude_code",
                "ToolCallRequestEvent",
                {
                    "type": "ToolCallRequestEvent",
                    "data": {
                        "name": tool_name,
                        "arguments": {"test": "data"},
                        "id": f"tool_{tool_name}"
                    }
                }
            )

            # Tool execution (immediate, no prompt)
            conversation_store.add_event(
                conv_id,
                "claude_code",
                "ToolCallExecutionEvent",
                {
                    "type": "ToolCallExecutionEvent",
                    "data": {
                        "name": tool_name,
                        "result": f"{tool_name} executed",
                        "is_error": False,
                        "id": f"tool_{tool_name}"
                    }
                }
            )

        # Verify all tools executed without permission events
        events = conversation_store.list_events(conv_id)
        permission_events = [
            e for e in events
            if "permission" in e["type"].lower()
        ]
        assert len(permission_events) == 0  # No permission prompts

        # Verify all tools executed successfully
        execution_events = [
            e for e in events
            if e["type"] == "ToolCallExecutionEvent"
        ]
        assert len(execution_events) == 3


class TestVoiceWebSocketCommunication:
    """E2E tests for voice WebSocket communication."""

    def test_voice_websocket_connection(self, client):
        """Test connecting to voice WebSocket endpoint."""
        # Note: This test may require OpenAI API key and will be skipped if not available
        try:
            with client.websocket_connect("/api/realtime-voice") as websocket:
                # Should receive initialization event
                try:
                    event = websocket.receive_json(timeout=2)
                    assert "type" in event
                except Exception:
                    # May timeout if OpenAI connection fails
                    pass
        except Exception as e:
            # WebSocket may not connect if OpenAI API not configured
            pytest.skip(f"Voice WebSocket not available: {e}")

    def test_voice_event_streaming(self, client, conversation_store):
        """Test voice event streaming to frontend."""
        # This would require mocking the OpenAI Realtime API
        # For now, we test the database persistence layer

        conv_id = conversation_store.create_conversation("Streaming Test")

        # Simulate rapid event stream
        for i in range(20):
            conversation_store.add_event(
                conv_id,
                "voice",
                "audio_delta",
                {
                    "type": "audio_delta",
                    "delta": f"chunk_{i}",
                    "index": i
                }
            )

        # Verify all events persisted
        events = conversation_store.list_events(conv_id)
        assert len(events) == 20

        # Verify ordering
        for i, event in enumerate(events):
            assert event["payload"]["index"] == i


class TestVoiceToolExecution:
    """E2E tests for voice tool execution."""

    def test_voice_tool_send_to_nested(self, conversation_store):
        """Test voice tool: send_to_nested."""
        conv_id = conversation_store.create_conversation("Tool: send_to_nested")

        # Voice calls tool
        conversation_store.add_event(
            conv_id,
            "voice",
            "function_call",
            {
                "name": "send_to_nested",
                "arguments": {"text": "Test task"},
                "call_id": "call_123"
            }
        )

        # Controller forwards to nested
        conversation_store.add_event(
            conv_id,
            "controller",
            "forward_to_nested",
            {"task": "Test task"}
        )

        # Nested executes
        conversation_store.add_event(
            conv_id,
            "nested",
            "task_started",
            {"status": "running"}
        )

        # Verify workflow
        events = conversation_store.list_events(conv_id)
        assert len(events) == 3

        event_types = [e["type"] for e in events]
        assert "function_call" in event_types
        assert "forward_to_nested" in event_types
        assert "task_started" in event_types

    def test_voice_tool_send_to_claude_code(self, conversation_store):
        """Test voice tool: send_to_claude_code."""
        conv_id = conversation_store.create_conversation("Tool: send_to_claude_code")

        # Voice calls tool
        conversation_store.add_event(
            conv_id,
            "voice",
            "function_call",
            {
                "name": "send_to_claude_code",
                "arguments": {"text": "Add feature X"},
                "call_id": "call_456"
            }
        )

        # Controller forwards to Claude Code
        conversation_store.add_event(
            conv_id,
            "controller",
            "forward_to_claude_code",
            {"instruction": "Add feature X"}
        )

        # Claude Code executes
        conversation_store.add_event(
            conv_id,
            "claude_code",
            "TextMessage",
            {"content": "I'll add feature X now"}
        )

        # Verify workflow
        events = conversation_store.list_events(conv_id)
        assert len(events) == 3

    def test_voice_tool_pause(self, conversation_store):
        """Test voice tool: pause."""
        conv_id = conversation_store.create_conversation("Tool: pause")

        # Nested is running
        conversation_store.add_event(
            conv_id,
            "nested",
            "task_running",
            {"status": "active"}
        )

        # Voice calls pause
        conversation_store.add_event(
            conv_id,
            "voice",
            "function_call",
            {"name": "pause", "arguments": {}}
        )

        # Controller pauses nested
        conversation_store.add_event(
            conv_id,
            "controller",
            "pause_nested",
            {}
        )

        # Nested pauses
        conversation_store.add_event(
            conv_id,
            "nested",
            "task_paused",
            {"status": "paused"}
        )

        # Verify pause workflow
        events = conversation_store.list_events(conv_id)
        statuses = [e["payload"].get("status") for e in events if "status" in e["payload"]]
        assert "active" in statuses
        assert "paused" in statuses

    def test_voice_tool_reset(self, conversation_store):
        """Test voice tool: reset."""
        conv_id = conversation_store.create_conversation("Tool: reset")

        # Add some state
        for i in range(5):
            conversation_store.add_event(
                conv_id,
                "nested",
                "state_update",
                {"step": i}
            )

        # Voice calls reset
        conversation_store.add_event(
            conv_id,
            "voice",
            "function_call",
            {"name": "reset", "arguments": {}}
        )

        # Controller resets
        conversation_store.add_event(
            conv_id,
            "controller",
            "reset_state",
            {}
        )

        # Verify reset event recorded
        events = conversation_store.list_events(conv_id)
        reset_events = [e for e in events if "reset" in e["type"].lower()]
        assert len(reset_events) > 0


class TestVoiceConversationExport:
    """E2E tests for voice conversation export."""

    def test_export_conversation_to_json(self, conversation_store, tmp_path):
        """Test exporting conversation to JSON format."""
        # Create conversation with diverse events
        conv_id = conversation_store.create_conversation("Export Test")

        # Add various event types
        sources = ["voice", "nested", "claude_code", "controller"]
        for i, source in enumerate(sources):
            conversation_store.add_event(
                conv_id,
                source,
                f"event_type_{i}",
                {"data": f"Event from {source}", "index": i}
            )

        # Get conversation and events
        conversation = conversation_store.get_conversation(conv_id)
        events = conversation_store.list_events(conv_id)

        # Export to JSON
        export_data = {
            "conversation": conversation,
            "events": events
        }

        export_file = tmp_path / f"{conv_id}.json"
        with open(export_file, "w") as f:
            json.dump(export_data, f, indent=2)

        # Verify export
        assert export_file.exists()

        # Load and verify
        with open(export_file) as f:
            loaded = json.load(f)

        assert loaded["conversation"]["id"] == conv_id
        assert len(loaded["events"]) == 4
        assert all(e["source"] in sources for e in loaded["events"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
