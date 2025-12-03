# Backend WebRTC Implementation - Testing Guide

**Date:** 2025-12-02
**Status:** Ready for Testing
**Implementation:** Phase 1-4 Complete

---

## Overview

This guide provides instructions for testing the backend-controlled WebRTC voice assistant implementation.

**Architecture:**
- Backend owns OpenAI Realtime API connection
- Frontend connects to backend via WebRTC data channel
- Function calls handled directly in backend
- Multi-client support with audio mixing

---

## Testing Checklist

### Phase 1: Unit Tests (Backend)

✅ **OpenAI WebRTC Client Tests** (10/10 passing)
```bash
cd backend
source venv/bin/activate
pytest tests/unit/test_openai_webrtc_client.py -v
```

**Tests:**
- AudioTrack initialization
- AudioTrack send/receive
- Client initialization
- Ephemeral token fetching
- Event handling (function calls, errors)
- Audio sending
- Function result sending
- Connection closing

✅ **Frontend Audio Handler Tests** (10/10 passing)
```bash
pytest tests/unit/test_frontend_audio_handler.py -v
```

**Tests:**
- Handler initialization
- Callback registration
- SDP offer/answer exchange
- Audio sending (open/closed channel)
- Control message sending
- Connection closing
- Data channel message handling

### Phase 2: Integration Tests (Backend)

✅ **WebRTC Integration Tests** (10/10 passing)
```bash
pytest tests/integration/test_backend_webrtc_integration.py -v
```

**Tests:**
- End-to-end audio track flow
- OpenAI client callbacks
- Frontend handler bidirectional audio
- Audio mixing (multiple streams, different lengths, empty streams)
- Session audio flow (frontend → OpenAI, OpenAI → frontend)
- Function call routing
- Multi-client broadcasting

### Phase 3: Manual Testing (End-to-End)

**Prerequisites:**
1. OpenAI API key configured in `.env`
2. Backend dependencies installed
3. Frontend dependencies installed

#### Step 1: Start Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

**Expected output:**
```
INFO:     Will watch for changes in these directories: ['/home/rodrigo/agentic/backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXXX]
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     WebRTC voice router mounted
```

#### Step 2: Start Frontend

```bash
cd frontend
npm start
```

**Expected:**
```
webpack compiled successfully
```

#### Step 3: Open Browser

Navigate to:
```
http://localhost:3000/voice-webrtc
```

**Expected UI:**
- Title: "Voice Assistant (Backend WebRTC)"
- Status: "disconnected"
- Button: "Start Session"

#### Step 4: Start Session

1. Click **"Start Session"**
2. Allow microphone access when prompted

**Expected:**
- Status changes: `disconnected` → `connecting` → `connected` → `ready`
- Session ID displayed
- Buttons: "Stop Session", "Unmute" (enabled when status = ready)

**Backend logs to verify:**
```
INFO:api.realtime_voice_webrtc:Created session {session_id}
INFO:api.openai_webrtc_client:Connecting to OpenAI Realtime API (model: gpt-4o-realtime-preview-2024-12-17)
INFO:api.openai_webrtc_client:Successfully connected to OpenAI
INFO:api.frontend_audio_handler:Handling SDP offer for session {session_id}
INFO:api.frontend_audio_handler:Data channel established: audio
INFO:api.frontend_audio_handler:SDP answer created
INFO:api.realtime_voice_webrtc:Frontend connected to session {session_id}
```

**Browser console to verify:**
```
Session created: {session_id}
WebRTC setup complete
Data channel opened
```

#### Step 5: Test Audio

1. Click **"Unmute"**
2. Say: **"Hello Archie"**
3. Wait for response

**Expected:**
- Audio is sent to backend (visible in backend logs if verbose)
- OpenAI processes audio
- Response audio plays in browser
- Voice says something like "Hello! How can I help you?"

**Troubleshooting:**
- If no response: Check backend logs for errors
- If no audio playback: Check browser console for audio errors
- If "connecting" timeout: Check OpenAI API key

#### Step 6: Test Function Call (Optional)

If function calling is configured:

1. Say: **"Send to nested team: Hello"**
2. Wait for backend to execute

**Expected backend logs:**
```
INFO:api.realtime_voice_webrtc:Function call: send_to_nested with args {'text': 'Hello'}
INFO:api.realtime_voice_webrtc:Nested team execution: Hello
```

#### Step 7: Stop Session

1. Click **"Stop Session"**

**Expected:**
- Data channel closes
- Peer connection closes
- Microphone stops
- Status: "disconnected"

**Backend logs:**
```
INFO:api.realtime_voice_webrtc:Closed session {session_id}
INFO:api.openai_webrtc_client:Closed OpenAI connection
INFO:api.frontend_audio_handler:Closed frontend connection for session {session_id}
```

### Phase 4: Multi-Client Testing

#### Test Multi-Device Audio

**Setup:**
1. Open browser on desktop: `http://localhost:3000/voice-webrtc`
2. Open browser on mobile: `http://[YOUR_IP]:3000/voice-webrtc`
3. Start same session ID on both devices (requires code modification for shared sessions)

**Expected:**
- Audio from OpenAI broadcasts to both devices
- Audio mixing occurs if both devices send audio (currently only desktop → OpenAI)

**Note:** Full multi-client requires session sharing logic (not yet implemented in frontend).

---

## Test Results Summary

| Phase | Component | Tests | Status |
|-------|-----------|-------|--------|
| 1 | OpenAI WebRTC Client | 10/10 | ✅ Pass |
| 1 | Frontend Audio Handler | 10/10 | ✅ Pass |
| 2 | WebRTC Integration | 10/10 | ✅ Pass |
| 3 | Manual E2E | - | 🔄 Pending |
| 4 | Multi-Client | - | 🔄 Pending |

**Total:** 30/30 automated tests passing

---

## Known Issues

### Backend

1. **Function Call Integration:**
   - `execute_nested_team()` returns placeholder string
   - `execute_claude_code()` returns placeholder string
   - TODO: Integrate with existing WebSocket-based agents

2. **Audio Mixing:**
   - Multi-client audio mixing implemented but not tested end-to-end
   - Requires frontend session sharing to fully test

3. **Error Handling:**
   - Some error paths log but don't propagate to frontend
   - Could improve user-facing error messages

### Frontend

1. **Session Sharing:**
   - Each client creates independent session
   - No UI for joining existing session
   - Multi-device requires manual session ID sharing

2. **Audio Visualization:**
   - No waveform visualization
   - No mic level indicator
   - No speaker level indicator

3. **Connection Recovery:**
   - No automatic reconnection on disconnect
   - No ICE restart support

---

## Next Steps

### Immediate (Required for Production)

1. **Integrate Function Calls:**
   - Connect `execute_nested_team()` to existing nested team WebSocket
   - Connect `execute_claude_code()` to Claude Code controller
   - Test function calling end-to-end

2. **Manual E2E Testing:**
   - Complete Step 1-7 above
   - Document any issues
   - Verify audio quality

3. **Deploy to Jetson:**
   - Install dependencies on Jetson Nano
   - Update systemd service
   - Test on production server

### Future Enhancements

1. **Session Management:**
   - Frontend session list/join UI
   - Session persistence (Redis/DB)
   - Session cleanup on timeout

2. **Audio Enhancements:**
   - Visualizations (waveform, levels)
   - Recording capability
   - Playback controls

3. **Mobile Optimization:**
   - Mobile-specific UI (like MobileVoice.js)
   - Battery optimization
   - Bluetooth headset support

4. **Monitoring:**
   - Latency metrics
   - Audio quality metrics
   - Connection stability metrics

---

## Deployment Checklist

### Local Development

- [x] Install dependencies (`pip install -r requirements.txt`)
- [x] Configure OPENAI_API_KEY in `.env`
- [ ] Start backend (`uvicorn main:app --reload`)
- [ ] Start frontend (`npm start`)
- [ ] Test at `http://localhost:3000/voice-webrtc`

### Jetson Nano Production

- [ ] Update `requirements.txt` on Jetson
- [ ] Install aiortc, aiohttp, av via pip/conda
- [ ] Deploy backend code
- [ ] Restart `agentic-backend` service
- [ ] Deploy frontend build
- [ ] Reload nginx
- [ ] Test at `https://192.168.0.200/voice-webrtc`

---

## Support

**Documentation:**
- Implementation Guide: `docs/BACKEND_WEBRTC_IMPLEMENTATION_GUIDE.md`
- Testing Guide: `docs/BACKEND_WEBRTC_TESTING_GUIDE.md` (this file)

**Code Locations:**
- Backend OpenAI client: `backend/api/openai_webrtc_client.py`
- Backend frontend handler: `backend/api/frontend_audio_handler.py`
- Backend main controller: `backend/api/realtime_voice_webrtc.py`
- Frontend component: `frontend/src/features/voice/pages/VoiceAssistantWebRTC.js`

**Test Locations:**
- Unit tests: `backend/tests/unit/test_*_webrtc_*.py`
- Integration tests: `backend/tests/integration/test_backend_webrtc_integration.py`

---

**Last Updated:** 2025-12-02
**Status:** Implementation Complete, Testing Pending
