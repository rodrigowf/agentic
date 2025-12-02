# Backend WebRTC Implementation Guide

**Complete Implementation Reference for Claude Code**

**Date:** 2025-12-02
**Status:** Ready for Implementation
**Architecture:** Backend-Controlled WebRTC with Frontend Audio Provider via Data Channel

---

## Quick Start for Implementation

**Context:** This guide provides everything needed to implement backend-controlled WebRTC architecture where the Python backend owns the OpenAI Realtime API connection and communicates with the frontend via WebRTC data channels (NOT WebSocket).

**Key Decision:** Frontend-backend communication uses **WebRTC data channel** instead of WebSocket for lower latency and better audio streaming.

**Reference Documentation:**
- Architecture overview: [docs/BACKEND_WEBRTC_DOCUMENTATION_INDEX.md](BACKEND_WEBRTC_DOCUMENTATION_INDEX.md)
- Detailed plan: [docs/planning/BACKEND_WEBRTC_IMPLEMENTATION_PLAN.md](planning/BACKEND_WEBRTC_IMPLEMENTATION_PLAN.md)
- Research report: [docs/research/BACKEND_WEBRTC_RESEARCH_REPORT.md](research/BACKEND_WEBRTC_RESEARCH_REPORT.md)
- Executive summary: [docs/research/BACKEND_WEBRTC_EXECUTIVE_SUMMARY.md](research/BACKEND_WEBRTC_EXECUTIVE_SUMMARY.md)

---

## Architecture Overview

### Dual WebRTC Connection Design

```
Frontend (Browser)
  ├─ Microphone (getUserMedia)
  ├─ Speaker (AudioContext)
  └─ WebRTC Data Channel
       │
       ↓ (Audio PCM16 bidirectional)
       │
Backend (Python/aiortc)
  ├─ Frontend Audio Handler (WebRTC server)
  ├─ Audio Router/Mixer (multi-client support)
  ├─ OpenAI WebRTC Client
  └─ Function Call Handler (direct execution)
       │
       ↓ (WebRTC Connection #2)
       │
OpenAI Realtime API
  ├─ gpt-4o-realtime-preview
  ├─ Voice responses
  └─ Function calling
```

### Key Simplifications vs Current System

**Removed from Frontend:**
- ❌ OpenAI token management
- ❌ Direct OpenAI WebRTC connection
- ❌ Function call forwarding via WebSocket
- ❌ WebSocket for audio streaming

**Retained in Frontend:**
- ✅ Browser audio I/O (echo cancellation, noise suppression)
- ✅ Device selection UI
- ✅ Multi-device support

**Added to Backend:**
- ✅ OpenAI WebRTC connection ownership
- ✅ Direct function call handling
- ✅ Audio mixing for multiple clients
- ✅ WebRTC data channel server

---

## Implementation Checklist

### Phase 1: Backend - OpenAI WebRTC Client (Days 1-2)

**File:** `backend/api/openai_webrtc_client.py`

**Tasks:**
- [ ] Install dependencies: `aiortc>=1.6.0`, `numpy<2.0`, `aiohttp>=3.9.0`
- [ ] Implement `OpenAIWebRTCClient` class
- [ ] Add ephemeral token fetching
- [ ] Implement SDP exchange
- [ ] Create custom `AudioTrack` for sending audio
- [ ] Handle incoming audio track
- [ ] Handle OpenAI data channel events
- [ ] Process function call events

**Key Dependencies:**
```python
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
import aiohttp
import asyncio
import json
import logging
```

**Critical Implementation Points:**
1. **Ephemeral Token:** `POST https://api.openai.com/v1/realtime/sessions`
2. **SDP Exchange:** `POST https://api.openai.com/v1/realtime?model={model}`
3. **Audio Track:** Custom `MediaStreamTrack` with asyncio queue
4. **Data Channel:** Handle `response.function_call_arguments.done` events
5. **Callbacks:** `on_audio_callback`, `on_function_call_callback`

### Phase 2: Backend - Frontend Audio Handler (Days 2-3)

**File:** `backend/api/frontend_audio_handler.py`

**Tasks:**
- [ ] Implement `FrontendAudioHandler` class
- [ ] Handle SDP offer from frontend
- [ ] Set up data channel listeners
- [ ] Receive audio from frontend (bytes)
- [ ] Send audio to frontend (bytes)
- [ ] Send control messages (JSON)

**Critical Implementation Points:**
1. **SDP Handling:** Accept offer, create answer, return SDP string
2. **Data Channel:** Listen for `datachannel` event, not create
3. **Audio Format:** Expect PCM16 bytes from frontend
4. **Message Types:** Distinguish bytes (audio) vs string (control)

### Phase 3: Backend - Main Controller (Days 3-4)

**File:** `backend/api/realtime_voice_webrtc.py`

**Tasks:**
- [ ] Create FastAPI router
- [ ] Implement `POST /api/realtime/session` endpoint
- [ ] Implement `POST /api/realtime/sdp/{session_id}` endpoint
- [ ] Implement session management (dict storage)
- [ ] Handle frontend audio → OpenAI routing
- [ ] Handle OpenAI audio → frontend broadcasting
- [ ] Implement function call handler
- [ ] Integrate with nested team execution
- [ ] Integrate with Claude Code execution
- [ ] Implement audio mixing (multi-client)
- [ ] Implement `DELETE /api/realtime/session/{session_id}` cleanup

**Session Data Structure:**
```python
sessions: Dict[str, dict] = {
    "session_id": {
        "openai_client": OpenAIWebRTCClient,
        "frontend_handlers": [FrontendAudioHandler, ...],
        "audio_buffers": {client_id: bytes},
    }
}
```

**Critical Implementation Points:**
1. **Session Creation:** Create OpenAI client first, then return session ID
2. **SDP Exchange:** Create frontend handler per client
3. **Audio Routing:** Frontend → OpenAI (forward), OpenAI → Frontend (broadcast)
4. **Function Calls:** Execute directly in backend, send result to OpenAI
5. **Multi-Client:** Support multiple frontend handlers per session

### Phase 4: Backend - Audio Mixing (Day 4)

**File:** `backend/api/realtime_voice_webrtc.py` (add mixing logic)

**Tasks:**
- [ ] Implement `mix_audio_streams(streams: list) -> bytes`
- [ ] Handle different buffer sizes (padding)
- [ ] Use NumPy for efficient mixing
- [ ] Average samples to prevent clipping
- [ ] Store per-client audio buffers

**Implementation:**
```python
import numpy as np

def mix_audio_streams(streams: list) -> bytes:
    if not streams:
        return b""
    if len(streams) == 1:
        return streams[0]

    arrays = [np.frombuffer(s, dtype=np.int16) for s in streams]
    max_length = max(len(arr) for arr in arrays)
    arrays = [np.pad(arr, (0, max_length - len(arr))) for arr in arrays]
    mixed = np.mean(arrays, axis=0).astype(np.int16)
    return mixed.tobytes()
```

### Phase 5: Frontend - WebRTC Data Channel (Days 5-6)

**File:** `frontend/src/features/voice/pages/VoiceAssistant.js`

**Tasks:**
- [ ] Remove OpenAI token fetching
- [ ] Remove direct OpenAI WebRTC connection
- [ ] Add backend session creation: `POST /api/realtime/session`
- [ ] Create WebRTC peer connection
- [ ] Create data channel (`pc.createDataChannel('audio')`)
- [ ] Implement SDP exchange with backend
- [ ] Stream microphone audio via data channel
- [ ] Receive and play audio from data channel
- [ ] Remove function call forwarding logic
- [ ] Update UI for backend-controlled mode

**Critical Implementation Points:**
1. **Session Creation First:** Get session_id before WebRTC setup
2. **Data Channel:** Create before offer generation
3. **Audio Format:** Convert Float32 (getUserMedia) → PCM16 (data channel)
4. **SDP Exchange:** Send offer to `/api/realtime/sdp/{session_id}`
5. **Playback:** Convert PCM16 → Float32 → AudioContext playback

**Audio Conversion (JavaScript):**
```javascript
// Float32 → PCM16 (for sending)
function convertToPCM16(float32Array) {
  const pcm16 = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return pcm16.buffer;
}

// PCM16 → Float32 (for playback)
function convertToFloat32(pcm16Buffer) {
  const pcm16 = new Int16Array(pcm16Buffer);
  const float32 = new Float32Array(pcm16.length);
  for (let i = 0; i < pcm16.length; i++) {
    float32[i] = pcm16[i] / (pcm16[i] < 0 ? 0x8000 : 0x7FFF);
  }
  return float32;
}
```

### Phase 6: Integration & Testing (Days 6-7)

**Tasks:**
- [ ] Test end-to-end audio flow
- [ ] Test function call execution (send_to_nested)
- [ ] Test function call execution (send_to_claude_code)
- [ ] Test multi-client audio mixing
- [ ] Test connection error recovery
- [ ] Test session cleanup
- [ ] Measure latency
- [ ] Profile CPU usage

**Test Scenarios:**
1. **Basic Audio:** Start session, unmute, speak, hear response
2. **Function Calls:** "Create a file test.txt" → Claude Code execution
3. **Multi-Client:** Desktop + mobile simultaneously
4. **Disconnection:** Kill backend, verify frontend handles error
5. **Latency:** Measure round-trip time (mic → speaker)
6. **CPU:** Monitor backend CPU with 5 concurrent sessions

### Phase 7: Deployment (Days 8-9)

**Tasks:**
- [ ] Update `backend/requirements.txt`
- [ ] Install dependencies on Jetson Nano
- [ ] Deploy backend code
- [ ] Deploy frontend code
- [ ] Test on staging
- [ ] Deploy to production
- [ ] Monitor for 24 hours

**Deployment Commands:**
```bash
# Jetson Nano deployment
ssh rodrigo@192.168.0.200

# Backend
cd ~/agentic/backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart agentic-backend

# Frontend
cd ~/agentic/frontend
source ~/miniconda3/etc/profile.d/conda.sh && conda activate agentic
npm run build
sudo kill -HUP $(cat ~/nginx.pid)

# Verify
curl -I https://192.168.0.200/api/agents
```

---

## Complete Code Examples

### Backend: OpenAI WebRTC Client

```python
"""
backend/api/openai_webrtc_client.py
OpenAI Realtime API WebRTC client using aiortc
"""

import asyncio
import logging
from typing import Callable, Optional
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaRecorder
import aiohttp
import json

logger = logging.getLogger(__name__)

class OpenAIWebRTCClient:
    """Manages WebRTC connection to OpenAI Realtime API"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-realtime-preview-2024-12-17",
        voice: str = "alloy",
        on_audio_callback: Optional[Callable] = None,
        on_function_call_callback: Optional[Callable] = None
    ):
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.on_audio_callback = on_audio_callback
        self.on_function_call_callback = on_function_call_callback

        self.pc: Optional[RTCPeerConnection] = None
        self.audio_track: Optional[MediaStreamTrack] = None
        self.data_channel = None
        self.session_id: Optional[str] = None

    async def connect(self):
        """Establish WebRTC connection to OpenAI"""
        logger.info(f"Connecting to OpenAI Realtime API (model: {self.model})")

        # Step 1: Get ephemeral token
        token = await self._get_ephemeral_token()

        # Step 2: Create peer connection
        self.pc = RTCPeerConnection()

        # Step 3: Add audio track
        self.audio_track = AudioTrack()
        self.pc.addTrack(self.audio_track)

        # Step 4: Set up event handlers
        @self.pc.on("track")
        def on_track(track):
            logger.info(f"Received track: {track.kind}")
            if track.kind == "audio":
                asyncio.create_task(self._handle_audio_track(track))

        @self.pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(f"Received data channel: {channel.label}")
            self.data_channel = channel

            @channel.on("message")
            def on_message(message):
                self._handle_openai_event(json.loads(message))

        # Step 5: Exchange SDP
        await self._exchange_sdp(token)

        logger.info("Successfully connected to OpenAI")

    async def _get_ephemeral_token(self) -> str:
        """Get ephemeral token from OpenAI API"""
        url = "https://api.openai.com/v1/realtime/sessions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "voice": self.voice
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                resp_data = await resp.json()
                self.session_id = resp_data["id"]
                return resp_data["client_secret"]["value"]

    async def _exchange_sdp(self, token: str):
        """Exchange SDP offer/answer with OpenAI"""
        # Create offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)

        # Send offer to OpenAI
        url = f"https://api.openai.com/v1/realtime?model={self.model}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/sdp"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=offer.sdp) as resp:
                answer_sdp = await resp.text()

        # Set remote description
        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await self.pc.setRemoteDescription(answer)

    async def _handle_audio_track(self, track: MediaStreamTrack):
        """Handle incoming audio from OpenAI"""
        while True:
            try:
                frame = await track.recv()

                # Convert frame to PCM16 and send to callback
                if self.on_audio_callback:
                    audio_data = frame.to_ndarray()  # NumPy array
                    await self.on_audio_callback(audio_data)

            except Exception as e:
                logger.error(f"Error receiving audio: {e}")
                break

    def _handle_openai_event(self, event: dict):
        """Handle events from OpenAI data channel"""
        event_type = event.get("type")

        if event_type == "response.function_call_arguments.done":
            # Function call received
            if self.on_function_call_callback:
                asyncio.create_task(
                    self.on_function_call_callback(event)
                )

        elif event_type == "error":
            logger.error(f"OpenAI error: {event}")

    async def send_audio(self, audio_data: bytes):
        """Send audio to OpenAI"""
        if self.audio_track:
            await self.audio_track.send(audio_data)

    async def send_function_result(self, call_id: str, result: str):
        """Send function call result to OpenAI"""
        if self.data_channel:
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result)
                }
            }
            self.data_channel.send(json.dumps(message))

    async def close(self):
        """Close connection"""
        if self.pc:
            await self.pc.close()
            logger.info("Closed OpenAI connection")


class AudioTrack(MediaStreamTrack):
    """Custom audio track for sending audio to OpenAI"""
    kind = "audio"

    def __init__(self):
        super().__init__()
        self.queue = asyncio.Queue()

    async def recv(self):
        """Called by aiortc to get next audio frame"""
        return await self.queue.get()

    async def send(self, audio_data: bytes):
        """Send audio frame"""
        await self.queue.put(audio_data)
```

### Backend: Frontend Audio Handler

```python
"""
backend/api/frontend_audio_handler.py
Handles WebRTC data channel connection with frontend for audio streaming
"""

import asyncio
import logging
from typing import Callable, Optional
from aiortc import RTCPeerConnection, RTCSessionDescription
import json

logger = logging.getLogger(__name__)

class FrontendAudioHandler:
    """Manages WebRTC data channel with frontend"""

    def __init__(
        self,
        session_id: str,
        on_audio_callback: Optional[Callable] = None
    ):
        self.session_id = session_id
        self.on_audio_callback = on_audio_callback

        self.pc: Optional[RTCPeerConnection] = None
        self.data_channel = None

    async def handle_sdp_offer(self, offer_sdp: str) -> str:
        """Handle SDP offer from frontend, return SDP answer"""
        logger.info(f"Handling SDP offer for session {self.session_id}")

        # Create peer connection
        self.pc = RTCPeerConnection()

        # Set up data channel handlers
        @self.pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(f"Data channel established: {channel.label}")
            self.data_channel = channel

            @channel.on("message")
            def on_message(message):
                # Receive audio from frontend
                if isinstance(message, bytes):
                    # Audio data
                    if self.on_audio_callback:
                        asyncio.create_task(self.on_audio_callback(message))
                else:
                    # Control message
                    data = json.loads(message)
                    logger.debug(f"Control message: {data}")

        # Set remote description (offer from frontend)
        offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
        await self.pc.setRemoteDescription(offer)

        # Create answer
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        logger.info("SDP answer created")
        return self.pc.localDescription.sdp

    async def send_audio(self, audio_data: bytes):
        """Send audio to frontend"""
        if self.data_channel and self.data_channel.readyState == "open":
            self.data_channel.send(audio_data)

    async def send_control(self, message: dict):
        """Send control message to frontend"""
        if self.data_channel and self.data_channel.readyState == "open":
            self.data_channel.send(json.dumps(message))

    async def close(self):
        """Close connection"""
        if self.pc:
            await self.pc.close()
            logger.info(f"Closed frontend connection for session {self.session_id}")
```

### Backend: Main Controller (Simplified)

```python
"""
backend/api/realtime_voice_webrtc.py
Main controller for backend-controlled WebRTC voice sessions
"""

import asyncio
import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
import os
import uuid

from .openai_webrtc_client import OpenAIWebRTCClient
from .frontend_audio_handler import FrontendAudioHandler

logger = logging.getLogger(__name__)
router = APIRouter()

# Active sessions
sessions: Dict[str, dict] = {}


@router.post("/api/realtime/session")
async def create_session():
    """Create new voice session with backend WebRTC"""
    session_id = str(uuid.uuid4())

    # Get OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    # Create OpenAI client
    openai_client = OpenAIWebRTCClient(
        api_key=api_key,
        model="gpt-4o-realtime-preview-2024-12-17",
        voice="alloy",
        on_audio_callback=lambda audio: handle_openai_audio(session_id, audio),
        on_function_call_callback=lambda event: handle_function_call(session_id, event)
    )

    # Connect to OpenAI
    await openai_client.connect()

    # Store session
    sessions[session_id] = {
        "openai_client": openai_client,
        "frontend_handlers": [],
    }

    logger.info(f"Created session {session_id}")

    return JSONResponse({
        "session_id": session_id,
        "status": "connected"
    })


@router.post("/api/realtime/sdp/{session_id}")
async def exchange_sdp(session_id: str, request: Request):
    """Exchange SDP with frontend"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get SDP offer from frontend
    offer_sdp = await request.body()
    offer_sdp = offer_sdp.decode("utf-8")

    # Create frontend handler
    frontend_handler = FrontendAudioHandler(
        session_id=session_id,
        on_audio_callback=lambda audio: handle_frontend_audio(session_id, audio)
    )

    # Handle SDP offer
    answer_sdp = await frontend_handler.handle_sdp_offer(offer_sdp)

    # Store handler
    sessions[session_id]["frontend_handlers"].append(frontend_handler)

    logger.info(f"Frontend connected to session {session_id}")

    return Response(content=answer_sdp, media_type="application/sdp")


async def handle_frontend_audio(session_id: str, audio_data: bytes):
    """Handle audio from frontend, forward to OpenAI"""
    if session_id in sessions:
        openai_client = sessions[session_id]["openai_client"]
        await openai_client.send_audio(audio_data)


async def handle_openai_audio(session_id: str, audio_data: bytes):
    """Handle audio from OpenAI, broadcast to all frontends"""
    if session_id in sessions:
        frontend_handlers = sessions[session_id]["frontend_handlers"]
        for handler in frontend_handlers:
            await handler.send_audio(audio_data)


async def handle_function_call(session_id: str, event: dict):
    """Handle function calls from OpenAI"""
    function_name = event.get("name")
    arguments = event.get("arguments", {})
    call_id = event.get("call_id")

    logger.info(f"Function call: {function_name} with args {arguments}")

    # Execute function
    result = None

    if function_name == "send_to_nested":
        result = await execute_nested_team(arguments.get("text"))
    elif function_name == "send_to_claude_code":
        result = await execute_claude_code(arguments.get("text"))

    # Send result back to OpenAI
    if session_id in sessions:
        openai_client = sessions[session_id]["openai_client"]
        await openai_client.send_function_result(call_id, result)


async def execute_nested_team(text: str) -> str:
    """Execute nested team agent"""
    # TODO: Integrate with existing nested team logic
    return f"Nested team executed: {text}"


async def execute_claude_code(text: str) -> str:
    """Execute Claude Code"""
    # TODO: Integrate with existing Claude Code logic
    return f"Claude Code executed: {text}"


@router.delete("/api/realtime/session/{session_id}")
async def close_session(session_id: str):
    """Close session and cleanup"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Close OpenAI connection
    await session["openai_client"].close()

    # Close frontend connections
    for handler in session["frontend_handlers"]:
        await handler.close()

    # Remove session
    del sessions[session_id]

    logger.info(f"Closed session {session_id}")

    return JSONResponse({"status": "closed"})
```

### Frontend: VoiceAssistant.js (Key Changes)

```javascript
// frontend/src/features/voice/pages/VoiceAssistant.js

// STEP 1: Create session
const startSession = async () => {
  try {
    // Create session on backend
    const resp = await fetch('/api/realtime/session', {
      method: 'POST'
    });
    const data = await resp.json();
    setSessionId(data.session_id);

    // Setup WebRTC
    await setupWebRTC(data.session_id);

    setIsRunning(true);
    console.log('Session started:', data.session_id);

  } catch (err) {
    console.error('Failed to start session:', err);
  }
};

// STEP 2: Setup WebRTC data channel
const setupWebRTC = async (sessionId) => {
  // Create peer connection
  const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
  });
  pcRef.current = pc;

  // Create data channel
  const dataChannel = pc.createDataChannel('audio', {
    ordered: true
  });
  dataChannelRef.current = dataChannel;

  dataChannel.onopen = () => {
    console.log('Data channel opened');
    startAudioStreaming();
  };

  dataChannel.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      // Audio from backend (PCM16)
      playAudio(event.data);
    } else {
      // Control message (JSON)
      const msg = JSON.parse(event.data);
      console.log('Control message:', msg);
    }
  };

  // Get microphone
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    }
  });
  micStreamRef.current = stream;

  // Mute by default
  stream.getAudioTracks().forEach(track => track.enabled = false);

  // Create offer
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  // Send offer to backend
  const sdpResp = await fetch(`/api/realtime/sdp/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/sdp' },
    body: offer.sdp
  });
  const answerSdp = await sdpResp.text();

  // Set remote description
  const answer = new RTCSessionDescription({
    type: 'answer',
    sdp: answerSdp
  });
  await pc.setRemoteDescription(answer);

  console.log('WebRTC setup complete');
};

// STEP 3: Stream microphone audio to backend
const startAudioStreaming = () => {
  const stream = micStreamRef.current;
  if (!stream) return;

  const audioContext = new AudioContext({ sampleRate: 24000 });
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);

  processor.onaudioprocess = (e) => {
    const dataChannel = dataChannelRef.current;
    if (!dataChannel || dataChannel.readyState !== 'open') return;

    const inputData = e.inputBuffer.getChannelData(0);

    // Convert Float32 to PCM16
    const pcm16 = new Int16Array(inputData.length);
    for (let i = 0; i < inputData.length; i++) {
      const s = Math.max(-1, Math.min(1, inputData[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    // Send to backend
    dataChannel.send(pcm16.buffer);
  };

  source.connect(processor);
  processor.connect(audioContext.destination);
};

// STEP 4: Play audio from backend
const playAudio = (audioData) => {
  if (!audioContextRef.current) {
    audioContextRef.current = new AudioContext({ sampleRate: 24000 });
  }

  const audioContext = audioContextRef.current;

  // Convert PCM16 to Float32
  const pcm16 = new Int16Array(audioData);
  const float32 = new Float32Array(pcm16.length);
  for (let i = 0; i < pcm16.length; i++) {
    float32[i] = pcm16[i] / (pcm16[i] < 0 ? 0x8000 : 0x7FFF);
  }

  // Create audio buffer
  const audioBuffer = audioContext.createBuffer(1, float32.length, 24000);
  audioBuffer.getChannelData(0).set(float32);

  // Play
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.start();
};
```

---

## Dependencies

### Backend Requirements

Add to `backend/requirements.txt`:
```
aiortc>=1.6.0
numpy>=1.24.0,<2.0
aiohttp>=3.9.0
```

**Installation:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

**On Jetson Nano (ARM64):**
```bash
# Use conda for tokenizers (required by aiortc)
conda install -c conda-forge tokenizers
```

---

## Testing Strategy

### Unit Tests

**Test File:** `backend/tests/unit/test_backend_webrtc.py`

```python
import pytest
from api.openai_webrtc_client import OpenAIWebRTCClient
from api.frontend_audio_handler import FrontendAudioHandler

@pytest.mark.asyncio
async def test_openai_client_connect():
    """Test OpenAI WebRTC connection"""
    # Mock OpenAI API responses
    # Assert connection succeeds

@pytest.mark.asyncio
async def test_frontend_handler_sdp():
    """Test SDP exchange with frontend"""
    handler = FrontendAudioHandler(session_id="test")
    offer_sdp = "v=0\no=- ..."  # Valid SDP
    answer_sdp = await handler.handle_sdp_offer(offer_sdp)
    assert answer_sdp is not None
```

### Integration Tests

**Test Scenarios:**
1. **End-to-End Audio:** Frontend → Backend → OpenAI → Backend → Frontend
2. **Function Calls:** send_to_nested execution
3. **Multi-Client:** Two frontends connected to same session
4. **Error Recovery:** Backend disconnect and reconnect

### Manual Testing

```bash
# 1. Start backend
cd backend && uvicorn main:app --reload

# 2. Start frontend
cd frontend && npm start

# 3. Test voice session
http://localhost:3000/voice
- Click "Start Session"
- Click "Unmute"
- Speak: "Hello Archie"
- Expect: OpenAI responds

# 4. Test function call
- Speak: "Create a file called test.txt"
- Expect: Claude Code creates file
- Expect: OpenAI confirms completion
```

---

## Troubleshooting

### Common Issues

**1. "OpenAI connection failed"**
```bash
# Check API key
echo $OPENAI_API_KEY

# Test token endpoint
curl -X POST https://api.openai.com/v1/realtime/sessions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-realtime-preview-2024-12-17","voice":"alloy"}'
```

**2. "Data channel not opening"**
- Check SDP exchange logs
- Verify `createDataChannel` called before `createOffer`
- Check ICE candidate gathering

**3. "No audio playback"**
- Check AudioContext state (must be "running")
- Check browser console for errors
- Verify PCM16 → Float32 conversion

**4. "High CPU usage"**
- Profile with `cProfile`
- Check NumPy audio mixing performance
- Consider reducing sample rate

---

## Performance Targets

**Latency:**
- Target: < 600ms round-trip (mic → speaker)
- Expected: 260-600ms (comparable to current system)

**CPU Usage (Jetson Nano):**
- Single session: < 20% CPU
- 5 concurrent sessions: < 60% CPU
- 10 concurrent sessions: < 90% CPU

**Memory Usage:**
- Per session: ~10-15 MB
- 10 sessions: ~150 MB total

---

## Rollback Plan

If critical issues arise:

**1. Feature Flag Rollback:**
```python
# backend/.env
ENABLE_BACKEND_WEBRTC=false

# main.py
if os.getenv("ENABLE_BACKEND_WEBRTC") == "true":
    from api.realtime_voice_webrtc import router
else:
    from api.realtime_voice import router  # Existing system
```

**2. Git Rollback:**
```bash
git log --oneline  # Find previous commit
git checkout <commit-hash>
sudo systemctl restart agentic-backend
```

---

## Success Criteria

### Must Have
- ✅ End-to-end audio working
- ✅ Function calls executed in backend
- ✅ Multi-client support (desktop + mobile)
- ✅ Latency < 1 second

### Nice to Have
- ⚪ Audio recording capability
- ⚪ Performance monitoring
- ⚪ Load testing (10+ sessions)

---

## Next Steps After Implementation

1. **Monitor Production:** Watch for errors, latency spikes, CPU issues
2. **User Feedback:** Test with real voice usage patterns
3. **Optimize:** Profile and optimize bottlenecks
4. **Document:** Update CLAUDE.md with final implementation details

---

## Quick Reference

**File Locations:**
- OpenAI client: `backend/api/openai_webrtc_client.py`
- Frontend handler: `backend/api/frontend_audio_handler.py`
- Main controller: `backend/api/realtime_voice_webrtc.py`
- Frontend: `frontend/src/features/voice/pages/VoiceAssistant.js`

**Key URLs:**
- Create session: `POST /api/realtime/session`
- Exchange SDP: `POST /api/realtime/sdp/{session_id}`
- Close session: `DELETE /api/realtime/session/{session_id}`

**Audio Format:**
- Codec: PCM16
- Sample rate: 24kHz
- Channels: 1 (mono)
- Bitrate: 384 kbps

**Reference Implementation:**
- Mobile voice: `frontend/src/features/voice/pages/MobileVoice.js`
- Already uses WebRTC data channel pattern

---

**Last Updated:** 2025-12-02
**Status:** Ready for Claude Code Implementation
**Estimated Time:** 1-2 weeks
