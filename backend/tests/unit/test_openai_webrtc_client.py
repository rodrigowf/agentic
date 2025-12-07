"""
Unit tests for OpenAI WebRTC client
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from api.openai_webrtc_client import OpenAIWebRTCClient, AudioTrack


@pytest.mark.asyncio
async def test_audio_track_initialization():
    """Test AudioTrack initializes correctly"""
    track = AudioTrack()
    assert track.kind == "audio"
    assert track._sample_rate == 24000
    assert track._timestamp == 0
    assert track.queue.qsize() == 0


@pytest.mark.asyncio
async def test_audio_track_send_and_recv():
    """Test AudioTrack can send and receive audio data"""
    track = AudioTrack()

    # Create test audio data (PCM16, 24kHz, 0.1s = 2400 samples)
    import numpy as np
    test_audio = np.zeros(2400, dtype=np.int16)
    audio_bytes = test_audio.tobytes()

    # Send audio
    await track.send(audio_bytes)

    # Receive audio
    frame = await track.recv()

    assert frame is not None
    assert frame.sample_rate == 24000
    assert frame.samples > 0


@pytest.mark.asyncio
async def test_openai_client_initialization():
    """Test OpenAIWebRTCClient initializes with correct parameters"""
    client = OpenAIWebRTCClient(
        api_key="test-key",
        model="gpt-4o-realtime-preview-2024-12-17",
        voice="alloy"
    )

    assert client.api_key == "test-key"
    assert client.model == "gpt-4o-realtime-preview-2024-12-17"
    assert client.voice == "alloy"
    assert client.pc is None
    assert client.session_id is None


@pytest.mark.asyncio
async def test_get_ephemeral_token():
    """Test ephemeral token fetching"""
    client = OpenAIWebRTCClient(api_key="test-key")

    # Mock aiohttp response
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={
        "id": "session_123",
        "client_secret": {"value": "token_456"}
    })

    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_response

        token = await client._get_ephemeral_token()

        assert token == "token_456"
        assert client.session_id == "session_123"

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://api.openai.com/v1/realtime/sessions" in str(call_args)


@pytest.mark.asyncio
async def test_handle_openai_event_function_call():
    """Test handling function call events from OpenAI"""
    callback_called = False
    received_event = None

    async def mock_callback(event):
        nonlocal callback_called, received_event
        callback_called = True
        received_event = event

    client = OpenAIWebRTCClient(
        api_key="test-key",
        on_function_call_callback=mock_callback
    )

    # Simulate function call event
    event = {
        "type": "response.function_call_arguments.done",
        "name": "send_to_nested",
        "arguments": {"text": "test"},
        "call_id": "call_123"
    }

    client._handle_openai_event(event)

    # Wait for async callback
    await asyncio.sleep(0.1)

    assert callback_called
    assert received_event == event


@pytest.mark.asyncio
async def test_handle_openai_event_error():
    """Test handling error events from OpenAI"""
    client = OpenAIWebRTCClient(api_key="test-key")

    # Simulate error event
    error_event = {
        "type": "error",
        "error": {"message": "Test error"}
    }

    # Should log error but not crash
    with patch('api.openai_webrtc_client.logger.error') as mock_logger:
        client._handle_openai_event(error_event)
        mock_logger.assert_called_once()


@pytest.mark.asyncio
async def test_send_function_result():
    """Test sending function result back to OpenAI"""
    client = OpenAIWebRTCClient(api_key="test-key")

    # Mock data channel
    mock_channel = MagicMock()
    client.data_channel = mock_channel

    # Send function result
    await client.send_function_result("call_123", "Success")

    # Verify message sent
    mock_channel.send.assert_called_once()
    sent_message = json.loads(mock_channel.send.call_args[0][0])

    assert sent_message["type"] == "conversation.item.create"
    assert sent_message["item"]["call_id"] == "call_123"
    assert "Success" in sent_message["item"]["output"]


@pytest.mark.asyncio
async def test_send_audio():
    """Test sending audio to OpenAI"""
    client = OpenAIWebRTCClient(api_key="test-key")
    client.audio_track = AudioTrack()

    # Create test audio
    import numpy as np
    test_audio = np.zeros(2400, dtype=np.int16)
    audio_bytes = test_audio.tobytes()

    # Send audio
    await client.send_audio(audio_bytes)

    # Verify audio queued
    assert client.audio_track.queue.qsize() == 1


@pytest.mark.asyncio
async def test_close():
    """Test closing connection"""
    client = OpenAIWebRTCClient(api_key="test-key")

    # Mock peer connection
    mock_pc = AsyncMock()
    client.pc = mock_pc

    # Close
    await client.close()

    # Verify close called
    mock_pc.close.assert_called_once()


def test_import_dependencies():
    """Test that all required dependencies are available"""
    try:
        import aiortc
        import aiohttp
        import numpy
        import av
        assert True
    except ImportError as e:
        pytest.fail(f"Missing dependency: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
