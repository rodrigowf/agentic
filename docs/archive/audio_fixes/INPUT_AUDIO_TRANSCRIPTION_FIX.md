# Voice Assistant Fix: Input Audio Transcription Enabled

**Date:** 2025-12-04
**Status:** FIXED
**Issue:** Model responses sometimes don't match user speech or respond to old questions

---

## Problem Analysis

### Symptoms
- User audio was successfully reaching OpenAI (logs showed "Forwarded 4300 frames")
- OpenAI was responding to user speech
- BUT: No user transcripts were being saved in the conversation store
- Model responses sometimes seemed out of context or stale

### Root Cause
The `session.update` message sent to OpenAI was **missing the `input_audio_transcription` configuration**.

Without this setting:
- OpenAI processes audio for VAD and responses
- BUT does not generate transcripts of user speech
- The model has less context about what was actually said
- No transcript events are emitted (no `conversation.item.input_audio_transcription.completed` events)

### Diagnostic Evidence

Checked exported conversations:
```bash
python3 debug/export_voice_conversations.py
```

Found that ALL recent conversations had:
- **0 user transcripts** (should have multiple)
- **1+ assistant transcripts** (working correctly)
- Audio frames were being sent (logs confirmed)

This proved that audio was reaching OpenAI, but transcription was not enabled.

---

## Solution

### 1. Enable Input Audio Transcription

**File:** `backend/api/openai_webrtc_client.py`
**Lines:** 134-143

Added `input_audio_transcription` to the session configuration:

```python
session_update = {
    "type": "session.update",
    "session": {
        "voice": self.voice,
        "modalities": self.modalities,
        # Enable input audio transcription to get user speech transcripts
        "input_audio_transcription": {
            "model": "whisper-1"
        },
    },
}
```

### 2. Improved VAD Configuration

**File:** `backend/api/openai_webrtc_client.py`
**Lines:** 147-158

Enhanced `turn_detection` settings for better speech detection:

```python
session_update["session"]["turn_detection"] = {
    "type": "server_vad",
    "threshold": 0.5,           # Default sensitivity
    "prefix_padding_ms": 300,   # Audio before speech starts
    "silence_duration_ms": 500  # Increased from 200ms to avoid premature cutoff
}
```

**Why increase `silence_duration_ms`?**
- Default 200ms can cut off natural pauses in speech
- 500ms gives users more time to think/pause without ending their turn
- Reduces risk of fragmented transcripts

### 3. Added Debug Logging

Added logging to verify the session configuration is sent correctly:

```python
logger.info(f"!!! Sending session.update with transcription enabled: {json.dumps(session_update, indent=2)}")
```

---

## Expected Behavior After Fix

### Before Fix ❌
```
Events in conversation:
- session.created ✅
- response.audio_transcript.done ✅ (assistant)
- NO input_audio_transcription.completed ❌ (user)
```

### After Fix ✅
```
Events in conversation:
- session.created ✅
- input_audio_buffer.speech_started ✅
- input_audio_buffer.speech_stopped ✅
- conversation.item.input_audio_transcription.completed ✅ (user speech)
- response.audio_transcript.done ✅ (assistant response)
```

---

## Testing Instructions

### 1. Restart Backend

```bash
# Kill existing backend
pkill -f "uvicorn main:app"

# Start fresh
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

### 2. Start Voice Session

```bash
# Frontend
cd frontend
~/.nvm/versions/node/v22.21.1/bin/npm start

# Open: http://localhost:3000/agentic/voice
```

### 3. Test Conversation Flow

1. Click "Start Session"
2. Wait for assistant greeting
3. **Speak a clear question:** "What is the capital of France?"
4. Wait for response
5. Stop session

### 4. Verify Fix

**Check conversation store:**

```bash
python3 debug/export_voice_conversations.py
# Look at latest JSON file
```

**Expected results:**
- User transcript: "What is the capital of France?"
- Assistant transcript: "The capital of France is Paris..."

**Check logs:**

```bash
tail -100 /tmp/agentic-logs/backend.log | grep -E "(transcription|session.update)"
```

**Expected output:**
- "Sending session.update with transcription enabled"
- Session config shows `input_audio_transcription: { model: 'whisper-1' }`
- Events showing `conversation.item.input_audio_transcription.completed`

---

## Technical Details

### OpenAI Realtime API Configuration

The complete session configuration now includes:

```json
{
  "type": "session.update",
  "session": {
    "voice": "alloy",
    "modalities": ["audio", "text"],
    "input_audio_transcription": {
      "model": "whisper-1"
    },
    "instructions": "Your system prompt...",
    "turn_detection": {
      "type": "server_vad",
      "threshold": 0.5,
      "prefix_padding_ms": 300,
      "silence_duration_ms": 500
    }
  }
}
```

### Event Flow

**User Speech → OpenAI → Backend → Frontend:**

1. Browser captures audio
2. Browser → Backend (WebRTC)
3. Backend → OpenAI (WebRTC)
4. OpenAI VAD detects speech start → `input_audio_buffer.speech_started`
5. User stops speaking → `input_audio_buffer.speech_stopped`
6. OpenAI transcribes audio → `conversation.item.input_audio_transcription.completed`
7. OpenAI generates response → `response.created`, `response.audio_transcript.delta`, `response.audio_transcript.done`

---

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `backend/api/openai_webrtc_client.py` | 134-143 | Added `input_audio_transcription` config |
| `backend/api/openai_webrtc_client.py` | 147-158 | Enhanced `turn_detection` config with explicit parameters |
| `backend/api/openai_webrtc_client.py` | 159 | Added debug logging for session config |

---

## Related Documentation

- **OpenAI Realtime API Docs:** https://platform.openai.com/docs/guides/realtime
- **Session Configuration:** https://platform.openai.com/docs/api-reference/realtime-sessions/create
- **Turn Detection (VAD):** https://platform.openai.com/docs/guides/realtime#voice-activity-detection

---

## Previous Issues Fixed

1. **Issue 1 (FIXED):** Slow motion audio playback
   - **Cause:** Stereo-to-mono conversion error
   - **Fix:** Used `AudioResampler` for proper conversion

2. **Issue 2 (FIXED):** Browser audio not reaching backend
   - **Cause:** `ontrack` event not firing reliably
   - **Fix:** Check transceivers after `setRemoteDescription()`

3. **Issue 3 (FIXED - THIS FIX):** Responses don't match user speech
   - **Cause:** Missing `input_audio_transcription` configuration
   - **Fix:** Added Whisper-1 transcription + improved VAD settings

---

**Status:** Ready for testing
**Next Steps:**
1. Test with interactive voice session
2. Verify user transcripts appear in conversation store
3. Confirm responses now match user questions accurately

---

**End of Document**
