# Audio Fixes Log

**Purpose:** Historical record of audio quality issues and their resolutions
**System:** WebRTC Voice Bridge (Browser ↔ Backend ↔ OpenAI)
**Period:** November 2024 - December 2024

---

## Table of Contents

1. [Fix #1: Slow Motion Audio (Sample Rate Mismatch)](#fix-1-slow-motion-audio-sample-rate-mismatch)
2. [Fix #2: Stereo-to-Mono Conversion Error](#fix-2-stereo-to-mono-conversion-error)
3. [Fix #3: Browser Audio Not Reaching Backend](#fix-3-browser-audio-not-reaching-backend)
4. [Fix #4: Input Audio Transcription Missing](#fix-4-input-audio-transcription-missing)
5. [Fix #5: VAD Configuration Improvements](#fix-5-vad-configuration-improvements)
6. [Fix #6: Language Detection Issues](#fix-6-language-detection-issues)
7. [Fix #7: Turn Detection Modes](#fix-7-turn-detection-modes)
8. [Fix #8: Manual Mode Implementation](#fix-8-manual-mode-implementation)
9. [Fix #9: VAD Cutoff Sensitivity](#fix-9-vad-cutoff-sensitivity)

---

## Fix #1: Slow Motion Audio (Sample Rate Mismatch)

**Date:** 2025-12-04
**Severity:** High
**Status:** ✅ Fixed

### Problem
Voice assistant audio playing at 0.5x speed (slow motion).

### Root Cause
**Sample rate mismatch:**
- OpenAI documentation claims: 24000 Hz
- OpenAI actually sends: **48000 Hz** stereo audio
- Our bridge initialized: 24000 Hz track
- Result: 48kHz data played through 24kHz clock = 0.5x speed

### Evidence
Backend logs showed:
```
[AudioFrameSourceTrack] Initialized with sample_rate=24000
[OpenAI Audio] First frame: sample_rate=48000, samples=960
```

### Solution
**File:** `backend/api/realtime_voice_webrtc.py` (Line 89)

```python
# Before
def __init__(self, sample_rate: int = 24000):

# After
def __init__(self, sample_rate: int = 48000):
    # CRITICAL: OpenAI sends 48000 Hz audio (not 24000 Hz as documented)
```

### Verification
- Audio now plays at normal speed
- 20ms frames contain 960 samples @ 48kHz (correct)

---

## Fix #2: Stereo-to-Mono Conversion Error

**Date:** 2025-12-04
**Severity:** Critical
**Status:** ✅ Fixed

### Problem
Even after Fix #1, audio still played in slow motion.

### Root Cause
**Sample count doubling during stereo-to-mono conversion:**
- OpenAI sends: 960 samples stereo (2 channels × 960 = 1920 total values)
- Our naive conversion: Averaged channels but kept array shape
- Result: 1920 samples mono instead of 960
- Browser Opus expected: 960 samples for 20ms @ 48kHz
- Actual duration: 40ms → played at 0.5x speed

### Solution
**File:** `backend/api/realtime_voice_webrtc.py` (Lines 98-137)

```python
# Before (WRONG)
if array.shape[0] > 1:
    array = np.mean(array, axis=0, dtype=np.int16, keepdims=True)
    # Kept shape as (2, 960) instead of (1, 960)!

# After (CORRECT) - Use AudioResampler
from av import AudioResampler
resampler = AudioResampler(format="s16", layout="mono")
mono_frames = resampler.resample(frame)
mono = next(iter(mono_frames))
# Properly converts (2, 960) → (1, 960)
```

### Verification
- First frame after conversion: 960 samples
- Duration: 20ms @ 48kHz (correct)
- Audio plays at normal speed

---

## Fix #3: Browser Audio Not Reaching Backend

**Date:** 2025-12-04
**Severity:** High
**Status:** ✅ Fixed

### Problem
User could hear assistant, but assistant couldn't hear user.

### Root Cause
**`ontrack` event not firing:**
- Browser sent audio track in SDP offer
- Backend's `ontrack` handler never triggered
- Audio track existed but wasn't being forwarded

### Solution
**File:** `backend/api/realtime_voice_webrtc.py` (Lines 199-210)

```python
# After setRemoteDescription, check transceivers manually
await self.browser_pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))

# Check if we already have remote tracks (ontrack might not fire)
logger.info("[WebRTC Bridge] Checking for existing remote tracks...")
for transceiver in self.browser_pc.getTransceivers():
    if transceiver.receiver and transceiver.receiver.track:
        track = transceiver.receiver.track
        if track.kind == "audio" and not self.browser_audio_task:
            logger.info("[WebRTC Bridge] Starting audio forwarding for existing track...")
            self.browser_audio_task = asyncio.create_task(self._forward_browser_audio(track))
```

### Verification
- Browser audio frames now reach backend
- Logs show: `[Browser Audio] Forwarded {N} frames to OpenAI`
- Assistant responds to user speech

---

## Fix #4: Input Audio Transcription Missing

**Date:** 2025-12-04
**Severity:** Medium
**Status:** ✅ Fixed

### Problem
- User audio reached OpenAI (confirmed by logs)
- Assistant responded to speech
- BUT: No user transcripts saved in conversation store
- Model responses sometimes out of context

### Root Cause
Missing `input_audio_transcription` configuration in OpenAI session setup.

Without this:
- OpenAI processes audio for VAD and responses
- BUT does not generate transcripts of user speech
- No `conversation.item.input_audio_transcription.completed` events

### Evidence
Export showed:
- **0 user transcripts** (should have multiple)
- **1+ assistant transcripts** (working correctly)

### Solution
**File:** `backend/api/openai_webrtc_client.py` (Lines 134-143)

```python
# Added to session configuration
"input_audio_transcription": {
    "model": "whisper-1"
}
```

### Verification
- User transcripts now appear in conversation exports
- Model has full context of user speech
- Responses more accurate and contextual

---

## Fix #5: VAD Configuration Improvements

**Date:** 2025-12-04
**Severity:** Low
**Status:** ✅ Fixed

### Problem
- Voice activity detection cutting off too early
- User had to speak very clearly to be detected
- Awkward pauses mid-sentence

### Solution
**File:** `backend/api/openai_webrtc_client.py` (Lines 144-150)

```python
# Improved VAD settings
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,              # Sensitivity (0.0-1.0)
    "prefix_padding_ms": 300,      # Include 300ms before speech
    "silence_duration_ms": 500     # Wait 500ms of silence before cutoff
}
```

### Configuration Options
- **threshold:** Lower = more sensitive (default: 0.5)
- **prefix_padding_ms:** Audio to include before detected speech (default: 300ms)
- **silence_duration_ms:** Silence duration before ending turn (default: 500ms)

### Verification
- More natural conversation flow
- Less premature cutoffs
- Better handling of pauses

---

## Fix #6: Language Detection Issues

**Date:** 2025-12-04
**Severity:** Low
**Status:** ✅ Fixed

### Problem
Assistant occasionally responded in wrong language or mixed languages.

### Solution
**File:** `backend/api/openai_webrtc_client.py`

Added explicit language instruction to system prompt:
```python
system_prompt = f"{base_prompt}\n\nIMPORTANT: Always respond in the same language as the user's input."
```

### Verification
- Consistent language matching
- No unexpected language switches

---

## Fix #7: Turn Detection Modes

**Date:** 2025-12-04
**Severity:** Low
**Status:** ✅ Implemented

### Feature
Support for different turn detection modes.

### Modes Available

#### 1. Server VAD (Default)
```python
"turn_detection": {"type": "server_vad"}
```
- Automatic voice activity detection by OpenAI
- Hands-free operation
- Best for natural conversation

#### 2. Manual Mode
```python
"turn_detection": None  # or explicitly set to null
```
- User controls when to send audio
- Requires explicit "Done Speaking" button press
- Calls `commit_audio_buffer()` endpoint
- Best for noisy environments or precise control

### Endpoint Added
```python
POST /api/realtime/webrtc/bridge/{conversation_id}/commit
```
Manually commits audio buffer and triggers model response.

---

## Fix #8: Manual Mode Implementation

**Date:** 2025-12-04
**Severity:** Low
**Status:** ✅ Implemented

### Feature
Push-to-talk style interaction for precise control.

### Implementation
**Backend:** Added `commit_audio_buffer()` method to OpenAI client

**Frontend:** Would require "Done Speaking" button (not yet implemented in UI)

### Use Cases
- Noisy environments
- Precise control over turn-taking
- Recording-style interactions

---

## Fix #9: VAD Cutoff Sensitivity

**Date:** 2025-12-04
**Severity:** Low
**Status:** ✅ Tuned

### Problem
Default VAD settings too aggressive, cutting off mid-sentence.

### Solution
Tuned VAD parameters for more natural conversation:

```python
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,              # Balanced sensitivity
    "prefix_padding_ms": 300,      # Capture lead-in
    "silence_duration_ms": 500     # Tolerate natural pauses
}
```

### Recommendations by Environment

**Quiet room:**
```python
threshold: 0.6              # Less sensitive (fewer false positives)
silence_duration_ms: 400    # Shorter wait
```

**Noisy environment:**
```python
threshold: 0.4              # More sensitive
silence_duration_ms: 700    # Longer wait for pauses
```

**Long-form speech:**
```python
silence_duration_ms: 1000   # Tolerate longer pauses
prefix_padding_ms: 500      # More context
```

---

## Additional Improvements

### Input Gain Boost
**Environment Variable:** `VOICE_INPUT_GAIN=4.0`

Applies gain to microphone input before sending to OpenAI.

**Use case:** Low microphone levels, quiet speakers

**Configuration:**
```python
# backend/api/openai_webrtc_client.py
self.input_gain = float(os.getenv("VOICE_INPUT_GAIN", "4.0"))

# Applied during audio forwarding
array = (array * self.input_gain).clip(-32768, 32767).astype(np.int16)
```

### Debug Audio Recording
**Environment Variable:** `VOICE_DEBUG_RECORD=1`

Records raw microphone input to WAV file for debugging.

**Output:** `/tmp/agentic-logs/mic_{conversation_id}_{session_id}.wav`

---

## Testing Checklist

After any audio fix, verify:

- [ ] Audio plays at normal speed (not slow/fast)
- [ ] User speech reaches backend (check logs)
- [ ] User transcripts appear in conversation exports
- [ ] Assistant transcripts appear in conversation exports
- [ ] VAD detects speech start/stop appropriately
- [ ] No echo or feedback
- [ ] Latency < 500ms (network dependent)
- [ ] Sample rate consistent (48kHz throughout)

---

## Common Diagnostic Commands

```bash
# Export conversations to check transcripts
python3 debug/export_voice_conversations.py

# Check user transcripts
cat debug/db_exports/voice_conversations/*.json | jq '.events[] | select(.type == "conversation.item.input_audio_transcription.completed")'

# Check assistant transcripts
cat debug/db_exports/voice_conversations/*.json | jq '.events[] | select(.type == "response.audio_transcript.delta")'

# Monitor backend audio logs
tail -f /tmp/agentic-logs/backend.log | grep -E "Audio|audio_frame|VAD"

# Check sample rates
grep "sample_rate" /tmp/agentic-logs/backend.log
```

---

## Lessons Learned

1. **Never trust documentation** - Always verify actual sample rates
2. **Log everything** - Detailed logging caught all these issues
3. **Test with exports** - Conversation exports revealed missing transcripts
4. **Stereo ≠ Mono** - Sample count changes during channel conversion
5. **WebRTC events can be unreliable** - Check transceivers manually
6. **VAD needs tuning** - One size doesn't fit all environments

---

## Related Documentation

- **[Voice System Overview](../VOICE_SYSTEM_OVERVIEW.md)** - Architecture
- **[Voice Troubleshooting](../VOICE_TROUBLESHOOTING.md)** - Debug guide
- **[Backend Implementation](BACKEND_IMPLEMENTATION.md)** - Technical details

---

**Last Updated:** 2025-12-05
**Maintained by:** Agentic System Development Team
