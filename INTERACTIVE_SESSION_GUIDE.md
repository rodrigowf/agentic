# Interactive WebRTC Voice Session Guide

Complete walkthrough for starting and debugging WebRTC voice sessions from the command line.

## Prerequisites

- ✅ Python 3.12+ with venv activated
- ✅ Node.js 22.x via nvm
- ✅ OPENAI_API_KEY configured in `backend/.env`
- ✅ Backend dependencies installed: `aiortc>=1.6.0`, `numpy<2.0`
- ✅ Frontend dependencies installed: `npm install`

## Quick Start (Recommended)

### Two Terminal Setup

This gives you full visibility into both backend and frontend logs.

**Terminal 1 - Backend:**
```bash
cd /home/rodrigo/agentic
./start-backend.sh
```

Expected output:
```
✓ Loaded environment from .env
=== Backend Starting ===
URL: http://localhost:8000
WebRTC endpoint: POST /api/realtime/webrtc/bridge
Watch for: [WebRTC] [aiortc] [OpenAI] logs

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Terminal 2 - Frontend:**
```bash
cd /home/rodrigo/agentic
./start-frontend.sh
```

Expected output:
```
Now using node v22.21.1 (npm v10.9.4)
=== Frontend Starting ===
URL: http://localhost:3000/agentic/voice
Browser DevTools: Check console for [WebRTC Bridge] logs

Compiled successfully!

You can now view frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.1.100:3000
```

## Using the Voice Interface

### Step 1: Open Browser

Navigate to: **http://localhost:3000/agentic/voice**

You should see:
- Green "Start Session" button
- Microphone visualization (gray bars)
- Speaker visualization (gray bars)
- Text input field

### Step 2: Open DevTools

Press **F12** to open browser DevTools and go to **Console** tab.

You'll see logs like:
```
[WebRTC Bridge] Initializing...
PUBLIC_URL: /agentic
Location: http://localhost:3000/agentic/voice
```

### Step 3: Start Session

Click the **green "Start Session"** button.

**Browser will:**
1. Request microphone permission (allow it)
2. Create RTCPeerConnection
3. Generate SDP offer
4. Send to backend: `POST /api/realtime/webrtc/bridge`
5. Apply SDP answer
6. Wait for ICE connection

**Browser console logs:**
```javascript
[WebRTC Bridge] Creating peer connection...
[WebRTC Bridge] Microphone: MediaStream {id: "...", active: true}
[WebRTC Bridge] Adding microphone track
[WebRTC Bridge] Creating SDP offer...
[WebRTC Bridge] Offer created: v=0\r\no=- ...
[WebRTC Bridge] Sending offer to backend...
[WebRTC Bridge] Received SDP answer (length: 1234)
[WebRTC Bridge] Setting remote description
[WebRTC Bridge] ICE state: checking
[WebRTC Bridge] Connection state: connecting
[WebRTC Bridge] ICE state: connected
[WebRTC Bridge] Connection state: connected
[WebRTC Bridge] Received audio track: MediaStreamTrack {kind: "audio"}
[WebRTC Bridge] Data channel state: open
```

**Backend terminal logs:**
```
DEBUG:    POST /api/realtime/webrtc/bridge
INFO:     Creating WebRTC bridge session
DEBUG:    Connecting to OpenAI Realtime API...
INFO:     OpenAI WebRTC client connected
DEBUG:    Creating browser peer connection
DEBUG:    Adding outbound audio track for browser
INFO:     SDP offer set, creating answer
DEBUG:    ICE gathering complete
INFO:     SDP answer ready (1234 bytes)
DEBUG:    Starting audio forwarding tasks
DEBUG:    [Browser → OpenAI] Audio forwarding started
DEBUG:    [OpenAI → Browser] Audio forwarding started
INFO:     WebRTC bridge fully established
```

### Step 4: Test Voice

**Speak into your microphone:**
- Say: "Hello, can you hear me?"

**Watch browser:**
- Green bars should animate (your voice)
- Console shows: `[WebRTC Bridge] Audio level: 0.42`

**Watch backend terminal:**
```
DEBUG:    [Browser → OpenAI] Received audio frame (480 samples, 24000 Hz)
DEBUG:    OpenAI event: input_audio_buffer.speech_started
DEBUG:    OpenAI event: input_audio_buffer.committed
DEBUG:    OpenAI event: response.created
DEBUG:    OpenAI event: response.audio_transcript.delta: "Hello"
DEBUG:    OpenAI event: response.audio_transcript.delta: ", can"
DEBUG:    OpenAI event: response.audio_transcript.delta: " you hear"
DEBUG:    OpenAI event: response.audio_transcript.delta: " me?"
DEBUG:    OpenAI event: response.audio.delta (1024 bytes)
DEBUG:    [OpenAI → Browser] Forwarding audio frame (480 samples)
```

**Hear assistant response:**
- Blue bars should animate (assistant voice)
- Assistant says: "Yes, I can hear you. How can I help you today?"

### Step 5: Test Text Messages

**Type in text input:**
- "What is the weather like?"
- Press Enter or click "Send Text"

**Watch browser console:**
```javascript
[WebRTC Bridge] Sending text via data channel: "What is the weather like?"
[WebRTC Bridge] Data channel message sent
```

**Watch backend terminal:**
```
DEBUG:    Received data channel message: {"text":"What is the weather like?"}
DEBUG:    Creating OpenAI input_text event
DEBUG:    Sent input_text event to OpenAI
DEBUG:    OpenAI event: response.created
DEBUG:    OpenAI event: response.audio_transcript.delta: "I don't"
DEBUG:    OpenAI event: response.audio_transcript.delta: " have access"
...
```

### Step 6: Monitor Conversation

**Frontend displays:**
- Recent events in "Recent Activity" section
- Tool usage if assistant uses tools
- Real-time transcript

**Backend stores:**
- All events in SQLite: `backend/voice_conversations.db`
- Queryable via: `GET /api/realtime/conversations/{id}`

## What to Watch in Logs

### Critical Success Indicators

**Browser Console:**
```javascript
✓ [WebRTC Bridge] ICE state: connected
✓ [WebRTC Bridge] Connection state: connected
✓ [WebRTC Bridge] Data channel state: open
✓ [WebRTC Bridge] Received audio track
```

**Backend Terminal:**
```
✓ INFO: OpenAI WebRTC client connected
✓ INFO: SDP answer ready
✓ INFO: WebRTC bridge fully established
✓ DEBUG: [Browser → OpenAI] Audio forwarding started
✓ DEBUG: [OpenAI → Browser] Audio forwarding started
```

### Common Error Patterns

**❌ Microphone Permission Denied:**
```javascript
[WebRTC Bridge] Error: NotAllowedError: Permission denied
```
**Fix:** Allow microphone in browser settings, try different browser

**❌ OPENAI_API_KEY Missing:**
```
ERROR: OpenAI API key not configured
ERROR: openai.AuthenticationError: Invalid API key
```
**Fix:** Set in `backend/.env` or export manually

**❌ ICE Connection Fails:**
```javascript
[WebRTC Bridge] ICE state: failed
[WebRTC Bridge] Connection state: failed
```
**Fix:** Check firewall, verify STUN server reachable, check network

**❌ Backend Not Reachable:**
```javascript
[WebRTC Bridge] POST http://localhost:8000/api/realtime/webrtc/bridge net::ERR_CONNECTION_REFUSED
```
**Fix:** Start backend, check port 8000 not in use

## Advanced Monitoring

### Real-Time Log Filtering

**Backend - Show only WebRTC events:**
```bash
tail -f /tmp/agentic-logs/backend.log | grep -E "WebRTC|aiortc"
```

**Backend - Show only OpenAI events:**
```bash
tail -f /tmp/agentic-logs/backend.log | grep "OpenAI event"
```

**Backend - Show only audio frames:**
```bash
tail -f /tmp/agentic-logs/backend.log | grep -E "audio frame|Forwarding"
```

### WebRTC Stats in Browser

Open browser console and run:
```javascript
// Get peer connection stats
const pc = window.peerConnection; // If exposed globally
const stats = await pc.getStats();

stats.forEach(report => {
  if (report.type === 'inbound-rtp' && report.mediaType === 'audio') {
    console.log('Inbound Audio:', {
      packetsReceived: report.packetsReceived,
      packetsLost: report.packetsLost,
      jitter: report.jitter,
      bytesReceived: report.bytesReceived
    });
  }
  if (report.type === 'outbound-rtp' && report.mediaType === 'audio') {
    console.log('Outbound Audio:', {
      packetsSent: report.packetsSent,
      bytesSent: report.bytesSent
    });
  }
});
```

### Database Query for Events

```bash
# Export conversation events
cd /home/rodrigo/agentic
python3 debug/export_voice_conversations.py

# View JSON
cat debug/db_exports/voice_conversations/*.json | jq '.events[] | select(.type == "response.audio_transcript.delta")'
```

## Troubleshooting Decision Tree

```
Session won't start?
  ↓
Check browser console
  ↓
Microphone permission denied?
  ├─ Yes → Allow in browser settings
  └─ No → Check backend
      ↓
Backend reachable (curl http://localhost:8000/api/agents)?
  ├─ No → Start backend, check port
  └─ Yes → Check OPENAI_API_KEY
      ↓
API key valid (curl -H "Authorization: Bearer $KEY" https://api.openai.com/v1/models)?
  ├─ No → Update .env file
  └─ Yes → Check WebRTC connection
      ↓
ICE state "connected"?
  ├─ No → Check firewall, STUN server
  └─ Yes → Check audio flow
      ↓
Microphone bars active?
  ├─ No → Check mic permissions, hardware
  └─ Yes → Check OpenAI response
      ↓
Backend shows "response.audio.delta"?
  ├─ No → Check OpenAI logs for errors
  └─ Yes → Check speaker
      ↓
Blue bars active?
  ├─ No → Check audio element, browser audio
  └─ Yes → ✓ Working!
```

## Performance Tuning

### Reduce Latency

**Backend - Optimize audio forwarding:**
```python
# In openai_webrtc_client.py
# Increase frame rate (more frequent, smaller chunks)
FRAME_RATE = 50  # Default: 50 (20ms frames)
```

**Browser - Reduce buffering:**
```javascript
// In VoiceAssistantModular.js
audioElement.playbackRate = 1.0;  // Normal speed
// Avoid buffering delays
```

### Monitor Resource Usage

```bash
# CPU and memory
watch -n 1 'ps aux | grep -E "(uvicorn|node)" | grep -v grep'

# Network bandwidth
iftop -i any -f "port 8000"
```

## Clean Shutdown

**Stop backend:**
- Press **Ctrl+C** in Terminal 1
- Or: `pkill -f uvicorn`

**Stop frontend:**
- Press **Ctrl+C** in Terminal 2
- Or: `pkill -f "npm start"`

**Verify stopped:**
```bash
ps aux | grep -E "(uvicorn|npm start)" | grep -v grep
```

## Additional Resources

- **Quick Start:** [WEBRTC_QUICK_START.md](WEBRTC_QUICK_START.md)
- **Full Testing Guide:** [docs/WEBRTC_INTERACTIVE_TESTING.md](docs/WEBRTC_INTERACTIVE_TESTING.md)
- **Migration Notes:** [docs/webrtc-bridge-notes.md](docs/webrtc-bridge-notes.md)
- **Backend Implementation:** [backend/api/realtime_voice_webrtc.py](backend/api/realtime_voice_webrtc.py)
- **Frontend Client:** [frontend/src/features/voice/pages/VoiceAssistantModular.js](frontend/src/features/voice/pages/VoiceAssistantModular.js)

## Summary Checklist

- [ ] Backend started and shows "Uvicorn running"
- [ ] Frontend started and shows "Compiled successfully"
- [ ] Browser opened to http://localhost:3000/agentic/voice
- [ ] DevTools console open (F12)
- [ ] Microphone permission granted
- [ ] "Start Session" clicked
- [ ] ICE state "connected" in console
- [ ] Green bars show when speaking
- [ ] Backend shows audio frames forwarding
- [ ] OpenAI responses received
- [ ] Blue bars show assistant audio
- [ ] Assistant voice heard in speakers
- [ ] Text messages work via data channel

✅ **All working!**

---

**Last Updated:** 2025-12-04
