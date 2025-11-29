"""
Test that voice_conversation_store uses the correct database path after refactoring.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.voice_conversation_store import DEFAULT_DB_PATH, ConversationStore


def test_default_db_path_points_to_backend_dir():
    """Verify that DEFAULT_DB_PATH points to backend/ not backend/utils/"""
    # Should be /path/to/backend/voice_conversations.db
    # NOT /path/to/backend/utils/voice_conversations.db
    assert DEFAULT_DB_PATH.endswith("backend/voice_conversations.db"), \
        f"Expected DEFAULT_DB_PATH to end with 'backend/voice_conversations.db', got: {DEFAULT_DB_PATH}"

    assert "utils/voice_conversations.db" not in DEFAULT_DB_PATH, \
        f"DEFAULT_DB_PATH should not contain 'utils/', got: {DEFAULT_DB_PATH}"

    print(f"✓ DEFAULT_DB_PATH is correct: {DEFAULT_DB_PATH}")


def test_conversation_store_can_list_conversations():
    """Verify that the conversation store can access existing conversations"""
    store = ConversationStore()
    conversations = store.list_conversations()

    # We know there are conversations in the database
    assert len(conversations) > 0, "Expected to find existing conversations in database"

    # Verify structure
    for conv in conversations:
        assert "id" in conv
        assert "name" in conv
        assert "created_at" in conv
        assert "updated_at" in conv

    print(f"✓ Found {len(conversations)} conversations in database")
    print(f"  Sample: {conversations[0]['name']}")


def test_conversation_store_singleton_uses_correct_path():
    """Verify that the singleton store instance uses the correct path"""
    from utils.voice_conversation_store import store as singleton_store

    assert singleton_store.db_path == DEFAULT_DB_PATH, \
        f"Singleton store should use DEFAULT_DB_PATH, got: {singleton_store.db_path}"

    assert singleton_store.db_path.endswith("backend/voice_conversations.db"), \
        f"Singleton store path should end with 'backend/voice_conversations.db', got: {singleton_store.db_path}"

    print(f"✓ Singleton store uses correct path: {singleton_store.db_path}")


if __name__ == "__main__":
    print("Testing voice_conversation_store database path...")
    print()

    test_default_db_path_points_to_backend_dir()
    test_conversation_store_can_list_conversations()
    test_conversation_store_singleton_uses_correct_path()

    print()
    print("✓ All tests passed!")
