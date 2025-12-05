# WebRTC Voice Architecture - Complete File List

**Date:** 2025-12-04
**Purpose:** Integration guide for the WebRTC voice assistant architecture

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Backend Files](#core-backend-files)
3. [Core Frontend Files](#core-frontend-files)
4. [Test Files](#test-files)
5. [Utility & Support Files](#utility--support-files)
6. [Dependencies](#dependencies)
7. [Integration Points](#integration-points)
8. [Deployment Files](#deployment-files)

---

## Architecture Overview

### High-Level Flow

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Browser   │ WebRTC  │   Backend    │ WebRTC  │   OpenAI    │
│  (React)    │◄───────►│  (aiortc)    │◄───────►│  Realtime   │
│             │         │              │         │     API     │
└─────────────┘         └──────────────┘         └─────────────┘
       │                       │
       │                       │
       ▼                       ▼
  WebSocket              Voice Store
  (Events)              (Transcripts)
```

### Key Features

- **Direct WebRTC Bridge:** Browser ↔ Backend ↔ OpenAI (no Pipecat dependency)
- **Real-time Audio:** PCM16 @ 48kHz, bidirectional streaming
- **Voice Activity Detection:** Server-side VAD by OpenAI
- **Input Transcription:** Whisper-1 transcribes user speech
- **Event Streaming:** WebSocket for UI updates
- **Conversation Storage:** SQLite database for transcripts and events

---

## Core Backend Files

### 1. WebRTC Controllers

| File | Purpose | Lines | Description |
|------|---------|-------|-------------|
| **`backend/api/realtime_voice_webrtc.py`** | Main WebRTC bridge controller | 440 | FastAPI endpoints for WebRTC signaling, bridge management, and audio streaming |
| **`backend/api/openai_webrtc_client.py`** | OpenAI WebRTC client | 380 | Manages WebRTC connection to OpenAI Realtime API using aiortc |

**Key Endpoints:**

```python
# realtime_voice_webrtc.py
POST   /api/realtime/webrtc/bridge/offer     # Browser sends SDP offer
DELETE /api/realtime/webrtc/bridge/{conv_id} # Stop session
POST   /api/realtime/webrtc/bridge/{conv_id}/text  # Send text to model
GET    /api/realtime/conversations            # List conversations
```

### 2. Conversation Store

| File | Purpose | Description |
|------|---------|-------------|
| **`backend/utils/voice_conversation_store.py`** | SQLite conversation store | Stores voice events, transcripts, and session metadata |

**Database Schema:**

```sql
conversations (id, name, created_at, updated_at, voice_model, metadata)
voice_events (id, conversation_id, timestamp, source, type, payload)
```

### 3. Legacy/Alternative Implementations (NOT ACTIVE)

These files exist but are **not part of the current WebRTC architecture**:

| File | Status | Notes |
|------|--------|-------|
| `backend/api/realtime_voice.py` | Legacy | Old WebSocket-based implementation |
| `backend/api/realtime_voice_pipecat.py` | Deprecated | Pipecat HTTP-based approach |
| `backend/api/realtime_voice_pipecat_ws.py` | Deprecated | Pipecat WebSocket approach |
| `backend/api/realtime_voice_pipecat_simple.py` | Deprecated | Simplified Pipecat version |
| `backend/api/webrtc_signaling.py` | Deprecated | Old signaling approach |

**Note:** Do NOT include these files when integrating the WebRTC architecture. They are kept for reference only.

---

## Core Frontend Files

### 1. Main Voice Pages

| File | Active? | Purpose |
|------|---------|---------|
| **`frontend/src/features/voice/pages/VoiceAssistantModular.js`** | ✅ YES | **Primary voice assistant page** (uses WebRTC) |
| `frontend/src/features/voice/pages/VoiceAssistant.js` | ❌ Legacy | Old implementation |
| `frontend/src/features/voice/pages/VoiceAssistantWebSocket.js` | ❌ Legacy | WebSocket-based version |
| **`frontend/src/features/voice/pages/MobileVoice.js`** | ✅ YES | Mobile-optimized voice interface |

**Primary URL:** `http://localhost:3000/agentic/voice`
**Mobile URL:** `http://localhost:3000/agentic/mobile-voice`

### 2. WebRTC Hooks (Core Logic)

| File | Purpose | Description |
|------|---------|-------------|
| **`frontend/src/features/voice/hooks/useBackendWebRTC.js`** | **PRIMARY WEBRTC HOOK** | Manages WebRTC connection with backend bridge |
| `frontend/src/features/voice/hooks/useOpenAIWebRTC.js` | Alternative | Direct browser→OpenAI (not used in current arch) |
| **`frontend/src/features/voice/hooks/useOpenAIEventHandler.js`** | Event processing | Handles OpenAI Realtime API events |
| **`frontend/src/features/voice/hooks/useConversationStore.js`** | State management | Manages conversation history in UI |
| **`frontend/src/features/voice/hooks/useVoiceSession.js`** | Session lifecycle | Coordinates session start/stop/cleanup |

**Key Hook:** `useBackendWebRTC.js` is the **heart of the WebRTC implementation**.

### 3. UI Components

| File | Purpose |
|------|---------|
| **`frontend/src/features/voice/components/VoiceControlPanel.js`** | Start/Stop session controls |
| **`frontend/src/features/voice/components/ConversationHistory.js`** | Display transcripts and events |
| **`frontend/src/features/voice/components/AudioVisualizer.js`** | Real-time audio visualization |
| `frontend/src/features/voice/components/VoiceSessionControls.js` | Session management UI |
| `frontend/src/features/voice/components/DesktopVoiceLayout.js` | Desktop layout wrapper |
| `frontend/src/features/voice/components/MobileVoiceLayout.js` | Mobile layout wrapper |

### 4. Deprecated Frontend Files (NOT ACTIVE)

| File | Status | Notes |
|------|--------|-------|
| `frontend/src/features/voice/hooks/usePipecatWebSocket.js` | Deprecated | Pipecat WebSocket connection |
| `frontend/src/features/voice/hooks/useMobileWebRTC.js` | Deprecated | Old mobile WebRTC approach |
| `frontend/src/features/voice/pages/VoiceDashboard*.js` | Deprecated | Old dashboard implementations |

---

## Test Files

### Unit Tests

| File | Tests | Description |
|------|-------|-------------|
| **`backend/tests/unit/test_openai_webrtc_client.py`** | OpenAI client | Tests WebRTC client connection, audio track, data channel |

### Integration Tests

| File | Tests | Description |
|------|-------|-------------|
| **`backend/tests/integration/test_backend_webrtc_integration.py`** | Full bridge flow | Tests browser→backend→OpenAI complete flow |

### Test Coverage

```bash
# Run all WebRTC tests
cd backend
pytest tests/unit/test_openai_webrtc_client.py -v
pytest tests/integration/test_backend_webrtc_integration.py -v

# Expected: All tests should pass with audio streaming verified
```

---

## Utility & Support Files

### Debug/Export Tools

| File | Purpose | Usage |
|------|---------|-------|
| **`debug/export_voice_conversations.py`** | Export conversations to JSON | `python3 debug/export_voice_conversations.py` |
| `debug/screenshot.js` | Take UI screenshots | `node debug/screenshot.js <url> [filename]` |

**Export Output:** `debug/db_exports/voice_conversations/*.json`

### Helper Scripts

| File | Purpose |
|------|---------|
| **`start-backend.sh`** | Start backend with logging |
| **`start-frontend.sh`** | Start frontend with nvm node |
| **`start-webrtc-session.sh`** | Complete session startup |

**Usage:**
```bash
# Terminal 1
./start-backend.sh

# Terminal 2
./start-frontend.sh

# Open: http://localhost:3000/agentic/voice
```

### Documentation

| File | Purpose |
|------|---------|
| **`INPUT_AUDIO_TRANSCRIPTION_FIX.md`** | Latest fix documentation |
| **`AUDIO_FIX_SUMMARY.md`** | Slow-motion audio fix |
| **`CRITICAL_FIX_APPLIED.md`** | Browser audio forwarding fix |
| **`WEBRTC_QUICK_START.md`** | 1-minute setup guide |
| **`INTERACTIVE_SESSION_GUIDE.md`** | Complete testing walkthrough |
| **`WEBRTC_COMMANDS.md`** | Command reference |
| `docs/WEBRTC_INTERACTIVE_TESTING.md` | Testing procedures |

---

## Dependencies

### Backend Requirements

```txt
# Core WebRTC
aiortc>=1.6.0
aiohttp>=3.9.0

# Audio processing
numpy>=1.24.0,<2.0  # Required by aiortc
av>=10.0.0          # PyAV for audio frame manipulation

# FastAPI
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Database
sqlalchemy>=2.0.0
```

**Install:**
```bash
cd backend
pip install -r requirements.txt
```

### Frontend Requirements

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "@mui/material": "^5.15.0",
    "axios": "^1.6.0"
  }
}
```

**Install:**
```bash
cd frontend
~/.nvm/versions/node/v22.21.1/bin/npm install
```

---

## Integration Points

### 1. Backend Integration

**File:** `backend/main.py`

**Lines 93-102:**
```python
try:
    from .api.realtime_voice_webrtc import router as webrtc_router
except ImportError:  # pragma: no cover
    try:
        from api.realtime_voice_webrtc import router as webrtc_router
    except ImportError:
        webrtc_router = None

if webrtc_router is not None:
    app.include_router(webrtc_router)
```

**What it does:**
- Imports WebRTC router
- Registers all WebRTC endpoints under `/api/realtime/`
- Gracefully handles missing module (for testing)

### 2. Frontend Routing

**File:** `frontend/src/App.js`

**Route configuration:**
```jsx
<Route path="/agentic/voice" element={<VoiceAssistantModular />} />
<Route path="/agentic/mobile-voice" element={<MobileVoice />} />
```

### 3. API Communication

**Frontend → Backend:**
```javascript
// 1. Start session with SDP offer
POST /api/realtime/webrtc/bridge/offer
{
  conversation_id: "uuid",
  offer: "SDP string",
  voice: "alloy",
  agent_name: "MainConversation"
}

// 2. Receive SDP answer
Response: { session_id: "...", answer: "SDP string" }

// 3. WebRTC audio flows automatically
// 4. Events stream via WebSocket (if enabled)

// 5. Stop session
DELETE /api/realtime/webrtc/bridge/{conversation_id}
```

### 4. Event Broadcasting

**Backend broadcasts to WebSocket clients:**

```python
# backend/api/realtime_voice_webrtc.py
await stream_manager.broadcast(
    conversation_id,
    {"type": "event", "event": event_record}
)
```

**Frontend listens:**
```javascript
// useConversationStore.js
socket.on('voice_event', (data) => {
  updateConversationHistory(data);
});
```

---

## Deployment Files

### Local Development

| File | Purpose |
|------|---------|
| `backend/.env` | Environment variables (OPENAI_API_KEY) |
| `frontend/.env` | Frontend config (optional) |

### Production (Jetson Nano)

| Component | Location |
|-----------|----------|
| Backend service | `systemctl status agentic-backend` |
| Frontend build | `/home/rodrigo/agentic/frontend/build/` |
| Nginx config | `/etc/nginx/sites-available/agentic` |
| Logs | `/tmp/agentic-logs/backend.log` |

**Systemd Service:**
```bash
# View service
sudo systemctl status agentic-backend

# Restart
sudo systemctl restart agentic-backend

# View logs
sudo journalctl -u agentic-backend -f
```

---

## File Checklist for Integration

### Essential Backend Files ✅

```
backend/
├── api/
│   ├── openai_webrtc_client.py        ← OpenAI WebRTC client
│   └── realtime_voice_webrtc.py       ← WebRTC bridge controller
├── utils/
│   └── voice_conversation_store.py    ← Conversation database
└── main.py                             ← Router registration
```

### Essential Frontend Files ✅

```
frontend/src/features/voice/
├── pages/
│   ├── VoiceAssistantModular.js       ← Main voice page
│   └── MobileVoice.js                  ← Mobile version
├── hooks/
│   ├── useBackendWebRTC.js            ← PRIMARY WebRTC hook
│   ├── useOpenAIEventHandler.js       ← Event processing
│   ├── useConversationStore.js        ← State management
│   └── useVoiceSession.js             ← Session lifecycle
└── components/
    ├── VoiceControlPanel.js           ← Session controls
    ├── ConversationHistory.js         ← Transcript display
    └── AudioVisualizer.js             ← Audio visualization
```

### Essential Tests ✅

```
backend/tests/
├── unit/
│   └── test_openai_webrtc_client.py
└── integration/
    └── test_backend_webrtc_integration.py
```

### Essential Utilities ✅

```
./
├── start-backend.sh                   ← Backend startup
├── start-frontend.sh                  ← Frontend startup
└── debug/
    └── export_voice_conversations.py  ← Export tool
```

---

## Migration from Legacy Systems

### Remove These Files (Deprecated)

If you're cleaning up the codebase, these files can be **safely removed**:

**Backend (Deprecated):**
```
backend/api/realtime_voice.py
backend/api/realtime_voice_pipecat.py
backend/api/realtime_voice_pipecat_ws.py
backend/api/realtime_voice_pipecat_simple.py
backend/api/webrtc_signaling.py
```

**Frontend (Deprecated):**
```
frontend/src/features/voice/pages/VoiceAssistant.js
frontend/src/features/voice/pages/VoiceAssistantWebSocket.js
frontend/src/features/voice/pages/VoiceDashboard.js
frontend/src/features/voice/pages/VoiceDashboardModular.js
frontend/src/features/voice/pages/VoiceDashboardWebSocket.js
frontend/src/features/voice/hooks/usePipecatWebSocket.js
frontend/src/features/voice/hooks/useMobileWebRTC.js
frontend/src/features/voice/hooks/useOpenAIWebRTC.js (unless doing direct browser→OpenAI)
```

**Why keep some alternative files?**
- `useOpenAIWebRTC.js` - May be useful for future direct browser→OpenAI experiments
- Legacy pages - Keep as reference until migration is complete

---

## Quick Integration Checklist

### For New Systems

- [ ] Copy **Backend Core Files** (3 files: `openai_webrtc_client.py`, `realtime_voice_webrtc.py`, `voice_conversation_store.py`)
- [ ] Copy **Frontend Core Files** (8 files: 1 page + 4 hooks + 3 components)
- [ ] Install **Dependencies** (`aiortc`, `aiohttp`, `av`, `numpy`)
- [ ] Register **WebRTC Router** in `main.py`
- [ ] Add **Frontend Routes** for `/agentic/voice`
- [ ] Configure **Environment Variables** (`.env` with `OPENAI_API_KEY`)
- [ ] Run **Tests** to verify integration
- [ ] Test **Live Session** with browser

### Verification Steps

```bash
# 1. Backend test
cd backend
pytest tests/integration/test_backend_webrtc_integration.py -v

# 2. Start services
./start-backend.sh  # Terminal 1
./start-frontend.sh # Terminal 2

# 3. Open browser
# URL: http://localhost:3000/agentic/voice

# 4. Test session
# - Click "Start Session"
# - Speak: "What is 2+2?"
# - Verify assistant responds
# - Stop session

# 5. Check transcripts
python3 debug/export_voice_conversations.py
# Verify user transcripts appear in JSON export
```

---

## Recent Fixes Applied

### Fix #1: Slow Motion Audio (FIXED)
- **File:** `backend/api/realtime_voice_webrtc.py:98-137`
- **Issue:** Audio played at 0.5x speed
- **Fix:** Used `AudioResampler` for stereo→mono conversion

### Fix #2: Browser Audio Not Reaching Backend (FIXED)
- **File:** `backend/api/realtime_voice_webrtc.py:199-210`
- **Issue:** `ontrack` event not firing
- **Fix:** Check transceivers after `setRemoteDescription()`

### Fix #3: Input Audio Transcription Missing (FIXED) ⭐ NEW
- **File:** `backend/api/openai_webrtc_client.py:134-158`
- **Issue:** No user transcripts, responses out of context
- **Fix:** Added `input_audio_transcription: { model: "whisper-1" }` + improved VAD settings

**Documentation:** See `INPUT_AUDIO_TRANSCRIPTION_FIX.md` for complete details.

---

## Support & References

### Documentation
- **Quick Start:** `WEBRTC_QUICK_START.md`
- **Interactive Testing:** `INTERACTIVE_SESSION_GUIDE.md`
- **Commands:** `WEBRTC_COMMANDS.md`
- **Latest Fix:** `INPUT_AUDIO_TRANSCRIPTION_FIX.md`

### API References
- **OpenAI Realtime API:** https://platform.openai.com/docs/guides/realtime
- **aiortc Documentation:** https://aiortc.readthedocs.io/
- **WebRTC API:** https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API

### Contact
- **Issues:** Check logs in `/tmp/agentic-logs/backend.log`
- **Testing:** Use `debug/export_voice_conversations.py` to inspect data
- **Screenshots:** Use `debug/screenshot.js` for UI debugging

---

**Last Updated:** 2025-12-04
**Architecture Version:** WebRTC Bridge v2 (Pure aiortc, no Pipecat)

---

**End of Document**
