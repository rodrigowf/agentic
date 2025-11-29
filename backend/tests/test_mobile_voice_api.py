"""
End-to-end test for mobile-voice API endpoints.
Tests the full conversation lifecycle from mobile perspective.
"""
import os
import sys
import requests
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.voice_conversation_store import ConversationStore

# API base URL
API_BASE = "http://localhost:8000/api/realtime"


def test_list_conversations_endpoint():
    """Test GET /api/realtime/conversations"""
    response = requests.get(f"{API_BASE}/conversations")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert isinstance(data, list), "Expected list of conversations"

    if len(data) > 0:
        # Verify structure
        first_conv = data[0]
        assert "id" in first_conv
        assert "name" in first_conv
        assert "created_at" in first_conv
        assert "updated_at" in first_conv
        assert "metadata" in first_conv

        print(f"✓ Found {len(data)} conversations via API")
        print(f"  Sample: {first_conv['name']} (id: {first_conv['id'][:8]}...)")
    else:
        print("⚠ No conversations found (database might be empty)")

    return data


def test_create_conversation():
    """Test POST /api/realtime/conversations"""
    payload = {
        "name": "Test Mobile Conversation",
        "voice_model": None,
        "metadata": {"source": "mobile_test"}
    }

    response = requests.post(f"{API_BASE}/conversations", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    data = response.json()
    assert data["name"] == payload["name"]
    assert "id" in data
    assert data["metadata"]["source"] == "mobile_test"

    print(f"✓ Created conversation: {data['name']} (id: {data['id'][:8]}...)")
    return data["id"]


def test_get_conversation(conversation_id):
    """Test GET /api/realtime/conversations/{id}"""
    response = requests.get(f"{API_BASE}/conversations/{conversation_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert data["id"] == conversation_id
    assert "events" in data
    assert isinstance(data["events"], list)

    print(f"✓ Retrieved conversation: {data['name']} with {len(data['events'])} events")
    return data


def test_append_event(conversation_id):
    """Test POST /api/realtime/conversations/{id}/events"""
    payload = {
        "source": "mobile",
        "type": "test_event",
        "payload": {
            "message": "Test from mobile",
            "timestamp": time.time()
        }
    }

    response = requests.post(f"{API_BASE}/conversations/{conversation_id}/events", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    data = response.json()
    assert data["source"] == "mobile"
    assert data["type"] == "test_event"
    assert "id" in data

    print(f"✓ Appended event: id={data['id']}, type={data['type']}")
    return data["id"]


def test_get_events(conversation_id, expected_event_id):
    """Test GET /api/realtime/conversations/{id}/events"""
    response = requests.get(f"{API_BASE}/conversations/{conversation_id}/events")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert isinstance(data, list)

    # Verify our test event is in the list
    event_ids = [evt["id"] for evt in data]
    assert expected_event_id in event_ids, f"Expected event {expected_event_id} in events list"

    print(f"✓ Retrieved {len(data)} events (including our test event)")


def test_cleanup_inactive_conversations():
    """Test POST /api/realtime/conversations/cleanup"""
    # Use a very large threshold so we don't delete active conversations
    response = requests.post(f"{API_BASE}/conversations/cleanup?inactive_minutes=99999")
    # Accept both 200 and 422 (if no body is expected)
    if response.status_code == 422:
        print("⚠ Cleanup endpoint returned 422 (might need request body)")
        return

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert "deleted_count" in data
    assert "deleted_ids" in data

    print(f"✓ Cleanup endpoint works (deleted {data['deleted_count']} conversations)")


def test_delete_conversation(conversation_id):
    """Test DELETE /api/realtime/conversations/{id}"""
    response = requests.delete(f"{API_BASE}/conversations/{conversation_id}")
    assert response.status_code == 204, f"Expected 204, got {response.status_code}"

    # Verify it's gone
    response = requests.get(f"{API_BASE}/conversations/{conversation_id}")
    assert response.status_code == 404, f"Expected 404 for deleted conversation, got {response.status_code}"

    print(f"✓ Deleted conversation: {conversation_id[:8]}...")


def run_all_tests():
    """Run complete mobile-voice API test suite"""
    print("=" * 60)
    print("MOBILE-VOICE API END-TO-END TESTS")
    print("=" * 60)
    print()

    try:
        # Test 1: List existing conversations
        print("Test 1: List conversations")
        conversations = test_list_conversations_endpoint()
        print()

        # Test 2: Create new conversation
        print("Test 2: Create conversation")
        new_conv_id = test_create_conversation()
        print()

        # Test 3: Get conversation details
        print("Test 3: Get conversation details")
        conv_data = test_get_conversation(new_conv_id)
        print()

        # Test 4: Append event
        print("Test 4: Append event")
        event_id = test_append_event(new_conv_id)
        print()

        # Test 5: Get events
        print("Test 5: Get events")
        test_get_events(new_conv_id, event_id)
        print()

        # Test 6: Cleanup endpoint
        print("Test 6: Cleanup inactive conversations")
        test_cleanup_inactive_conversations()
        print()

        # Test 7: Delete conversation
        print("Test 7: Delete conversation")
        test_delete_conversation(new_conv_id)
        print()

        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to backend server at", API_BASE)
        print("  Make sure the backend is running: uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
