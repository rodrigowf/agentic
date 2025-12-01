# Mobile Voice Fix Summary - Nov 29, 2025

## Problem
Mobile voice doesn't play audio response even though data is being received.

## Root Cause
**Chrome AudioContext Suspended** - Chrome's autoplay policy suspends AudioContext until user interaction. Even though audio chunks were being received and "played", no sound came out because AudioContext was suspended.

## Evidence
Console logs showed:
```
✅ [MobileVoice] Audio relay connected
✅ [MobileVoice] Playing desktop audio chunk: 16384 samples (86 times in 1ms!)
❌ No actual sound output
```

## Fix Applied
Added AudioContext resume in `startSession()` function:

```javascript
// Resume AudioContext (Chrome autoplay policy requires user gesture)
if (window.mobilePlaybackContext.state === 'suspended') {
  await window.mobilePlaybackContext.resume();
  console.log('[MobileVoice] AudioContext resumed - audio playback enabled');
}
```

**Location:** `frontend/src/features/voice/pages/MobileVoice.js` line 348-352

## How to Test
1. **Refresh mobile browser** (Ctrl+R or pull-to-refresh)
2. **Start desktop session** at http://localhost:3000/voice
3. **Connect mobile** and select conversation
4. **Tap green play button** - This triggers AudioContext resume
5. **Speak on desktop** or **trigger AI response**
6. **Should hear audio** on mobile speaker!

## Expected Console Output
```
[MobileVoice] Connecting to audio relay: wss://...
[MobileVoice] AudioContext resumed - audio playback enabled  ← NEW!
[MobileVoice] Audio relay connected - ready to send microphone audio
[MobileVoice] Session started successfully with audio relay
[MobileVoice] Playing desktop audio chunk: 16384 samples
```

## Complete Fix Chain (Session History)

### 1. WebRTC Signaling Missing ✅
- Created `/backend/api/webrtc_signaling.py`
- Added endpoint to `main.py`
- Restarted nginx

### 2. Architecture Mismatch ✅
- Mobile was using WebRTC peer connection
- Desktop expects WebSocket audio relay
- **Fixed:** Replaced WebRTC with WebSocket in MobileVoice.js

### 3. AudioContext Suspended ✅
- Chrome blocks audio until user gesture
- AudioContext.state was 'suspended'
- **Fixed:** Added `audioContext.resume()` in startSession

## Files Modified

1. `frontend/src/features/voice/pages/MobileVoice.js`
   - Line 26: Removed WebRTC import
   - Line 54: Removed webrtcPeerRef
   - Line 348-352: Added AudioContext resume
   - Line 354-447: Replaced WebRTC with WebSocket audio relay
   - Line 468-486: Updated cleanup code

2. `backend/api/webrtc_signaling.py` (NEW - not used)
3. `backend/main.py` (Added WebRTC endpoint - not used)

## Architecture (Final)

```
Mobile Mic (muted by default)
  ↓ getUserMedia
  ↓ ScriptProcessorNode (16384 samples)
  ↓ Float32 → Int16 PCM
  ↓ WebSocket /realtime/audio-relay/{id}/mobile
  ↓
Desktop receives on /realtime/audio-relay/{id}/desktop
  ↓ Mix with desktop mic
  ↓ Send to OpenAI Realtime API (WebRTC)
  ↓
OpenAI Response
  ↓ Desktop receives (WebRTC)
  ↓ Desktop relays to Mobile (WebSocket)
  ↓ Mobile: Int16 → Float32
  ↓ AudioContext.createBufferSource()
  ↓ Mobile Speaker (IF AudioContext resumed!)
```

## Key Learnings

1. **Chrome AudioContext Policy** - Always resume() on user gesture
2. **Architecture Documentation** - Desktop/Mobile expected different protocols
3. **Console Logging** - "Playing audio" doesn't mean audio is audible
4. **WebRTC vs WebSocket** - Different use cases, can't mix arbitrarily
5. **Hot Reload Cache** - Banner removal confirmed new code loaded

## Status
🟢 **LIKELY FIXED** - Awaiting user confirmation after browser refresh
