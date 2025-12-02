# Backend WebRTC Implementation Plan
**Date:** 2025-12-02
**Status:** Planning Phase - Not Yet Implemented
**Architecture:** Backend-Controlled WebRTC with Frontend Audio Provider

---

## Executive Summary

This document outlines the implementation plan for **backend-controlled WebRTC architecture** where:
- **Backend** owns the OpenAI Realtime API WebRTC connection
- **Frontend** provides audio via secondary WebRTC data channel
- **Function calls** handled directly in backend (no forwarding)

### Key Architecture Decision

**Backend-Frontend Communication:** WebRTC data channel (NOT WebSocket)
- Lower latency than WebSocket
- Native audio streaming support
- Already proven in MobileVoice.js implementation

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Data Flow](#data-flow)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [Audio Routing and Mixing](#audio-routing-and-mixing)
6. [Function Call Handling](#function-call-handling)
7. [Testing Plan](#testing-plan)
8. [Deployment Strategy](#deployment-strategy)
9. [Rollback Strategy](#rollback-strategy)
10. [Timeline and Milestones](#timeline-and-milestones)

---

## Architecture Overview

### Dual WebRTC Connection Design

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (Browser)                   │
│                                                              │
│  ┌────────────┐    ┌──────────────┐    ┌────────────────┐ │
│  │ Microphone │───►│   WebRTC     │    │   WebRTC       │ │
│  │  (getUserMedia) │   Peer #1    │    │   Peer #2      │ │
│  └────────────┘    │              │    │                │ │
│                     │  Data        │    │  Audio Track   │ │
│  ┌────────────┐    │  Channel     │    │  (playback)    │ │
│  │  Speaker   │◄───│              │    │                │ │
│  │ (AudioContext)  │              │    └────────────────┘ │
│  └────────────┘    └──────┬───────┘                       │
│                            │                               │
└────────────────────────────┼───────────────────────────────┘
                             │ WebRTC Data Channel
                             │ (bidirectional audio + control)
                             │
┌────────────────────────────▼───────────────────────────────┐
│                    Python Backend (aiortc)                 │
│                                                             │
│  ┌───────────────────────┐       ┌──────────────────────┐ │
│  │  Frontend Audio       │       │  OpenAI WebRTC       │ │
│  │  Handler              │       │  Client              │ │
│  │                       │       │                      │ │
│  │  - Receive mic audio  │       │  - Connect to OpenAI │ │
│  │  - Send speaker audio │◄─────►│  - Send/receive     │ │
│  │  - Control signaling  │       │    audio             │ │
│  │                       │       │  - Receive function  │ │
│  │                       │       │    calls             │ │
│  └───────────────────────┘       └──────────┬───────────┘ │
│                                              │              │
│  ┌───────────────────────────────────────────▼───────────┐ │
│  │  Function Call Handler                                │ │
│  │  - send_to_nested(text)                              │ │
│  │  - send_to_claude_code(text)                         │ │
│  │  - Direct execution (no frontend forwarding)         │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Audio Router/Mixer                                   │ │
│  │  - Mix multiple client audio streams                 │ │
│  │  - Route OpenAI response to all clients              │ │
│  │  - Support desktop + mobile simultaneously           │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                             │
                             │ WebRTC Connection #2
                             │
┌────────────────────────────▼───────────────────────────────┐
│                    OpenAI Realtime API                      │
│                                                             │
│  - Receives audio from backend                             │
│  - Sends audio responses                                   │
│  - Sends function calls (to backend)                       │
│  - Native WebRTC protocol (Opus codec)                     │
└─────────────────────────────────────────────────────────────┘
```

### Key Simplifications

**Compared to Current Architecture:**

1. **No WebSocket for audio** - WebRTC data channel replaces it
2. **No frontend function forwarding** - Backend receives directly from OpenAI
3. **No OpenAI token in frontend** - Backend manages authentication
4. **Single orchestration point** - Backend controls everything

---

## Data Flow

### Session Initialization

```
1. Frontend                          Backend                     OpenAI
   │                                   │                           │
   │──► GET /api/realtime/session ───►│                           │
   │                                   │                           │
   │                                   │──► Authenticate ─────────►│
   │                                   │◄─── Token ───────────────┤
   │                                   │                           │
   │                                   │──► Create WebRTC Peer ───►│
   │                                   │◄─── SDP Offer ───────────┤
   │                                   │──► SDP Answer ───────────►│
   │                                   │                           │
   │                                   │ [WebRTC Connected]        │
   │◄── Session ID + SDP Endpoint ───┤                           │
   │                                   │                           │
   │──► Create RTCPeerConnection      │                           │
   │──► Create DataChannel            │                           │
   │──► getUserMedia (mic)            │                           │
   │──► Generate SDP Offer            │                           │
   │                                   │                           │
   │──► POST /api/realtime/sdp ──────►│                           │
   │◄─── SDP Answer ─────────────────┤                           │
   │                                   │                           │
   │ [Data Channel Connected]          │                           │
   │                                   │                           │
```

### Audio Flow (Running Session)

```
Microphone                          Frontend                    Backend                     OpenAI
   │                                   │                           │                           │
   │──► PCM audio ───────────────────►│                           │                           │
   │                                   │                           │                           │
   │                                   │──► DataChannel.send() ───►│                           │
   │                                   │    (audio chunk)          │                           │
   │                                   │                           │──► WebRTC track.send() ──►│
   │                                   │                           │    (audio to OpenAI)      │
   │                                   │                           │                           │
   │                                   │                           │◄─── Audio response ──────┤
   │                                   │                           │                           │
   │                                   │◄─── DataChannel.send() ──┤                           │
   │                                   │     (audio chunk)         │                           │
   │                                   │                           │                           │
   │◄─── Speaker playback ────────────┤                           │                           │
   │     (AudioContext)                │                           │                           │
```

### Function Call Flow

```
OpenAI                              Backend                     Nested Team / Claude Code
   │                                   │                           │
   │──► Function call event ─────────►│                           │
   │    {                              │                           │
   │      "type": "function_call",     │                           │
   │      "name": "send_to_nested",    │                           │
   │      "arguments": {"text": "..."}│                           │
   │    }                              │                           │
   │                                   │                           │
   │                                   │──► Execute function ─────►│
   │                                   │                           │
   │                                   │◄─── Result ──────────────┤
   │                                   │                           │
   │◄─── Function call result ────────┤                           │
   │    {                              │                           │
   │      "type": "function_result",   │                           │
   │      "call_id": "...",           │                           │
   │      "result": "..."             │                           │
   │    }                              │                           │
```

**Key difference:** No frontend involvement in function calls!

---

## Backend Implementation

### File Structure

```
backend/
├── api/
│   ├── realtime_voice_webrtc.py     # New: Backend WebRTC controller
│   ├── openai_webrtc_client.py      # New: OpenAI connection handler
│   └── frontend_audio_handler.py    # New: Frontend data channel handler
├── requirements.txt                  # Add: aiortc, numpy
└── tests/
    ├── test_backend_webrtc.py       # Unit tests
    └── integration/
        └── test_webrtc_e2e.py       # Integration tests
```

### 1. OpenAI WebRTC Client (`openai_webrtc_client.py`)

```python
"""
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
        self.session_id: Optional[str] = None

    async def connect(self):
        """Establish WebRTC connection to OpenAI"""
        logger.info(f"Connecting to OpenAI Realtime API (model: {self.model})")

        # Step 1: Get ephemeral token
        token = await self._get_ephemeral_token()

        # Step 2: Create peer connection
        self.pc = RTCPeerConnection()

        # Step 3: Add audio track
        self.audio_track = AudioTrack()  # Custom track for sending audio
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

### 2. Frontend Audio Handler (`frontend_audio_handler.py`)

```python
"""
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

### 3. Main Controller (`realtime_voice_webrtc.py`)

```python
"""
Main controller for backend-controlled WebRTC voice sessions
"""

import asyncio
import logging
from typing import Dict
from fastapi import APIRouter, WebSocket, HTTPException, Request
from fastapi.responses import JSONResponse
import os

from .openai_webrtc_client import OpenAIWebRTCClient
from .frontend_audio_handler import FrontendAudioHandler

logger = logging.getLogger(__name__)
router = APIRouter()

# Active sessions
sessions: Dict[str, dict] = {}


@router.post("/api/realtime/session")
async def create_session():
    """Create new voice session with backend WebRTC"""
    import uuid
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
        "frontend_handlers": [],  # Multiple frontends (desktop + mobile)
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
        # Execute nested team
        result = await execute_nested_team(arguments.get("text"))

    elif function_name == "send_to_claude_code":
        # Execute Claude Code
        result = await execute_claude_code(arguments.get("text"))

    # Send result back to OpenAI
    if session_id in sessions:
        openai_client = sessions[session_id]["openai_client"]
        # Send function result via data channel
        # (Implementation depends on OpenAI's protocol)


async def execute_nested_team(text: str) -> str:
    """Execute nested team agent"""
    # Import existing nested team logic
    from core.runner import run_agent_ws
    from config.config_loader import load_agent_config

    # Load agent
    agent_config = load_agent_config("MainConversation")

    # Execute (would need WebSocket or alternative)
    # This is a placeholder - actual implementation depends on architecture
    return f"Nested team executed: {text}"


async def execute_claude_code(text: str) -> str:
    """Execute Claude Code"""
    # Import existing Claude Code logic
    from api.claude_code_controller import ClaudeCodeSession

    # Execute
    session = ClaudeCodeSession()
    # ... execute logic ...

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

### Dependencies (`requirements.txt`)

```txt
# Existing dependencies
fastapi
uvicorn
websockets
...

# New dependencies for backend WebRTC
aiortc>=1.6.0
numpy>=1.24.0,<2.0  # For ChromaDB compatibility
aiohttp>=3.9.0
```

---

## Frontend Implementation

### Reference: MobileVoice.js

The frontend implementation will be similar to the existing [MobileVoice.js](../../../frontend/src/features/voice/pages/MobileVoice.js) which already demonstrates:

1. WebRTC peer connection creation
2. Data channel setup
3. Microphone audio streaming
4. Speaker audio playback
5. SDP signaling

### Key Changes from Current VoiceAssistant.js

**Remove:**
- ❌ OpenAI token fetching
- ❌ Direct OpenAI WebRTC connection
- ❌ Function call forwarding via WebSocket

**Add:**
- ✅ Backend WebRTC data channel connection
- ✅ Audio streaming via data channel
- ✅ Simplified control flow

### New VoiceAssistant.js Structure

```javascript
// frontend/src/features/voice/pages/VoiceAssistant.js

import React, { useState, useRef, useEffect } from 'react';
import { Button, Box, Typography } from '@mui/material';

export default function VoiceAssistant() {
  const [isRunning, setIsRunning] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [sessionId, setSessionId] = useState(null);

  const pcRef = useRef(null);  // RTCPeerConnection
  const dataChannelRef = useRef(null);  // DataChannel
  const micStreamRef = useRef(null);  // Microphone stream
  const audioContextRef = useRef(null);  // For playback

  // Step 1: Create session
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

  // Step 2: Setup WebRTC data channel
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
        // Audio from backend
        playAudio(event.data);
      } else {
        // Control message
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

  // Step 3: Stream microphone audio to backend
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

  // Step 4: Play audio from backend
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

  // Toggle mute
  const toggleMute = () => {
    if (micStreamRef.current) {
      micStreamRef.current.getAudioTracks().forEach(track => {
        track.enabled = !track.enabled;
      });
      setIsMuted(!isMuted);
    }
  };

  // Stop session
  const stopSession = async () => {
    // Close connections
    if (pcRef.current) {
      pcRef.current.close();
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(track => track.stop());
    }

    // Close backend session
    if (sessionId) {
      await fetch(`/api/realtime/session/${sessionId}`, {
        method: 'DELETE'
      });
    }

    setIsRunning(false);
    setSessionId(null);
    console.log('Session stopped');
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Voice Assistant (Backend WebRTC)
      </Typography>

      <Box sx={{ mt: 2 }}>
        {!isRunning ? (
          <Button
            variant="contained"
            color="success"
            size="large"
            onClick={startSession}
          >
            Start Session
          </Button>
        ) : (
          <>
            <Button
              variant="contained"
              color="error"
              size="large"
              onClick={stopSession}
              sx={{ mr: 2 }}
            >
              Stop Session
            </Button>

            <Button
              variant="contained"
              color={isMuted ? "warning" : "success"}
              size="large"
              onClick={toggleMute}
            >
              {isMuted ? "Unmute" : "Mute"}
            </Button>
          </>
        )}
      </Box>

      {sessionId && (
        <Typography variant="body2" sx={{ mt: 2 }}>
          Session ID: {sessionId}
        </Typography>
      )}
    </Box>
  );
}
```

---

## Audio Routing and Mixing

### Multi-Client Audio Mixing

When multiple clients (desktop + mobile) are connected to the same session, the backend must:

1. **Mix microphone inputs** from all clients
2. **Broadcast OpenAI responses** to all clients

```python
# In realtime_voice_webrtc.py

import numpy as np

async def handle_frontend_audio(session_id: str, audio_data: bytes, client_id: str):
    """Handle audio from one frontend client"""
    if session_id not in sessions:
        return

    session = sessions[session_id]

    # Store audio in client buffer
    if "audio_buffers" not in session:
        session["audio_buffers"] = {}

    session["audio_buffers"][client_id] = audio_data

    # Mix all client audio
    mixed_audio = mix_audio_streams(session["audio_buffers"].values())

    # Send mixed audio to OpenAI
    openai_client = session["openai_client"]
    await openai_client.send_audio(mixed_audio)


def mix_audio_streams(audio_streams: list) -> bytes:
    """Mix multiple PCM16 audio streams"""
    if not audio_streams:
        return b""

    if len(audio_streams) == 1:
        return audio_streams[0]

    # Convert to numpy arrays
    arrays = [np.frombuffer(audio, dtype=np.int16) for audio in audio_streams]

    # Find minimum length (handle different buffer sizes)
    min_length = min(len(arr) for arr in arrays)
    arrays = [arr[:min_length] for arr in arrays]

    # Mix by averaging (prevents clipping)
    mixed = np.mean(arrays, axis=0).astype(np.int16)

    return mixed.tobytes()
```

### Audio Format Considerations

**OpenAI expects:** PCM16, 24kHz, mono
**Browser provides:** Float32, variable sample rate, mono/stereo

**Conversion required:**
- Frontend: Float32 → PCM16 (in JavaScript)
- Backend: PCM16 → PCM16 (no conversion needed if frontend matches)
- Backend to frontend: PCM16 → Float32 (in JavaScript for playback)

---

## Function Call Handling

### Tool Definitions (Backend)

```python
# In realtime_voice_webrtc.py

VOICE_TOOLS = [
    {
        "type": "function",
        "name": "send_to_nested",
        "description": "Send a task to the nested team agent for execution",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The task description or question"
                }
            },
            "required": ["text"]
        }
    },
    {
        "type": "function",
        "name": "send_to_claude_code",
        "description": "Send a code editing instruction to Claude Code",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The code editing instruction"
                }
            },
            "required": ["text"]
        }
    }
]

# Register tools with OpenAI during session creation
async def create_session():
    # ...
    openai_client = OpenAIWebRTCClient(
        api_key=api_key,
        tools=VOICE_TOOLS,  # Register tools
        # ...
    )
```

### Function Execution

```python
async def handle_function_call(session_id: str, event: dict):
    """Handle function calls from OpenAI"""
    function_name = event.get("name")
    arguments = event.get("arguments", {})
    call_id = event.get("call_id")

    logger.info(f"Function call: {function_name}({arguments})")

    result = None
    error = None

    try:
        if function_name == "send_to_nested":
            result = await execute_nested_team(
                session_id=session_id,
                text=arguments.get("text")
            )

        elif function_name == "send_to_claude_code":
            result = await execute_claude_code(
                session_id=session_id,
                text=arguments.get("text")
            )

        else:
            error = f"Unknown function: {function_name}"

    except Exception as e:
        logger.error(f"Function execution error: {e}")
        error = str(e)

    # Send result back to OpenAI
    await send_function_result(session_id, call_id, result, error)


async def send_function_result(
    session_id: str,
    call_id: str,
    result: Optional[str],
    error: Optional[str]
):
    """Send function call result to OpenAI"""
    if session_id not in sessions:
        return

    openai_client = sessions[session_id]["openai_client"]

    # Send via OpenAI's protocol (depends on their implementation)
    # This is a placeholder - actual implementation depends on OpenAI's docs
    await openai_client.send_function_result(call_id, result, error)
```

**Key advantage:** No frontend involvement! Backend handles everything.

---

## Testing Plan

### Unit Tests

```bash
# backend/tests/test_backend_webrtc.py

import pytest
from api.openai_webrtc_client import OpenAIWebRTCClient
from api.frontend_audio_handler import FrontendAudioHandler

@pytest.mark.asyncio
async def test_openai_client_connect():
    """Test OpenAI WebRTC connection"""
    client = OpenAIWebRTCClient(api_key="test_key")
    # Mock OpenAI API
    # Assert connection succeeds


@pytest.mark.asyncio
async def test_frontend_handler_sdp():
    """Test SDP exchange with frontend"""
    handler = FrontendAudioHandler(session_id="test")
    offer_sdp = "v=0\no=- ..."  # Valid SDP
    answer_sdp = await handler.handle_sdp_offer(offer_sdp)
    assert answer_sdp is not None
    assert "a=sendrecv" in answer_sdp


def test_audio_mixing():
    """Test audio stream mixing"""
    import numpy as np
    from api.realtime_voice_webrtc import mix_audio_streams

    # Create test streams
    stream1 = np.array([100, 200, 300], dtype=np.int16).tobytes()
    stream2 = np.array([200, 300, 400], dtype=np.int16).tobytes()

    mixed = mix_audio_streams([stream1, stream2])
    mixed_array = np.frombuffer(mixed, dtype=np.int16)

    expected = np.array([150, 250, 350], dtype=np.int16)
    np.testing.assert_array_equal(mixed_array, expected)
```

### Integration Tests

```bash
# backend/tests/integration/test_webrtc_e2e.py

import pytest
import asyncio
from api.realtime_voice_webrtc import create_session, exchange_sdp

@pytest.mark.asyncio
async def test_full_session_flow():
    """Test complete session creation and audio flow"""
    # Create session
    session_resp = await create_session()
    session_id = session_resp["session_id"]

    # Connect frontend
    offer_sdp = generate_test_offer()
    answer_sdp = await exchange_sdp(session_id, offer_sdp)

    assert answer_sdp is not None

    # Send test audio
    test_audio = generate_test_audio()
    # ... send via data channel ...

    # Verify audio reaches OpenAI
    # ... check logs/events ...

    # Cleanup
    await close_session(session_id)
```

### Manual Testing

```bash
# 1. Start backend
cd backend
source venv/bin/activate
uvicorn main:app --reload

# 2. Start frontend
cd frontend
npm start

# 3. Open browser
http://localhost:3000/voice

# 4. Click "Start Session"
# Expected: Session created, WebRTC connected

# 5. Click "Unmute"
# Expected: Microphone active, audio streaming

# 6. Speak: "Hello Archie"
# Expected: OpenAI responds with greeting

# 7. Speak: "Create a new file called test.txt"
# Expected: send_to_claude_code function called
#          Claude Code creates file
#          OpenAI confirms completion

# 8. Open mobile
http://192.168.x.x:3000/mobile-voice

# 9. Select same conversation
# Expected: Desktop + mobile both active
#          Both receive OpenAI audio
#          Either can speak (audio mixed)

# 10. Click "Stop" on desktop
# Expected: Session closes gracefully
#          Mobile disconnects
```

---

## Deployment Strategy

### Development Environment

```bash
# Install dependencies
cd backend
pip install aiortc numpy aiohttp

# Start backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend already running
cd frontend
npm start
```

### Staging Deployment

```bash
# 1. Update requirements.txt
cd /home/rodrigo/agentic/backend
echo "aiortc>=1.6.0" >> requirements.txt
echo "aiohttp>=3.9.0" >> requirements.txt

# 2. Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# 3. Deploy code
# (Copy new files: realtime_voice_webrtc.py, etc.)

# 4. Test on staging
# Use test OpenAI API key
# Verify audio quality
# Test function calls

# 5. Monitor logs
tail -f logs/backend.log
```

### Production Deployment (Jetson Nano)

```bash
# SSH to Jetson
ssh rodrigo@192.168.0.200

# 1. Pull changes
cd ~/agentic
git pull origin main

# 2. Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 3. Restart backend service
sudo systemctl restart agentic-backend

# 4. Verify service
sudo systemctl status agentic-backend
sudo journalctl -u agentic-backend -f

# 5. Test via HTTPS
https://192.168.0.200/agentic/voice

# 6. Monitor for issues
tail -f ~/logs/nginx-error.log
```

---

## Rollback Strategy

### Immediate Rollback (If Critical Issue)

```bash
# 1. SSH to server
ssh rodrigo@192.168.0.200

# 2. Checkout previous commit
cd ~/agentic
git log --oneline  # Find previous working commit
git checkout <previous-commit-hash>

# 3. Restart backend
sudo systemctl restart agentic-backend

# 4. Verify
curl -I https://192.168.0.200/api/agents
```

### Feature Flag Rollback

```python
# backend/.env

# Add feature flag
ENABLE_BACKEND_WEBRTC=false

# In main.py
import os

if os.getenv("ENABLE_BACKEND_WEBRTC") == "true":
    # Use new backend WebRTC
    from api.realtime_voice_webrtc import router
    app.include_router(router)
else:
    # Use existing frontend WebRTC
    from api.realtime_voice import router
    app.include_router(router)
```

### Database Rollback

```bash
# Voice conversations are stored in SQLite
# Backup before deployment

cd /home/rodrigo/agentic/backend

# Backup
cp voice_conversations.db voice_conversations.db.backup_$(date +%Y%m%d_%H%M%S)

# If rollback needed
cp voice_conversations.db.backup_YYYYMMDD_HHMMSS voice_conversations.db
```

---

## Timeline and Milestones

### Week 1: Backend Prototyping

**Days 1-2: OpenAI WebRTC Client**
- [ ] Implement `OpenAIWebRTCClient` class
- [ ] Test connection to OpenAI
- [ ] Verify audio send/receive
- [ ] Handle function calls

**Days 3-4: Frontend Audio Handler**
- [ ] Implement `FrontendAudioHandler` class
- [ ] Test SDP exchange
- [ ] Test data channel audio streaming
- [ ] Verify bidirectional audio

**Day 5: Audio Routing**
- [ ] Implement audio mixing
- [ ] Test multi-client scenarios
- [ ] Measure performance (latency, CPU)

### Week 2: Frontend & Integration

**Days 1-2: Frontend WebRTC**
- [ ] Update VoiceAssistant.js
- [ ] Remove OpenAI token logic
- [ ] Implement data channel connection
- [ ] Test audio streaming

**Days 3-4: Function Call Integration**
- [ ] Integrate nested team execution
- [ ] Integrate Claude Code execution
- [ ] Test end-to-end function calls
- [ ] Verify event flow

**Day 5: Testing & Bug Fixes**
- [ ] Run full test suite
- [ ] Fix bugs found during testing
- [ ] Performance optimization

### Week 3: Deployment & Monitoring

**Days 1-2: Staging Deployment**
- [ ] Deploy to staging environment
- [ ] Run integration tests
- [ ] Load test with multiple users
- [ ] Monitor performance metrics

**Days 3-4: Production Deployment**
- [ ] Deploy to Jetson Nano
- [ ] Test HTTPS access
- [ ] Verify mobile compatibility
- [ ] Monitor for 24 hours

**Day 5: Documentation & Handoff**
- [ ] Update CLAUDE.md
- [ ] Document troubleshooting steps
- [ ] Create user guide
- [ ] Team knowledge transfer

---

## Estimated Effort

**Total: 1-2 weeks**

- Backend implementation: 3-4 days
- Frontend implementation: 2-3 days
- Testing & integration: 2 days
- Deployment & monitoring: 2 days
- Buffer for unexpected issues: 2-3 days

---

**Last Updated:** 2025-12-02
**Status:** Planning Phase
**Next Step:** Prototype OpenAI WebRTC client

