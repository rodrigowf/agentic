"""
Test audio format validation for WebRTC bridge
Diagnoses slow-motion audio issues
"""

import pytest
import numpy as np
from av import AudioFrame
from fractions import Fraction


def test_audio_frame_sample_rate_preservation():
    """Test that sample rates are preserved correctly"""

    # Simulate OpenAI audio frame at 24000 Hz
    openai_sample_rate = 24000
    duration_ms = 20  # 20ms frame
    num_samples = int(openai_sample_rate * duration_ms / 1000)

    # Create test audio data
    audio_data = np.random.randint(-32768, 32767, size=(1, num_samples), dtype=np.int16)

    # Create frame with OpenAI's format
    frame = AudioFrame.from_ndarray(audio_data, format="s16", layout="mono")
    frame.sample_rate = openai_sample_rate
    frame.time_base = Fraction(1, openai_sample_rate)
    frame.pts = 0

    print(f"\n[Test] Created frame:")
    print(f"  - sample_rate: {frame.sample_rate}")
    print(f"  - samples: {frame.samples}")
    print(f"  - time_base: {frame.time_base}")
    print(f"  - format: {frame.format}")
    print(f"  - layout: {frame.layout}")
    print(f"  - pts: {frame.pts}")
    print(f"  - duration (ms): {frame.samples / frame.sample_rate * 1000:.2f}")

    # This is what should happen
    assert frame.sample_rate == 24000, "Sample rate should be 24000 Hz"
    assert frame.samples == num_samples, "Sample count should match"
    assert frame.time_base == Fraction(1, 24000), "Time base should match sample rate"


def test_audio_frame_resampling_issue():
    """Demonstrate the slow-motion issue if sample rate is mismatched"""

    # Original audio: 24000 Hz
    original_sr = 24000
    # If we tell the browser it's 48000 Hz but send 24000 Hz data
    # The browser will play it at 48000 Hz speed, making it sound fast
    # If we tell it 12000 Hz with 24000 Hz data, it will sound slow

    duration_s = 1.0
    original_samples = int(original_sr * duration_s)

    audio_data = np.random.randint(-32768, 32767, size=(1, original_samples), dtype=np.int16)

    frame = AudioFrame.from_ndarray(audio_data, format="s16", layout="mono")
    frame.sample_rate = original_sr
    frame.time_base = Fraction(1, original_sr)

    print(f"\n[Test] Original frame: {original_samples} samples at {original_sr} Hz = {duration_s}s")

    # Scenario 1: Correct
    correct_duration = frame.samples / frame.sample_rate
    print(f"[Test] Correct playback: {correct_duration}s")

    # Scenario 2: Browser thinks it's 48000 Hz (sounds fast/high-pitched)
    wrong_sr_high = 48000
    wrong_duration_high = frame.samples / wrong_sr_high
    print(f"[Test] If browser expects {wrong_sr_high} Hz: {wrong_duration_high}s (sounds fast)")

    # Scenario 3: Browser thinks it's 12000 Hz (sounds slow/low-pitched)
    wrong_sr_low = 12000
    wrong_duration_low = frame.samples / wrong_sr_low
    print(f"[Test] If browser expects {wrong_sr_low} Hz: {wrong_duration_low}s (sounds SLOW)")

    assert correct_duration == duration_s


def test_openai_audio_format_specs():
    """Document OpenAI Realtime API audio specifications"""

    print("\n[OpenAI Realtime API Audio Specs]")
    print("Input Audio:")
    print("  - Format: PCM16 (signed 16-bit little-endian)")
    print("  - Sample Rate: 24000 Hz")
    print("  - Channels: 1 (mono)")
    print("  - Chunk Size: Recommended 20ms frames (480 samples)")
    print("\nOutput Audio:")
    print("  - Format: PCM16 (signed 16-bit little-endian)")
    print("  - Sample Rate: 24000 Hz")
    print("  - Channels: 1 (mono)")
    print("  - Delivery: Real-time via WebRTC audio track")
    print("\nCommon Issues:")
    print("  - Sample rate mismatch → pitch/speed changes")
    print("  - Time base mismatch → audio drift")
    print("  - Timestamp errors → audio jitter/gaps")


def test_browser_webrtc_audio_expectations():
    """Document browser WebRTC audio expectations"""

    print("\n[Browser WebRTC Audio Expectations]")
    print("Standard Opus Codec:")
    print("  - Sample Rates: 8000, 12000, 16000, 24000, 48000 Hz")
    print("  - Channels: 1-2")
    print("  - Frame Duration: 2.5, 5, 10, 20, 40, 60 ms")
    print("\nPCM16 Raw Audio:")
    print("  - Sample Rate: Usually 48000 Hz (browser default)")
    print("  - Channels: 1-2")
    print("  - Format: Signed 16-bit little-endian")
    print("\nKEY ISSUE:")
    print("  - OpenAI sends 24000 Hz PCM16")
    print("  - Browser may expect 48000 Hz")
    print("  - If we send 24000 Hz data with 48000 Hz clock:")
    print("    → Audio plays 2x speed (chipmunk voice)")
    print("  - If we send 24000 Hz data with 12000 Hz clock:")
    print("    → Audio plays 0.5x speed (SLOW MOTION)")


if __name__ == "__main__":
    print("=" * 60)
    print("AUDIO FORMAT VALIDATION TESTS")
    print("=" * 60)

    test_audio_frame_sample_rate_preservation()
    test_audio_frame_resampling_issue()
    test_openai_audio_format_specs()
    test_browser_webrtc_audio_expectations()

    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)
