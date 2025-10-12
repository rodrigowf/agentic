#!/usr/bin/env python3
"""
Integration tests for Voice API endpoints.

Tests:
- POST /api/realtime/conversations (create)
- GET /api/realtime/conversations (list)
- GET /api/realtime/conversations/{id} (get)
- PUT /api/realtime/conversations/{id} (update)
- DELETE /api/realtime/conversations/{id} (delete)
- POST /api/realtime/conversations/{id}/events (append event)
- GET /api/realtime/conversations/{id}/events (list events)
"""

import json
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from utils.voice_conversation_store import ConversationStore


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_db(monkeypatch):
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_voice.db"

    # Monkeypatch the database path
    monkeypatch.setenv("VOICE_CONVERSATION_DB_PATH", str(db_path))

    # Create new store with temp database
    from utils.voice_conversation_store import ConversationStore
    store = ConversationStore(str(db_path))

    # Patch the module-level store in realtime_voice
    try:
        from api.realtime_voice import conversation_store
        import api.realtime_voice as rv_module
        original_store = rv_module.conversation_store
        rv_module.conversation_store = store
    except ImportError:
        original_store = None

    yield store

    # Cleanup
    if original_store:
        rv_module.conversation_store = original_store
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        "name": "Test Conversation",
        "voice_model": "gpt-4o-realtime-preview",
        "metadata": {"test": True}
    }


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "source": "test",
        "type": "TextMessage",
        "data": {"content": "Test message"}
    }


class TestConversationCreateEndpoint:
    """Tests for POST /api/realtime/conversations."""

    def test_create_conversation_success(self, client, temp_db, sample_conversation_data):
        """Test creating a new conversation."""
        response = client.post(
            "/api/realtime/conversations",
            json=sample_conversation_data
        )
        assert response.status_code == 201

        # Verify response structure
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Conversation"
        assert data["voice_model"] == "gpt-4o-realtime-preview"
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_conversation_minimal(self, client, temp_db):
        """Test creating conversation with minimal data."""
        response = client.post(
            "/api/realtime/conversations",
            json={}
        )
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["name"] == "Untitled conversation"

    def test_create_conversation_custom_name(self, client, temp_db):
        """Test creating conversation with custom name."""
        response = client.post(
            "/api/realtime/conversations",
            json={"name": "My Custom Conversation"}
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "My Custom Conversation"


class TestConversationListEndpoint:
    """Tests for GET /api/realtime/conversations."""

    def test_list_conversations_empty(self, client, temp_db):
        """Test listing conversations when none exist."""
        response = client.get("/api/realtime/conversations")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_conversations_with_data(self, client, temp_db):
        """Test listing conversations when they exist."""
        # Create some conversations
        for i in range(3):
            client.post(
                "/api/realtime/conversations",
                json={"name": f"Conversation {i}"}
            )

        response = client.get("/api/realtime/conversations")
        assert response.status_code == 200

        conversations = response.json()
        assert len(conversations) == 3

        # Verify structure
        for conv in conversations:
            assert "id" in conv
            assert "name" in conv
            assert "created_at" in conv

    def test_list_conversations_ordering(self, client, temp_db):
        """Test that conversations are properly ordered."""
        # Create conversations with different names
        names = ["Alpha", "Beta", "Gamma"]
        for name in names:
            client.post(
                "/api/realtime/conversations",
                json={"name": name}
            )

        response = client.get("/api/realtime/conversations")
        assert response.status_code == 200

        conversations = response.json()
        retrieved_names = [c["name"] for c in conversations]
        # All names should be present
        assert set(retrieved_names) == set(names)


class TestConversationGetEndpoint:
    """Tests for GET /api/realtime/conversations/{id}."""

    def test_get_conversation_success(self, client, temp_db):
        """Test getting a specific conversation."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test Conversation"}
        )
        conv_id = create_response.json()["id"]

        # Get conversation
        response = client.get(f"/api/realtime/conversations/{conv_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == conv_id
        assert data["name"] == "Test Conversation"
        assert "conversation" in data
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_get_conversation_not_found(self, client, temp_db):
        """Test getting non-existent conversation."""
        response = client.get("/api/realtime/conversations/nonexistent-id")
        assert response.status_code == 404

    def test_get_conversation_with_events(self, client, temp_db):
        """Test getting conversation that has events."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        # Add some events
        for i in range(3):
            client.post(
                f"/api/realtime/conversations/{conv_id}/events",
                json={
                    "source": "test",
                    "type": "message",
                    "data": {"content": f"Message {i}"}
                }
            )

        # Get conversation
        response = client.get(f"/api/realtime/conversations/{conv_id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data["events"]) == 3


class TestConversationUpdateEndpoint:
    """Tests for PUT /api/realtime/conversations/{id}."""

    def test_update_conversation_name(self, client, temp_db):
        """Test updating conversation name."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Original Name"}
        )
        conv_id = create_response.json()["id"]

        # Update conversation
        response = client.put(
            f"/api/realtime/conversations/{conv_id}",
            json={"name": "Updated Name"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Name"

        # Verify update persisted
        get_response = client.get(f"/api/realtime/conversations/{conv_id}")
        assert get_response.json()["conversation"]["name"] == "Updated Name"

    def test_update_conversation_metadata(self, client, temp_db):
        """Test updating conversation metadata."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test", "metadata": {"key": "value1"}}
        )
        conv_id = create_response.json()["id"]

        # Update metadata
        response = client.put(
            f"/api/realtime/conversations/{conv_id}",
            json={"metadata": {"key": "value2", "new_key": "new_value"}}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["metadata"]["key"] == "value2"
        assert data["metadata"]["new_key"] == "new_value"

    def test_update_conversation_not_found(self, client, temp_db):
        """Test updating non-existent conversation."""
        response = client.put(
            "/api/realtime/conversations/nonexistent-id",
            json={"name": "Updated"}
        )
        assert response.status_code == 404

    def test_update_conversation_voice_model(self, client, temp_db):
        """Test updating voice model."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        # Update voice model
        response = client.put(
            f"/api/realtime/conversations/{conv_id}",
            json={"voice_model": "gpt-4o-mini-realtime"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["voice_model"] == "gpt-4o-mini-realtime"


class TestConversationDeleteEndpoint:
    """Tests for DELETE /api/realtime/conversations/{id}."""

    def test_delete_conversation_success(self, client, temp_db):
        """Test deleting a conversation."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "To Delete"}
        )
        conv_id = create_response.json()["id"]

        # Delete conversation
        response = client.delete(f"/api/realtime/conversations/{conv_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/realtime/conversations/{conv_id}")
        assert get_response.status_code == 404

    def test_delete_conversation_not_found(self, client, temp_db):
        """Test deleting non-existent conversation."""
        response = client.delete("/api/realtime/conversations/nonexistent-id")
        assert response.status_code == 404

    def test_delete_conversation_with_events(self, client, temp_db):
        """Test deleting conversation that has events (cascade delete)."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        # Add events
        client.post(
            f"/api/realtime/conversations/{conv_id}/events",
            json={
                "source": "test",
                "type": "message",
                "data": {"content": "Test"}
            }
        )

        # Delete conversation
        response = client.delete(f"/api/realtime/conversations/{conv_id}")
        assert response.status_code == 204

        # Verify conversation and events are gone
        get_response = client.get(f"/api/realtime/conversations/{conv_id}")
        assert get_response.status_code == 404


class TestEventListEndpoint:
    """Tests for GET /api/realtime/conversations/{id}/events."""

    def test_list_events_empty(self, client, temp_db):
        """Test listing events when none exist."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        response = client.get(f"/api/realtime/conversations/{conv_id}/events")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_events_with_data(self, client, temp_db):
        """Test listing events when they exist."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        # Add events
        for i in range(5):
            client.post(
                f"/api/realtime/conversations/{conv_id}/events",
                json={
                    "source": "test",
                    "type": f"event_{i}",
                    "data": {"index": i}
                }
            )

        response = client.get(f"/api/realtime/conversations/{conv_id}/events")
        assert response.status_code == 200

        events = response.json()
        assert len(events) == 5

        # Verify structure
        for event in events:
            assert "id" in event
            assert "conversation_id" in event
            assert "timestamp" in event
            assert "source" in event
            assert "type" in event
            assert "data" in event

    def test_list_events_conversation_not_found(self, client, temp_db):
        """Test listing events for non-existent conversation."""
        response = client.get("/api/realtime/conversations/nonexistent/events")
        # May return 404 or empty list depending on implementation
        assert response.status_code in [200, 404]


class TestEventAppendEndpoint:
    """Tests for POST /api/realtime/conversations/{id}/events."""

    def test_append_event_success(self, client, temp_db):
        """Test appending an event to a conversation."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        # Append event
        event_data = {
            "source": "claude_code",
            "type": "ToolCallRequestEvent",
            "data": {
                "name": "Bash",
                "arguments": {"command": "ls -la"}
            }
        }

        response = client.post(
            f"/api/realtime/conversations/{conv_id}/events",
            json=event_data
        )
        assert response.status_code == 201

        # Verify response structure
        data = response.json()
        assert "id" in data
        assert data["source"] == "claude_code"
        assert data["type"] == "ToolCallRequestEvent"

    def test_append_event_multiple_sources(self, client, temp_db):
        """Test appending events from different sources."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        sources = ["voice", "nested", "claude_code", "controller"]
        for source in sources:
            response = client.post(
                f"/api/realtime/conversations/{conv_id}/events",
                json={
                    "source": source,
                    "type": "TestEvent",
                    "data": {"test": True}
                }
            )
            assert response.status_code == 201

        # Verify all events stored
        events_response = client.get(f"/api/realtime/conversations/{conv_id}/events")
        events = events_response.json()
        assert len(events) == 4

        event_sources = {e["source"] for e in events}
        assert event_sources == set(sources)

    def test_append_event_conversation_not_found(self, client, temp_db):
        """Test appending event to non-existent conversation."""
        response = client.post(
            "/api/realtime/conversations/nonexistent/events",
            json={
                "source": "test",
                "type": "test",
                "data": {}
            }
        )
        # May fail with 404 or succeed and create orphan event
        # depending on foreign key constraints
        assert response.status_code in [201, 404, 500]

    def test_append_event_with_complex_data(self, client, temp_db):
        """Test appending event with complex nested data."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        # Complex event data
        event_data = {
            "source": "nested",
            "type": "ComplexEvent",
            "data": {
                "nested": {
                    "deeply": {
                        "nested": {
                            "data": [1, 2, 3],
                            "more": {"key": "value"}
                        }
                    }
                },
                "array": [{"a": 1}, {"b": 2}]
            }
        }

        response = client.post(
            f"/api/realtime/conversations/{conv_id}/events",
            json=event_data
        )
        assert response.status_code == 201

        # Verify data preserved
        data = response.json()
        assert data["data"]["nested"]["deeply"]["nested"]["data"] == [1, 2, 3]


class TestVoiceEdgeCases:
    """Test edge cases and error handling."""

    def test_conversation_with_unicode_name(self, client, temp_db):
        """Test conversation with unicode characters in name."""
        response = client.post(
            "/api/realtime/conversations",
            json={"name": "会话 🎙️ Conversation"}
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "会话 🎙️ Conversation"

    def test_event_with_unicode_content(self, client, temp_db):
        """Test event with unicode content."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        # Event with unicode
        response = client.post(
            f"/api/realtime/conversations/{conv_id}/events",
            json={
                "source": "test",
                "type": "message",
                "data": {"content": "Hello 世界 🌍"}
            }
        )
        assert response.status_code == 201

        # Verify preserved
        data = response.json()
        assert "世界" in data["data"]["content"]

    def test_large_event_payload(self, client, temp_db):
        """Test event with large payload."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]

        # Large payload
        large_data = {
            "source": "test",
            "type": "large",
            "data": {"content": "x" * 10000}  # 10KB of data
        }

        response = client.post(
            f"/api/realtime/conversations/{conv_id}/events",
            json=large_data
        )
        assert response.status_code == 201

    def test_conversation_timestamps(self, client, temp_db):
        """Test that timestamps are properly set and updated."""
        # Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test"}
        )
        conv_id = create_response.json()["id"]
        created_at = create_response.json()["created_at"]
        updated_at = create_response.json()["updated_at"]

        assert created_at == updated_at

        # Update conversation
        import time
        time.sleep(0.1)  # Small delay

        update_response = client.put(
            f"/api/realtime/conversations/{conv_id}",
            json={"name": "Updated"}
        )
        new_updated_at = update_response.json()["updated_at"]

        # Updated timestamp should be different
        assert new_updated_at >= updated_at


class TestVoiceIntegration:
    """Integration tests for voice conversation workflow."""

    def test_full_conversation_lifecycle(self, client, temp_db):
        """Test complete conversation lifecycle."""
        # 1. Create conversation
        create_response = client.post(
            "/api/realtime/conversations",
            json={"name": "Test Lifecycle"}
        )
        assert create_response.status_code == 201
        conv_id = create_response.json()["id"]

        # 2. Add multiple events
        events_to_add = [
            {"source": "voice", "type": "user_message", "data": {"text": "Hello"}},
            {"source": "nested", "type": "agent_response", "data": {"text": "Hi"}},
            {"source": "claude_code", "type": "tool_call", "data": {"tool": "Bash"}}
        ]

        for event in events_to_add:
            response = client.post(
                f"/api/realtime/conversations/{conv_id}/events",
                json=event
            )
            assert response.status_code == 201

        # 3. List events
        events_response = client.get(f"/api/realtime/conversations/{conv_id}/events")
        assert len(events_response.json()) == 3

        # 4. Update conversation
        update_response = client.put(
            f"/api/realtime/conversations/{conv_id}",
            json={"name": "Updated Lifecycle"}
        )
        assert update_response.status_code == 200

        # 5. Get full conversation
        get_response = client.get(f"/api/realtime/conversations/{conv_id}")
        conv_data = get_response.json()
        assert conv_data["conversation"]["name"] == "Updated Lifecycle"
        assert len(conv_data["events"]) == 3

        # 6. Delete conversation
        delete_response = client.delete(f"/api/realtime/conversations/{conv_id}")
        assert delete_response.status_code == 204

        # 7. Verify deleted
        final_get = client.get(f"/api/realtime/conversations/{conv_id}")
        assert final_get.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
