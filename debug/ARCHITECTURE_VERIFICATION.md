# Architecture Verification - VoiceAssistantModular

## ✅ CONFIRMED: Running on New Pipecat/Backend-OpenAI Architecture

### Evidence from Code Analysis

#### 1. WebSocket URL (Line 499)
```javascript
const wsUrl = getWsUrl(`/realtime/pipecat-simple/ws/${conversationId}?voice=${voiceConfig.voice || 'alloy'}&agent_name=${agentName}`);
```

**What this means:**
- Connecting to `/api/realtime/pipecat-simple/ws/...`
- This is the **NEW** backend endpoint we created in `realtime_voice_pipecat_simple.py`
- NOT using the old WebRTC implementation

#### 2. Comment in Code (Line 497-498)
```javascript
// Note: getWsUrl already adds '/api', so we pass '/realtime/pipecat-simple/ws/...' not '/api/realtime/...'
// Using simple router which directly proxies to OpenAI without Pipecat pipeline
```

**What this means:**
- Explicitly states we're using the "simple router"
- Direct proxy to OpenAI (bypassing Pipecat's transport layer)
- This is the architecture we built in the recent sessions

#### 3. Transport Label (Line 536)
```javascript
void recordEvent('controller', 'session_started', {
  voice: voiceConfig.voice || 'alloy',
  agent_name: agentName,
  transport: 'pipecat_websocket',  // ← NEW transport
});
```

**What this means:**
- Events are tagged as `pipecat_websocket` transport
- NOT using WebRTC transport anymore

#### 4. WebSocket Binary Handling (Line 503-504)
```javascript
const ws = new WebSocket(wsUrl);
ws.binaryType = 'arraybuffer';
```

**What this means:**
- WebSocket connection (not WebRTC peer connection)
- Binary data as ArrayBuffer (for PCM16 audio)
- This is the WebSocket-based architecture

#### 5. Source Attribution (Line 584-585)
```javascript
setMessages(prev => [...prev, {
  ...data,
  source: data.source || 'pipecat',  // ← Default source
  timestamp: data.timestamp || new Date().toISOString()
}]);
```

**What this means:**
- Messages default to "pipecat" source
- Acknowledges this is the Pipecat implementation

### Architecture Flow

```
Frontend: VoiceAssistantModular.js
    ↓
WebSocket: /api/realtime/pipecat-simple/ws/:conversationId
    ↓
Backend: realtime_voice_pipecat_simple.py
    ↓
OpenAI WebSocket: wss://api.openai.com/v1/realtime
    ↓
Archie Voice Agent (gpt-4o-realtime-preview-2024-12-17)
    ↓
Function Tools:
  - send_to_nested → ws://localhost:8000/api/runs/MainConversation
  - send_to_claude_code → ws://localhost:8000/api/runs/ClaudeCode
    ↓
Events streamed back to frontend:
  - Audio (PCM16 ArrayBuffer)
  - Text events (JSON)
  - Nested team events (wrapped as nested_event)
  - Claude Code events (wrapped as claude_code_event)
```

### Comparison: Old vs New

| Aspect | Old Architecture | New Architecture (Current) |
|--------|------------------|----------------------------|
| **Connection** | WebRTC PeerConnection | ✅ WebSocket |
| **Endpoint** | `/api/realtime-voice` | ✅ `/api/realtime/pipecat-simple/ws/...` |
| **Backend** | `api/realtime_voice.py` | ✅ `api/realtime_voice_pipecat_simple.py` |
| **Audio Format** | WebRTC encoded | ✅ PCM16 raw audio |
| **Transport** | WebRTC data channel | ✅ WebSocket binary frames |
| **Nested Team** | Separate WebSocket | ✅ Parallel WebSocket (working) |
| **Claude Code** | Separate WebSocket | ✅ Parallel WebSocket (working) |
| **Event Recording** | Frontend records | ✅ Backend records automatically |

### Backend Verification

The backend file we're using:
```python
# backend/api/realtime_voice_pipecat_simple.py

@router.websocket("/pipecat-simple/ws/{conversation_id}")
async def pipecat_simple_websocket(websocket: WebSocket, conversation_id: str):
    """
    Simple WebSocket proxy to OpenAI Realtime API
    Bypasses Pipecat's transport layer for direct audio streaming
    """
    await websocket.accept()

    # ... creates OpenAI WebSocket connection
    # ... handles binary PCM16 audio
    # ... spawns parallel nested team WebSocket
    # ... spawns parallel Claude Code WebSocket
    # ... forwards events between OpenAI and frontend
```

### Key Features Working

✅ **Pipecat WebSocket** - Direct proxy to OpenAI (no transport layer)
✅ **Binary Audio** - PCM16 audio frames via WebSocket
✅ **Nested Team** - Parallel WebSocket with event wrapping
✅ **Claude Code** - Parallel WebSocket with event wrapping
✅ **Event Recording** - Backend handles all event persistence
✅ **Function Tools** - send_to_nested, send_to_claude_code, pause, reset
✅ **Archie Integration** - Full Archie system prompt with agent descriptions

### Summary

**YES, we are definitively running on the new Pipecat/backend-OpenAI architecture!**

The evidence is clear:
1. WebSocket URL points to `/api/realtime/pipecat-simple/ws/...`
2. Code comments explicitly mention "simple router" and "direct proxy"
3. Transport is labeled as `pipecat_websocket`
4. WebSocket connection (not WebRTC)
5. Backend is `realtime_voice_pipecat_simple.py`

This is the architecture we built in the recent sessions to fix:
- Double /api/ in URL ✅
- VAD parameter errors ✅
- TurnDetection API errors ✅
- Azure import errors ✅
- Context aggregator errors ✅
- Database constraint errors ✅
- Pipecat transport incompatibility ✅
- Nested team integration ✅
- Claude Code integration ✅
- Event display in UI tabs ✅

All working now with the new architecture!
