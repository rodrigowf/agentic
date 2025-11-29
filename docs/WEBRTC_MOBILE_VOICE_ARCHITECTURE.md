# WebRTC Mobile Voice Architecture

**Last Updated:** 2025-11-29
**Status:** ✅ Refactored and Simplified

---

## Overview

The mobile voice feature enables using a smartphone as a **wireless microphone and speaker** for voice conversations running on desktop. Audio is transmitted peer-to-peer using WebRTC for low latency and high quality.

### Key Components

1. **Backend WebRTC Signaling Server** (`backend/api/realtime_voice.py`)
2. **Desktop Client** (`frontend/src/features/voice/pages/VoiceAssistant.js`)
3. **Mobile Client** (`frontend/src/features/voice/pages/MobileVoice.js`)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Desktop (VoiceAssistant.js)                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │   Desktop    │      │   OpenAI     │      │   Mobile     │  │
│  │ Microphone   │──┬──→│  Realtime    │      │  WebRTC Peer │  │
│  └──────────────┘  │   │     API      │      └──────┬───────┘  │
│                    │   └──────┬───────┘             │          │
│  ┌──────────────┐  │          │                     │          │
│  │   Desktop    │←─┘          │                     │          │
│  │   Speaker    │←────────────┘                     │          │
│  └──────────────┘                                   │          │
│                                                      │          │
│                      WebRTC Signaling WS            │          │
│                 ws://backend/webrtc-signal/         │          │
│                    {conversationId}/desktop         │          │
│                                                      │          │
└──────────────────────────────────────────────────────┼──────────┘
                                                       │
                                                       │ P2P Audio
                                                       │ (WebRTC)
                                                       │
┌──────────────────────────────────────────────────────┼──────────┐
│                    Mobile (MobileVoice.js)           │          │
│                                                       │          │
│  ┌──────────────┐                    ┌───────────────▼───────┐  │
│  │   Mobile     │──────────────────→ │   Desktop WebRTC     │  │
│  │ Microphone   │                    │   Peer Connection    │  │
│  └──────────────┘                    └───────────┬──────────┘  │
│                                                   │             │
│  ┌──────────────┐                                │             │
│  │   Mobile     │←───────────────────────────────┘             │
│  │   Speaker    │  (OpenAI response audio)                     │
│  └──────────────┘                                               │
│                                                                 │
│                      WebRTC Signaling WS                        │
│                 ws://backend/webrtc-signal/                     │
│                    {conversationId}/mobile                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                ▲
                                │
                     ┌──────────┴──────────┐
                     │   Backend Server    │
                     │  WebRTC Signaling   │
                     │   (FastAPI WS)      │
                     └─────────────────────┘
```

---

## Backend: WebRTC Signaling Endpoint

### Location
`backend/api/realtime_voice.py`

### Endpoint
```
WebSocket: /api/realtime/webrtc-signal/{conversation_id}/{peer_id}
```

**Parameters:**
- `conversation_id` - The voice conversation ID
- `peer_id` - Either `"desktop"` or `"mobile"`

### Message Format

**Offer (Desktop → Mobile):**
```json
{
  "type": "offer",
  "sdp": "v=0\r\no=- ... [SDP content]"
}
```

**Answer (Mobile → Desktop):**
```json
{
  "type": "answer",
  "sdp": "v=0\r\no=- ... [SDP content]"
}
```

**ICE Candidate (Bidirectional):**
```json
{
  "type": "candidate",
  "candidate": {
    "candidate": "candidate:... [ICE candidate]",
    "sdpMLineIndex": 0,
    "sdpMid": "0"
  }
}
```

### Implementation

```python
@router.websocket("/webrtc-signal/{conversation_id}/{peer_id}")
async def webrtc_signaling(websocket: WebSocket, conversation_id: str, peer_id: str):
    """
    Unified WebRTC signaling endpoint.
    Forwards SDP offers/answers and ICE candidates between peers.
    """
    # Validate peer_id
    if peer_id not in ["desktop", "mobile"]:
        await websocket.close(code=4400, reason="Invalid peer_id")
        return

    # Register peer
    await audio_relay_manager.register_signaling_peer(conversation_id, peer_id, websocket)

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            msg_type = data.get("type")

            # Forward to the other peer
            target = "mobile" if peer_id == "desktop" else "desktop"
            await audio_relay_manager.forward_signaling(conversation_id, target, data)
    finally:
        await audio_relay_manager.unregister_signaling_peer(conversation_id, peer_id)
```

**Key Features:**
- ✅ Simple message forwarding (no complex state management)
- ✅ Automatic cleanup on disconnect
- ✅ Supports multiple concurrent conversations
- ✅ Graceful handling when peer not connected

---

## Desktop Client: VoiceAssistant.js

### WebRTC Setup Flow

1. **Start Session** (`startSession()`)
   - Get desktop microphone
   - Create audio mixer (desktop mic + mobile audio)
   - Connect to OpenAI Realtime API via WebRTC
   - Open signaling WebSocket for mobile

2. **Mobile Signaling WebSocket**
   ```javascript
   const mobileSignalingUrl = getWsUrl(
     `/realtime/webrtc-signal/${conversationId}/desktop`
   );
   const mobileSignalingWs = new WebSocket(mobileSignalingUrl);
   ```

3. **Setup Mobile WebRTC** (`setupMobileWebRTC()`)
   ```javascript
   // Create peer connection
   const pc = new RTCPeerConnection({
     iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
   });

   // Add desktop's mixed audio (desktop mic + mobile audio)
   const mixedStream = mixerDestinationRef.current.stream;
   for (const track of mixedStream.getAudioTracks()) {
     pc.addTrack(track, mixedStream);
   }

   // Add OpenAI response audio
   if (responseStreamRef.current) {
     for (const track of responseStreamRef.current.getAudioTracks()) {
       pc.addTrack(track, responseStreamRef.current);
     }
   }

   // Receive mobile microphone audio
   pc.ontrack = (evt) => {
     const source = audioContextRef.current.createMediaStreamSource(evt.streams[0]);
     source.connect(mobileGainNodeRef.current); // Mix into desktop
   };

   // Send offer to mobile
   const offer = await pc.createOffer({ offerToReceiveAudio: true });
   await pc.setLocalDescription(offer);
   mobileSignalingWs.send(JSON.stringify({ type: 'offer', sdp: offer.sdp }));
   ```

4. **Handle Mobile Answer**
   ```javascript
   mobileSignalingWs.onmessage = (event) => {
     const msg = JSON.parse(event.data);

     if (msg.type === 'answer') {
       mobileWebRTCPeerRef.current.setRemoteDescription(
         new RTCSessionDescription({ type: 'answer', sdp: msg.sdp })
       );
     } else if (msg.type === 'candidate') {
       mobileWebRTCPeerRef.current.addIceCandidate(
         new RTCIceCandidate(msg.candidate)
       );
     }
   };
   ```

### Audio Flow

**Outgoing (Desktop → Mobile):**
- Desktop microphone → Audio mixer → WebRTC peer → Mobile speaker
- OpenAI response → WebRTC peer → Mobile speaker

**Incoming (Mobile → Desktop):**
- Mobile microphone → WebRTC peer → Desktop audio mixer → OpenAI Realtime API

---

## Mobile Client: MobileVoice.js

### WebRTC Setup Flow

1. **Start Session** (`startSession()`)
   - Get mobile microphone
   - Create Web Audio API context for playback
   - Connect to signaling WebSocket
   - Wait for offer from desktop

2. **Mobile Signaling WebSocket**
   ```javascript
   const signalingUrl = getWsUrl(
     `/realtime/webrtc-signal/${selectedConversationId}/mobile`
   );
   const signalingWs = new WebSocket(signalingUrl);
   ```

3. **Handle Desktop Offer**
   ```javascript
   signalingWs.onmessage = async (event) => {
     const msg = JSON.parse(event.data);

     if (msg.type === 'offer') {
       // Create peer connection
       const pc = new RTCPeerConnection({
         iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
       });

       // Add mobile microphone
       for (const track of micStreamRef.current.getAudioTracks()) {
         pc.addTrack(track, micStreamRef.current);
       }

       // Receive desktop + OpenAI audio
       pc.ontrack = (evt) => {
         const source = window.mobilePlaybackContext.createMediaStreamSource(evt.streams[0]);
         source.connect(speakerGainNodeRef.current); // Play on mobile speaker
       };

       // Send ICE candidates
       pc.onicecandidate = (e) => {
         if (e.candidate) {
           signalingWs.send(JSON.stringify({
             type: 'candidate',
             candidate: e.candidate
           }));
         }
       };

       // Set remote offer and create answer
       await pc.setRemoteDescription(new RTCSessionDescription({
         type: 'offer',
         sdp: msg.sdp
       }));

       const answer = await pc.createAnswer();
       await pc.setLocalDescription(answer);

       // Send answer back to desktop
       signalingWs.send(JSON.stringify({
         type: 'answer',
         sdp: answer.sdp
       }));
     } else if (msg.type === 'candidate') {
       pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
     }
   };
   ```

### Audio Flow

**Outgoing (Mobile → Desktop):**
- Mobile microphone → WebRTC peer → Desktop audio mixer → OpenAI

**Incoming (Desktop/OpenAI → Mobile):**
- OpenAI response → Desktop → WebRTC peer → Mobile speaker
- Desktop microphone → Desktop → WebRTC peer → Mobile speaker (echo if unmuted)

---

## Connection States

### Desktop Connection States

```javascript
// Desktop OpenAI connection
peerRef.current.connectionState → 'connected'  // OpenAI Realtime API

// Desktop-Mobile connection
mobileWebRTCPeerRef.current.connectionState → 'connected'  // Mobile peer
```

### Mobile Connection States

```javascript
// Mobile-Desktop connection
mobilePeerRef.current.connectionState → 'connected'  // Desktop peer
```

### Monitoring Connection State

**Desktop:**
```javascript
mobileWebRTCPeerRef.current.onconnectionstatechange = () => {
  console.log('Mobile peer:', mobileWebRTCPeerRef.current.connectionState);
};
```

**Mobile:**
```javascript
pc.onconnectionstatechange = () => {
  console.log('Desktop peer:', pc.connectionState);
  if (pc.connectionState === 'connected') {
    console.log('✅ WebRTC peer connected!');
  }
};
```

---

## Audio Mixing Architecture

### Desktop Audio Mixer

```
┌─────────────────────────────────────────────────────────┐
│                Desktop Audio Context                     │
│                                                          │
│  ┌──────────────┐       ┌──────────────┐               │
│  │   Desktop    │       │   Mobile     │               │
│  │ Microphone   │       │    Audio     │               │
│  │   Source     │       │   Source     │               │
│  └──────┬───────┘       └──────┬───────┘               │
│         │                      │                        │
│         ▼                      ▼                        │
│  ┌──────────────┐       ┌──────────────┐               │
│  │   Desktop    │       │   Mobile     │               │
│  │  Gain Node   │       │  Gain Node   │               │
│  └──────┬───────┘       └──────┬───────┘               │
│         │                      │                        │
│         └──────────┬───────────┘                        │
│                    ▼                                    │
│            ┌──────────────┐                             │
│            │    Mixer     │                             │
│            │ Destination  │                             │
│            └──────┬───────┘                             │
│                   │                                     │
│                   ▼                                     │
│            ┌──────────────┐                             │
│            │  Mixed Audio │──────────────┐             │
│            │    Stream    │              │             │
│            └──────────────┘              │             │
│                   │                      │             │
│                   ▼                      ▼             │
│            ┌──────────────┐       ┌──────────────┐    │
│            │   OpenAI     │       │   Mobile     │    │
│            │  Realtime    │       │  WebRTC Peer │    │
│            └──────────────┘       └──────────────┘    │
└─────────────────────────────────────────────────────────┘
```

**Implementation:**
```javascript
// Create mixer
const audioContext = new AudioContext();
const mixerDestination = audioContext.createMediaStreamDestination();

// Desktop mic → gain → mixer
const desktopSource = audioContext.createMediaStreamSource(micStream);
const desktopGain = audioContext.createGain();
desktopSource.connect(desktopGain);
desktopGain.connect(mixerDestination);

// Mobile audio → gain → mixer
const mobileGain = audioContext.createGain();
mobileGain.connect(mixerDestination);

// When mobile audio arrives:
pc.ontrack = (evt) => {
  const mobileSource = audioContext.createMediaStreamSource(evt.streams[0]);
  mobileSource.connect(mobileGain);
};

// Use mixed stream
const mixedStream = mixerDestination.stream;
```

---

## Troubleshooting

### Common Issues

#### 1. "Mobile peer not connected"

**Symptom:** Desktop logs `[MobileWebRTC] Failed to forward signaling - mobile not connected`

**Causes:**
- Mobile hasn't connected to signaling endpoint yet
- Mobile disconnected before desktop sent offer
- Network issues preventing WebSocket connection

**Solution:**
- Check mobile is on same network
- Verify mobile can reach `ws://[IP]:8000/api/realtime/webrtc-signal/{conversationId}/mobile`
- Check browser console on mobile for errors

#### 2. "No audio from mobile"

**Symptom:** Desktop doesn't receive audio from mobile mic

**Debugging:**
```javascript
// On desktop
mobileWebRTCPeerRef.current.ontrack = (evt) => {
  console.log('✅ Received track from mobile:', evt.track);
  console.log('Track kind:', evt.track.kind); // Should be 'audio'
  console.log('Track enabled:', evt.track.enabled);
  console.log('Stream:', evt.streams[0]);
};
```

**Common Causes:**
- Mobile microphone is muted (check `isMuted` state)
- Mobile mic permission denied
- Mobile audio track not enabled: `track.enabled = false`
- Mobile browser doesn't support getUserMedia (check HTTPS requirement)

#### 3. "No audio on mobile speaker"

**Symptom:** Mobile doesn't play desktop/OpenAI audio

**Debugging:**
```javascript
// On mobile
pc.ontrack = (evt) => {
  console.log('✅ Received track from desktop:', evt.track);
  const stream = evt.streams[0];
  console.log('Stream tracks:', stream.getTracks());

  // Check playback
  if (audioRef.current) {
    audioRef.current.srcObject = stream;
    audioRef.current.play()
      .then(() => console.log('✅ Audio playing'))
      .catch(err => console.error('❌ Play failed:', err));
  }
};
```

**Common Causes:**
- Mobile speaker muted (check `isSpeakerMuted` state)
- AudioContext suspended (need user gesture to resume)
- Autoplay blocked by browser (requires user interaction)
- Web Audio API createMediaStreamSource called multiple times on same element

#### 4. "ICE connection failed"

**Symptom:** `pc.connectionState` stays in `'connecting'` or goes to `'failed'`

**Debugging:**
```javascript
pc.oniceconnectionstatechange = () => {
  console.log('ICE connection state:', pc.iceConnectionState);
};

pc.onicegatheringstatechange = () => {
  console.log('ICE gathering state:', pc.iceGatheringState);
};

pc.onicecandidate = (e) => {
  if (e.candidate) {
    console.log('ICE candidate:', e.candidate);
  } else {
    console.log('ICE gathering complete');
  }
};
```

**Common Causes:**
- Firewall blocking WebRTC (UDP ports)
- Both peers behind symmetric NAT (STUN not enough, need TURN)
- STUN server unreachable
- ICE candidates not being forwarded correctly

**Solution:**
- Use TURN server for NAT traversal:
  ```javascript
  new RTCPeerConnection({
    iceServers: [
      { urls: 'stun:stun.l.google.com:19302' },
      {
        urls: 'turn:turnserver.example.com:3478',
        username: 'user',
        credential: 'pass'
      }
    ]
  });
  ```

---

## Testing

### Manual Testing Steps

**1. Start Backend:**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**2. Start Frontend:**
```bash
cd frontend
npm start
```

**3. Desktop Setup:**
- Navigate to `http://localhost:3000/voice/[conversationId]`
- Click "Start Session"
- Verify OpenAI connection established
- Check console for: `[MobileWebRTC] Desktop signaling connected`

**4. Mobile Setup:**
- Navigate to `http://[DESKTOP_IP]:3000/mobile-voice`
- Select conversation from dropdown
- Tap green play button
- Check console for:
  - `[MobileVoice] WebRTC signaling connected`
  - `[MobileVoice] Received offer from desktop`
  - `[MobileVoice] Sent answer to desktop`
  - `[MobileVoice] WebRTC peer connected successfully!`

**5. Test Audio:**
- **Mobile → Desktop:** Unmute mobile mic, speak, verify audio reaches OpenAI
- **Desktop → Mobile:** Speak into desktop mic, verify mobile hears it
- **OpenAI → Both:** Trigger AI response, verify both devices play it

### Automated Testing

```bash
# Test WebRTC signaling endpoint
python3 -c "
import asyncio
import websockets

async def test_signaling():
    uri = 'ws://localhost:8000/api/realtime/webrtc-signal/test-conv/desktop'
    async with websockets.connect(uri) as ws:
        print('✅ Connected to WebRTC signaling')
        await ws.send('{\"type\": \"test\"}')
        print('✅ Sent message')

asyncio.run(test_signaling())
"
```

---

## Performance Metrics

### Latency
- **Desktop ↔ OpenAI:** ~200-400ms (network dependent)
- **Mobile ↔ Desktop (same network):** ~50-150ms (WebRTC P2P)
- **Total (Mobile → OpenAI):** ~250-550ms

### Audio Quality
- **Sample Rate:** 48kHz (requested, actual may vary)
- **Channels:** Mono (1 channel)
- **Codec:** Opus (WebRTC automatic selection)
- **Bitrate:** Adaptive (WebRTC auto-negotiates)

### Network Usage
- **WebRTC audio:** ~40-60 KB/s bidirectional
- **Signaling:** <1 KB/s (SDP + ICE candidates)
- **Total:** ~80-120 KB/s per mobile connection

---

## Migration Notes

### Changes from Old Architecture

**Before (2025-11-28):**
```
Desktop: ws://backend/realtime/audio-relay/{conversationId}/desktop
Mobile: ws://backend/realtime/audio-relay/{conversationId}/mobile
```

**After (2025-11-29):**
```
Desktop: ws://backend/realtime/webrtc-signal/{conversationId}/desktop
Mobile: ws://backend/realtime/webrtc-signal/{conversationId}/mobile
```

**What Changed:**
1. ✅ Dedicated WebRTC signaling endpoint (not mixed with binary audio)
2. ✅ Peer ID in URL path (not via register message)
3. ✅ Simplified message handling (just forward offer/answer/candidate)
4. ✅ Better error logging and debugging
5. ✅ Connection state monitoring

**Backwards Compatibility:**
- Old `/audio-relay` endpoints still exist but are deprecated
- No clients should use them for WebRTC signaling

---

## Future Improvements

### Potential Enhancements

1. **TURN Server Integration**
   - Add TURN server for NAT traversal
   - Handle symmetric NAT scenarios
   - Support corporate networks with restrictive firewalls

2. **Data Channel**
   - Send metadata alongside audio (mute state, speaker level, etc.)
   - Share transcripts in real-time
   - Send low-latency control messages

3. **Reconnection Logic**
   - Auto-reconnect on connection drop
   - Resume session without full restart
   - Queue audio during brief disconnects

4. **Quality Monitoring**
   - Track RTT (round-trip time)
   - Monitor packet loss
   - Adaptive bitrate based on network conditions

5. **Multi-Mobile Support**
   - Support multiple mobile devices per conversation
   - Audio mixing from multiple sources
   - Select active microphone

---

## References

- [WebRTC API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API)
- [RTCPeerConnection](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection)
- [OpenAI Realtime API](https://platform.openai.com/docs/api-reference/realtime)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

---

**End of Documentation**
