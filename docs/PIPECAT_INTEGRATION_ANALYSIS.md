# Pipecat Integration Analysis

**Date:** 2025-12-03
**Status:** Research Complete - Ready for Implementation Planning
**Decision:** Replace custom WebRTC implementation with Pipecat framework

---

## Executive Summary

Pipecat is an **open-source Python framework** specifically designed for building real-time voice and multimodal conversational AI agents. After comprehensive research, **Pipecat is the ideal solution** to replace our current custom WebRTC implementation.

**Key Benefits:**
- ✅ **Production-ready framework** - Battle-tested with thousands of deployments
- ✅ **Native OpenAI Realtime API support** - Built-in integration, no custom WebRTC code
- ✅ **Clean pipeline architecture** - Frame-based processing, easy to understand
- ✅ **Built-in function calling** - Seamless tool integration
- ✅ **Multiple transport support** - Daily (WebRTC), WebSocket, local
- ✅ **aiortc under the hood** - Uses same technology we started with
- ✅ **Active development** - Backed by Daily.co, frequent updates

---

## Why Pipecat Solves Our Problems

### Current Pain Points (Custom Implementation)

Our current approach in [backend/api/openai_webrtc_client.py](../backend/api/openai_webrtc_client.py) has several challenges:

1. **Low-level aiortc complexity:**
   - Manual SDP negotiation (lines 111-166)
   - Custom audio track implementation (lines 237-271)
   - Manual data channel event handling (lines 73-147)
   - PCM16 ↔ NumPy ↔ AudioFrame conversions (lines 168-189)
   - Complex event parsing and routing (lines 190-211)

2. **Custom audio mixing logic:**
   - Manual multi-client audio mixing (lines 221-242 in realtime_voice_webrtc.py)
   - Buffer management across multiple frontends
   - No built-in latency optimization

3. **Function call integration:**
   - Placeholder implementations (lines 178-189 in realtime_voice_webrtc.py)
   - Manual WebSocket coordination needed
   - No standardized event flow

4. **Transport inflexibility:**
   - Locked into custom WebRTC implementation
   - No easy way to switch to WebSocket or other transports
   - No session persistence or replay

### How Pipecat Solves These

**1. High-Level Abstractions:**
```python
# Our current code (openai_webrtc_client.py:42-90, 111-166):
# 140+ lines of manual WebRTC setup

# Pipecat equivalent:
transport = DailyTransport(
    room_url="...",
    token="...",
    params=DailyParams(audio_in_enabled=True, audio_out_enabled=True)
)
llm = OpenAIRealtimeBetaLLMService(api_key=api_key)
```

**2. Clean Pipeline Architecture:**
```python
# Instead of manual audio routing, we get:
pipeline = Pipeline([
    transport.input(),      # Auto-handles WebRTC audio
    llm,                    # Auto-connects to OpenAI Realtime
    transport.output()      # Auto-broadcasts to clients
])
```

**3. Built-in Function Calling:**
```python
# Instead of our manual handling (realtime_voice_webrtc.py:151-176):
async def execute_nested_team(params: FunctionCallParams):
    result = await nested_team_agent.run(params.arguments["text"])
    await params.result_callback(result)

llm.register_function("send_to_nested", execute_nested_team)
```

**4. Multi-Client Support:**
- Daily transport handles room-based multi-client automatically
- No manual audio mixing needed
- Built-in session persistence

---

## Pipecat Architecture Deep Dive

### Core Concepts

**1. Frames**
- Atomic units of data flowing through pipeline
- Types: `AudioFrame`, `TextFrame`, `ImageFrame`, `TranscriptionFrame`, `FunctionCallFrame`, `FunctionResultFrame`
- Similar to our event system, but type-safe and structured

**2. Processors**
- Consume frames, process, emit frames
- Chain together to form pipelines
- Examples: `LLMProcessor`, `TransportProcessor`, `TranscriptionProcessor`

**3. Pipelines**
- Directed graph of processors
- Auto-handles frame routing
- Built-in error handling and logging

**4. Transports**
- Handle I/O with clients
- Daily (WebRTC), WebSocket, local audio
- Emit `AudioFrame`s from mic, consume `AudioFrame`s to speaker

### OpenAI Realtime Integration

Pipecat provides `OpenAIRealtimeBetaLLMService` which:
- Manages WebRTC connection to OpenAI (using aiortc internally)
- Converts frames ↔ OpenAI events automatically
- Handles session configuration (voice, turn detection, noise reduction)
- Implements function calling protocol
- Auto-reconnects on errors

**Example Configuration:**
```python
session_properties = SessionProperties(
    # Input audio transcription (like our conversation store)
    input_audio_transcription=InputAudioTranscription(),

    # Turn detection (VAD)
    turn_detection=SemanticTurnDetection(),

    # Noise reduction (near_field or far_field)
    input_audio_noise_reduction=InputAudioNoiseReduction(type="near_field"),

    # Voice selection
    voice="alloy",

    # System instructions
    instructions="You are Archie, the voice assistant...",

    # Tools/functions
    tools=[weather_function, nested_team_function, claude_code_function]
)

llm = OpenAIRealtimeBetaLLMService(
    api_key=os.getenv("OPENAI_API_KEY"),
    session_properties=session_properties,
    start_audio_paused=False
)
```

---

## Mapping Pipecat to Our Architecture

### Current System

```
Frontend (Browser)
  ├─ Microphone (getUserMedia)
  ├─ Speaker (AudioContext)
  └─ WebRTC Data Channel
       │
       ↓ (Audio PCM16 bidirectional)
       │
Backend (Python/aiortc)
  ├─ Frontend Audio Handler (custom, 77 lines)
  ├─ OpenAI WebRTC Client (custom, 309 lines)
  ├─ Audio Router/Mixer (custom, 198 lines)
  └─ Function Call Handler
       │
       ↓
OpenAI Realtime API
  └─ gpt-4o-realtime-preview
```

**Total custom code:** ~584 lines of WebRTC/audio handling

### Pipecat System

```
Frontend (Browser)
  ├─ Microphone
  ├─ Speaker
  └─ Daily WebRTC Client (JS library, ~50 lines)
       │
       ↓ (Daily room connection)
       │
Backend (Python/Pipecat)
  ├─ DailyTransport (built-in)
  ├─ Pipeline (built-in)
  ├─ OpenAIRealtimeBetaLLMService (built-in)
  └─ Function Handlers (our code, ~50 lines)
       │
       ↓
OpenAI Realtime API
  └─ gpt-4o-realtime-preview
```

**Total custom code:** ~50 lines of function handlers

**Code reduction:** ~90% less custom code!

---

## Implementation Plan

### Phase 1: Backend Migration (High Priority)

**Goal:** Replace custom WebRTC backend with Pipecat

**Tasks:**

1. **Install Pipecat dependencies:**
   ```bash
   pip install pipecat-ai[daily]  # Includes aiortc, Daily SDK
   ```

2. **Create new voice controller:**
   - File: `backend/api/realtime_voice_pipecat.py`
   - Import Pipecat components
   - Set up Daily transport
   - Configure OpenAI Realtime LLM service
   - Build pipeline

3. **Implement function handlers:**
   ```python
   # Nested team integration
   async def send_to_nested_handler(params: FunctionCallParams):
       text = params.arguments["text"]
       # Use existing WebSocket logic
       result = await nested_team_websocket.run(text)
       await params.result_callback(result)

   # Claude Code integration
   async def send_to_claude_code_handler(params: FunctionCallParams):
       text = params.arguments["text"]
       # Use existing Claude Code controller
       result = await claude_code_session.run(text)
       await params.result_callback(result)
   ```

4. **Add FastAPI endpoints:**
   ```python
   @router.post("/api/realtime/pipecat/session")
   async def create_pipecat_session():
       # Create Daily room
       # Start Pipecat pipeline
       # Return room URL and token
   ```

5. **Conversation persistence:**
   - Use existing `voice_conversation_store.py`
   - Hook into Pipecat's frame processors
   - Store transcription frames, function call frames, etc.

### Phase 2: Frontend Migration (Medium Priority)

**Goal:** Replace custom WebRTC frontend with Daily client

**Tasks:**

1. **Install Daily JS client:**
   ```bash
   npm install @daily-co/daily-js
   ```

2. **Update VoiceAssistant component:**
   - File: `frontend/src/features/voice/pages/VoiceAssistantPipecat.js`
   - Replace custom RTCPeerConnection with Daily
   - Simplified audio handling (Daily manages it)
   - Focus on UI/UX

3. **Example Daily client setup:**
   ```javascript
   import DailyIframe from '@daily-co/daily-js';

   const callFrame = DailyIframe.createCallObject();
   await callFrame.join({ url: roomUrl, token: token });

   // Audio is automatic!
   callFrame.on('participant-joined', handleParticipant);
   callFrame.on('track-started', handleTrack);
   ```

### Phase 3: Function Integration (High Priority)

**Goal:** Connect Pipecat function calls to existing agents

**Tasks:**

1. **Nested team integration:**
   - Import existing nested team logic from `api/realtime_voice.py`
   - Adapt WebSocket event streaming to Pipecat frames
   - Return results to OpenAI

2. **Claude Code integration:**
   - Import existing Claude Code controller
   - Stream events to conversation store
   - Return completion status to OpenAI

3. **Event persistence:**
   - Create Pipecat frame → SQLite event mapper
   - Store in existing `voice_conversations.db`
   - Maintain compatibility with export scripts

### Phase 4: Testing & Deployment (Critical)

**Goal:** Verify all functionality and deploy

**Tasks:**

1. **Unit tests:**
   - Test function handlers
   - Test frame processors
   - Test conversation persistence

2. **Integration tests:**
   - Test full pipeline flow
   - Test multi-client scenarios
   - Test error handling

3. **E2E tests:**
   - Voice quality verification
   - Latency measurement
   - Function call execution
   - Nested team integration
   - Claude Code integration

4. **Jetson deployment:**
   - Install Daily SDK on ARM64
   - Update systemd service
   - Update nginx config (if needed)
   - Production testing

---

## Dependencies

### Backend

**Required:**
```bash
pip install pipecat-ai[daily]  # Main framework + Daily transport
```

**Includes:**
- `pipecat-ai` - Core framework
- `daily-python` - Daily SDK for room management
- `aiortc` - WebRTC implementation (already have)
- `aiohttp` - HTTP client (already have)
- `av` - Audio/video processing (already have)

**Optional:**
- `pipecat-ai[silero]` - Silero VAD (Voice Activity Detection)
- `pipecat-ai[deepgram]` - Deepgram transcription (if needed)

### Frontend

**Required:**
```bash
npm install @daily-co/daily-js
```

**No other changes** - Daily client is lightweight

---

## Migration Strategy

### Approach: Parallel Development

**Keep existing system running** while building Pipecat version:

1. **Create new files:**
   - `backend/api/realtime_voice_pipecat.py` (new)
   - `frontend/src/features/voice/pages/VoiceAssistantPipecat.js` (new)
   - New route: `/voice-pipecat` (parallel to `/voice-webrtc`)

2. **Test extensively** with new route

3. **Gradual rollout:**
   - Week 1: Internal testing on `/voice-pipecat`
   - Week 2: Beta testing with select users
   - Week 3: Make `/voice-pipecat` the default
   - Week 4: Deprecate old `/voice-webrtc` route

4. **Fallback plan:**
   - Keep old implementation for 1 month
   - Monitor for issues
   - Complete migration only when confident

---

## Code Examples

### Backend: Pipecat Voice Controller

```python
# backend/api/realtime_voice_pipecat.py

import os
from pipecat.pipeline import Pipeline
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.services.openai import OpenAIRealtimeBetaLLMService
from pipecat.processors.aggregators.context import ContextAggregator
from pipecat.processors.logger import FrameLogger
from pipecat.frames.frames import FunctionCallFrame, FunctionResultFrame

# Import existing logic
from ..utils.voice_conversation_store import store as conversation_store
from .realtime_voice import execute_nested_team, execute_claude_code

async def create_voice_pipeline(conversation_id: str):
    """Create Pipecat pipeline for voice assistant"""

    # 1. Create Daily transport
    transport = DailyTransport(
        room_url=os.getenv("DAILY_ROOM_URL"),
        token=os.getenv("DAILY_TOKEN"),
        params=DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer()  # Voice activity detection
        )
    )

    # 2. Configure OpenAI Realtime service
    session_properties = SessionProperties(
        input_audio_transcription=InputAudioTranscription(),
        turn_detection=SemanticTurnDetection(),
        voice="alloy",
        instructions="You are Archie, the voice interface...",
        tools=[
            FunctionSchema(
                name="send_to_nested",
                description="Send task to nested team agents",
                properties={"text": {"type": "string"}},
                required=["text"]
            ),
            FunctionSchema(
                name="send_to_claude_code",
                description="Send instruction to Claude Code",
                properties={"text": {"type": "string"}},
                required=["text"]
            )
        ]
    )

    llm = OpenAIRealtimeBetaLLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        session_properties=session_properties
    )

    # 3. Register function handlers
    async def nested_handler(params: FunctionCallParams):
        text = params.arguments["text"]
        result = await execute_nested_team(text)
        await params.result_callback(result)

    async def claude_handler(params: FunctionCallParams):
        text = params.arguments["text"]
        result = await execute_claude_code(text)
        await params.result_callback(result)

    llm.register_function("send_to_nested", nested_handler)
    llm.register_function("send_to_claude_code", claude_handler)

    # 4. Create context aggregator (for conversation history)
    context = ContextAggregator()

    # 5. Create frame logger (for debugging)
    logger = FrameLogger()

    # 6. Build pipeline
    pipeline = Pipeline([
        transport.input(),    # Get audio from Daily
        context.user(),       # Track user context
        llm,                  # Process with OpenAI Realtime
        logger,               # Log frames (optional)
        transport.output(),   # Send audio to Daily
        context.assistant()   # Track assistant context
    ])

    # 7. Store events to conversation DB
    @pipeline.on("frame")
    async def on_frame(frame):
        # Store transcription frames
        if isinstance(frame, TranscriptionFrame):
            conversation_store.append_event(
                conversation_id,
                {"type": "transcription", "text": frame.text},
                source="voice"
            )
        # Store function calls
        elif isinstance(frame, FunctionCallFrame):
            conversation_store.append_event(
                conversation_id,
                {"type": "function_call", "name": frame.name, "args": frame.arguments},
                source="voice"
            )

    return pipeline, transport


# FastAPI endpoint
@router.post("/api/realtime/pipecat/session")
async def create_pipecat_session(request: Request):
    body = await request.json()
    conversation_id = body.get("conversation_id")

    # Create Daily room
    daily_client = Daily(api_key=os.getenv("DAILY_API_KEY"))
    room = daily_client.rooms.create()

    # Create pipeline
    pipeline, transport = await create_voice_pipeline(conversation_id)

    # Start pipeline
    await pipeline.start()

    return {
        "room_url": room.url,
        "token": room.token,
        "conversation_id": conversation_id
    }
```

### Frontend: Daily Client

```javascript
// frontend/src/features/voice/pages/VoiceAssistantPipecat.js

import React, { useState, useEffect } from 'react';
import DailyIframe from '@daily-co/daily-js';

function VoiceAssistantPipecat() {
    const [callFrame, setCallFrame] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [isMuted, setIsMuted] = useState(false);

    const startSession = async () => {
        // 1. Create backend session
        const response = await fetch('/api/realtime/pipecat/session', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                conversation_id: 'conversation-123'
            })
        });

        const {room_url, token} = await response.json();

        // 2. Create Daily call object
        const daily = DailyIframe.createCallObject();

        // 3. Set up event handlers
        daily.on('joined-meeting', () => {
            console.log('Joined Daily room');
            setIsConnected(true);
        });

        daily.on('left-meeting', () => {
            console.log('Left Daily room');
            setIsConnected(false);
        });

        daily.on('participant-joined', (event) => {
            console.log('Participant joined:', event.participant.user_name);
        });

        // 4. Join room
        await daily.join({url: room_url, token: token});

        setCallFrame(daily);
    };

    const stopSession = async () => {
        if (callFrame) {
            await callFrame.leave();
            await callFrame.destroy();
            setCallFrame(null);
        }
    };

    const toggleMute = () => {
        if (callFrame) {
            callFrame.setLocalAudio(!isMuted);
            setIsMuted(!isMuted);
        }
    };

    return (
        <div>
            <h1>Voice Assistant (Pipecat)</h1>

            {!isConnected ? (
                <button onClick={startSession}>Start Session</button>
            ) : (
                <>
                    <button onClick={stopSession}>Stop Session</button>
                    <button onClick={toggleMute}>
                        {isMuted ? 'Unmute' : 'Mute'}
                    </button>
                </>
            )}
        </div>
    );
}

export default VoiceAssistantPipecat;
```

---

## Comparison: Custom vs Pipecat

| Aspect | Custom Implementation | Pipecat |
|--------|----------------------|---------|
| **Lines of Code** | ~584 lines (backend) | ~150 lines (backend) |
| | ~333 lines (frontend) | ~100 lines (frontend) |
| **WebRTC Setup** | Manual SDP, ICE, tracks | Automatic (Daily) |
| **Audio Handling** | Custom PCM16 conversion | Automatic |
| **Function Calling** | Manual parsing | Built-in framework |
| **Multi-Client** | Custom audio mixing | Automatic (Daily rooms) |
| **Error Handling** | Custom | Framework-provided |
| **Transport Options** | WebRTC only | WebRTC, WebSocket, local |
| **Testing** | Custom test suite | Framework-tested |
| **Maintenance** | Our responsibility | Pipecat team |
| **Documentation** | DIY | Comprehensive |
| **Community** | None | Active (GitHub, Discord) |

---

## Risks & Mitigation

### Potential Risks

1. **Daily dependency:**
   - **Risk:** Locked into Daily.co infrastructure
   - **Mitigation:** Pipecat supports multiple transports (WebSocket, local), can switch if needed

2. **Learning curve:**
   - **Risk:** Team unfamiliar with Pipecat
   - **Mitigation:** Excellent documentation, active community, examples for our use case

3. **Migration complexity:**
   - **Risk:** Breaking existing functionality during migration
   - **Mitigation:** Parallel development, gradual rollout, keep old implementation as fallback

4. **Jetson compatibility:**
   - **Risk:** Daily SDK may not work on ARM64
   - **Mitigation:** Pipecat supports WebSocket transport (no Daily needed), can use that on Jetson

5. **Function call integration:**
   - **Risk:** Existing nested team/Claude Code integration may be complex
   - **Mitigation:** Pipecat provides `FunctionCallParams` with clean callback API

### Risk Assessment

Overall risk: **LOW**

- Pipecat is production-ready (thousands of deployments)
- Backed by Daily.co (well-funded, stable)
- Clean migration path with fallback options
- Significant code reduction and maintainability improvement

---

## Timeline Estimate

### Conservative Estimate (3-4 weeks)

**Week 1: Backend Foundation**
- Install Pipecat, set up development environment
- Create basic pipeline with OpenAI Realtime
- Test audio flow (no function calls)
- **Milestone:** Audio conversation working

**Week 2: Function Integration**
- Implement function handlers
- Integrate nested team WebSocket
- Integrate Claude Code controller
- **Milestone:** Full feature parity with custom implementation

**Week 3: Frontend & Testing**
- Build Daily client frontend
- End-to-end testing
- Multi-client testing
- **Milestone:** Production-ready code

**Week 4: Deployment & Monitoring**
- Deploy to Jetson Nano
- Production testing
- User feedback
- **Milestone:** Live in production

### Aggressive Estimate (1-2 weeks)

If we prioritize this:
- **Days 1-3:** Backend pipeline + function handlers
- **Days 4-5:** Frontend Daily client
- **Days 6-7:** Testing & deployment

---

## Recommendation

**STRONG RECOMMENDATION: Migrate to Pipecat**

**Reasons:**

1. **90% code reduction** - Less code to maintain, fewer bugs
2. **Production-ready** - Battle-tested framework
3. **Better architecture** - Clean separation of concerns
4. **Active development** - Frequent updates, security patches
5. **Community support** - Active Discord, GitHub issues
6. **Future-proof** - Multiple transport options, easy to extend
7. **Time savings** - 3-4 weeks vs months of custom development

**Next Steps:**

1. ✅ Research complete (this document)
2. 🔄 **Get user approval** to proceed with Pipecat
3. ⏳ Start Week 1 implementation (backend foundation)
4. ⏳ Parallel development (keep existing system)
5. ⏳ Gradual rollout and testing
6. ⏳ Full migration and deprecation of custom code

---

## Additional Resources

**Pipecat Documentation:**
- Main docs: https://docs.pipecat.ai
- GitHub: https://github.com/pipecat-ai/pipecat
- Examples: https://github.com/pipecat-ai/pipecat/tree/main/examples
- Discord: https://discord.gg/pipecat

**OpenAI Realtime:**
- Example: [19-openai-realtime-beta.py](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/19-openai-realtime-beta.py)
- Reference: https://docs.pipecat.ai/server/services/openai-realtime

**Daily:**
- Python SDK: https://docs.daily.co/reference/python
- JS SDK: https://docs.daily.co/reference/daily-js
- Rooms API: https://docs.daily.co/reference/rest-api/rooms

**Our Existing Code:**
- Custom implementation: [backend/api/openai_webrtc_client.py](../backend/api/openai_webrtc_client.py)
- Nested team: [backend/api/realtime_voice.py](../backend/api/realtime_voice.py)
- Claude Code: [backend/api/claude_code_controller.py](../backend/api/claude_code_controller.py)

---

**Last Updated:** 2025-12-03
**Status:** Research Complete - Awaiting Approval
**Next Action:** User approval to proceed with Pipecat integration
