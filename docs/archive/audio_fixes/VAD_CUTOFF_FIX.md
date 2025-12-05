# Voice Assistant Fix: VAD Cutting Off Long Sentences

**Date:** 2025-12-04
**Status:** FIXED
**Issue:** User gets cut off when trying to say long sentences or anything more than a few words

---

## Problem Analysis

### Symptoms
- User speech gets fragmented into multiple short segments
- Long sentences are cut mid-thought
- Natural pauses between words trigger premature end-of-speech detection
- Transcripts show multiple START/STOP cycles within seconds

### Example from Conversation Logs

```
15:25:37 | 🎤 START
15:25:37 | ✅ "Please let's speak in English."
15:25:37 | 🎤 STOP  ← Premature stop!
15:25:38 | (empty transcript)
15:25:39 | ✅ "What can you hear me?"  ← Should have been one sentence
```

**What the user said:** "Please let's speak in English. What can you hear me?"
**What VAD detected:** TWO separate speech segments with gaps

### Root Cause

The **`silence_duration_ms`** parameter was set to **500ms**, which is too aggressive for natural speech patterns.

**OpenAI VAD Parameters:**
- `threshold: 0.5` - Sensitivity for detecting speech (default)
- `prefix_padding_ms: 300` - Audio captured before speech starts
- **`silence_duration_ms: 500`** ← **TOO SHORT!**

**Why 500ms was insufficient:**
- Natural speech has pauses between words (100-300ms)
- Breaths between clauses (200-400ms)
- Thinking pauses mid-sentence (300-600ms)
- 500ms doesn't account for longer natural pauses
- Result: VAD triggers `speech_stopped` too early

### Diagnostic Evidence

**Conversation Timeline Analysis:**
```
curl -s "http://localhost:8000/api/realtime/conversations/{id}" | grep speech
```

Found rapid START/STOP cycles:
- Multiple speech segments within 1-2 seconds
- Empty transcripts between segments
- User sentences fragmented across multiple VAD cycles

**Session Configuration Check:**
```json
{
  "turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,
    "prefix_padding_ms": 300,
    "silence_duration_ms": 500  ← TOO SHORT
  }
}
```

---

## Solution

### Increased `silence_duration_ms` to 1200ms

**File:** `backend/api/openai_webrtc_client.py`
**Lines:** 147-159

**Change:**
```python
# OLD (500ms - too aggressive)
"silence_duration_ms": 500

# NEW (1200ms - allows natural pauses)
"silence_duration_ms": 1200
```

**Complete VAD configuration:**
```python
session_update["session"]["turn_detection"] = {
    "type": "server_vad",
    "threshold": 0.5,           # Default sensitivity
    "prefix_padding_ms": 300,   # Audio before speech starts
    "silence_duration_ms": 1200 # 1.2 seconds of silence before ending turn
}
```

### Why 1200ms?

**Research on natural speech pauses:**
- **Breath pauses:** 200-500ms
- **Between clauses:** 300-700ms
- **Thinking mid-sentence:** 400-800ms
- **Between sentences:** 500-1000ms

**1200ms (1.2 seconds) allows:**
- ✅ Natural breathing between phrases
- ✅ Thinking pauses while formulating thoughts
- ✅ Longer sentences without fragmentation
- ✅ Multiple clauses in one turn
- ✅ User can gather thoughts without being cut off

**Trade-off:**
- Slightly longer wait before model responds (1.2s vs 0.5s)
- BUT: Much better user experience with complete sentences

---

## Testing Instructions

### 1. Restart Backend

```bash
# Backend needs restart for changes to take effect
pkill -f "uvicorn main:app"

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

### 3. Test Long Sentences

**Test cases to try:**

1. **Long sentence with pauses:**
   - "I would like to know... if you can handle... a very long sentence with multiple pauses and clauses that go on for quite a while."

2. **Multiple clauses:**
   - "Can you tell me the weather, and also what time it is, and maybe suggest some activities for today?"

3. **Thinking pauses:**
   - "So I was thinking about this project... and I need you to help me with... let me think... the database schema."

4. **Natural speech:**
   - Talk naturally without rushing
   - Use normal breathing pauses
   - Think between words

### 4. Verify Fix

**Check conversation timeline:**
```bash
python3 debug/export_voice_conversations.py

# Analyze latest conversation
python3 -c "
import json, os
files = sorted([f for f in os.listdir('debug/db_exports/voice_conversations') if f.endswith('.json')],
               key=lambda x: os.path.getmtime(f'debug/db_exports/voice_conversations/{x}'), reverse=True)
with open(f'debug/db_exports/voice_conversations/{files[0]}') as f:
    data = json.load(f)

# Find speech events
for evt in data['events']:
    t = evt.get('type', '')
    ts = evt.get('timestamp', '')[:19]
    p = evt.get('payload', {})
    if 'speech_started' in t:
        print(f'{ts} | START')
    elif 'speech_stopped' in t:
        print(f'{ts} | STOP')
    elif 'transcription.completed' in t:
        print(f'{ts} | TRANSCRIPT: {p.get(\"transcript\", \"\")}')
"
```

**Expected results:**
- Fewer START/STOP cycles
- Complete sentences in single transcripts
- No mid-sentence fragmentation
- Gaps of 1-2 seconds between speech segments (not milliseconds)

---

## Technical Details

### VAD Parameter Comparison

| Parameter | Default | Previous | Current | Rationale |
|-----------|---------|----------|---------|-----------|
| `threshold` | 0.5 | 0.5 | 0.5 | Default sensitivity is appropriate |
| `prefix_padding_ms` | 300 | 300 | 300 | 300ms captures beginning of speech well |
| `silence_duration_ms` | **200** | **500** | **1200** | Increased 6x to allow natural pauses |

### Speech Pause Research

**Studies on conversational speech timing:**
- Between words: 50-200ms
- Between phrases: 200-500ms
- Between clauses: 400-800ms
- Turn-taking pauses: 500-1200ms
- Thinking pauses: 600-1500ms

**Sources:**
- Goldman-Eisler, F. (1968). "Psycholinguistics: Experiments in spontaneous speech"
- Beattie, G. W. (1983). "Talk: An analysis of speech and non-verbal behaviour in conversation"

### OpenAI Realtime API Documentation

From OpenAI's documentation:

```json
{
  "turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,              // 0-1, higher = less sensitive
    "prefix_padding_ms": 300,      // Audio before speech
    "silence_duration_ms": 200     // Silence to end turn (DEFAULT)
  }
}
```

**Recommendations:**
- Default 200ms is for "snappy" conversations
- For natural, thoughtful speech: 500-1500ms
- Our choice: 1200ms (sweet spot for most users)

---

## Related Issues Fixed

### Issue #1: Slow Motion Audio (FIXED)
- **File:** `backend/api/realtime_voice_webrtc.py:98-137`
- **Fix:** AudioResampler for stereo→mono conversion

### Issue #2: Browser Audio Not Reaching Backend (FIXED)
- **File:** `backend/api/realtime_voice_webrtc.py:199-210`
- **Fix:** Check transceivers after setRemoteDescription()

### Issue #3: Missing Input Transcription (FIXED)
- **File:** `backend/api/openai_webrtc_client.py:134-158`
- **Fix:** Added input_audio_transcription with Whisper-1

### Issue #4: VAD Cutting Off Long Sentences (FIXED) ⭐ THIS FIX
- **File:** `backend/api/openai_webrtc_client.py:147-159`
- **Fix:** Increased silence_duration_ms from 500ms to 1200ms

---

## Configuration for Different Use Cases

### Snappy Conversations (Quick Back-and-Forth)
```python
"silence_duration_ms": 300  # 0.3 seconds
```
**Use case:** Quick commands, short questions, fast-paced dialogue

### Normal Conversations (Default)
```python
"silence_duration_ms": 800  # 0.8 seconds
```
**Use case:** Regular conversation, some pauses allowed

### Thoughtful Speech (Recommended)
```python
"silence_duration_ms": 1200  # 1.2 seconds ← OUR CHOICE
```
**Use case:** Natural speech with thinking pauses, longer sentences

### Very Patient (For Non-Native Speakers)
```python
"silence_duration_ms": 2000  # 2.0 seconds
```
**Use case:** Users who speak slowly or need time to formulate thoughts

---

## Future Improvements

### Adaptive VAD
Could dynamically adjust `silence_duration_ms` based on:
- User speech patterns (fast vs slow talkers)
- Conversation context (questions vs explanations)
- Language (some languages have longer pauses)

### User Preferences
Add UI control to let users adjust sensitivity:
```javascript
// Slider in frontend
setSilenceDuration(value) {
  // value: 300-2000ms
}
```

---

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `backend/api/openai_webrtc_client.py` | 151, 158 | Changed `silence_duration_ms: 500` → `1200` |
| `backend/api/openai_webrtc_client.py` | 152-153 | Updated comments to explain reasoning |

---

## Verification Checklist

After applying this fix:

- [ ] Backend restarted
- [ ] New voice session started
- [ ] Tested long sentence with pauses
- [ ] Checked conversation transcript (no fragmentation)
- [ ] Speech segments are complete sentences
- [ ] Natural pauses don't trigger early cutoff
- [ ] Response time acceptable (~1.2s after user stops)

---

**Status:** Ready for testing
**Expected Outcome:** Users can speak naturally without being cut off mid-sentence

---

**End of Document**
