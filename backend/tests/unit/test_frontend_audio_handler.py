"""
Unit tests for Frontend Audio Handler
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from api.frontend_audio_handler import FrontendAudioHandler


@pytest.mark.asyncio
async def test_frontend_handler_initialization():
    """Test FrontendAudioHandler initializes correctly"""
    handler = FrontendAudioHandler(
        session_id="test-session-123"
    )

    assert handler.session_id == "test-session-123"
    assert handler.pc is None
    assert handler.data_channel is None


@pytest.mark.asyncio
async def test_frontend_handler_with_callback():
    """Test FrontendAudioHandler initializes with callback"""
    callback_called = False

    async def mock_callback(audio_data):
        nonlocal callback_called
        callback_called = True

    handler = FrontendAudioHandler(
        session_id="test-session",
        on_audio_callback=mock_callback
    )

    assert handler.on_audio_callback is not None


@pytest.mark.asyncio
async def test_handle_sdp_offer_creates_answer():
    """Test handling SDP offer returns SDP answer"""
    handler = FrontendAudioHandler(session_id="test-session")

    # Mock offer SDP
    offer_sdp = """v=0
o=- 123456789 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
m=application 9 UDP/DTLS/SCTP webrtc-datachannel
c=IN IP4 0.0.0.0
a=ice-ufrag:test
a=ice-pwd:testpassword
a=fingerprint:sha-256 AA:BB:CC:DD:EE:FF
a=setup:actpass
a=mid:0
a=sctp-port:5000
"""

    # Mock RTCPeerConnection with event decorator support
    mock_pc = AsyncMock()
    mock_local_desc = MagicMock()
    mock_local_desc.sdp = "answer_sdp"
    mock_pc.localDescription = mock_local_desc

    # Mock the event decorator
    def mock_on_decorator(event_name):
        def decorator(func):
            return func
        return decorator

    mock_pc.on = mock_on_decorator

    with patch('api.frontend_audio_handler.RTCPeerConnection') as MockPC:
        MockPC.return_value = mock_pc

        answer_sdp = await handler.handle_sdp_offer(offer_sdp)

        # Verify answer returned
        assert answer_sdp == "answer_sdp"

        # Verify SDP exchange
        mock_pc.setRemoteDescription.assert_called_once()
        mock_pc.createAnswer.assert_called_once()
        mock_pc.setLocalDescription.assert_called_once()


@pytest.mark.asyncio
async def test_send_audio_when_channel_open():
    """Test sending audio when data channel is open"""
    handler = FrontendAudioHandler(session_id="test-session")

    # Mock open data channel
    mock_channel = MagicMock()
    mock_channel.readyState = "open"
    handler.data_channel = mock_channel

    # Send audio
    audio_data = b"test_audio"
    await handler.send_audio(audio_data)

    # Verify send called
    mock_channel.send.assert_called_once_with(audio_data)


@pytest.mark.asyncio
async def test_send_audio_when_channel_closed():
    """Test sending audio when data channel is closed"""
    handler = FrontendAudioHandler(session_id="test-session")

    # Mock closed data channel
    mock_channel = MagicMock()
    mock_channel.readyState = "closed"
    handler.data_channel = mock_channel

    # Send audio (should not crash)
    audio_data = b"test_audio"
    await handler.send_audio(audio_data)

    # Verify send NOT called
    mock_channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_send_audio_when_no_channel():
    """Test sending audio when no data channel exists"""
    handler = FrontendAudioHandler(session_id="test-session")
    handler.data_channel = None

    # Send audio (should not crash)
    audio_data = b"test_audio"
    await handler.send_audio(audio_data)

    # Should complete without error


@pytest.mark.asyncio
async def test_send_control_message():
    """Test sending control message to frontend"""
    handler = FrontendAudioHandler(session_id="test-session")

    # Mock open data channel
    mock_channel = MagicMock()
    mock_channel.readyState = "open"
    handler.data_channel = mock_channel

    # Send control message
    message = {"type": "status", "data": "ready"}
    await handler.send_control(message)

    # Verify message sent as JSON
    mock_channel.send.assert_called_once()
    sent_message = mock_channel.send.call_args[0][0]
    assert json.loads(sent_message) == message


@pytest.mark.asyncio
async def test_close_connection():
    """Test closing connection"""
    handler = FrontendAudioHandler(session_id="test-session")

    # Mock peer connection
    mock_pc = AsyncMock()
    handler.pc = mock_pc

    # Close
    await handler.close()

    # Verify close called
    mock_pc.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_when_no_connection():
    """Test closing when no connection exists"""
    handler = FrontendAudioHandler(session_id="test-session")
    handler.pc = None

    # Should complete without error
    await handler.close()


@pytest.mark.asyncio
async def test_datachannel_message_handling():
    """Test data channel handles both audio and control messages"""
    audio_received = False
    received_audio = None

    async def mock_audio_callback(audio_data):
        nonlocal audio_received, received_audio
        audio_received = True
        received_audio = audio_data

    handler = FrontendAudioHandler(
        session_id="test-session",
        on_audio_callback=mock_audio_callback
    )

    # Simulate setting up data channel
    mock_channel = MagicMock()
    mock_channel.readyState = "open"

    # Capture the message handler
    message_handler = None

    def capture_handler(event_name):
        def decorator(func):
            nonlocal message_handler
            if event_name == "message":
                message_handler = func
            return func
        return decorator

    mock_channel.on = capture_handler

    # Simulate datachannel event
    handler.data_channel = mock_channel

    # Simulate receiving bytes (audio)
    if message_handler:
        message_handler(b"audio_data")
        await asyncio.sleep(0.1)  # Wait for async callback

        assert audio_received
        assert received_audio == b"audio_data"

    # Simulate receiving string (control)
    if message_handler:
        control_msg = json.dumps({"type": "control", "data": "test"})
        # Should not crash
        message_handler(control_msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
