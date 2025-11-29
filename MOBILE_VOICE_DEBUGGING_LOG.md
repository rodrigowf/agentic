# Mobile Voice Debugging Log - Nov 29, 2025

## Problem Statement
Mobile voice interface doesn't send/receive audio when speaking.

## Root Cause Analysis

### Issue 1: WebRTC vs WebSocket Mismatch ✅ FIXED
**Problem:** Mobile was using WebRTC peer connection, but desktop expects WebSocket audio relay.

**Evidence:**
- Mobile code created `WebRTCPeerConnection`
- Desktop code listens on WebSocket `/realtime/audio-relay/${conversationId}/desktop`
- No WebRTC receiver on desktop side (`mobileWebRTCPeerRef` declared but never instantiated)

**Fix Applied:** Replaced WebRTC with WebSocket audio relay in `MobileVoice.js`

### Issue 2: Missing Backend WebRTC Signaling ✅ FIXED
**Problem:** Backend had no WebRTC signaling endpoint when mobile tried to use WebRTC.

**Evidence:**
- Frontend tried to connect to `/api/webrtc-signal/${conversationId}`
- Backend returned 404 on this endpoint
- nginx returned 403 because endpoint didn't exist

**Fix Applied:** Created `/backend/api/webrtc_signaling.py` and added endpoint to `main.py` (no longer needed since we switched to WebSocket)

### Issue 3: Browser Cache ⚠️ PENDING
**Problem:** Mobile browser is loading OLD code (from 04:47 timestamp in logs).

**Evidence:**
- Console still shows `[MobileVoice WebRTC] Creating peer connection...`
- New code should show `[MobileVoice] Connecting to audio relay:`
- Errors are from before nginx restart (403 on webrtc-signal)

**Solution Required:** User must hard refresh mobile browser (Ctrl+Shift+R or clear cache)

## Architecture Diagram

### Correct Flow (After Fix):
```
Mobile Mic
  → getUserMedia (muted by default)
  → ScriptProcessorNode (16384 samples)
  → Float32 → Int16 PCM conversion
  → WebSocket.send() to /realtime/audio-relay/{id}/mobile

Desktop receives on /realtime/audio-relay/{id}/desktop
  → Mixes with desktop mic
  → Sends to OpenAI Realtime API via WebRTC

OpenAI Response
  → Desktop receives via WebRTC
  → Desktop relays to Mobile via WebSocket
  → Mobile converts Int16 → Float32
  → AudioBuffer playback through speaker
```

## Code Changes Made

### File: `frontend/src/features/voice/pages/MobileVoice.js`

**Removed:**
- WebRTC peer connection creation
- `import { WebRTCPeerConnection } from '../../../utils/webrtcHelper'`
- `webrtcPeerRef` useState
- WebRTC version banner

**Added:**
- WebSocket connection to `/realtime/audio-relay/${conversationId}/mobile`
- ScriptProcessorNode for mic audio capture
- PCM audio conversion (Float32 ↔ Int16)
- Audio playback for desktop responses
- Proper cleanup in stopSession

**Key Implementation:**
```javascript
// Connect to audio relay
const audioRelayWs = new WebSocket(getWsUrl(`/realtime/audio-relay/${selectedConversationId}/mobile`));

// Create audio processor
const processor = audioContext.createScriptProcessor(16384, 1, 1);
processor.onaudioprocess = (audioEvent) => {
  if (audioRelayWsRef.current?.readyState === WebSocket.OPEN && !isMuted) {
    const inputData = audioEvent.inputBuffer.getChannelData(0);
    const pcmData = new Int16Array(inputData.length);
    // Convert and send to desktop
    audioRelayWsRef.current.send(pcmData.buffer);
  }
};
```

### File: `backend/api/webrtc_signaling.py` (NEW - not needed anymore)
Created WebRTC signaling server but it's not used since we switched to WebSocket.

### File: `backend/main.py`
Added WebRTC signaling endpoint at line 575 (not needed anymore).

## Testing Checklist

- [ ] Hard refresh mobile browser (Ctrl+Shift+R)
- [ ] Verify new console logs appear: `[MobileVoice] Connecting to audio relay:`
- [ ] Start desktop voice session first
- [ ] Connect mobile to same conversation
- [ ] Tap green play button on mobile
- [ ] Tap orange microphone to unmute
- [ ] Speak and verify desktop receives audio
- [ ] Verify mobile hears desktop + OpenAI responses

## Expected Console Output (Mobile)

```
[MobileVoice] Connecting to audio relay: wss://192.168.0.25/api/realtime/audio-relay/{id}/mobile
[MobileVoice] Audio relay connected - ready to send microphone audio
[MobileVoice] Session started successfully with audio relay
[MobileVoice] Playing desktop audio chunk: 16384 samples
```

## Expected Console Output (Desktop)

```
[MobileAudio] Mobile audio relay connected
[MobileAudio] Playing mobile PCM chunk: 16384 samples
[MobileAudio] Started relaying OpenAI response to mobile
```

## Known Issues

1. **Microphone starts muted** - User must tap mic button to unmute (by design for privacy)
2. **ScriptProcessorNode deprecated** - Should migrate to AudioWorklet in future
3. **No visual feedback** - Audio level bars don't work yet (separate issue)
4. **Cache aggressiveness** - React dev server caches aggressively, may need version query param

## Next Steps if Still Not Working

1. Check desktop session is actually running
2. Check conversation IDs match between mobile and desktop
3. Check WebSocket connection in Network tab
4. Check audio permissions granted on mobile
5. Check speaker/microphone aren't muted by system
6. Try incognito mode to bypass cache completely

## Backend Endpoints Used

- `GET /api/realtime/conversations` - List conversations
- `WS /api/realtime/audio-relay/{id}/mobile` - Mobile sends audio here
- `WS /api/realtime/audio-relay/{id}/desktop` - Desktop receives audio here

## Files Modified

1. `frontend/src/features/voice/pages/MobileVoice.js` - Complete rewrite of audio handling
2. `backend/api/webrtc_signaling.py` - NEW (not needed)
3. `backend/main.py` - Added endpoint (not needed)
