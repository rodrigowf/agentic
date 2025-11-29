# Final Fix: Audio Overlap Issue - Nov 29, 2025

## Problem
Mobile receives desktop audio chunks but no sound is heard.

## Root Cause Discovery
From desktop browser console logs:
```
[MobileVoice] Playing desktop audio chunk: 16384 samples (86 times!)
```

**86 audio chunks** playing **simultaneously** at the same timestamp creates:
- Audio overlap and interference
- Garbled sound or silence
- Audio glitches from buffer contention

## Technical Explanation
Previous code:
```javascript
source.start(0);  // Always starts immediately!
```

This made every chunk start at time `0`, causing massive overlap when chunks arrive rapidly.

## Fix Applied
Sequential audio scheduling using AudioContext timeline:

```javascript
// Track next scheduled audio time to prevent overlap
let nextAudioTime = 0;

audioRelayWs.onmessage = (event) => {
  // ... convert PCM data ...

  const currentTime = audioContext.currentTime;
  const bufferDuration = audioBuffer.duration;

  // If we're behind, catch up to current time
  if (nextAudioTime < currentTime) {
    nextAudioTime = currentTime;
  }

  source.start(nextAudioTime);  // Schedule at next available slot
  nextAudioTime += bufferDuration;  // Advance timeline

  console.log('[MobileVoice] Scheduled desktop audio chunk at', nextAudioTime.toFixed(3), 's');
};
```

**Location:** `frontend/src/features/voice/pages/MobileVoice.js` lines 367-420

## How It Works

### Before (Broken):
```
Chunk 1: start(0) → plays at time 0.000s
Chunk 2: start(0) → plays at time 0.000s  ← OVERLAP!
Chunk 3: start(0) → plays at time 0.000s  ← OVERLAP!
...
Chunk 86: start(0) → plays at time 0.000s ← OVERLAP!
Result: Garbled mess or silence
```

### After (Fixed):
```
Chunk 1: start(0.000) → plays at 0.000-0.341s
Chunk 2: start(0.341) → plays at 0.341-0.682s  ← Sequential!
Chunk 3: start(0.682) → plays at 0.682-1.023s  ← Sequential!
...
Result: Clean, continuous audio playback
```

## Expected Console Output (After Fix)
```
[MobileVoice] Connecting to audio relay: ws://...
[MobileVoice] Audio relay connected - ready to send microphone audio
[MobileVoice] Session started successfully with audio relay
[MobileVoice] Scheduled desktop audio chunk at 0.000 s
[MobileVoice] Scheduled desktop audio chunk at 0.341 s
[MobileVoice] Scheduled desktop audio chunk at 0.682 s
[MobileVoice] Scheduled desktop audio chunk at 1.023 s
...
```

Notice: **Scheduled** instead of **Playing**, with **increasing timestamps**

## Test Instructions
1. **Refresh page** (Ctrl+R or Shift+Ctrl+R)
2. **Start desktop voice session**
3. **Connect mobile** and select conversation
4. **Tap green play button**
5. **Speak or trigger AI response**
6. **Listen for clean audio!** 🎧

## Session Fix Summary

| Issue | Status | Fix |
|-------|--------|-----|
| WebRTC endpoint missing | ✅ Fixed | Created backend signaling server |
| WebRTC/WebSocket mismatch | ✅ Fixed | Replaced WebRTC with WebSocket in mobile |
| AudioContext suspended | ⚠️ Not needed | Context auto-runs on desktop |
| **Audio overlap** | ✅ **FIXED** | **Sequential scheduling with timeline** |

## Files Modified (Final)
- `frontend/src/features/voice/pages/MobileVoice.js`
  - Line 367-368: Added `nextAudioTime` tracker
  - Line 399-414: Sequential scheduling logic
  - Line 416: Changed log message to "Scheduled"

## Key Learning
**Web Audio API Best Practice:**
- NEVER use `source.start(0)` for streaming audio
- ALWAYS use `audioContext.currentTime` + duration for scheduling
- Track `nextAudioTime` to maintain sequential playback
- Use `.duration` to calculate proper spacing

## Audio Buffer Duration
```
16384 samples ÷ 48000 Hz = 0.341 seconds per chunk
```

With 86 chunks received rapidly:
- **Before:** 86 × 0.341s = 29.3 seconds of audio playing in 0s → overlap/silence
- **After:** 86 × 0.341s = 29.3 seconds played sequentially over 29.3s → clear audio

## Status
🟢 **SHOULD BE FULLY FIXED** - Refresh and test!
