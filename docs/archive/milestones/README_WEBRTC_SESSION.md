# WebRTC Voice Session - Complete Guide

Ready-to-use setup for driving interactive browser/mic sessions with full logging.

## Quick Reference

| Need | Use This |
|------|----------|
| **Start quickly** | `./start-backend.sh` + `./start-frontend.sh` |
| **Quick help** | [WEBRTC_QUICK_START.md](WEBRTC_QUICK_START.md) |
| **Full walkthrough** | [INTERACTIVE_SESSION_GUIDE.md](INTERACTIVE_SESSION_GUIDE.md) |
| **Testing guide** | [docs/WEBRTC_INTERACTIVE_TESTING.md](docs/WEBRTC_INTERACTIVE_TESTING.md) |
| **Flow diagram** | [docs/webrtc-session-flow.txt](docs/webrtc-session-flow.txt) |
| **Migration notes** | [docs/webrtc-bridge-notes.md](docs/webrtc-bridge-notes.md) |

## Two Terminal Setup (Recommended)

### Terminal 1 - Backend with Logs

```bash
cd /home/rodrigo/agentic
./start-backend.sh
```

**What you'll see:**
- ✓ Loaded environment from .env
- Backend starting on port 8000
- WebRTC bridge logs
- aiortc state changes
- OpenAI data channel events
- Audio frame forwarding

**Key logs to watch:**
```
INFO:     OpenAI WebRTC client connected
DEBUG:    [Browser → OpenAI] Received audio frame (480 samples)
DEBUG:    OpenAI event: response.audio_transcript.delta: "Hello"
DEBUG:    [OpenAI → Browser] Forwarding audio frame
```

### Terminal 2 - Frontend with Logs

```bash
cd /home/rodrigo/agentic
./start-frontend.sh
```

**What you'll see:**
- React dev server starting
- Webpack compilation
- Hot reload notifications
- Network requests

**Open in browser:**
- Main URL: http://localhost:3000/agentic/voice
- DevTools console: F12 → Console tab

**Key logs to watch (browser console):**
```javascript
[WebRTC Bridge] ICE state: connected
[WebRTC Bridge] Connection state: connected
[WebRTC Bridge] Data channel state: open
[WebRTC Bridge] Audio level: 0.42
```

## Using the Interface

1. **Click "Start Session"**
   - Microphone permission requested
   - Wait for "Connected" status

2. **Speak**
   - Green bars = your voice
   - Blue bars = assistant voice

3. **Type text**
   - Enter message in text field
   - Sent via WebRTC data channel

4. **Monitor**
   - Backend terminal: Server-side events
   - Frontend terminal: Build/network logs
   - Browser console: Client-side WebRTC

## Log File Locations

All logs are saved to `/tmp/agentic-logs/`:

```bash
# Backend logs (WebRTC, aiortc, OpenAI)
tail -f /tmp/agentic-logs/backend.log

# Frontend logs (React, webpack)
tail -f /tmp/agentic-logs/frontend.log

# Filter backend logs
grep -E "WebRTC|OpenAI" /tmp/agentic-logs/backend.log
grep "audio frame" /tmp/agentic-logs/backend.log
grep "error" /tmp/agentic-logs/backend.log -i
```

## Architecture Overview

```
Browser Microphone
    ↓ WebRTC audio track
Backend (aiortc)
    ↓ Forward audio frames
OpenAI Realtime API
    ↓ Process & respond
Backend (aiortc)
    ↓ WebRTC audio track
Browser Speakers
```

**Data channel (parallel):**
- Browser ↔ Backend: Session control
- Backend ↔ OpenAI: Events/transcript
- Backend ↔ SQLite: Conversation storage

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Backend controller** | `backend/api/realtime_voice_webrtc.py` | Manages WebRTC bridge sessions |
| **OpenAI client** | `backend/api/openai_webrtc_client.py` | Handles OpenAI WebRTC connection |
| **Frontend client** | `frontend/src/features/voice/pages/VoiceAssistantModular.js` | Browser WebRTC implementation |
| **Backend startup** | `start-backend.sh` | Launches backend with logging |
| **Frontend startup** | `start-frontend.sh` | Launches frontend with logging |

## Session Lifecycle

```
1. User clicks "Start Session"
   ↓
2. Browser gets microphone (getUserMedia)
   ↓
3. Browser creates SDP offer
   ↓
4. POST to backend: /api/realtime/webrtc/bridge
   ↓
5. Backend connects to OpenAI first
   ↓
6. Backend creates SDP answer
   ↓
7. Browser applies answer
   ↓
8. ICE negotiation (new → checking → connected)
   ↓
9. Connection established
   ↓
10. Audio flows bidirectionally
    ↓
11. Data channel opens (events/text)
    ↓
12. Session ready ✓
```

## Troubleshooting Quick Reference

| Issue | Symptom | Fix |
|-------|---------|-----|
| **No microphone** | Permission denied error | Allow in browser settings |
| **No audio response** | Silent assistant | Check OPENAI_API_KEY in .env |
| **Connection fails** | ICE state "failed" | Check firewall, port 8000 |
| **Backend error** | 500 response | Check backend terminal for stack trace |
| **Echo** | Hearing own voice | Use headphones |
| **High latency** | Slow responses | Check network, reduce WiFi congestion |

## Performance Monitoring

### Resource Usage
```bash
# CPU and memory
top -p $(pgrep -f uvicorn)
top -p $(pgrep -f node)

# Network bandwidth
iftop -i any -f "port 8000"
```

### WebRTC Stats (Browser Console)
```javascript
const stats = await window.peerConnection.getStats();
stats.forEach(report => {
  if (report.type === 'inbound-rtp') {
    console.log('Packets:', report.packetsReceived, 'Lost:', report.packetsLost);
  }
});
```

## Stop Services

```bash
# Press Ctrl+C in both terminals
# Or:
pkill -f uvicorn      # Stop backend
pkill -f "npm start"  # Stop frontend

# Verify stopped
ps aux | grep -E "(uvicorn|npm)" | grep -v grep
```

## Testing

### Unit Tests (No Network)
```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
pytest tests/unit/test_openai_webrtc_client.py -v
pytest tests/integration/test_backend_webrtc_integration.py -v
```

### Integration Tests
```bash
# All WebRTC tests
pytest tests/ -k "webrtc" -v
```

## Advanced Usage

### Debug Mode
```bash
# Backend with verbose logging
export LOG_LEVEL=DEBUG
export AIORTC_LOG_LEVEL=DEBUG
./start-backend.sh

# Frontend with source maps
GENERATE_SOURCEMAP=true npm start
```

### Custom Configuration
```bash
# Use different port
PORT=3001 npm start

# Use different backend URL
REACT_APP_BACKEND_URL=http://192.168.1.100:8000 npm start
```

### Database Queries
```bash
# Export conversations
python3 debug/export_voice_conversations.py

# View events
cat debug/db_exports/voice_conversations/*.json | jq '.events[] | select(.type == "response.audio_transcript.delta")'

# Check database
sqlite3 backend/voice_conversations.db "SELECT * FROM conversations LIMIT 5;"
```

## Documentation Map

```
├── README_WEBRTC_SESSION.md (this file)
│   Quick reference and overview
│
├── WEBRTC_QUICK_START.md
│   1-minute quick start guide
│
├── INTERACTIVE_SESSION_GUIDE.md
│   Complete walkthrough with examples
│
├── docs/WEBRTC_INTERACTIVE_TESTING.md
│   Comprehensive testing guide
│
├── docs/webrtc-session-flow.txt
│   Visual flow diagram
│
├── docs/webrtc-bridge-notes.md
│   Migration notes and architecture
│
└── CLAUDE.md
    Complete codebase guide (includes WebRTC section)
```

## Next Steps

1. **Start the services:**
   ```bash
   # Terminal 1
   ./start-backend.sh

   # Terminal 2
   ./start-frontend.sh
   ```

2. **Open browser:**
   - http://localhost:3000/agentic/voice
   - Press F12 for DevTools

3. **Start session and speak:**
   - Click green "Start Session"
   - Allow microphone
   - Say "Hello"

4. **Monitor logs:**
   - Watch both terminals
   - Check browser console
   - Tail log files if needed

5. **Read full guides:**
   - [INTERACTIVE_SESSION_GUIDE.md](INTERACTIVE_SESSION_GUIDE.md) for detailed walkthrough
   - [docs/WEBRTC_INTERACTIVE_TESTING.md](docs/WEBRTC_INTERACTIVE_TESTING.md) for testing

## Support

If you encounter issues:
1. Check terminal logs for errors
2. Check browser console for WebRTC state
3. Verify OPENAI_API_KEY is set
4. Review troubleshooting section in [INTERACTIVE_SESSION_GUIDE.md](INTERACTIVE_SESSION_GUIDE.md)

---

**Last Updated:** 2025-12-04
