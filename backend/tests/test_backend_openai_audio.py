"""
Phase 1 Test: Backend → OpenAI Audio Isolation Test
Tests if backend can send audio to OpenAI and receive responses
No frontend involved - pure backend testing
"""
import asyncio
import numpy as np
import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env file
load_dotenv()

from api.openai_webrtc_client import OpenAIWebRTCClient

async def test_backend_to_openai():
    """Send simulated audio to OpenAI and verify events"""

    print("=" * 60)
    print("Phase 1: Backend → OpenAI Audio Test")
    print("=" * 60)
    print()

    received_events = []
    received_audio = []

    # Callbacks to track what we receive
    def on_audio(audio_data):
        received_audio.append(len(audio_data))
        print(f"✓ Received {len(audio_data)} bytes from OpenAI")

    def on_event(event):
        event_type = event.get('type')
        received_events.append(event_type)
        print(f"✓ Event: {event_type}")

    # 1. Create OpenAI client
    print("1. Creating OpenAI client...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set")
        return False

    client = OpenAIWebRTCClient(
        api_key=api_key,
        voice="alloy",
        on_audio_callback=on_audio,
        on_event_callback=on_event
    )
    print("✓ Client created")
    print()

    # 2. Connect to OpenAI
    print("2. Connecting to OpenAI Realtime API...")
    try:
        await client.connect()
        print("✓ Connected to OpenAI")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    print()

    # Wait for initial events
    await asyncio.sleep(1)

    # 2.5. Send a session.update command to trigger session.updated event
    print("2.5. Sending session.update command...")
    # Wait for data channel to be open
    max_wait = 5
    waited = 0
    while client.data_channel and client.data_channel.readyState != "open" and waited < max_wait:
        await asyncio.sleep(0.1)
        waited += 0.1

    if client.data_channel and client.data_channel.readyState == "open":
        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "You are a test assistant.",
            }
        }
        import json
        client.data_channel.send(json.dumps(session_update))
        print("✓ Session update sent")
        await asyncio.sleep(1)  # Wait for session.updated event
    else:
        print(f"❌ Data channel not open (state: {client.data_channel.readyState if client.data_channel else 'None'})")
    print()

    # 3. Send simulated audio (24kHz, mono, PCM16)
    print("3. Sending 5 seconds of test audio (1kHz tone)...")
    sample_rate = 24000
    frequency = 1000  # 1kHz test tone

    for i in range(50):  # 50 chunks of 100ms = 5 seconds
        # Generate 100ms of 1kHz sine wave at 24kHz
        t = np.linspace(i * 0.1, (i + 1) * 0.1, 2400, endpoint=False)
        audio = (np.sin(2 * np.pi * frequency * t) * 10000).astype(np.int16)

        await client.send_audio(audio.tobytes())
        await asyncio.sleep(0.1)

        if i % 10 == 0 and i > 0:
            print(f"  {i * 100}ms sent...")

    print("✓ All audio sent")
    print()

    # 4. Wait for OpenAI response
    print("4. Waiting for OpenAI to process and respond...")
    await asyncio.sleep(5)

    # 5. Results
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Events received: {len(received_events)}")
    if received_events:
        print("\nEvent types:")
        for evt in received_events[:20]:  # Show first 20
            print(f"  - {evt}")
    else:
        print("  (none)")

    print(f"\nAudio chunks received: {len(received_audio)}")
    if received_audio:
        total_bytes = sum(received_audio)
        print(f"Total audio bytes: {total_bytes}")
    else:
        print("  (none)")

    # Check critical events
    has_session_created = 'session.created' in received_events
    has_session_updated = 'session.updated' in received_events
    has_audio_buffer = any('audio_buffer' in e for e in received_events)
    has_response = any('response' in e for e in received_events)

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    print(f"✓ Session created: {has_session_created}")
    print(f"✓ Session updated: {has_session_updated}")
    print(f"✓ Audio buffer events: {has_audio_buffer}")
    print(f"✓ Response events: {has_response}")
    print(f"✓ Audio received: {len(received_audio) > 0}")

    success = has_session_created and has_audio_buffer and len(received_audio) > 0
    print()
    if success:
        print("🎉 TEST PASSED - Backend → OpenAI connection works!")
    else:
        print("❌ TEST FAILED - Check what's missing above")

    print("=" * 60)

    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(test_backend_to_openai())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
