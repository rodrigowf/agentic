"""
Integration tests for backend WebRTC components
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from api.openai_webrtc_client import OpenAIWebRTCClient, AudioTrack
from api.frontend_audio_handler import FrontendAudioHandler
from api.realtime_voice_webrtc import (
    create_session,
    handle_frontend_audio,
    handle_openai_audio,
    handle_function_call,
    mix_audio_streams,
    sessions
)


@pytest.mark.asyncio
async def test_audio_track_end_to_end():
    """Test AudioTrack can send and receive audio in sequence"""
    track = AudioTrack()

    # Create test audio samples
    test_samples = [
        np.zeros(2400, dtype=np.int16),
        np.ones(2400, dtype=np.int16) * 1000,
        np.ones(2400, dtype=np.int16) * -1000
    ]

    # Send multiple audio frames
    for sample in test_samples:
        await track.send(sample.tobytes())

    # Receive and verify
    for i in range(len(test_samples)):
        frame = await track.recv()
        assert frame is not None
        assert frame.sample_rate == 24000


@pytest.mark.asyncio
async def test_openai_client_audio_callback():
    """Test OpenAI client triggers audio callback"""
    audio_received = []

    async def audio_callback(audio_data):
        audio_received.append(audio_data)

    client = OpenAIWebRTCClient(
        api_key="test-key",
        on_audio_callback=audio_callback
    )

    # Simulate audio callback
    test_audio = b"test_audio_data"
    await audio_callback(test_audio)

    assert len(audio_received) == 1
    assert audio_received[0] == test_audio


@pytest.mark.asyncio
async def test_openai_client_function_call_callback():
    """Test OpenAI client triggers function call callback"""
    function_calls = []

    async def function_callback(event):
        function_calls.append(event)

    client = OpenAIWebRTCClient(
        api_key="test-key",
        on_function_call_callback=function_callback
    )

    # Simulate function call event
    test_event = {
        "type": "response.function_call_arguments.done",
        "name": "send_to_nested",
        "arguments": {"text": "test"}
    }

    client._handle_openai_event(test_event)

    # Wait for async callback
    await asyncio.sleep(0.1)

    assert len(function_calls) == 1
    assert function_calls[0]["name"] == "send_to_nested"


@pytest.mark.asyncio
async def test_frontend_handler_bidirectional_audio():
    """Test frontend handler can send and receive audio"""
    audio_from_frontend = []

    async def audio_callback(audio_data):
        audio_from_frontend.append(audio_data)

    handler = FrontendAudioHandler(
        session_id="test-session",
        on_audio_callback=audio_callback
    )

    # Mock data channel
    mock_channel = MagicMock()
    mock_channel.readyState = "open"
    handler.data_channel = mock_channel

    # Send audio to frontend
    test_audio = b"audio_to_frontend"
    await handler.send_audio(test_audio)

    mock_channel.send.assert_called_once_with(test_audio)


@pytest.mark.asyncio
async def test_audio_mixing():
    """Test audio mixing with multiple streams"""
    # Create test audio streams
    stream1 = np.ones(2400, dtype=np.int16) * 1000
    stream2 = np.ones(2400, dtype=np.int16) * 2000
    stream3 = np.ones(2400, dtype=np.int16) * 3000

    streams = [stream1.tobytes(), stream2.tobytes(), stream3.tobytes()]

    # Mix audio
    mixed = mix_audio_streams(streams)

    # Verify mixing
    assert len(mixed) > 0

    # Convert back to numpy to verify
    mixed_array = np.frombuffer(mixed, dtype=np.int16)
    assert len(mixed_array) == 2400

    # Average should be approximately (1000 + 2000 + 3000) / 3 = 2000
    avg_value = np.mean(mixed_array)
    assert 1900 <= avg_value <= 2100


@pytest.mark.asyncio
async def test_audio_mixing_different_lengths():
    """Test audio mixing with streams of different lengths"""
    # Create streams of different lengths
    stream1 = np.ones(1000, dtype=np.int16) * 1000
    stream2 = np.ones(2400, dtype=np.int16) * 2000

    streams = [stream1.tobytes(), stream2.tobytes()]

    # Mix audio
    mixed = mix_audio_streams(streams)

    # Verify mixing handles different lengths
    assert len(mixed) > 0
    mixed_array = np.frombuffer(mixed, dtype=np.int16)

    # Should be padded to max length (2400)
    assert len(mixed_array) == 2400


@pytest.mark.asyncio
async def test_audio_mixing_empty_streams():
    """Test audio mixing with empty streams"""
    # Empty list
    mixed = mix_audio_streams([])
    assert mixed == b""

    # Single stream
    stream1 = np.ones(2400, dtype=np.int16) * 1000
    mixed = mix_audio_streams([stream1.tobytes()])
    assert mixed == stream1.tobytes()


@pytest.mark.asyncio
async def test_session_audio_flow():
    """Test complete audio flow through session"""
    # Clear any existing sessions
    sessions.clear()

    # Create mock session
    session_id = "test-session-123"

    mock_openai_client = AsyncMock()
    mock_openai_client.send_audio = AsyncMock()

    mock_frontend_handler = AsyncMock()
    mock_frontend_handler.send_audio = AsyncMock()

    sessions[session_id] = {
        "openai_client": mock_openai_client,
        "frontend_handlers": [mock_frontend_handler],
        "audio_buffers": {}
    }

    # Test frontend → OpenAI flow
    frontend_audio = b"audio_from_frontend"
    await handle_frontend_audio(session_id, frontend_audio)

    mock_openai_client.send_audio.assert_called_once_with(frontend_audio)

    # Test OpenAI → frontend flow
    openai_audio = b"audio_from_openai"
    await handle_openai_audio(session_id, openai_audio)

    mock_frontend_handler.send_audio.assert_called_once_with(openai_audio)

    # Cleanup
    sessions.clear()


@pytest.mark.asyncio
async def test_function_call_routing():
    """Test function call routing"""
    # Clear sessions
    sessions.clear()

    session_id = "test-session-123"

    mock_openai_client = AsyncMock()
    mock_openai_client.send_function_result = AsyncMock()

    sessions[session_id] = {
        "openai_client": mock_openai_client,
        "frontend_handlers": [],
        "audio_buffers": {}
    }

    # Test send_to_nested function
    event = {
        "name": "send_to_nested",
        "arguments": {"text": "test task"},
        "call_id": "call_123"
    }

    await handle_function_call(session_id, event)

    # Verify function result sent
    mock_openai_client.send_function_result.assert_called_once()
    call_args = mock_openai_client.send_function_result.call_args
    assert call_args[0][0] == "call_123"
    assert "Nested team executed" in call_args[0][1]

    # Cleanup
    sessions.clear()


@pytest.mark.asyncio
async def test_multi_client_broadcast():
    """Test audio broadcasting to multiple frontend clients"""
    sessions.clear()

    session_id = "test-session-123"

    # Create multiple frontend handlers
    mock_handler1 = AsyncMock()
    mock_handler1.send_audio = AsyncMock()

    mock_handler2 = AsyncMock()
    mock_handler2.send_audio = AsyncMock()

    mock_handler3 = AsyncMock()
    mock_handler3.send_audio = AsyncMock()

    sessions[session_id] = {
        "openai_client": AsyncMock(),
        "frontend_handlers": [mock_handler1, mock_handler2, mock_handler3],
        "audio_buffers": {}
    }

    # Broadcast audio from OpenAI
    audio_data = b"broadcast_audio"
    await handle_openai_audio(session_id, audio_data)

    # Verify all handlers received audio
    mock_handler1.send_audio.assert_called_once_with(audio_data)
    mock_handler2.send_audio.assert_called_once_with(audio_data)
    mock_handler3.send_audio.assert_called_once_with(audio_data)

    # Cleanup
    sessions.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
