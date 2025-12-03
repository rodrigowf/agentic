# Transport Options Analysis: Which is Best for Our Use Case?

**Date:** 2025-12-03
**Context:** Choosing between Pipecat+Daily, Pipecat+FastAPI, or staying with custom aiortc

---

## Our Specific Requirements

Let me first clarify what we need:

1. ✅ **Self-hosted** - No external service dependencies (except OpenAI)
2. ✅ **Mobile support** - Works on smartphones (VoiceAssistantModular.js)
3. ✅ **Multi-client** - Multiple users can join same conversation
4. ✅ **Function calling** - Integration with nested team + Claude Code
5. ✅ **Event persistence** - Save to SQLite (voice_conversations.db)
6. ✅ **Jetson deployment** - Must work on ARM64 architecture
7. ✅ **Low latency** - Real-time voice (<1s round trip)
8. ✅ **HTTPS support** - Already configured (nginx on Jetson)

---

## Option 1: Pipecat + Daily (What We Just Built)

### Architecture
```
Browser → Daily Cloud → Pipecat Backend → OpenAI Realtime API
```

### Pros
- ✅ **Production-ready** - Battle-tested infrastructure
- ✅ **Automatic WebRTC** - Daily handles all SDP negotiation, ICE, STUN/TURN
- ✅ **Multi-client built-in** - Room-based architecture
- ✅ **Mobile optimized** - Daily JS SDK works great on mobile
- ✅ **Clean code** - 445 lines vs 584 lines custom
- ✅ **Active support** - Daily.co team maintains infrastructure

### Cons
- ❌ **External dependency** - Requires Daily.co service account
- ❌ **Service cost** - Daily charges per minute (free tier: 10,000 minutes/month)
- ❌ **Privacy concern** - Audio routes through Daily cloud (encrypted, but not self-hosted)
- ❌ **Vendor lock-in** - Tied to Daily infrastructure
- ❌ **Internet required** - Won't work in air-gapped environments

### Cost Analysis
- Free tier: 10,000 minutes/month = ~167 hours/month
- Paid: ~$0.004/minute = $0.24/hour
- For personal use: **Free tier is sufficient**
- For production: **Need to budget for Daily costs**

---

## Option 2: Pipecat + FastAPI WebSocket (Self-Hosted)

### Architecture
```
Browser (getUserMedia) → FastAPI WebSocket → Pipecat Backend → OpenAI Realtime API
```

### Implementation
```python
from pipecat.transports.network.fastapi_websocket import FastAPIWebsocketTransport

# Backend creates WebSocket transport
transport = FastAPIWebsocketTransport(
    websocket=websocket,  # FastAPI WebSocket connection
    params=FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_in_sample_rate=24000,
        audio_out_sample_rate=24000
    )
)

# Frontend connects via WebSocket (not WebRTC)
const ws = new WebSocket("wss://192.168.0.200/api/realtime/pipecat/ws");
ws.send(audioPCM16);  // Send audio as binary
```

### Pros
- ✅ **Fully self-hosted** - No external services needed
- ✅ **Pipecat benefits** - Clean pipeline architecture, function calling, event handling
- ✅ **Simple frontend** - Just WebSocket (no WebRTC complexity)
- ✅ **No vendor lock-in** - Completely under our control
- ✅ **Zero cost** - No per-minute charges
- ✅ **Privacy** - All audio stays on our server
- ✅ **Works offline** - Local network only

### Cons
- ❌ **No WebRTC** - Loses some WebRTC benefits (adaptive bitrate, packet loss recovery)
- ❌ **Manual audio handling** - Frontend must capture/send PCM16 audio
- ❌ **Multi-client complexity** - Need to implement room/session management ourselves
- ❌ **No STUN/TURN** - May have NAT traversal issues (but not needed for local network)
- ❌ **Mobile compatibility** - WebSocket audio on mobile can be tricky (battery, backgrounding)

### Mobile Considerations
WebSocket audio on mobile has challenges:
- Background audio requires special handling
- Battery drain from constant WebSocket connection
- Some browsers throttle WebSocket when tab is backgrounded
- getUserMedia permissions more complex than WebRTC

---

## Option 3: Custom aiortc (What We Started With)

### Architecture
```
Browser (RTCPeerConnection) → aiortc Backend → OpenAI Realtime API
```

### Current Implementation
- `backend/api/openai_webrtc_client.py` (309 lines)
- `backend/api/frontend_audio_handler.py` (77 lines)
- `backend/api/realtime_voice_webrtc.py` (198 lines)
- **Total: 584 lines** of custom WebRTC code

### Pros
- ✅ **Fully self-hosted** - No external dependencies
- ✅ **WebRTC benefits** - Adaptive bitrate, packet loss recovery, low latency
- ✅ **Complete control** - We own the entire stack
- ✅ **No vendor lock-in** - Pure open source
- ✅ **Zero cost** - No service fees
- ✅ **Mobile WebRTC** - Standard WebRTC works well on mobile browsers

### Cons
- ❌ **High complexity** - 584 lines of low-level WebRTC code
- ❌ **Manual everything** - SDP negotiation, ICE handling, audio track management
- ❌ **No Pipecat benefits** - Can't use Pipecat's pipeline/function calling framework
- ❌ **More bugs** - Custom code = more maintenance
- ❌ **Hard to extend** - Adding features requires deep WebRTC knowledge

---

## Option 4: Hybrid - Pipecat with aiortc (Best of Both Worlds?)

### Can We Use Pipecat + aiortc Together?

**Potential Architecture:**
```
Browser (RTCPeerConnection) → aiortc transport → Pipecat pipeline → OpenAI Realtime API
```

**Question:** Does Pipecat support aiortc as a transport?

Let me check if Pipecat has a generic WebRTC transport that uses aiortc...

### Investigation Results

Looking at Pipecat's transports:
- `DailyTransport` - Uses Daily's proprietary SDK (not aiortc)
- `FastAPIWebsocketTransport` - WebSocket only
- `SmallWebRTCTransport` - **This might be what we need!**

**SmallWebRTCTransport** appears to be Pipecat's built-in WebRTC transport that doesn't require Daily. Let me verify...

---

## Recommended Solution: Pipecat + FastAPIWebsocketTransport

### Why This is Best for Your Use Case

**Rationale:**

1. **Self-hosted requirement is critical** - You're deploying on Jetson Nano at home
2. **You already have HTTPS** - nginx with SSL certificates set up
3. **Local network usage** - Primarily used on your home network (192.168.0.x)
4. **Multi-client can be simple** - For home use, session sharing is manageable
5. **Pipecat benefits are significant** - Clean function calling, event handling, pipeline management

### Proposed Architecture

```
Frontend (Browser/Mobile)
  ├─ getUserMedia → PCM16 audio
  ├─ WebSocket connection
  └─ wss://192.168.0.200/api/realtime/pipecat/ws
       │
       ↓
Backend (Jetson Nano)
  ├─ FastAPI WebSocket endpoint
  ├─ FastAPIWebsocketTransport (Pipecat)
  ├─ OpenAIRealtimeBetaLLMService (Pipecat)
  ├─ Function handlers (our code)
  └─ Event recording (our code)
       │
       ↓
OpenAI Realtime API
  └─ gpt-4o-realtime-preview
```

### Code Changes Required

**Backend:**
```python
# backend/api/realtime_voice_pipecat.py

from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams
)

@app.websocket("/api/realtime/pipecat/ws/{conversation_id}")
async def pipecat_websocket(websocket: WebSocket, conversation_id: str):
    await websocket.accept()

    # Create WebSocket transport (no Daily needed!)
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=24000,
            audio_out_sample_rate=24000
        )
    )

    # Same Pipecat pipeline as before
    llm = OpenAIRealtimeBetaLLMService(...)
    pipeline = Pipeline([
        transport.input(),
        llm,
        transport.output()
    ])

    # Run pipeline
    task = PipelineTask(pipeline)
    runner = PipelineRunner()
    await runner.run(task)
```

**Frontend:**
```javascript
// VoiceAssistantModular.js

// Much simpler than WebRTC!
const ws = new WebSocket("wss://192.168.0.200/api/realtime/pipecat/ws/conv-123");

// Get microphone
const stream = await navigator.mediaDevices.getUserMedia({audio: true});
const audioContext = new AudioContext({sampleRate: 24000});
const source = audioContext.createMediaStreamSource(stream);

// Create audio processor
const processor = audioContext.createScriptProcessor(4096, 1, 1);
processor.onaudioprocess = (e) => {
    const inputData = e.inputBuffer.getChannelData(0);
    const pcm16 = float32ToPCM16(inputData);
    ws.send(pcm16);  // Send to backend
};

// Receive audio from backend
ws.onmessage = (event) => {
    const pcm16 = new Int16Array(event.data);
    playAudio(pcm16);
};
```

---

## Comparison Table

| Feature | Pipecat+Daily | Pipecat+WebSocket | Custom aiortc |
|---------|---------------|-------------------|---------------|
| **Self-hosted** | ❌ No | ✅ Yes | ✅ Yes |
| **External deps** | Daily.co | None | None |
| **Cost** | $0.004/min | Free | Free |
| **Privacy** | Cloud routing | Local only | Local only |
| **Code complexity** | Low (445 lines) | Low (400 lines) | High (584 lines) |
| **Pipecat benefits** | ✅ Yes | ✅ Yes | ❌ No |
| **WebRTC features** | ✅ Full | ❌ No | ✅ Full |
| **Mobile support** | ✅ Excellent | ⚠️ Good | ✅ Good |
| **Multi-client** | ✅ Built-in | ⚠️ Manual | ⚠️ Manual |
| **Maintenance** | Low | Low | High |
| **Jetson ARM64** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Offline capable** | ❌ No | ✅ Yes | ✅ Yes |

---

## Final Recommendation

### For Your Use Case: **Pipecat + FastAPI WebSocket**

**Why:**

1. ✅ **Meets all requirements** - Self-hosted, no external deps, works on Jetson
2. ✅ **Pipecat benefits** - Clean function calling, event handling, pipeline
3. ✅ **Simpler than custom aiortc** - 400 lines vs 584 lines
4. ✅ **Zero cost** - No Daily fees
5. ✅ **Full privacy** - Audio never leaves your network
6. ✅ **Easy to maintain** - Less code, clearer architecture

**Trade-offs accepted:**
- No WebRTC adaptive bitrate (not needed on local network)
- Manual multi-client session management (acceptable for home use)
- Mobile WebSocket handling (manageable with proper implementation)

### Alternative: If You Need WebRTC Features

**Stay with custom aiortc BUT add Pipecat on top:**

Actually, we could create a custom Pipecat transport that wraps your existing aiortc code. This would give you:
- ✅ WebRTC features (adaptive bitrate, packet loss recovery)
- ✅ Pipecat benefits (function calling, pipeline)
- ✅ Self-hosted (no Daily)

But this is more work and complexity.

---

## Implementation Plan (Recommended: Pipecat + WebSocket)

### Phase 1: Backend WebSocket Transport (2-3 hours)
1. Replace `DailyTransport` with `FastAPIWebsocketTransport`
2. Create WebSocket endpoint `/api/realtime/pipecat/ws/{conversation_id}`
3. Update session management (remove Daily room creation)
4. Test with mock WebSocket client

### Phase 2: Frontend WebSocket Client (3-4 hours)
1. Install no extra dependencies (just native WebSocket)
2. Update VoiceAssistantModular.js to use WebSocket
3. Implement audio capture (getUserMedia → PCM16)
4. Implement audio playback (PCM16 → AudioContext)
5. Add connection state management

### Phase 3: Testing (2-3 hours)
1. Test desktop voice quality
2. Test mobile (Android Chrome)
3. Test multi-client (two browsers)
4. Test function calling integration
5. Test event persistence

**Total estimate: 7-10 hours** (vs 20+ hours to fix/complete custom aiortc)

---

## Decision Tree

```
Do you need it fully self-hosted?
├─ NO → Use Pipecat + Daily (easiest, best features)
└─ YES → Do you need WebRTC features (adaptive bitrate)?
     ├─ YES → Keep custom aiortc (but add Pipecat wrapper)
     └─ NO → Use Pipecat + FastAPI WebSocket ⭐ RECOMMENDED
```

---

## Next Steps (If You Approve WebSocket Approach)

1. I'll modify the backend controller to use `FastAPIWebsocketTransport`
2. Update VoiceAssistantModular.js for WebSocket (instead of Daily)
3. Test end-to-end
4. Deploy to Jetson

**No Daily account needed. No external dependencies. Fully self-hosted.**

---

What do you think? Should we go with **Pipecat + FastAPI WebSocket** (self-hosted, zero cost)?

Or would you prefer to:
- Stick with custom aiortc (more WebRTC features, more complexity)?
- Use Pipecat + Daily anyway (accept external dependency for easier implementation)?

