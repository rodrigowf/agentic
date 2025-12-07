"""
Lightweight integration checks for the WebRTC bridge primitives.
These tests avoid external network calls and validate the local media helpers.
"""

import asyncio
from fractions import Fraction
from typing import List

import numpy as np
import pytest
from av import AudioFrame

from api.openai_webrtc_client import AudioTrack, OpenAIWebRTCClient
from api.realtime_voice_webrtc import AudioFrameSourceTrack


@pytest.mark.asyncio
async def test_audio_track_roundtrip():
    track = AudioTrack()

    samples = np.ones(480, dtype=np.int16) * 500
    await track.send(samples.tobytes())

    frame = await track.recv()
    assert isinstance(frame, AudioFrame)
    assert frame.sample_rate == 24000
    assert frame.time_base == Fraction(1, 24000)
    assert frame.samples == samples.shape[0]


@pytest.mark.asyncio
async def test_audio_track_accepts_frame():
    track = AudioTrack()
    original = AudioFrame.from_ndarray(np.ones((1, 160), dtype=np.int16), format="s16", layout="mono")
    original.sample_rate = 16000

    await track.send(original)
    frame = await track.recv()
    assert frame.sample_rate == 16000
    assert frame.time_base == Fraction(1, 16000)


@pytest.mark.asyncio
async def test_audio_source_track_normalizes_to_mono():
    source = AudioFrameSourceTrack()
    stereo = AudioFrame.from_ndarray(
        np.stack(
            [np.ones(160, dtype=np.int16), np.ones(160, dtype=np.int16) * 2]
        ),
        format="s16p",
        layout="stereo",
    )
    stereo.sample_rate = 48000

    await source.send_frame(stereo)
    frame = await source.recv()
    assert frame.sample_rate == 48000
    assert frame.time_base == Fraction(1, 48000)
    assert frame.to_ndarray().shape[0] == 1  # mono


@pytest.mark.asyncio
async def test_event_callback_invoked():
    events: List[dict] = []

    def on_event(evt):
        events.append(evt)

    client = OpenAIWebRTCClient(api_key="test-key", on_event_callback=on_event)
    client._handle_openai_event({"type": "response.audio_transcript.delta", "delta": "hello"})

    await asyncio.sleep(0.05)
    assert events
    assert events[0]["type"] == "response.audio_transcript.delta"
