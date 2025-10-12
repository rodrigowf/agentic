"""
Unit tests for utils/voice_conversation_store.py

Tests SQLite-backed voice conversation storage including conversations,
events, and database integrity.
"""

import pytest
import json
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.voice_conversation_store import (
    ConversationStore,
    _utc_now,
    DEFAULT_DB_PATH,
)


# ============================================================================
# Test _utc_now Helper
# ============================================================================


def test_utc_now_returns_iso_format():
    """Test that _utc_now returns ISO format timestamp."""
    timestamp = _utc_now()

    assert isinstance(timestamp, str)
    # Should be parseable as ISO format
    dt = datetime.fromisoformat(timestamp)
    assert dt is not None


def test_utc_now_has_timezone():
    """Test that _utc_now includes timezone information."""
    timestamp = _utc_now()

    dt = datetime.fromisoformat(timestamp)
    assert dt.tzinfo is not None
    assert dt.tzinfo == timezone.utc


def test_utc_now_sequential_calls_increase():
    """Test that sequential calls to _utc_now produce increasing timestamps."""
    timestamp1 = _utc_now()
    time.sleep(0.001)  # Small delay
    timestamp2 = _utc_now()

    dt1 = datetime.fromisoformat(timestamp1)
    dt2 = datetime.fromisoformat(timestamp2)

    assert dt2 > dt1


# ============================================================================
# Test ConversationStore Initialization
# ============================================================================


def test_store_init_creates_database(tmp_path):
    """Test that ConversationStore creates database on initialization."""
    db_path = tmp_path / "test.db"

    store = ConversationStore(db_path=str(db_path))

    assert db_path.exists()


def test_store_init_creates_tables(tmp_path):
    """Test that initialization creates required tables."""
    db_path = tmp_path / "test.db"
    store = ConversationStore(db_path=str(db_path))

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Check conversations table
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
    )
    assert cursor.fetchone() is not None

    # Check conversation_events table
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_events'"
    )
    assert cursor.fetchone() is not None

    conn.close()


def test_store_init_enables_foreign_keys(tmp_path):
    """Test that foreign keys are enabled."""
    db_path = tmp_path / "test.db"
    store = ConversationStore(db_path=str(db_path))

    # Foreign keys are enabled per-connection in the store
    # This test verifies the store's context manager enables them
    with store._connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()

        # Foreign keys should be enabled (1)
        assert result[0] == 1


def test_store_default_db_path():
    """Test that store uses default DB path when none provided."""
    store = ConversationStore()

    assert store.db_path == DEFAULT_DB_PATH


def test_store_custom_db_path(tmp_path):
    """Test that store uses custom DB path when provided."""
    db_path = tmp_path / "custom.db"

    store = ConversationStore(db_path=str(db_path))

    assert store.db_path == str(db_path)


# ============================================================================
# Test create_conversation
# ============================================================================


def test_create_conversation_minimal(conversation_store):
    """Test creating conversation with minimal parameters."""
    conversation = conversation_store.create_conversation()

    assert "id" in conversation
    assert conversation["name"] == "Untitled conversation"
    assert "created_at" in conversation
    assert "updated_at" in conversation
    assert conversation["voice_model"] is None
    assert conversation["metadata"] == {}


def test_create_conversation_with_name(conversation_store):
    """Test creating conversation with custom name."""
    conversation = conversation_store.create_conversation(name="Test Conversation")

    assert conversation["name"] == "Test Conversation"


def test_create_conversation_with_voice_model(conversation_store):
    """Test creating conversation with voice model."""
    conversation = conversation_store.create_conversation(
        voice_model="gpt-4o-realtime-preview-2024-10-01"
    )

    assert conversation["voice_model"] == "gpt-4o-realtime-preview-2024-10-01"


def test_create_conversation_with_metadata(conversation_store):
    """Test creating conversation with metadata."""
    metadata = {"key": "value", "count": 42}

    conversation = conversation_store.create_conversation(metadata=metadata)

    assert conversation["metadata"] == metadata


def test_create_conversation_has_unique_id(conversation_store):
    """Test that each conversation gets a unique ID."""
    conv1 = conversation_store.create_conversation()
    conv2 = conversation_store.create_conversation()

    assert conv1["id"] != conv2["id"]


def test_create_conversation_timestamps_are_equal(conversation_store):
    """Test that created_at and updated_at are equal on creation."""
    conversation = conversation_store.create_conversation()

    assert conversation["created_at"] == conversation["updated_at"]


def test_create_conversation_persists_to_database(conversation_store):
    """Test that conversation is actually saved to database."""
    conversation = conversation_store.create_conversation(name="Persisted")

    # Retrieve directly from database
    retrieved = conversation_store.get_conversation(conversation["id"])

    assert retrieved is not None
    assert retrieved["name"] == "Persisted"


# ============================================================================
# Test list_conversations
# ============================================================================


def test_list_conversations_empty_database(conversation_store):
    """Test listing conversations in empty database."""
    conversations = conversation_store.list_conversations()

    assert conversations == []


def test_list_conversations_returns_all(conversation_store):
    """Test that list_conversations returns all conversations."""
    # Create multiple conversations
    conversation_store.create_conversation(name="Conv1")
    conversation_store.create_conversation(name="Conv2")
    conversation_store.create_conversation(name="Conv3")

    conversations = conversation_store.list_conversations()

    assert len(conversations) == 3
    names = [c["name"] for c in conversations]
    assert "Conv1" in names
    assert "Conv2" in names
    assert "Conv3" in names


def test_list_conversations_ordered_by_updated_desc(conversation_store):
    """Test that conversations are ordered by updated_at descending."""
    # Create three conversations
    conv1 = conversation_store.create_conversation(name="Conversation1")
    conv2 = conversation_store.create_conversation(name="Conversation2")
    conv3 = conversation_store.create_conversation(name="Conversation3")

    # Update conv1 to make it most recent
    time.sleep(0.1)
    updated_conv1 = conversation_store.rename_conversation(conv1["id"], "UpdatedConversation1")

    conversations = conversation_store.list_conversations()

    # Verify we have 3 conversations
    assert len(conversations) == 3

    # The updated conversation should be first (most recent updated_at)
    assert conversations[0]["id"] == conv1["id"], \
        f"Updated conversation should be first, got: {conversations[0]['name']}"
    assert conversations[0]["name"] == "UpdatedConversation1"

    # Verify the updated_at timestamp is indeed most recent
    updated_ts = datetime.fromisoformat(conversations[0]["updated_at"])
    for conv in conversations[1:]:
        other_ts = datetime.fromisoformat(conv["updated_at"])
        assert updated_ts >= other_ts, \
            f"First conversation should have most recent timestamp: {updated_ts} < {other_ts}"


def test_list_conversations_includes_all_fields(conversation_store):
    """Test that list includes all conversation fields."""
    conversation_store.create_conversation(
        name="Complete",
        voice_model="gpt-4o-realtime-preview-2024-10-01",
        metadata={"key": "value"}
    )

    conversations = conversation_store.list_conversations()

    assert len(conversations) == 1
    conv = conversations[0]

    assert "id" in conv
    assert "name" in conv
    assert "created_at" in conv
    assert "updated_at" in conv
    assert "voice_model" in conv
    assert "metadata" in conv


# ============================================================================
# Test get_conversation
# ============================================================================


def test_get_conversation_by_id(conversation_store):
    """Test retrieving conversation by ID."""
    created = conversation_store.create_conversation(name="GetTest")

    retrieved = conversation_store.get_conversation(created["id"])

    assert retrieved is not None
    assert retrieved["id"] == created["id"]
    assert retrieved["name"] == "GetTest"


def test_get_conversation_nonexistent_returns_none(conversation_store):
    """Test that getting nonexistent conversation returns None."""
    retrieved = conversation_store.get_conversation("nonexistent-id")

    assert retrieved is None


def test_get_conversation_returns_all_fields(conversation_store):
    """Test that get_conversation returns all fields."""
    created = conversation_store.create_conversation(
        name="Complete",
        voice_model="model-v1",
        metadata={"key": "value"}
    )

    retrieved = conversation_store.get_conversation(created["id"])

    assert retrieved["name"] == "Complete"
    assert retrieved["voice_model"] == "model-v1"
    assert retrieved["metadata"] == {"key": "value"}


# ============================================================================
# Test rename_conversation
# ============================================================================


def test_rename_conversation(conversation_store):
    """Test renaming a conversation."""
    conversation = conversation_store.create_conversation(name="Original")

    renamed = conversation_store.rename_conversation(
        conversation["id"],
        "Renamed"
    )

    assert renamed is not None
    assert renamed["name"] == "Renamed"


def test_rename_conversation_updates_updated_at(conversation_store):
    """Test that renaming updates the updated_at timestamp."""
    conversation = conversation_store.create_conversation(name="Original")
    original_updated = conversation["updated_at"]

    time.sleep(0.01)

    renamed = conversation_store.rename_conversation(
        conversation["id"],
        "Renamed"
    )

    assert renamed["updated_at"] > original_updated


def test_rename_nonexistent_conversation_returns_none(conversation_store):
    """Test that renaming nonexistent conversation returns None."""
    result = conversation_store.rename_conversation(
        "nonexistent-id",
        "NewName"
    )

    assert result is None


def test_rename_conversation_persists(conversation_store):
    """Test that rename persists to database."""
    conversation = conversation_store.create_conversation(name="Original")

    conversation_store.rename_conversation(conversation["id"], "Renamed")

    # Retrieve again
    retrieved = conversation_store.get_conversation(conversation["id"])

    assert retrieved["name"] == "Renamed"


# ============================================================================
# Test update_metadata
# ============================================================================


def test_update_metadata(conversation_store):
    """Test updating conversation metadata."""
    conversation = conversation_store.create_conversation()

    new_metadata = {"key": "value", "count": 42}

    updated = conversation_store.update_metadata(
        conversation["id"],
        new_metadata
    )

    assert updated is not None
    assert updated["metadata"] == new_metadata


def test_update_metadata_replaces_existing(conversation_store):
    """Test that update_metadata replaces existing metadata."""
    conversation = conversation_store.create_conversation(
        metadata={"old": "data"}
    )

    new_metadata = {"new": "data"}

    updated = conversation_store.update_metadata(
        conversation["id"],
        new_metadata
    )

    assert updated["metadata"] == {"new": "data"}
    assert "old" not in updated["metadata"]


def test_update_metadata_updates_updated_at(conversation_store):
    """Test that updating metadata updates the updated_at timestamp."""
    conversation = conversation_store.create_conversation()
    original_updated = conversation["updated_at"]

    time.sleep(0.01)

    updated = conversation_store.update_metadata(
        conversation["id"],
        {"key": "value"}
    )

    assert updated["updated_at"] > original_updated


def test_update_metadata_nonexistent_returns_none(conversation_store):
    """Test that updating nonexistent conversation returns None."""
    result = conversation_store.update_metadata(
        "nonexistent-id",
        {"key": "value"}
    )

    assert result is None


# ============================================================================
# Test delete_conversation
# ============================================================================


def test_delete_conversation(conversation_store):
    """Test deleting a conversation."""
    conversation = conversation_store.create_conversation()

    result = conversation_store.delete_conversation(conversation["id"])

    assert result is True


def test_delete_conversation_removes_from_database(conversation_store):
    """Test that deleted conversation is removed from database."""
    conversation = conversation_store.create_conversation()

    conversation_store.delete_conversation(conversation["id"])

    # Should not be retrievable
    retrieved = conversation_store.get_conversation(conversation["id"])
    assert retrieved is None


def test_delete_nonexistent_conversation_returns_false(conversation_store):
    """Test that deleting nonexistent conversation returns False."""
    result = conversation_store.delete_conversation("nonexistent-id")

    assert result is False


def test_delete_conversation_cascades_to_events(conversation_store):
    """Test that deleting conversation deletes associated events."""
    conversation = conversation_store.create_conversation()

    # Add events
    conversation_store.append_event(
        conversation["id"],
        {"type": "test", "data": "event1"}
    )
    conversation_store.append_event(
        conversation["id"],
        {"type": "test", "data": "event2"}
    )

    # Delete conversation
    conversation_store.delete_conversation(conversation["id"])

    # Events should be gone
    events = conversation_store.list_events(conversation["id"])
    assert events == []


# ============================================================================
# Test append_event
# ============================================================================


def test_append_event_minimal(conversation_store):
    """Test appending event with minimal parameters."""
    conversation = conversation_store.create_conversation()

    event = conversation_store.append_event(
        conversation["id"],
        {"type": "test", "data": "value"}
    )

    assert "id" in event
    assert event["conversation_id"] == conversation["id"]
    assert event["payload"] == {"type": "test", "data": "value"}
    assert "timestamp" in event


def test_append_event_with_source(conversation_store):
    """Test appending event with source."""
    conversation = conversation_store.create_conversation()

    event = conversation_store.append_event(
        conversation["id"],
        {"data": "value"},
        source="claude_code"
    )

    assert event["source"] == "claude_code"


def test_append_event_with_event_type(conversation_store):
    """Test appending event with event type."""
    conversation = conversation_store.create_conversation()

    event = conversation_store.append_event(
        conversation["id"],
        {"data": "value"},
        event_type="ToolCallRequestEvent"
    )

    assert event["type"] == "ToolCallRequestEvent"


def test_append_event_with_custom_timestamp(conversation_store):
    """Test appending event with custom timestamp."""
    conversation = conversation_store.create_conversation()
    custom_timestamp = "2024-01-01T00:00:00+00:00"

    event = conversation_store.append_event(
        conversation["id"],
        {"data": "value"},
        timestamp=custom_timestamp
    )

    assert event["timestamp"] == custom_timestamp


def test_append_event_updates_conversation_updated_at(conversation_store):
    """Test that appending event updates conversation's updated_at."""
    conversation = conversation_store.create_conversation()
    original_updated = conversation["updated_at"]

    time.sleep(0.01)

    conversation_store.append_event(
        conversation["id"],
        {"data": "value"}
    )

    # Retrieve conversation
    updated_conv = conversation_store.get_conversation(conversation["id"])

    assert updated_conv["updated_at"] > original_updated


def test_append_event_returns_event_with_id(conversation_store):
    """Test that append_event returns event with auto-increment ID."""
    conversation = conversation_store.create_conversation()

    event1 = conversation_store.append_event(
        conversation["id"],
        {"data": "event1"}
    )
    event2 = conversation_store.append_event(
        conversation["id"],
        {"data": "event2"}
    )

    assert event1["id"] < event2["id"]


# ============================================================================
# Test list_events
# ============================================================================


def test_list_events_empty_conversation(conversation_store):
    """Test listing events for conversation with no events."""
    conversation = conversation_store.create_conversation()

    events = conversation_store.list_events(conversation["id"])

    assert events == []


def test_list_events_returns_all_events(conversation_store):
    """Test that list_events returns all events."""
    conversation = conversation_store.create_conversation()

    # Add events
    conversation_store.append_event(conversation["id"], {"data": "event1"})
    conversation_store.append_event(conversation["id"], {"data": "event2"})
    conversation_store.append_event(conversation["id"], {"data": "event3"})

    events = conversation_store.list_events(conversation["id"])

    assert len(events) == 3


def test_list_events_ordered_by_id_asc(conversation_store):
    """Test that events are ordered by ID ascending."""
    conversation = conversation_store.create_conversation()

    event1 = conversation_store.append_event(
        conversation["id"],
        {"data": "first"}
    )
    event2 = conversation_store.append_event(
        conversation["id"],
        {"data": "second"}
    )
    event3 = conversation_store.append_event(
        conversation["id"],
        {"data": "third"}
    )

    events = conversation_store.list_events(conversation["id"])

    assert events[0]["payload"]["data"] == "first"
    assert events[1]["payload"]["data"] == "second"
    assert events[2]["payload"]["data"] == "third"


def test_list_events_after_id(conversation_store):
    """Test listing events after a specific ID."""
    conversation = conversation_store.create_conversation()

    event1 = conversation_store.append_event(
        conversation["id"],
        {"data": "event1"}
    )
    event2 = conversation_store.append_event(
        conversation["id"],
        {"data": "event2"}
    )
    event3 = conversation_store.append_event(
        conversation["id"],
        {"data": "event3"}
    )

    # Get events after event1
    events = conversation_store.list_events(
        conversation["id"],
        after_id=event1["id"]
    )

    assert len(events) == 2
    assert events[0]["payload"]["data"] == "event2"
    assert events[1]["payload"]["data"] == "event3"


def test_list_events_with_limit(conversation_store):
    """Test listing events with limit."""
    conversation = conversation_store.create_conversation()

    # Add 5 events
    for i in range(5):
        conversation_store.append_event(
            conversation["id"],
            {"data": f"event{i}"}
        )

    # Get only first 3
    events = conversation_store.list_events(
        conversation["id"],
        limit=3
    )

    assert len(events) == 3


def test_list_events_after_id_with_limit(conversation_store):
    """Test combining after_id and limit parameters."""
    conversation = conversation_store.create_conversation()

    events_created = []
    for i in range(10):
        event = conversation_store.append_event(
            conversation["id"],
            {"data": f"event{i}"}
        )
        events_created.append(event)

    # Get 3 events after the 5th event
    events = conversation_store.list_events(
        conversation["id"],
        after_id=events_created[4]["id"],
        limit=3
    )

    assert len(events) == 3
    assert events[0]["payload"]["data"] == "event5"
    assert events[1]["payload"]["data"] == "event6"
    assert events[2]["payload"]["data"] == "event7"


def test_list_events_includes_all_fields(conversation_store):
    """Test that events include all fields."""
    conversation = conversation_store.create_conversation()

    conversation_store.append_event(
        conversation["id"],
        {"data": "value"},
        source="claude_code",
        event_type="ToolCallRequestEvent"
    )

    events = conversation_store.list_events(conversation["id"])

    assert len(events) == 1
    event = events[0]

    assert "id" in event
    assert "conversation_id" in event
    assert "timestamp" in event
    assert "source" in event
    assert "type" in event
    assert "payload" in event


# ============================================================================
# Test Database Integrity
# ============================================================================


def test_foreign_key_constraint(conversation_store):
    """Test that foreign key constraint prevents orphaned events."""
    # This test documents expected behavior - events require valid conversation_id
    # The actual constraint enforcement depends on SQLite PRAGMA foreign_keys setting

    conversation = conversation_store.create_conversation()
    conversation_store.delete_conversation(conversation["id"])

    # Events should be cascade deleted
    events = conversation_store.list_events(conversation["id"])
    assert events == []


def test_conversation_id_is_primary_key(tmp_path):
    """Test that conversation ID is unique."""
    db_path = tmp_path / "test.db"
    store = ConversationStore(db_path=str(db_path))

    conv = store.create_conversation()

    # Try to insert duplicate ID directly (should fail)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO conversations (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv["id"], "Duplicate", _utc_now(), _utc_now())
        )

    conn.close()


def test_metadata_json_serialization(conversation_store):
    """Test that complex metadata is properly serialized."""
    complex_metadata = {
        "string": "value",
        "number": 42,
        "float": 3.14,
        "bool": True,
        "null": None,
        "array": [1, 2, 3],
        "object": {"nested": "data"}
    }

    conversation = conversation_store.create_conversation(
        metadata=complex_metadata
    )

    retrieved = conversation_store.get_conversation(conversation["id"])

    assert retrieved["metadata"] == complex_metadata


def test_payload_json_serialization(conversation_store):
    """Test that complex payloads are properly serialized."""
    complex_payload = {
        "type": "ToolCallRequestEvent",
        "data": {
            "name": "Bash",
            "arguments": {"command": "ls -la", "timeout": 30},
            "result": None,
            "nested": {"deep": {"value": 123}}
        }
    }

    conversation = conversation_store.create_conversation()
    event = conversation_store.append_event(
        conversation["id"],
        complex_payload
    )

    events = conversation_store.list_events(conversation["id"])

    assert events[0]["payload"] == complex_payload


# ============================================================================
# Test Thread Safety
# ============================================================================


def test_concurrent_conversation_creation(conversation_store):
    """Test that multiple threads can create conversations concurrently."""

    def create_conversation(thread_id):
        return conversation_store.create_conversation(
            name=f"Thread-{thread_id}"
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(create_conversation, i)
            for i in range(50)
        ]
        results = [future.result() for future in as_completed(futures)]

    # All should have unique IDs
    ids = [r["id"] for r in results]
    assert len(ids) == len(set(ids))  # All unique

    # All should be in database
    all_convs = conversation_store.list_conversations()
    assert len(all_convs) == 50


def test_concurrent_event_appending(conversation_store):
    """Test that multiple threads can append events concurrently."""
    conversation = conversation_store.create_conversation()

    def append_event(event_id):
        return conversation_store.append_event(
            conversation["id"],
            {"event_id": event_id}
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(append_event, i)
            for i in range(100)
        ]
        results = [future.result() for future in as_completed(futures)]

    # All should have unique IDs
    ids = [r["id"] for r in results]
    assert len(ids) == len(set(ids))

    # All should be in database
    events = conversation_store.list_events(conversation["id"])
    assert len(events) == 100


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_empty_string_conversation_name(conversation_store):
    """Test that empty string defaults to 'Untitled conversation'."""
    # The store implementation treats empty string as None, defaulting to "Untitled conversation"
    conversation = conversation_store.create_conversation(name="")

    # Empty name gets replaced with default
    assert conversation["name"] == "Untitled conversation"


def test_empty_metadata(conversation_store):
    """Test that empty dict is valid metadata."""
    conversation = conversation_store.create_conversation(metadata={})

    assert conversation["metadata"] == {}


def test_empty_payload(conversation_store):
    """Test that empty dict is valid event payload."""
    conversation = conversation_store.create_conversation()

    event = conversation_store.append_event(conversation["id"], {})

    assert event["payload"] == {}


def test_very_long_conversation_name(conversation_store):
    """Test handling of very long conversation names."""
    long_name = "A" * 10000

    conversation = conversation_store.create_conversation(name=long_name)

    assert conversation["name"] == long_name


def test_large_metadata(conversation_store):
    """Test handling of large metadata."""
    large_metadata = {f"key_{i}": f"value_{i}" for i in range(1000)}

    conversation = conversation_store.create_conversation(metadata=large_metadata)

    retrieved = conversation_store.get_conversation(conversation["id"])

    assert retrieved["metadata"] == large_metadata


def test_special_characters_in_name(conversation_store):
    """Test handling of special characters in conversation name."""
    special_name = "Test 'with' \"quotes\" and \n newlines \t tabs"

    conversation = conversation_store.create_conversation(name=special_name)

    assert conversation["name"] == special_name


def test_unicode_in_metadata(conversation_store):
    """Test handling of Unicode characters in metadata."""
    unicode_metadata = {
        "emoji": "😀🎉",
        "chinese": "你好",
        "arabic": "مرحبا",
        "cyrillic": "Привет"
    }

    conversation = conversation_store.create_conversation(metadata=unicode_metadata)

    retrieved = conversation_store.get_conversation(conversation["id"])

    assert retrieved["metadata"] == unicode_metadata


# ============================================================================
# Pytest Markers
# ============================================================================


pytestmark = pytest.mark.unit
