# WebRTC Interactive Testing Guide

Complete guide for running and debugging interactive WebRTC voice sessions.

## Quick Start

### Option 1: Automated Setup (Single Terminal)

```bash
cd /home/rodrigo/agentic
export OPENAI_API_KEY=sk-proj-...  # Required
./start-webrtc-session.sh
```

This will:
- Start backend on port 8000
- Start frontend on port 3000
- Log to `/tmp/agentic-logs/backend.log` and `frontend.log`
- Open both in background
- Press Ctrl+C to stop both

### Option 2: Manual Setup (Two Terminals)

**Terminal 1 - Backend:**
```bash
cd /home/rodrigo/agentic
export OPENAI_API_KEY=sk-proj-...  # Required
./start-backend.sh
```

**Terminal 2 - Frontend:**
```bash
cd /home/rodrigo/agentic
./start-frontend.sh
```

### Option 3: Manual Commands (Full Control)

**Terminal 1 - Backend:**
```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
export OPENAI_API_KEY=sk-proj-...
export LOG_LEVEL=DEBUG  # Optional
uvicorn main:app --reload --host 0.0.0.0 --port 8000 2>&1 | tee /tmp/backend.log
```

**Terminal 2 - Frontend:**
```bash
cd /home/rodrigo/agentic/frontend
source ~/.nvm/nvm.sh && nvm use default
npm start 2>&1 | tee /tmp/frontend.log
```

## Using the Voice Interface

1. **Open Browser:**
   - Navigate to: `http://localhost:3000/agentic/voice`
   - Open DevTools console (F12) to see [WebRTC Bridge] logs

2. **Start Session:**
   - Click green "Start Session" button
   - Allow microphone access when prompted
   - Wait for "Connected" status

3. **Test Audio:**
   - Speak into microphone
   - Should see audio visualization (green bars)
   - OpenAI assistant responds (blue bars)

4. **Test Text:**
   - Type message in text input
   - Click "Send Text" or press Enter
   - Text sent via WebRTC data channel

5. **Monitor Logs:**
   - **Browser console:** Client-side WebRTC events
   - **Backend terminal:** Server-side WebRTC bridge logs
   - **OpenAI events:** Transcript deltas, audio chunks

## What to Watch For

### Browser Console Logs (DevTools)

```javascript
[WebRTC Bridge] Creating peer connection...
[WebRTC Bridge] Adding microphone track
[WebRTC Bridge] Creating SDP offer...
[WebRTC Bridge] Sending offer to backend...
[WebRTC Bridge] Received SDP answer
[WebRTC Bridge] Setting remote description
[WebRTC Bridge] ICE state: checking
[WebRTC Bridge] ICE state: connected
[WebRTC Bridge] Connection state: connected
[WebRTC Bridge] Received audio track
[WebRTC Bridge] Data channel opened
[WebRTC Bridge] Received message: {"type":"session.created",...}
```

### Backend Terminal Logs

```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
DEBUG:    POST /api/realtime/webrtc/bridge
INFO:     Creating WebRTC bridge session: conv-123
DEBUG:    Connecting to OpenAI Realtime API...
DEBUG:    OpenAI connection established
DEBUG:    Setting up browser peer connection
INFO:     ICE gathering state: complete
DEBUG:    Forwarding browser audio to OpenAI
DEBUG:    Forwarding OpenAI audio to browser
INFO:     Data channel opened: oai-events
DEBUG:    Received OpenAI event: session.created
DEBUG:    Received OpenAI event: response.audio_transcript.delta
```

### Key Events to Monitor

**WebRTC Connection States:**
- ICE state: `new → checking → connected → completed`
- Connection state: `new → connecting → connected`
- Data channel: `connecting → open`

**OpenAI Events:**
- `session.created` - Session initialized
- `input_audio_buffer.speech_started` - User speaking detected
- `input_audio_buffer.speech_stopped` - User stopped speaking
- `response.audio_transcript.delta` - Transcript chunks
- `response.audio.delta` - Audio response chunks
- `response.done` - Response completed

## Debugging Common Issues

### Issue: Microphone Not Working

**Symptoms:**
- No green audio bars
- "Microphone permission denied" in console

**Solutions:**
```bash
# Check browser permissions
# Chrome: chrome://settings/content/microphone
# Firefox: about:preferences#privacy

# Check system audio
pactl list sources  # Linux
system_profiler SPAudioDataType  # macOS
```

### Issue: No Audio from Assistant

**Symptoms:**
- User audio works, but no response
- Backend logs show OpenAI connection but no audio deltas

**Solutions:**
```bash
# Verify OPENAI_API_KEY
echo $OPENAI_API_KEY

# Check backend logs for errors
grep -i error /tmp/backend.log

# Test OpenAI API directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Issue: WebRTC Connection Fails

**Symptoms:**
- ICE state stuck at "checking"
- Connection state stuck at "connecting"
- Timeout errors in console

**Solutions:**
```bash
# Check firewall
sudo ufw status  # Linux
sudo pfctl -s all  # macOS

# Test STUN server
npm install -g stun-test
stun-test stun.l.google.com 19302

# Check backend is reachable
curl http://localhost:8000/api/agents
```

### Issue: Echo or Feedback

**Symptoms:**
- Hearing own voice back
- Multiple audio sources playing

**Solutions:**
```javascript
// Disable local audio playback in browser
const audioElement = document.getElementById('audio');
audioElement.muted = true;

// Or use headphones
```

## Advanced Debugging

### Enable Verbose Logging

**Backend:**
```python
# In main.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('aiortc').setLevel(logging.DEBUG)
logging.getLogger('openai').setLevel(logging.DEBUG)
```

**Frontend:**
```javascript
// In VoiceAssistantModular.js, enable all logs:
const DEBUG = true;
```

### Capture Network Traffic

**Chrome DevTools:**
1. Open DevTools (F12)
2. Go to Network tab
3. Filter: `WS` (WebSocket) or `Media` (WebRTC)
4. Click session to see frames

**tcpdump:**
```bash
# Capture WebRTC traffic
sudo tcpdump -i any -w /tmp/webrtc.pcap port 8000 or port 19302
wireshark /tmp/webrtc.pcap
```

### Analyze Audio Quality

**Browser Console:**
```javascript
// Get WebRTC stats
const stats = await pc.getStats();
stats.forEach(report => {
  if (report.type === 'inbound-rtp' && report.mediaType === 'audio') {
    console.log('Audio stats:', {
      packetsLost: report.packetsLost,
      jitter: report.jitter,
      bytesReceived: report.bytesReceived
    });
  }
});
```

**Backend Logs:**
```bash
# Check for audio frame issues
grep -E "AudioFrame|PCM|sample_rate" /tmp/backend.log
```

## Testing Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts and loads UI
- [ ] Browser requests microphone permission
- [ ] ICE connection reaches "connected"
- [ ] Green bars show when speaking
- [ ] OpenAI transcripts appear in logs
- [ ] Blue bars show assistant audio
- [ ] Text messages send via data channel
- [ ] No echo or feedback
- [ ] Session stops cleanly

## Log File Locations

```bash
# View logs
tail -f /tmp/agentic-logs/backend.log
tail -f /tmp/agentic-logs/frontend.log

# Or use original log paths
tail -f /tmp/backend.log
tail -f /tmp/frontend.log

# Search logs
grep -i webrtc /tmp/backend.log
grep -i error /tmp/backend.log
grep "ICE state" /tmp/backend.log
```

## Performance Monitoring

### Monitor Resource Usage

```bash
# CPU and memory
top -p $(pgrep -f uvicorn)
top -p $(pgrep -f node)

# Network bandwidth
iftop -i any -f "port 8000 or port 19302"
```

### Check Latency

```javascript
// In browser console
let start = Date.now();
// Speak something
// Wait for response
let end = Date.now();
console.log(`Latency: ${end - start}ms`);
```

## Clean Shutdown

```bash
# Stop services gracefully
pkill -f uvicorn
pkill -f "npm start"

# Or if using script
# Press Ctrl+C in terminal

# Verify stopped
ps aux | grep -E "(uvicorn|npm)"
```

## Additional Resources

- **Backend WebRTC Implementation:** `backend/api/realtime_voice_webrtc.py`
- **Frontend WebRTC Client:** `frontend/src/features/voice/pages/VoiceAssistantModular.js`
- **OpenAI WebRTC Client:** `backend/api/openai_webrtc_client.py`
- **Migration Guide:** `docs/webrtc-bridge-notes.md`
- **Test Suite:** `backend/tests/integration/test_backend_webrtc_integration.py`

## Quick Commands Reference

```bash
# Start everything
export OPENAI_API_KEY=sk-proj-...
./start-webrtc-session.sh

# Backend only
./start-backend.sh

# Frontend only
./start-frontend.sh

# Check status
curl http://localhost:8000/api/realtime/conversations

# Stop backend
pkill -f uvicorn

# Stop frontend
pkill -f "npm start"

# View logs
tail -f /tmp/agentic-logs/*.log

# Clear logs
rm /tmp/agentic-logs/*.log
```

## Troubleshooting Flow

```
Issue?
  ↓
Check browser console
  ↓ Errors?
  ├─ Yes → Check microphone permissions, WebRTC support
  └─ No → Check backend logs
      ↓ Errors?
      ├─ Yes → Check OPENAI_API_KEY, network, firewall
      └─ No → Check OpenAI status, test API directly
```

---

**Last Updated:** 2025-12-04
