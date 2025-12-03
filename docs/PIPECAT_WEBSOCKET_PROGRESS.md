# Pipecat WebSocket Implementation Progress

**Date:** 2025-12-03
**Status:** ✅ Backend Complete - ✅ Frontend Complete - Testing Pending
**Transport:** FastAPI WebSocket (Self-hosted, No Daily!)

---

## ✅ Completed: Backend WebSocket Implementation

### 1. Backend Controller Created

**File:** [backend/api/realtime_voice_pipecat_ws.py](../backend/api/realtime_voice_pipecat_ws.py) (428 lines)

**Key Features:**
- FastAPI WebSocket endpoint: `/api/realtime/pipecat/ws/{conversation_id}`
- Pipecat pipeline with OpenAI Realtime API
- Function handlers: send_to_nested, send_to_claude_code, pause, reset, pause_claude_code
- Event persistence to SQLite (conversation store)
- Session management (list active sessions, stop sessions)

**WebSocket API:**
```
WS  /api/realtime/pipecat/ws/{conversation_id}?voice=alloy&agent_name=MainConversation
GET /api/realtime/pipecat/sessions
POST /api/realtime/pipecat/sessions/{session_id}/stop
```

**Pipeline Architecture:**
```python
Pipeline([
    transport.input(),              # Audio from WebSocket (PCM16)
    context_aggregator.user(),      # Track user context
    llm,                            # OpenAI Realtime API
    event_recorder,                 # Record to SQLite
    transport.output(),             # Audio to WebSocket (PCM16)
    context_aggregator.assistant()  # Track assistant context
])
```

**Transport Configuration:**
```python
FastAPIWebsocketTransport(
    websocket,
    FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_in_sample_rate=24000,  # OpenAI uses 24kHz
        audio_out_sample_rate=24000,
        audio_in_channels=1,  # Mono
        audio_out_channels=1,
        add_wav_header=False,  # Raw PCM16
        vad_enabled=True,  # Voice Activity Detection
        vad_analyzer="silero",
        vad_audio_passthrough=True
    )
)
```

### 2. Router Registered

**File:** [backend/main.py](../backend/main.py) (lines 119-131)

Successfully mounted at startup:
```
Pipecat WebSocket router mounted (self-hosted)
```

### 3. Import Verified

✅ Controller imports without errors:
```bash
$ python3 -c "from api.realtime_voice_pipecat_ws import router"
✅ Pipecat WebSocket controller imported successfully
```

---

## ✅ Completed: Frontend WebSocket Client

### Implementation

**File:** [frontend/src/features/voice/pages/VoiceAssistantWebSocket.js](../frontend/src/features/voice/pages/VoiceAssistantWebSocket.js) (570 lines)

**Features Implemented:**
- ✅ Simple WebSocket connection to Pipecat backend
- ✅ getUserMedia for microphone audio capture at 24kHz mono
- ✅ PCM16 audio encoding (Float32 → Int16)
- ✅ PCM16 audio decoding and playback (Int16 → Float32)
- ✅ Mute/unmute controls for microphone and speaker
- ✅ Audio playback queue for smooth streaming
- ✅ WebSocket event handling (transcriptions, function calls)
- ✅ Integration with nested team and Claude Code WebSockets
- ✅ Responsive layout (desktop/mobile)
- ✅ Error handling and session management

**Route Added:** `/voice-ws/:conversationId`

**Code Comparison:**
- VoiceAssistantModular.js (WebRTC): ~768 lines
- VoiceAssistantWebSocket.js (WebSocket): ~570 lines
- **Reduction: 26% less code**

### Implementation Details

#### 1. WebSocket Connection

**Key Changes:**
- Replaced `RTCPeerConnection` with simple `WebSocket`
- Removed SDP negotiation, ICE candidates, data channels
- Direct connection to Pipecat backend

```javascript
// Connect to Pipecat WebSocket backend
const wsUrl = `${getWsUrl()}/api/realtime/pipecat/ws/${conversationId}?voice=${voiceConfig.voice}`;
const ws = new WebSocket(wsUrl);

ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
        // Audio data - play it
        playAudio(event.data);
    }
};
```

#### 2. Audio Capture (getUserMedia → PCM16)

**Implementation:**
```javascript
// Get microphone at 24kHz mono
const stream = await navigator.mediaDevices.getUserMedia({
    audio: { sampleRate: 24000, channelCount: 1, echoCancellation: true }
});

// Create audio processor
const processor = audioContext.createScriptProcessor(4096, 1, 1);
processor.onaudioprocess = (e) => {
    const inputData = e.inputBuffer.getChannelData(0);
    const pcm16 = float32ToPCM16(inputData); // Convert to PCM16
    ws.send(pcm16); // Send to backend
};
```

#### 3. Audio Playback (PCM16 → AudioContext)

**Implementation:**
```javascript
const playAudio = (pcm16ArrayBuffer) => {
    const pcm16 = new Int16Array(pcm16ArrayBuffer);
    const float32 = pcm16ToFloat32(pcm16); // Convert to Float32

    // Create audio buffer and play
    const audioBuffer = audioContext.createBuffer(1, float32.length, 24000);
    audioBuffer.getChannelData(0).set(float32);

    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start();
};
```

#### 4. Audio Conversion Helpers

**Float32 → PCM16 (for sending):**
```javascript
const float32ToPCM16 = (float32Array) => {
    const pcm16 = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Array[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return pcm16.buffer;
};
```

**PCM16 → Float32 (for playback):**
```javascript
const pcm16ToFloat32 = (pcm16Array) => {
    const float32 = new Float32Array(pcm16Array.length);
    for (let i = 0; i < pcm16Array.length; i++) {
        const int16 = pcm16Array[i];
        float32[i] = int16 / (int16 < 0 ? 0x8000 : 0x7FFF);
    }
    return float32;
};
```

#### 5. Session Management

**Start session:**
```javascript
const startSession = async () => {
    connectWebSocket(); // Connect to Pipecat
    await waitForConnection(); // Wait for WebSocket.OPEN
    await startAudioCapture(); // Start mic
};
```

**Stop session:**
```javascript
const stopSession = () => {
    stopAudioCapture(); // Stop mic
    disconnectWebSocket(); // Close WebSocket
    playbackQueueRef.current = []; // Clear queue
};
```

---

## Testing Plan

### Backend Testing

✅ **Already Done:**
- Import verification
- Router registration
- Basic unit tests

⏳ **TODO:**
- WebSocket endpoint test (manual)
- Audio flow test (requires frontend)
- Function calling test
- Multi-client test

### Frontend Testing

⏳ **TODO:**
- WebSocket connection
- Audio capture (getUserMedia)
- PCM16 encoding
- Audio playback
- Mute/unmute controls
- Session start/stop
- Mobile compatibility

### End-to-End Testing

⏳ **TODO:**
- Voice quality verification
- Latency measurement (<1s target)
- Function call execution
- Event persistence
- Multi-device testing
- Mobile testing (Android/iOS)

---

## Benefits Summary

### vs Custom WebRTC (Our Previous Attempt)

| Aspect | Custom WebRTC | Pipecat WebSocket |
|--------|---------------|-------------------|
| **Backend Lines** | 584 | 428 (-27%) |
| **Frontend Lines** | 768 | ~500 (-35%) |
| **External Deps** | None | None |
| **Complexity** | Very High | Medium |
| **WebRTC Features** | Yes | No |
| **Self-hosted** | Yes | Yes |
| **Cost** | $0 | $0 |
| **Pipecat Benefits** | No | Yes |

### vs Pipecat + Daily

| Aspect | Pipecat + Daily | Pipecat WebSocket |
|--------|-----------------|-------------------|
| **External Deps** | Daily.co | None |
| **Cost** | $0.004/min | $0 |
| **Self-hosted** | No | Yes |
| **Privacy** | Cloud routing | Local only |
| **WebRTC Features** | Yes | No |
| **Complexity** | Low | Low |
| **Pipecat Benefits** | Yes | Yes |

---

## Next Steps

### Immediate (Frontend Implementation)

1. **Create simplified VoiceAssistantWebSocket.js** (new file)
   - Start fresh with WebSocket-only code
   - ~500 lines total
   - Estimated time: 4-5 hours

2. **Add route in App.js**
   ```javascript
   <Route path="/voice-ws/:conversationId?" element={<VoiceAssistantWebSocket />} />
   ```

3. **Test on desktop**
   - Start backend: `uvicorn main:app --reload`
   - Open: `http://localhost:3000/voice-ws/test-123`
   - Test audio quality

4. **Test on mobile**
   - Open: `http://192.168.0.200:3000/voice-ws/test-123`
   - Test mobile microphone
   - Test mobile audio playback

### Short Term (Integration)

5. **Connect function handlers**
   - Integrate send_to_nested with existing WebSocket
   - Integrate send_to_claude_code with existing controller
   - Test function execution

6. **Production deployment**
   - Update nginx configuration (if needed)
   - Deploy to Jetson Nano
   - Test HTTPS WebSocket (wss://)

### Long Term (Enhancement)

7. **Multi-client support**
   - Room/session management
   - Multiple browsers connecting to same conversation
   - Audio mixing (if needed)

8. **Mobile optimization**
   - Battery usage optimization
   - Background audio support
   - Bluetooth headset support

9. **Monitoring & Analytics**
   - Latency metrics
   - Audio quality metrics
   - Error tracking

---

## File Structure

```
backend/
├── api/
│   ├── realtime_voice.py                  # Original WebSocket (legacy)
│   ├── realtime_voice_webrtc.py           # Custom WebRTC (deprecated)
│   ├── realtime_voice_pipecat.py          # Pipecat + Daily (deprecated)
│   └── realtime_voice_pipecat_ws.py       # NEW: Pipecat + WebSocket ✅
├── main.py                                 # Modified: Added WebSocket router ✅
└── requirements.txt                        # Modified: Added pipecat-ai[daily] ✅

frontend/src/features/voice/pages/
├── VoiceAssistant.js                      # Original (legacy)
├── VoiceAssistantModular.js               # Current working version
└── VoiceAssistantWebSocket.js             # TODO: New WebSocket version

docs/
├── PIPECAT_INTEGRATION_ANALYSIS.md        # Research document ✅
├── PIPECAT_BACKEND_MILESTONE.md           # Daily-based implementation ✅
├── TRANSPORT_OPTIONS_ANALYSIS.md          # Transport comparison ✅
└── PIPECAT_WEBSOCKET_PROGRESS.md          # This file ✅
```

---

## Decision Rationale

### Why WebSocket over WebRTC?

1. **Self-hosted requirement** - No external services (Daily.co)
2. **Simplicity** - WebSocket is much simpler than WebRTC
3. **Local network usage** - On home WiFi, don't need WebRTC features
4. **Pipecat benefits** - Get framework benefits without Daily dependency
5. **Zero cost** - No per-minute charges

### What We Give Up

- **No adaptive bitrate** - Not needed on local WiFi
- **No packet loss recovery** - WiFi is reliable enough
- **No STUN/TURN** - Not needed for local network
- **Manual multi-client** - Acceptable for home use

### What We Gain

- ✅ **Fully self-hosted** - Complete control
- ✅ **Zero cost** - No service fees
- ✅ **Privacy** - Audio never leaves your network
- ✅ **Simpler code** - 35% less frontend code
- ✅ **Pipecat benefits** - Function calling, pipeline, event handling

---

## Summary & Next Steps

### ✅ What's Complete (2025-12-03)

**Backend (100%):**
- ✅ Pipecat + FastAPI WebSocket controller (`realtime_voice_pipecat_ws.py`)
- ✅ WebSocket endpoint at `/api/realtime/pipecat/ws/{conversation_id}`
- ✅ Function handlers (send_to_nested, send_to_claude_code, pause, reset)
- ✅ Event recording to SQLite (conversation store)
- ✅ Session management endpoints
- ✅ Router registered in `main.py`
- ✅ Python syntax validated

**Frontend (100%):**
- ✅ WebSocket voice component (`VoiceAssistantWebSocket.js`)
- ✅ Simple WebSocket connection (no WebRTC)
- ✅ Audio capture with getUserMedia (24kHz mono)
- ✅ PCM16 encoding/decoding helpers
- ✅ Audio playback queue
- ✅ Mute/unmute controls
- ✅ Session management (start/stop)
- ✅ Routes added to `App.js` (`/voice-ws/:conversationId`)
- ✅ Integration with nested team and Claude Code WebSockets
- ✅ Responsive layout (reuses existing layout components)

### ⏳ What Remains (Testing & Deployment)

**Testing (Estimated 2-3 hours):**
1. **Install dependencies:**
   ```bash
   # Backend (laptop - for development)
   cd /home/rodrigo/agentic/backend
   source venv/bin/activate
   pip install -r requirements.txt

   # Frontend (laptop - for development)
   cd /home/rodrigo/agentic/frontend
   npm install
   ```

2. **Test desktop:**
   ```bash
   # Terminal 1: Start backend
   cd /home/rodrigo/agentic/backend
   uvicorn main:app --reload

   # Terminal 2: Start frontend
   cd /home/rodrigo/agentic/frontend
   npm start

   # Browser: http://localhost:3000/voice-ws/test-123
   ```

3. **Test audio quality:**
   - Microphone capture works
   - Speech is transmitted to backend
   - OpenAI responds with audio
   - Audio playback is smooth (no stuttering)

4. **Test function calling:**
   - Say: "Search for information about Pipecat"
   - Verify: send_to_nested is called
   - Say: "Add a new feature to the voice page"
   - Verify: send_to_claude_code is called

5. **Test mobile (if possible):**
   - Open on smartphone: `http://[laptop-ip]:3000/voice-ws/test-123`
   - Verify mobile microphone and speaker work

**Deployment to Jetson (Estimated 1-2 hours):**
1. **Deploy backend:**
   ```bash
   ssh rodrigo@192.168.0.200
   cd ~/agentic
   git pull
   sudo systemctl restart agentic-backend
   ```

2. **Deploy frontend:**
   ```bash
   cd ~/agentic/frontend
   npm run build
   sudo kill -HUP $(cat ~/nginx.pid)
   ```

3. **Test production:**
   - Open: `https://192.168.0.200/voice-ws/test-123`
   - Verify HTTPS WebSocket (wss://) works
   - Verify audio quality on Jetson

### 📊 Benefits Achieved

| Aspect | Custom WebRTC | Pipecat WebSocket | Improvement |
|--------|---------------|-------------------|-------------|
| **Backend Lines** | 584 | 428 | -27% |
| **Frontend Lines** | 768 | 570 | -26% |
| **External Deps** | None | None | ✅ Same |
| **Complexity** | Very High | Medium | ✅ Simpler |
| **Self-hosted** | Yes | Yes | ✅ Same |
| **Cost** | $0 | $0 | ✅ Same |
| **Pipecat Benefits** | No | Yes | ✅ New |
| **Function Calling** | Manual | Built-in | ✅ Easier |
| **Event Handling** | Custom | Framework | ✅ Cleaner |

### 🎯 How to Continue

When you're ready to test:

1. **Install dependencies** (if not already installed)
2. **Start backend:** `uvicorn main:app --reload`
3. **Start frontend:** `npm start`
4. **Open:** `http://localhost:3000/voice-ws/test-123`
5. **Test audio:** Click start, speak, verify response
6. **Test functions:** Ask it to search or modify code
7. **Deploy to Jetson** when ready

---

**Last Updated:** 2025-12-03
**Status:** ✅ Backend complete, ✅ Frontend complete, ⏳ Testing pending
**Total Implementation Time:** ~2 hours (much faster than estimated 4-5 hours!)
**Next Action:** Test on desktop, then deploy to Jetson

