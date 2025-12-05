#!/usr/bin/env python3
"""
Check if a WebRTC session is stale by comparing timestamps.
"""
import sys
from datetime import datetime, timezone
import json

def check_session_age(conversation_file):
    """Analyze session age from conversation export."""
    with open(conversation_file) as f:
        data = json.load(f)

    conv = data['conversation']
    events = data['events']

    # Parse timestamps
    created = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
    updated = datetime.fromisoformat(conv['updated_at'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)

    # Find session_started events
    session_events = [e for e in events if e.get('payload', {}).get('type') == 'session_started']

    print("=" * 70)
    print("SESSION AGE DIAGNOSTIC")
    print("=" * 70)
    print(f"\nConversation ID: {conv['id']}")
    print(f"Name: {conv.get('name', 'N/A')}")
    print(f"\nTimestamps:")
    print(f"  Created:  {created.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Updated:  {updated.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Now:      {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    age_minutes = (now - created).total_seconds() / 60
    print(f"\nAge: {age_minutes:.1f} minutes")

    if session_events:
        print(f"\nSession Started Events: {len(session_events)}")
        for i, evt in enumerate(session_events):
            session_time = datetime.fromisoformat(evt['timestamp'].replace('Z', '+00:00'))
            session_age_min = (now - session_time).total_seconds() / 60
            payload = evt['payload']

            print(f"\n  Session #{i+1}:")
            print(f"    Backend Session ID: {payload.get('session_id', 'N/A')}")
            print(f"    Transport: {payload.get('transport', 'N/A')}")
            print(f"    Started: {session_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"    Age: {session_age_min:.1f} minutes")

            if session_age_min > 60:
                print(f"    ⚠️  WARNING: Session is {session_age_min:.0f} minutes old!")
                print(f"    ⚠️  OpenAI sessions typically expire after 15-60 minutes")
    else:
        print("\n  No session_started events found")

    # Check for OpenAI session ID in other events
    print("\nLooking for OpenAI session IDs in backend logs...")
    print("  (OpenAI session IDs start with 'sess_')")
    print("  Run: grep 'Session created: sess_' /tmp/agentic-logs/backend.log | tail -5")

    print("\n" + "=" * 70)
    print("RECOMMENDATION:")
    if age_minutes > 15:
        print("  🔄 This session may be stale - create a NEW conversation:")
        print("     1. Go to http://localhost:3000/agentic/voice")
        print("     2. Click 'New Conversation' or navigate to /voice (without ID)")
        print("     3. This will create a fresh OpenAI session")
    else:
        print("  ✅ Session is recent (< 15 minutes old)")
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_session_age.py <conversation_file.json>")
        print("\nExample:")
        print("  python3 debug/check_session_age.py debug/db_exports/voice_conversations/6bad2b1d-821f-4585-9af8-4ad0ff18cf73.json")
        sys.exit(1)

    check_session_age(sys.argv[1])
