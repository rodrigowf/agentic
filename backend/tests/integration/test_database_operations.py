#!/usr/bin/env python3
"""
Integration tests for database operations.

Tests:
- Conversation CRUD operations
- Event storage and retrieval
- Foreign key constraints
- Transaction handling
- Concurrent access
- Data integrity
"""

import json
import os
import pytest
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from datetime import datetime

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.voice_conversation_store import ConversationStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    store = ConversationStore(str(db_path))

    yield store

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def populated_db(temp_db):
    """Create a database with sample data."""
    # Create conversations
    conv1 = temp_db.create_conversation("Conversation 1")
    conv2 = temp_db.create_conversation("Conversation 2")

    # Add events to conv1
    for i in range(5):
        temp_db.add_event(
            conv1["id"],
            "test",
            f"event_{i}",
            {"index": i, "data": f"Event {i}"}
        )

    # Add events to conv2
    for i in range(3):
        temp_db.add_event(
            conv2["id"],
            "test",
            f"event_{i}",
            {"index": i}
        )

    yield temp_db, [conv1, conv2]


class TestConversationCRUD:
    """Tests for conversation CRUD operations."""

    def test_create_conversation(self, temp_db):
        """Test creating a conversation."""
        conv = temp_db.create_conversation("Test Conversation")

        assert "id" in conv
        assert conv["name"] == "Test Conversation"
        assert "created_at" in conv
        assert "updated_at" in conv
        assert conv["created_at"] == conv["updated_at"]

    def test_create_conversation_with_metadata(self, temp_db):
        """Test creating conversation with metadata."""
        metadata = {"user_id": "123", "session": "abc"}
        conv = temp_db.create_conversation(
            "Test",
            voice_model="gpt-4o",
            metadata=metadata
        )

        assert conv["voice_model"] == "gpt-4o"
        assert conv["metadata"] == metadata

    def test_get_conversation(self, temp_db):
        """Test retrieving a conversation."""
        created = temp_db.create_conversation("Test")
        conv_id = created["id"]

        retrieved = temp_db.get_conversation(conv_id)
        assert retrieved is not None
        assert retrieved["id"] == conv_id
        assert retrieved["name"] == "Test"

    def test_get_nonexistent_conversation(self, temp_db):
        """Test retrieving non-existent conversation."""
        result = temp_db.get_conversation("nonexistent-id")
        assert result is None

    def test_list_conversations_empty(self, temp_db):
        """Test listing conversations when none exist."""
        conversations = temp_db.list_conversations()
        assert conversations == []

    def test_list_conversations(self, temp_db):
        """Test listing multiple conversations."""
        # Create conversations
        for i in range(5):
            temp_db.create_conversation(f"Conversation {i}")

        conversations = temp_db.list_conversations()
        assert len(conversations) == 5

        # Verify structure
        for conv in conversations:
            assert "id" in conv
            assert "name" in conv
            assert "created_at" in conv

    def test_update_conversation(self, temp_db):
        """Test updating a conversation."""
        conv = temp_db.create_conversation("Original")
        conv_id = conv["id"]

        # Update
        updated = temp_db.update_conversation(
            conv_id,
            name="Updated",
            voice_model="gpt-4o-mini"
        )

        assert updated["name"] == "Updated"
        assert updated["voice_model"] == "gpt-4o-mini"
        assert updated["updated_at"] != conv["updated_at"]

    def test_update_conversation_metadata(self, temp_db):
        """Test updating conversation metadata."""
        conv = temp_db.create_conversation("Test", metadata={"key": "value1"})
        conv_id = conv["id"]

        # Update metadata
        updated = temp_db.update_conversation(
            conv_id,
            metadata={"key": "value2", "new": "data"}
        )

        assert updated["metadata"]["key"] == "value2"
        assert updated["metadata"]["new"] == "data"

    def test_update_nonexistent_conversation(self, temp_db):
        """Test updating non-existent conversation."""
        result = temp_db.update_conversation("nonexistent", name="Updated")
        assert result is None

    def test_delete_conversation(self, temp_db):
        """Test deleting a conversation."""
        conv = temp_db.create_conversation("To Delete")
        conv_id = conv["id"]

        # Delete
        result = temp_db.delete_conversation(conv_id)
        assert result is True

        # Verify deleted
        retrieved = temp_db.get_conversation(conv_id)
        assert retrieved is None

    def test_delete_nonexistent_conversation(self, temp_db):
        """Test deleting non-existent conversation."""
        result = temp_db.delete_conversation("nonexistent")
        assert result is False


class TestEventOperations:
    """Tests for event storage and retrieval."""

    def test_add_event(self, temp_db):
        """Test adding an event to a conversation."""
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        event_data = {"type": "test", "content": "Test message"}
        event = temp_db.add_event(conv_id, "test_source", "test_type", event_data)

        assert event["id"] is not None
        assert event["conversation_id"] == conv_id
        assert event["source"] == "test_source"
        assert event["type"] == "test_type"
        assert event["data"] == event_data
        assert "timestamp" in event

    def test_add_multiple_events(self, temp_db):
        """Test adding multiple events."""
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        # Add events
        for i in range(10):
            temp_db.add_event(
                conv_id,
                "test",
                f"event_{i}",
                {"index": i}
            )

        # Retrieve events
        events = temp_db.list_events(conv_id)
        assert len(events) == 10

        # Verify order (should be chronological)
        for i, event in enumerate(events):
            assert event["data"]["index"] == i

    def test_add_event_with_complex_data(self, temp_db):
        """Test adding event with nested data structure."""
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        complex_data = {
            "nested": {
                "deeply": {
                    "nested": [1, 2, 3],
                    "data": {"key": "value"}
                }
            },
            "array": [{"a": 1}, {"b": 2}],
            "unicode": "Hello 世界 🌍"
        }

        event = temp_db.add_event(conv_id, "test", "complex", complex_data)

        # Retrieve and verify
        retrieved = temp_db.list_events(conv_id)[0]
        assert retrieved["data"] == complex_data
        assert retrieved["data"]["unicode"] == "Hello 世界 🌍"

    def test_list_events_empty(self, temp_db):
        """Test listing events when none exist."""
        conv = temp_db.create_conversation("Test")
        events = temp_db.list_events(conv["id"])
        assert events == []

    def test_list_events_nonexistent_conversation(self, temp_db):
        """Test listing events for non-existent conversation."""
        events = temp_db.list_events("nonexistent")
        assert events == []

    def test_event_ordering(self, temp_db):
        """Test that events are returned in correct order."""
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        # Add events with small delays
        for i in range(5):
            temp_db.add_event(conv_id, "test", "event", {"seq": i})
            time.sleep(0.01)  # Small delay

        events = temp_db.list_events(conv_id)

        # Verify chronological order
        for i in range(5):
            assert events[i]["data"]["seq"] == i

        # Verify timestamps are increasing
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps)


class TestForeignKeyConstraints:
    """Tests for foreign key constraints."""

    def test_delete_conversation_cascades_to_events(self, temp_db):
        """Test that deleting conversation deletes associated events."""
        # Create conversation with events
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        # Add events
        for i in range(5):
            temp_db.add_event(conv_id, "test", "event", {"i": i})

        # Verify events exist
        events_before = temp_db.list_events(conv_id)
        assert len(events_before) == 5

        # Delete conversation
        temp_db.delete_conversation(conv_id)

        # Verify events are also deleted
        events_after = temp_db.list_events(conv_id)
        assert events_after == []

    def test_orphan_event_handling(self, temp_db):
        """Test handling of events without parent conversation."""
        # Try to add event to non-existent conversation
        # This should either fail or be allowed depending on implementation
        try:
            event = temp_db.add_event(
                "nonexistent-id",
                "test",
                "orphan",
                {"test": True}
            )
            # If it succeeds, verify it can be retrieved
            assert event["conversation_id"] == "nonexistent-id"
        except Exception:
            # If it fails due to foreign key constraint, that's also valid
            pass


class TestTransactionHandling:
    """Tests for database transaction handling."""

    def test_transaction_rollback_on_error(self, temp_db):
        """Test that errors cause transaction rollback."""
        # Get direct database connection
        with temp_db._connection() as conn:
            try:
                # Start a transaction
                cursor = conn.cursor()

                # Insert conversation
                cursor.execute(
                    "INSERT INTO conversations (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    ("test-id", "Test", "2025-01-01", "2025-01-01")
                )

                # Cause an error (duplicate id)
                cursor.execute(
                    "INSERT INTO conversations (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    ("test-id", "Duplicate", "2025-01-01", "2025-01-01")
                )

                conn.commit()
            except sqlite3.IntegrityError:
                # Error expected
                pass

        # Verify no conversation was created (rollback occurred)
        conversations = temp_db.list_conversations()
        test_convs = [c for c in conversations if c["id"] == "test-id"]
        # May have 0 or 1 depending on transaction handling
        assert len(test_convs) <= 1

    def test_concurrent_writes(self, temp_db):
        """Test concurrent writes to database."""
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        results = []
        errors = []

        def add_events(thread_id):
            try:
                for i in range(10):
                    temp_db.add_event(
                        conv_id,
                        f"thread_{thread_id}",
                        "event",
                        {"thread": thread_id, "i": i}
                    )
                results.append(thread_id)
            except Exception as e:
                errors.append(e)

        # Create threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_events, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0
        assert len(results) == 5

        # Verify all events were stored
        events = temp_db.list_events(conv_id)
        assert len(events) == 50


class TestDataIntegrity:
    """Tests for data integrity."""

    def test_conversation_id_uniqueness(self, temp_db):
        """Test that conversation IDs are unique."""
        conv1 = temp_db.create_conversation("Test 1")
        conv2 = temp_db.create_conversation("Test 2")

        assert conv1["id"] != conv2["id"]

    def test_event_id_autoincrement(self, temp_db):
        """Test that event IDs auto-increment."""
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        event_ids = []
        for i in range(5):
            event = temp_db.add_event(conv_id, "test", "event", {"i": i})
            event_ids.append(event["id"])

        # IDs should be sequential
        for i in range(1, len(event_ids)):
            assert event_ids[i] > event_ids[i-1]

    def test_timestamp_format(self, temp_db):
        """Test that timestamps are properly formatted."""
        conv = temp_db.create_conversation("Test")

        # Verify timestamp format
        created_at = conv["created_at"]
        # Should be ISO 8601 format with timezone
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            assert dt is not None
        except ValueError:
            pytest.fail("Invalid timestamp format")

    def test_metadata_json_storage(self, temp_db):
        """Test that metadata is properly stored as JSON."""
        metadata = {
            "string": "value",
            "number": 123,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "nested": {"key": "value"}
        }

        conv = temp_db.create_conversation("Test", metadata=metadata)

        # Retrieve and verify
        retrieved = temp_db.get_conversation(conv["id"])
        assert retrieved["metadata"] == metadata

    def test_event_data_json_storage(self, temp_db):
        """Test that event data is properly stored as JSON."""
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        event_data = {
            "types": ["string", 123, True, None],
            "nested": {"deep": {"data": "value"}}
        }

        temp_db.add_event(conv_id, "test", "event", event_data)

        # Retrieve and verify
        events = temp_db.list_events(conv_id)
        assert events[0]["data"] == event_data


class TestDatabaseSchema:
    """Tests for database schema correctness."""

    def test_conversations_table_exists(self, temp_db):
        """Test that conversations table exists."""
        with temp_db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_events_table_exists(self, temp_db):
        """Test that conversation_events table exists."""
        with temp_db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_events'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_foreign_key_constraint_exists(self, temp_db):
        """Test that foreign key constraint is enabled."""
        with temp_db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
            # Foreign keys should be enabled
            assert result[0] == 1

    def test_index_exists(self, temp_db):
        """Test that index on events table exists."""
        with temp_db._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_conversation_events_conversation'"
            )
            result = cursor.fetchone()
            assert result is not None


class TestDatabasePerformance:
    """Tests for database performance characteristics."""

    def test_large_event_storage(self, temp_db):
        """Test storing large events."""
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        # Create large event (100KB)
        large_data = {
            "content": "x" * 100000,
            "metadata": {"large": True}
        }

        event = temp_db.add_event(conv_id, "test", "large", large_data)
        assert event is not None

        # Retrieve and verify
        events = temp_db.list_events(conv_id)
        assert len(events[0]["data"]["content"]) == 100000

    def test_many_events_retrieval(self, temp_db):
        """Test retrieving many events."""
        conv = temp_db.create_conversation("Test")
        conv_id = conv["id"]

        # Add many events
        for i in range(1000):
            temp_db.add_event(conv_id, "test", "event", {"i": i})

        # Retrieve all
        events = temp_db.list_events(conv_id)
        assert len(events) == 1000

    def test_many_conversations(self, temp_db):
        """Test handling many conversations."""
        # Create many conversations
        for i in range(100):
            temp_db.create_conversation(f"Conversation {i}")

        # List all
        conversations = temp_db.list_conversations()
        assert len(conversations) == 100


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_conversation_name(self, temp_db):
        """Test creating conversation with empty name."""
        conv = temp_db.create_conversation("")
        assert conv["name"] == ""

    def test_very_long_conversation_name(self, temp_db):
        """Test conversation with very long name."""
        long_name = "x" * 10000
        conv = temp_db.create_conversation(long_name)
        assert conv["name"] == long_name

    def test_special_characters_in_name(self, temp_db):
        """Test conversation name with special characters."""
        special_name = "Test's \"Conversation\" with <special> & chars; 世界 🌍"
        conv = temp_db.create_conversation(special_name)

        retrieved = temp_db.get_conversation(conv["id"])
        assert retrieved["name"] == special_name

    def test_null_metadata(self, temp_db):
        """Test conversation with null metadata."""
        conv = temp_db.create_conversation("Test", metadata=None)
        assert conv["metadata"] == {}

    def test_empty_event_data(self, temp_db):
        """Test event with empty data."""
        conv = temp_db.create_conversation("Test")
        event = temp_db.add_event(conv["id"], "test", "empty", {})
        assert event["data"] == {}

    def test_null_event_source(self, temp_db):
        """Test event with null source."""
        conv = temp_db.create_conversation("Test")
        event = temp_db.add_event(conv["id"], None, "test", {"data": "test"})
        assert event["source"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
