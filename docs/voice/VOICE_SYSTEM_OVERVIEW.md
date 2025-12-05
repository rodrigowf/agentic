# Voice System Overview

**Last Updated:** 2025-12-05
**Architecture:** Pure WebRTC Bridge (no Pipecat dependency)
**Status:** Production-ready

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Key Features](#key-features)
5. [Integration Points](#integration-points)
6. [File Structure](#file-structure)
7. [Quick Links](#quick-links)

---

## Architecture Overview

### High-Level Architecture

```
┌──────────────┐         ┌───────────────────┐         ┌──────────────┐
│   Browser    │ WebRTC  │     Backend       │ WebRTC  │   OpenAI     │
│   (React)    │◄───────►│  (FastAPI+aiortc) │◄───────►│  Realtime    │
│              │         │                   │         │     API      │
└──────┬───────┘         └─────────┬─────────┘         └──────────────┘
       │                           │
       │ WebSocket                 │ WebSocket
       │ (events)                  ├───────────► Nested Agents
       │                           │
       ▼                           └───────────► Claude Code
   UI Updates
                                   ▼
                              SQLite Store
                           (Conversations +
                             Transcripts)
```

### Architecture Principles

**Backend-Controlled:**
- Backend owns both WebRTC connections
- Browser ↔ Backend ↔ OpenAI
- Centralized audio routing and orchestration

**Pure WebRTC:**
- No Pipecat dependency (migrated away Dec 2024)
- Direct aiortc implementation
- Efficient PCM16 audio streaming @ 48kHz

**Event-Driven:**
- Real-time event broadcasting via WebSocket
- SQLite persistence for conversation history
- UI updates streamed to frontend

---

## System Components

### Backend Components

#### 1. WebRTC Bridge Controller
**File:** [`backend/api/realtime_voice_webrtc.py`](../../backend/api/realtime_voice_webrtc.py)

**Purpose:** Main WebRTC bridge orchestrator

**Key Classes:**
- `BridgeSession` - Manages single browser ↔ OpenAI bridge
- `AudioFrameSourceTrack` - Streams assistant audio to browser
- Active bridges tracked per conversation ID

**Endpoints:**
```python
POST   /api/realtime/webrtc/bridge                      # Start session
DELETE /api/realtime/webrtc/bridge/{conversation_id}    # Stop session
POST   /api/realtime/webrtc/bridge/{conversation_id}/text        # Send text message
POST   /api/realtime/webrtc/bridge/{conversation_id}/commit      # Manual audio commit
POST   /api/realtime/webrtc/bridge/{conversation_id}/send-to-nested         # Send to nested agents
POST   /api/realtime/webrtc/bridge/{conversation_id}/send-to-claude-code    # Send to Claude Code
GET    /api/realtime/conversations                     # List conversations
```

#### 2. OpenAI WebRTC Client
**File:** [`backend/api/openai_webrtc_client.py`](../../backend/api/openai_webrtc_client.py)

**Purpose:** Manages WebRTC connection to OpenAI Realtime API

**Features:**
- ICE negotiation with OpenAI
- Audio frame normalization (PCM16, 48kHz)
- Data channel for events
- Function call handling
- Session configuration (voice, VAD, transcription)

**Key Methods:**
```python
async def connect()                              # Establish WebRTC connection
async def send_audio_frame(frame: AudioFrame)    # Send mic audio to OpenAI
async def send_text(text: str)                   # Send text message
async def send_function_call_result(...)         # Return tool execution results
async def commit_audio_buffer()                  # Manual VAD trigger
```

#### 3. Conversation Store
**File:** [`backend/utils/voice_conversation_store.py`](../../backend/utils/voice_conversation_store.py)

**Purpose:** SQLite persistence for voice conversations

**Database Schema:**
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    voice_model TEXT,
    metadata JSON
);

CREATE TABLE voice_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,
    timestamp TIMESTAMP,
    source TEXT,          -- 'voice', 'controller', 'nested_agent', 'claude_code'
    type TEXT,            -- OpenAI event types
    payload JSON,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

**Features:**
- Event persistence
- Conversation metadata
- Export to JSON
- Cleanup utilities

### Frontend Components

#### 1. Main Voice Page
**File:** [`frontend/src/features/voice/pages/VoiceAssistantModular.js`](../../frontend/src/features/voice/pages/VoiceAssistantModular.js)

**Purpose:** Primary voice assistant interface

**Features:**
- Session start/stop controls
- Microphone visualization
- Speaker visualization
- Conversation history display
- Text input for manual messages

#### 2. Backend WebRTC Hook
**File:** [`frontend/src/features/voice/hooks/useBackendWebRTC.js`](../../frontend/src/features/voice/hooks/useBackendWebRTC.js)

**Purpose:** Core WebRTC connection logic

**Responsibilities:**
- Create RTCPeerConnection
- Generate SDP offer
- Send to backend and apply answer
- Handle ICE state changes
- Attach microphone track
- Receive assistant audio track

#### 3. Event Handler Hook
**File:** [`frontend/src/features/voice/hooks/useOpenAIEventHandler.js`](../../frontend/src/features/voice/hooks/useOpenAIEventHandler.js)

**Purpose:** Process OpenAI Realtime API events

**Event Types Handled:**
- `session.created` - Session initialized
- `input_audio_buffer.speech_started` - User started speaking
- `input_audio_buffer.speech_stopped` - User stopped speaking
- `response.audio_transcript.delta` - Assistant transcript chunks
- `response.audio.delta` - Assistant audio chunks
- `response.function_call_arguments.done` - Tool call complete

#### 4. Supporting Hooks
- **`useConversationStore.js`** - Conversation state management
- **`useVoiceSession.js`** - Session lifecycle coordination

#### 5. UI Components
- **`VoiceControlPanel.js`** - Start/stop/mute controls
- **`ConversationHistory.js`** - Transcript and event display
- **`AudioVisualizer.js`** - Real-time waveform visualization
- **`DesktopVoiceLayout.js`** - Desktop responsive layout
- **`MobileVoiceLayout.js`** - Mobile-optimized layout (used by MobileVoice.js)

---

## Data Flow

### Session Startup Flow

```
1. User clicks "Start Session"
   ↓
2. Frontend: getUserMedia() → microphone stream
   ↓
3. Frontend: Create RTCPeerConnection
   ↓
4. Frontend: Add microphone track
   ↓
5. Frontend: Generate SDP offer
   ↓
6. Frontend: POST /api/realtime/webrtc/bridge
   {
     conversation_id: "uuid",
     offer: "SDP string",
     voice: "alloy",
     agent_name: "MainConversation",
     system_prompt: "..."
   }
   ↓
7. Backend: Create BridgeSession
   ↓
8. Backend: Connect to OpenAI first (pre-warm)
   ↓
9. Backend: Set up browser peer connection
   ↓
10. Backend: Create and set local description (answer)
   ↓
11. Backend: Return SDP answer
   ↓
12. Frontend: Apply remote description (answer)
   ↓
13. ICE negotiation (automatic)
   ↓
14. ✅ Audio flows bidirectionally
```

### Audio Flow (User → Assistant)

```
User speaks into microphone
   ↓
Browser captures PCM audio (getUserMedia)
   ↓
RTCPeerConnection sends to backend
   ↓
Backend receives AudioFrame
   ↓
Backend forwards to OpenAI WebRTC client
   ↓
OpenAI processes audio (Whisper transcription + VAD)
   ↓
OpenAI generates response (GPT-4 Realtime)
   ↓
OpenAI sends audio back via WebRTC
   ↓
Backend receives assistant AudioFrame
   ↓
Backend sends to browser via AudioFrameSourceTrack
   ↓
Browser plays audio via <audio> element
   ↓
User hears assistant response
```

### Event Flow

```
OpenAI generates event (e.g., transcript delta)
   ↓
Backend receives via data channel
   ↓
Backend stores in SQLite (voice_conversation_store)
   ↓
Backend broadcasts via WebSocket (stream_manager)
   ↓
Frontend receives WebSocket message
   ↓
Frontend updates UI (conversation history)
```

### Tool Execution Flow (Nested Agents Example)

```
User: "Create a weather app"
   ↓
OpenAI transcribes + decides to call send_to_nested
   ↓
Backend receives function_call event
   ↓
Backend sends message to nested agents WebSocket
   ↓
Nested agents process request (code generation, etc.)
   ↓
Nested agents send events back via WebSocket
   ↓
Backend formats events for voice
   ↓
Backend sends to OpenAI: "[TEAM Engineer] Creating weather app..."
   ↓
OpenAI narrates progress to user
   ↓
User hears: "The team is working on your weather app..."
```

---

## Key Features

### 1. Real-time Bidirectional Audio
- **Format:** PCM16, 48kHz, mono
- **Latency:** ~100-300ms (network dependent)
- **Quality:** High-fidelity voice

### 2. Server-Side Voice Activity Detection (VAD)
- **Provider:** OpenAI Realtime API
- **Configuration:**
  ```json
  {
    "type": "server_vad",
    "threshold": 0.5,
    "prefix_padding_ms": 300,
    "silence_duration_ms": 500
  }
  ```
- **Manual Mode:** Optional button-press mode (commit audio buffer)

### 3. Input Audio Transcription
- **Model:** Whisper-1
- **Accuracy:** High-quality speech-to-text
- **Storage:** Transcripts stored in conversation events
- **Configuration:**
  ```json
  {
    "input_audio_transcription": {
      "model": "whisper-1"
    }
  }
  ```

### 4. Tool Execution (5 Tools)

**Available Tools:**
1. **`send_to_nested`** - Send task to nested agents team
2. **`send_to_claude_code`** - Send code modification request
3. **`pause`** - Pause nested agents conversation
4. **reset`** - Reset nested agents state
5. **`pause_claude_code`** - Pause Claude Code execution

**Tool Flow:**
- OpenAI decides when to call tools
- Backend executes tool and returns result
- OpenAI narrates outcome to user

### 5. Event Persistence & Broadcasting
- **Storage:** SQLite database (voice_conversations.db)
- **Broadcasting:** WebSocket stream for real-time UI updates
- **Export:** JSON export utility (`debug/export_voice_conversations.py`)

### 6. Multiple Voice Models
- **Available:** alloy, echo, fable, onyx, nova, shimmer
- **Switchable:** Per-conversation configuration
- **Persistent:** Voice preference stored in conversation metadata

### 7. Mobile Support
- **Page:** `frontend/src/features/voice/pages/MobileVoice.js`
- **URL:** `http://localhost:3000/agentic/mobile-voice`
- **Requirements:** HTTPS for microphone access on mobile
- **Features:** Touch-optimized UI, fullscreen mode

---

## Integration Points

### Backend Integration

**File:** `backend/main.py`

```python
# Import WebRTC router
from api.realtime_voice_webrtc import router as webrtc_router

# Register routes
app.include_router(webrtc_router)
```

### Frontend Routing

**File:** `frontend/src/App.js`

```jsx
import VoiceAssistantModular from './features/voice/pages/VoiceAssistantModular';
import MobileVoice from './features/voice/pages/MobileVoice';

<Route path="/agentic/voice" element={<VoiceAssistantModular />} />
<Route path="/agentic/mobile-voice" element={<MobileVoice />} />
```

### WebSocket Integration

**Event Broadcasting:**
```python
# backend/api/realtime_voice_webrtc.py
from api.realtime_voice import stream_manager

await stream_manager.broadcast(
    conversation_id,
    {"type": "event", "event": event_record}
)
```

**Frontend Subscription:**
```javascript
// useConversationStore.js
socket.on('voice_event', (data) => {
  updateConversationHistory(data);
});
```

---

## File Structure

### Backend Files
```
backend/
├── api/
│   ├── realtime_voice_webrtc.py          # Main WebRTC bridge controller ⭐
│   ├── openai_webrtc_client.py           # OpenAI WebRTC client ⭐
│   └── realtime_voice.py                 # WebSocket stream manager (shared)
│
├── utils/
│   └── voice_conversation_store.py       # SQLite conversation store ⭐
│
└── tests/
    ├── unit/
    │   └── test_openai_webrtc_client.py  # Unit tests
    └── integration/
        └── test_backend_webrtc_integration.py  # Integration tests
```

### Frontend Files
```
frontend/src/features/voice/
├── pages/
│   ├── VoiceAssistantModular.js          # Main voice page ⭐
│   └── MobileVoice.js                     # Mobile version ⭐
│
├── hooks/
│   ├── useBackendWebRTC.js               # Core WebRTC logic ⭐
│   ├── useOpenAIEventHandler.js          # Event processing ⭐
│   ├── useConversationStore.js           # State management
│   └── useVoiceSession.js                # Session lifecycle
│
└── components/
    ├── VoiceControlPanel.js              # Session controls
    ├── ConversationHistory.js            # Transcript display
    ├── AudioVisualizer.js                # Waveform visualization
    ├── DesktopVoiceLayout.js             # Desktop layout
    └── MobileVoiceLayout.js              # Mobile layout
```

### Utility Files
```
debug/
└── export_voice_conversations.py         # Export conversations to JSON

Helper Scripts:
├── start-backend.sh                      # Start backend with logging
├── start-frontend.sh                     # Start frontend with nvm node
└── start-webrtc-session.sh              # Start both (automated)
```

⭐ = Core files essential to the architecture

---

## Quick Links

### Documentation
- **[Quick Start Guide](VOICE_QUICK_START.md)** - Get started in 5 minutes
- **[Interactive Testing Guide](VOICE_INTERACTIVE_GUIDE.md)** - Complete walkthrough
- **[Command Reference](VOICE_COMMANDS.md)** - Useful commands
- **[Troubleshooting Guide](VOICE_TROUBLESHOOTING.md)** - Debug common issues

### Technical Documentation
- **[Backend Implementation](technical/BACKEND_IMPLEMENTATION.md)** - Backend deep dive
- **[Frontend Implementation](technical/FRONTEND_IMPLEMENTATION.md)** - Frontend deep dive
- **[Nested Agents Integration](technical/NESTED_AGENTS_INTEGRATION.md)** - Agent orchestration
- **[Audio Fixes Log](technical/AUDIO_FIXES_LOG.md)** - Historical audio issues & fixes

### Related Guides
- **[Mobile Voice Guide](../guides/MOBILE_VOICE_GUIDE.md)** - Mobile-specific setup
- **[Deployment Guide](../deployment/JETSON_DEPLOYMENT_GUIDE.md)** - Production deployment

---

## Dependencies

### Backend Requirements
```txt
# Core WebRTC
aiortc>=1.6.0          # WebRTC implementation
av>=10.0.0             # Audio frame manipulation

# FastAPI
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Audio processing
numpy>=1.24.0,<2.0     # Required by aiortc

# Database
sqlalchemy>=2.0.0      # ORM for conversation store

# HTTP client
aiohttp>=3.9.0         # WebSocket client for nested agents
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

### Environment Variables
```bash
# Backend (.env)
OPENAI_API_KEY=sk-proj-...          # Required
VOICE_INPUT_GAIN=4.0                # Optional (mic gain boost)
VOICE_DEBUG_RECORD=1                # Optional (record mic to WAV)
BACKEND_WS_URL=ws://localhost:8000  # Optional (WebSocket base URL)
```

---

## URLs

### Local Development
- **Desktop Voice:** http://localhost:3000/agentic/voice
- **Mobile Voice:** http://localhost:3000/agentic/mobile-voice
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Production (Jetson Nano)
- **Desktop Voice:** https://192.168.0.200/agentic/voice
- **Mobile Voice:** https://192.168.0.200/agentic/mobile-voice
- **Backend API:** https://192.168.0.200/api/

---

## Recent Changes

### December 2024
- ✅ Migrated from Pipecat to pure WebRTC bridge
- ✅ Integrated nested agents + Claude Code via WebSocket
- ✅ Fixed audio sample rate issues (48kHz)
- ✅ Added Whisper-1 input transcription
- ✅ Improved VAD configuration
- ✅ Consolidated documentation

### November 2024
- Mobile voice interface
- HTTPS support for mobile WebRTC
- Audio visualization improvements
- Conversation export utility

---

**For quick setup, see:** [VOICE_QUICK_START.md](VOICE_QUICK_START.md)
**For troubleshooting, see:** [VOICE_TROUBLESHOOTING.md](VOICE_TROUBLESHOOTING.md)
**For technical details, see:** [technical/](technical/)

---

**Last Updated:** 2025-12-05
**Maintained by:** Agentic System Development Team
