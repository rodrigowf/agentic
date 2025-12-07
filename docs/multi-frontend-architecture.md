# Multi-Frontend Architecture for Voice

The system solves the N:1 problem (multiple browser tabs → single OpenAI Realtime session) through a layered architecture. Here's how it works.

## The Core Challenge

OpenAI's Realtime API provides a single WebSocket connection with bidirectional audio. But we want:
- Multiple users/tabs to share one session (per conversation)
- Independent audio control per frontend
- Graceful handling of connects/disconnects without disrupting the session
- **Isolated conversations** - different conversation IDs get separate OpenAI sessions

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RealtimeSessionManager                                │
│              (One OpenAI session per conversation_id)                        │
│                                                                              │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐         │
│  │ conversation_id: │   │ conversation_id: │   │ conversation_id: │         │
│  │     "abc123"     │   │     "xyz789"     │   │     "def456"     │         │
│  │                  │   │                  │   │                  │         │
│  │  OpenAISession   │   │  OpenAISession   │   │  OpenAISession   │         │
│  │  (WebRTC→OpenAI) │   │  (WebRTC→OpenAI) │   │  (WebRTC→OpenAI) │         │
│  └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘         │
└───────────┼──────────────────────┼──────────────────────┼───────────────────┘
            │                      │                      │
            ▼                      ▼                      ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│BrowserConnectionMgr│  │BrowserConnectionMgr│  │BrowserConnectionMgr│
│  (N connections)   │  │  (N connections)   │  │  (N connections)   │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│ ┌───┐ ┌───┐ ┌───┐ │  │ ┌───┐ ┌───┐       │  │ ┌───┐             │
│ │Tab│ │Tab│ │Tab│ │  │ │Tab│ │Tab│       │  │ │Tab│             │
│ │ A │ │ B │ │ C │ │  │ │ X │ │ Y │       │  │ │ Z │             │
│ └───┘ └───┘ └───┘ │  │ └───┘ └───┘       │  │ └───┘             │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

## Key Components

### 1. RealtimeSessionManager - Per-Conversation Singleton

Located in `backend/api/realtime_session_manager.py`, maintains **one OpenAI session per conversation_id**:

```python
class RealtimeSessionManager:
    _sessions: Dict[str, OpenAISession] = {}  # conversation_id → OpenAISession

    async def get_or_create_session(self, conversation_id, ...) -> OpenAISession:
        # Returns existing session or creates new one
        pass
```

This ensures:
- Conversations are **isolated** (no context leaking between them)
- Sessions persist even when all frontends disconnect
- Only closes when explicitly stopped

### 2. BrowserConnectionManager - The Multiplexer

Located in `backend/api/browser_connection_manager.py`, manages N frontend connections per conversation:

```python
class BrowserConnectionManager:
    _connections: Dict[str, BrowserConnection] = {}  # connection_id → BrowserConnection

    async def add_connection(self, offer_sdp) -> (connection_id, answer_sdp):
        # Add new browser WebRTC connection
        pass

    async def broadcast_audio(self, frame):
        # Send OpenAI audio to ALL connected browsers
        pass
```

### 3. Audio Flow Handling

**Inbound (Mic → OpenAI):**
- Each frontend's mic audio arrives via WebRTC
- BrowserConnectionManager receives frames via `on_browser_audio` callback
- Frames are forwarded to the shared OpenAI session

**Outbound (OpenAI → Speakers):**
- OpenAI sends assistant audio once
- OpenAISession calls `on_audio_callback`
- BrowserConnectionManager **broadcasts** to all connected frontends

### 4. Connection Lifecycle

**Connect (POST /api/realtime/webrtc/signal):**
```python
# 1. Get or create OpenAI session for this conversation
openai_session = await session_manager.get_or_create_session(conversation_id)

# 2. Get or create browser connection manager
browser_mgr = await get_or_create_manager(conversation_id)

# 3. Link them together
browser_mgr.on_browser_audio = openai_session.send_audio
openai_session.on_audio_callback = browser_mgr.broadcast_audio

# 4. Add this browser's WebRTC connection
connection_id, answer = await browser_mgr.add_connection(offer_sdp)

return { connection_id, answer }
```

**Disconnect (POST /api/realtime/webrtc/disconnect):**
```python
# Clean up just this browser connection
# OpenAI session stays alive for other browsers
await browser_mgr.remove_connection(connection_id)
```

**Stop Conversation (DELETE /api/realtime/webrtc/conversation/{id}):**
```python
# Close everything for this conversation
await browser_mgr.close_all()
await session_manager.close_session(conversation_id)
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/realtime/webrtc/signal` | POST | Connect browser, returns connection_id + SDP answer |
| `/api/realtime/webrtc/disconnect` | POST | Disconnect single browser (others stay connected) |
| `/api/realtime/webrtc/conversation/{id}` | DELETE | Stop entire conversation (all browsers + OpenAI) |
| `/api/realtime/webrtc/conversation/{id}/status` | GET | Get conversation status (browser count, etc.) |
| `/api/realtime/webrtc/conversation/{id}/text` | POST | Send text message |
| `/api/realtime/webrtc/conversation/{id}/commit` | POST | Manual VAD commit |

## Frontend Usage

```javascript
import { useBackendWebRTC } from './hooks/useBackendWebRTC';

function VoiceComponent() {
  const {
    connect,
    disconnect,
    stopConversation,
    isConnected,
    setAudioElement,
  } = useBackendWebRTC();

  // Connect this tab
  await connect({
    conversationId: 'my-conversation',
    voiceConfig: { voice: 'alloy' },
    audioStream: microphoneStream,
    onTrack: (evt) => { /* handle incoming audio */ },
  });

  // Disconnect just this tab (other tabs stay connected)
  await disconnect();

  // Stop entire conversation (all tabs + OpenAI)
  await stopConversation();
}
```

## Architectural Challenges Solved

| Challenge | Solution |
|-----------|----------|
| **Conversation isolation** | One OpenAI session per conversation_id |
| **Connection order matters** | Always establish OpenAI first, then browser connections |
| **Session persistence** | OpenAI session survives frontend disconnects |
| **Independent browser control** | Each browser has its own connection_id |
| **Resource cleanup** | Map-based tracking with unique IDs, graceful teardown |
| **Overlapping speech** | OpenAI's VAD handles multiple speakers naturally |
| **Broadcast efficiency** | Single OpenAI response → fan-out to all frontends |

## Why This Design?

1. **Conversation Isolation**: Different conversations have completely separate OpenAI sessions
2. **Decoupling**: Frontend lifecycle is independent from OpenAI session lifecycle
3. **Efficiency**: One OpenAI connection per conversation regardless of frontend count
4. **Resilience**: Tab crashes don't kill the session for others
5. **Simplicity**: Each layer has a single responsibility

## File Locations

| File | Purpose |
|------|---------|
| `backend/api/realtime_session_manager.py` | Per-conversation OpenAI session management |
| `backend/api/browser_connection_manager.py` | N browser connections per conversation |
| `backend/api/realtime_voice_webrtc.py` | API endpoints, links sessions and browsers |
| `backend/api/openai_webrtc_client.py` | OpenAI WebRTC client implementation |
| `frontend/src/features/voice/hooks/useBackendWebRTC.js` | Frontend WebRTC hook |
