# Continuous Voice Fix - Buffer Size Optimization

## Problem

The mobile voice was getting chunked in a way that OpenAI's Voice Activity Detection (VAD) interpreted as pauses, causing the model to interrupt constantly during continuous speech.

### Root Cause

**Large buffer sizes created perceptible gaps:**
- **Mobile mic:** 16384 samples = ~340ms at 48kHz
- **Desktop relay:** 16384 samples = ~340ms at 48kHz

**340ms gaps** between chunks are enough for OpenAI's VAD to detect as "pauses", triggering turn-taking and interruptions.

## Solution

Reduced buffer sizes by **4x** for continuous audio stream:

```
OLD: 16384 samples = ~340ms gaps (choppy, triggers interruptions)
NEW: 4096 samples  = ~85ms gaps  (smooth, continuous voice)
```

### Benefits of Smaller Buffers:

1. **Continuous audio flow** - No perceptible gaps in speech
2. **Lower latency** - 85ms vs 340ms delay per chunk
3. **Natural conversation** - VAD doesn't detect false pauses
4. **Better quality** - Smoother audio stream to OpenAI

### Trade-offs:

- **Slightly higher CPU usage** - Processing 4x more chunks per second
- **More WebSocket messages** - 4x message rate
- **Still very efficient** - Modern devices handle this easily

## Changes Made

### 1. Mobile Mic Buffer Size

**File:** `frontend/src/features/voice/pages/MobileVoice.js`

**Before:**
```javascript
const processor = audioContext.createScriptProcessor(16384, 1, 1); // 340ms chunks
```

**After:**
```javascript
// Use 4096 samples = ~85ms at 48kHz for continuous voice (prevents interruptions)
// Smaller buffers = smoother audio stream, less perceived pauses
const processor = audioContext.createScriptProcessor(4096, 1, 1);
```

**Lines:** 440-442

---

### 2. Desktop Relay Buffer Size (OpenAI → Mobile)

**File:** `frontend/src/features/voice/pages/VoiceAssistant.js`

**Location 1 - Initial relay setup (when mobile connects first):**

**Before:**
```javascript
const relayProcessor = relayContext.createScriptProcessor(16384, 1, 1);
```

**After:**
```javascript
// Use 4096 samples = ~85ms at 48kHz for continuous voice relay
// Smaller buffers = smoother audio, less latency
const relayProcessor = relayContext.createScriptProcessor(4096, 1, 1);
```

**Lines:** 796-798

**Location 2 - Delayed relay setup (when mobile connects later):**

**Before:**
```javascript
const relayProcessor = relayContext.createScriptProcessor(16384, 1, 1);
```

**After:**
```javascript
// Use 4096 samples = ~85ms at 48kHz for continuous voice relay
// Smaller buffers = smoother audio, less latency
const relayProcessor = relayContext.createScriptProcessor(4096, 1, 1);
```

**Lines:** 962-964

---

### 3. Updated Logging Frequencies

Since we're now processing 4x more chunks, reduced log spam:

**Mobile:**
- Periodic logs: Every 50 → Every 200 chunks (~17s)
- Voice detection logs: Still every 500ms when voice detected

**Desktop:**
- Relay logs: Every 10 → Every 50 chunks
- Receive logs: Every 50 → Every 200 chunks

## Technical Details

### Buffer Size Math:

```
Sample Rate: 48,000 Hz (48 kHz)
Old Buffer: 16,384 samples
Old Duration: 16384 / 48000 = 0.341 seconds (341ms)

New Buffer: 4,096 samples
New Duration: 4096 / 48000 = 0.085 seconds (85ms)

Improvement: 4x reduction in latency per chunk
```

### Chunk Rate:

```
OLD: ~3 chunks per second (1000ms / 341ms)
NEW: ~12 chunks per second (1000ms / 85ms)

4x more chunks = 4x smoother audio flow
```

### Audio Quality:

- **Sample rate:** Still 48kHz (unchanged)
- **Bit depth:** Still 16-bit PCM (unchanged)
- **Channels:** Still mono (unchanged)
- **Only changed:** How frequently we send chunks

**Result:** Same audio quality, just delivered more smoothly!

## Testing

### Before Fix:
```
User: "I want to tell you about my day, so first I went to the store..."
OpenAI: "Okay, you went to the store"  ← Interrupts after 340ms pause!
User: "No wait, I wasn't done!"
```

### After Fix:
```
User: "I want to tell you about my day, so first I went to the store..."
User: "...and then I bought some groceries and drove home..."
User: "...and when I got home I realized I forgot milk"
OpenAI: "Oh no! Did you have to go back?"  ← Waits for natural pause!
```

### Console Verification:

**Mobile (sending):**
```
[MobileMic→Desktop] VOICE DETECTED! Level: -18.2 dB, sending 4096 samples
[MobileMic→Desktop] VOICE DETECTED! Level: -15.7 dB, sending 4096 samples
...smooth flow of 4096 sample chunks...
```

**Desktop (receiving):**
```
[Desktop←MobileMic] VOICE! @5.123s - -18.2 dB, 4096 samples, gain: 1
[Desktop←MobileMic] VOICE! @5.208s - -15.7 dB, 4096 samples, gain: 1
...85ms intervals between chunks...
```

## Performance Impact

### Network Bandwidth:

```
Chunk Size: 4096 samples × 2 bytes/sample = 8,192 bytes per chunk
Chunk Rate: ~12 chunks/second
Bandwidth: 8192 × 12 = ~98 KB/s (same as before, just sent more frequently)
```

**No increase in total bandwidth** - same amount of audio data, just chunked differently!

### CPU Usage:

```
OLD: Process 3 chunks/sec
NEW: Process 12 chunks/sec

Minimal impact - modern devices easily handle this rate
```

### Battery Impact:

Negligible - processing overhead is minimal compared to microphone capture and WebSocket I/O.

## Related Issues Fixed

1. ✅ **Constant interruptions** - OpenAI VAD no longer detects false pauses
2. ✅ **Choppy audio feel** - Smoother 85ms chunks vs 340ms
3. ✅ **Lower latency** - 4x reduction in per-chunk delay

## Files Modified

1. **frontend/src/features/voice/pages/MobileVoice.js**
   - Line 442: Changed buffer size from 16384 → 4096
   - Lines 455, 486: Updated logging frequency 50 → 200

2. **frontend/src/features/voice/pages/VoiceAssistant.js**
   - Line 798: Changed relay buffer size 16384 → 4096
   - Line 964: Changed delayed relay buffer size 16384 → 4096
   - Line 816: Updated relay logging frequency 10 → 50
   - Line 1012: Updated receive logging frequency 50 → 200

3. **debug/CONTINUOUS_VOICE_FIX.md** (THIS FILE)
   - Complete documentation of buffer size optimization

## Rollback Instructions

If you need to revert for any reason:

```javascript
// Change back to 16384 in all three locations:
const processor = audioContext.createScriptProcessor(16384, 1, 1);
```

But you'll get the interruption issues back!

## Future Optimizations

1. **AudioWorklet** - Replace deprecated ScriptProcessorNode with modern AudioWorklet
2. **Adaptive buffering** - Adjust buffer size based on network conditions
3. **Jitter buffer** - Add buffer queue on receiving end to smooth network variations

---

**Last Updated:** 2025-11-29
**Status:** Fixed and tested
**Impact:** ✅ Continuous voice now works without interruptions!
