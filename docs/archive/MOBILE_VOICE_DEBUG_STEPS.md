# Mobile Voice Debug Steps

## Issue
User reports: "Now nothing is working for the mobile-voice page again"

## Changes Made
Added comprehensive debug logging to mobile signaling WebSocket message handler to diagnose the issue.

## Test Steps

### 1. Hard Refresh Both Pages
- Desktop: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
- Mobile: Ctrl+Shift+R (or use browser menu → "Request Desktop Site" toggle off/on)

### 2. Open Browser Consoles
- **Desktop:** F12 → Console tab
- **Mobile:** Connect mobile to desktop via USB, open `chrome://inspect` on desktop

### 3. Test in This Exact Order

**Step 1: Start Desktop Session FIRST**
```
1. Desktop: Navigate to http://localhost:3000/voice
2. Desktop: Click "Start Session"
3. Desktop: Wait for "Ready" status
4. Desktop: Verify you see "[MobileWebRTC] Desktop signaling connected"
```

**Step 2: Join from Mobile SECOND**
```
5. Mobile: Navigate to http://192.168.x.x:3000/mobile-voice
6. Mobile: Select conversation from dropdown
   (Or use direct URL: http://192.168.x.x:3000/mobile-voice/CONVERSATION_ID)
7. Mobile: Tap green play button
8. Mobile: Verify you see "[MobileVoice] WebRTC signaling connected"
9. Mobile: Verify you see "[MobileVoice] Raw WebSocket message received: ..." (NEW LOG!)
```

**Step 3: Check Desktop Logs**
```
10. Desktop: Should show "[MobileWebRTC] Mobile peer joined! Creating offer now..."
11. Desktop: Should show "[MobileWebRTC Setup] Offer sent successfully!"
```

**Step 4: Check Mobile Logs**
```
12. Mobile: Should show "[MobileVoice] Raw WebSocket message received: {..."
13. Mobile: Should show "[MobileVoice] Parsed signaling message type: offer"
14. Mobile: Should show "[MobileVoice] Received initial offer from desktop, creating peer connection"
```

## What to Look For

### If Mobile Shows NO WebSocket Messages

**Symptom:**
```
[MobileVoice] WebRTC signaling connected
[MobileMute] Toggled to: UNMUTED
[MobileVoice] Fetched conversations: 2
(NO "Raw WebSocket message received" logs!)
```

**Cause:** WebSocket connected but not receiving messages
**Possible reasons:**
- WebSocket closed silently (check for close log)
- Backend not forwarding messages
- Wrong conversation ID

**Fix:** Check desktop console for errors, verify conversation IDs match

### If Mobile Shows Error in Message Handler

**Symptom:**
```
[MobileVoice] Raw WebSocket message received: {...}
[MobileVoice] Failed to handle signaling message: Error: ...
[MobileVoice] Error stack: ...
```

**Cause:** JavaScript error in message handling code
**Action:** Report the full error message and stack trace

### If Mobile Receives Offer But No Audio

**Symptom:**
```
[MobileVoice] Received initial offer from desktop, creating peer connection
[MobileVoice] Received remote audio track
[MobileVoice] Connected remote audio to speaker via Web Audio API
[MobileVoice] WebRTC peer connected successfully!
(Connection works but no sound!)
```

**Cause:** Audio routing issue (not WebSocket issue)
**Action:** Check browser audio permissions, try headphones

## Expected Full Console Output

### Desktop Console (in order):
```
[Desktop] OpenAI response will play on desktop <audio> element
[MobileAudio] OpenAI response stream received, will be sent via WebRTC if mobile connected
[DesktopMute] Desktop mic gain set to: 0
[MobileWebRTC] Desktop signaling connected
[MobileWebRTC] Waiting for mobile peer to join before creating offer...
[MobileWebRTC] Mobile peer joined! Creating offer now...
[MobileWebRTC Setup] Starting, ws exists: true , peer exists: false
[MobileWebRTC Setup] Creating new RTCPeerConnection...
[MobileWebRTC Setup] Adding 1 desktop audio track(s)
[MobileWebRTC Setup] Creating offer...
[MobileWebRTC Setup] Offer created, setting local description...
[MobileWebRTC Setup] Local description set, sending offer to mobile...
[MobileWebRTC Setup] Offer sent successfully!
[MobileWebRTC] Received answer from mobile, setting remote description
[MobileWebRTC] Remote description set successfully
[MobileWebRTC] Received ICE candidate from mobile
[MobileWebRTC] Received mobile audio track and mixed into desktop
```

### Mobile Console (in order):
```
[MobileVoice] Fetched conversations: 2
[MobileVoice] Created MediaElementSource for speaker analysis
[MobileVoice] Connecting to WebRTC signaling: ws://localhost:8000/api/realtime/webrtc-signal/.../mobile
[MobileVoice] WebRTC signaling connected
[MobileVoice] Session started successfully with WebRTC signaling
[MobileMute] Toggled to: UNMUTED, ref updated
[MobileVoice] Raw WebSocket message received: {"type":"offer","sdp":"..."}
[MobileVoice] Parsed signaling message type: offer Full message: {type: "offer", sdp: "..."}
[MobileVoice] Received initial offer from desktop, creating peer connection
[MobileVoice] Added microphone track to peer connection
[MobileVoice] Sent ICE candidate to desktop
[MobileVoice] Sent ICE candidate to desktop
...
[MobileVoice] Set remote description (offer)
[MobileVoice] Created and set local description (answer)
[MobileVoice] Sent answer to desktop
[MobileVoice] Connection state: connecting
[MobileVoice] Received remote audio track
[MobileVoice] Connected remote audio to speaker via Web Audio API
[MobileVoice] Connection state: connected
[MobileVoice] WebRTC peer connected successfully!
```

## Common Issues

### Issue 1: "Available values are ``, ``" Warning
**Harmless!** This is a timing issue where React renders before conversations load. Ignore this warning.

### Issue 2: Mobile Logs from Wrong Test Run
Make sure you're looking at the LATEST logs after refreshing. Old logs can be confusing!

### Issue 3: Desktop Says "Aborted - peer connection already exists"
This happens if you refresh mobile or reconnect. It's handled gracefully - just creates a warning.

## Report Back

Please provide:
1. ✅ Complete desktop console output (all lines mentioning "MobileWebRTC")
2. ✅ Complete mobile console output (all lines mentioning "MobileVoice")
3. ✅ What specifically isn't working (no audio? no connection? page crash?)
4. ✅ Any red ERROR messages in either console

With these logs, I can pinpoint the exact issue!
