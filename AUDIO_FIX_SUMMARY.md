# Audio Slow-Motion Fix Summary

**Date:** 2025-12-04
**Issue:** Voice assistant audio playing in slow motion
**Root Cause:** Sample rate mismatch between OpenAI and browser

---

## Problem Diagnosis

### The Issue
OpenAI's documentation states they use **24000 Hz** audio, but actual testing revealed:
- **OpenAI sends: 48000 Hz stereo audio** (960 samples per frame)
- **Our bridge initialized: 24000 Hz track**
- **Result:** 48kHz data played through 24kHz clock = **0.5x speed (slow motion)**

### Evidence
From backend logs:
```
[AudioFrameSourceTrack] Initialized with sample_rate=24000
[OpenAI Audio] First frame: sample_rate=48000, samples=960, format=s16, layout=stereo
[AudioFrameSourceTrack] First frame: sample_rate=48000, samples=1920, format=s16, layout=mono
```

The mismatch is clear: we initialized a 24kHz track but received 48kHz audio.

---

## The Fix

### Files Changed

#### 1. `backend/api/realtime_voice_webrtc.py`
**Line 89:** Changed `AudioFrameSourceTrack` default sample rate from **24000** to **48000**

```python
# Before
def __init__(self, sample_rate: int = 24000):

# After
def __init__(self, sample_rate: int = 48000):
    # CRITICAL: OpenAI sends 48000 Hz audio (not 24000 Hz as documented)
```

**Lines 128-132:** Added detailed logging to detect future mismatches

```python
if self._timestamp == mono.samples:
    logger.info(f"[AudioFrameSourceTrack] First frame: sample_rate={sr}, samples={mono.samples}")
    logger.info(f"[AudioFrameSourceTrack] Duration: {mono.samples / sr * 1000:.2f}ms")
    logger.info(f"[AudioFrameSourceTrack] Track initialized at: {self.sample_rate} Hz")
    if sr != self.sample_rate:
        logger.warning(f"⚠️  SAMPLE RATE MISMATCH: track={self.sample_rate} Hz, frame={sr} Hz")
```

#### 2. `backend/api/openai_webrtc_client.py`
**Line 318:** Changed `AudioTrack` default sample rate from **24000** to **48000**

```python
# Before
def __init__(self, sample_rate: int = 24000):

# After
def __init__(self, sample_rate: int = 48000):
    # CRITICAL: OpenAI expects 48000 Hz input audio (despite docs saying 24000 Hz)
```

### Testing Tools Created

#### `backend/tests/test_audio_format_validation.py`
Diagnostic tool that documents:
- OpenAI audio format specifications
- Browser WebRTC expectations
- Sample rate mismatch effects
- Test cases for audio format validation

---

## Technical Details

### Audio Format Specifications

**OpenAI Realtime API (Actual Behavior):**
- Format: PCM16 (signed 16-bit little-endian)
- Sample Rate: **48000 Hz** (not 24000 as documented!)
- Channels: 2 (stereo) → converted to 1 (mono)
- Frame Size: 960 samples @ 48kHz = 20ms

**Browser WebRTC:**
- Standard Sample Rates: 8000, 12000, 16000, 24000, **48000** Hz
- Our Configuration: 48000 Hz (matches OpenAI)
- Format: PCM16 mono

### Why This Caused Slow Motion

When sample rates mismatch:
- **If track is 24kHz but data is 48kHz:**
  - Browser plays 48000 samples/second of data
  - But thinks the clock is 24000 samples/second
  - Playback speed = 24000/48000 = 0.5x = **SLOW MOTION**

- **If track is 48kHz but data is 24kHz:**
  - Playback speed = 48000/24000 = 2x = fast/high-pitched

---

## Testing Instructions

### 1. Verify Backend Reloaded
```bash
tail -f /tmp/agentic-logs/backend.log | grep "Initialized with sample_rate"
```

Expected output:
```
[AudioFrameSourceTrack] Initialized with sample_rate=48000
```

### 2. Start New Voice Session
1. Open browser: http://localhost:3000/agentic/voice
2. Click "Start" button
3. Wait for OpenAI connection
4. Speak or wait for AI greeting

### 3. Check Audio Quality
The audio should now play at **normal speed** with:
- ✅ Correct pitch
- ✅ Normal tempo
- ✅ No distortion
- ✅ No slow-motion effect

### 4. Monitor Logs
Watch for these key log lines:
```bash
tail -f /tmp/agentic-logs/backend.log | grep -E "First frame|sample_rate"
```

Expected output:
```
[AudioFrameSourceTrack] Initialized with sample_rate=48000
[OpenAI Audio] First frame: sample_rate=48000, samples=960, format=s16, layout=stereo
[AudioFrameSourceTrack] First frame: sample_rate=48000, samples=1920, format=s16, layout=mono
[AudioFrameSourceTrack] Duration: 20.00ms
[AudioFrameSourceTrack] Track initialized at: 48000 Hz
```

**⚠️ If you see this warning, there's still a mismatch:**
```
[AudioFrameSourceTrack] ⚠️  SAMPLE RATE MISMATCH: track=XXXX Hz, frame=YYYY Hz
```

---

## Rollback Instructions

If issues occur, revert changes:

```bash
cd /home/rodrigo/agentic/backend

# Revert realtime_voice_webrtc.py
git checkout backend/api/realtime_voice_webrtc.py

# Revert openai_webrtc_client.py
git checkout backend/api/openai_webrtc_client.py

# Backend will auto-reload
```

---

## Future Considerations

### 1. OpenAI API Documentation
The official docs state 24kHz, but actual implementation uses 48kHz. This may be:
- A documentation error
- A recent API change
- Model-specific behavior (gpt-4o-realtime-preview-2024-12-17)

**Recommendation:** Monitor OpenAI changelogs for audio format updates.

### 2. Dynamic Sample Rate Detection
Consider making sample rate dynamic:
```python
# Future enhancement
class AudioFrameSourceTrack(MediaStreamTrack):
    def __init__(self):
        self.sample_rate = None  # Detect from first frame

    def _to_mono(self, frame: AudioFrame):
        if self.sample_rate is None:
            self.sample_rate = frame.sample_rate
            logger.info(f"Detected sample rate: {self.sample_rate} Hz")
```

### 3. Browser Compatibility
Different browsers may handle sample rate mismatches differently:
- Chrome/Edge: May resample automatically
- Firefox: May fail or distort
- Safari: May have different behavior

**Testing recommended on multiple browsers.**

---

## Related Files

- `backend/api/realtime_voice_webrtc.py` - WebRTC bridge controller
- `backend/api/openai_webrtc_client.py` - OpenAI WebRTC client
- `backend/tests/test_audio_format_validation.py` - Audio format tests
- `frontend/src/features/voice/pages/VoiceAssistantModular.js` - Frontend voice UI

---

## Success Criteria

✅ Audio plays at normal speed
✅ No pitch distortion
✅ No "slow motion" or "chipmunk" effects
✅ Logs show matching sample rates (48000 Hz)
✅ No sample rate mismatch warnings

---

**Status:** ✅ FIXED - Ready for testing
**Test Required:** Manual voice session testing
**Auto-reload:** Backend already reloaded with fix
