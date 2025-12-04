"""
backend/api/openai_webrtc_client.py

Clean, modular OpenAI Realtime API WebRTC client using aiortc.

This client manages:
- WebRTC connection to OpenAI Realtime API
- Audio streaming (bidirectional)
- Data channel for events and function calls
- Tool/function call handling
"""

import asyncio
import json
import logging
from fractions import Fraction
from typing import Callable, Dict, List, Optional

import aiohttp
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import AudioFrame

logger = logging.getLogger(__name__)

# ============================================================================
# Audio Track (Outbound to OpenAI)
# ============================================================================

class AudioTrack(MediaStreamTrack):
    """
    Custom audio track for sending audio to OpenAI.

    CRITICAL: OpenAI expects 48000 Hz input audio (not 24000 Hz as documented).
    Sending incorrect sample rates causes pitch/speed issues.
    """
    kind = "audio"

    def __init__(self, sample_rate: int = 48000):
        super().__init__()
        self.queue: asyncio.Queue[AudioFrame] = asyncio.Queue()
        self._timestamp = 0
        self._sample_rate = sample_rate
        logger.info(f"[AudioTrack] Initialized with sample_rate={sample_rate} Hz")

    async def recv(self) -> AudioFrame:
        """Called by aiortc to get next audio frame"""
        return await self.queue.get()

    def _ensure_frame(self, audio_data) -> AudioFrame:
        """Normalize incoming audio to AudioFrame with correct timing"""
        # Handle AudioFrame input
        if isinstance(audio_data, AudioFrame):
            sample_rate = getattr(audio_data, "sample_rate", None) or self._sample_rate
            array = audio_data.to_ndarray()
        # Handle raw PCM bytes
        else:
            sample_rate = self._sample_rate
            array = np.frombuffer(audio_data, dtype=np.int16).reshape(1, -1)

        # Create frame with proper timing
        frame = AudioFrame.from_ndarray(array, format="s16", layout="mono")
        frame.sample_rate = sample_rate
        frame.time_base = Fraction(1, sample_rate)
        frame.pts = self._timestamp
        self._timestamp += frame.samples

        return frame

    async def send(self, audio_data):
        """Send audio frame or raw PCM16 bytes"""
        frame = self._ensure_frame(audio_data)
        await self.queue.put(frame)


# ============================================================================
# OpenAI WebRTC Client
# ============================================================================

class OpenAIWebRTCClient:
    """
    Manages WebRTC connection to OpenAI Realtime API.

    Features:
    - Bidirectional audio streaming
    - Data channel for events and function calls
    - Configurable tools/functions
    - Session management
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-realtime",
        voice: str = "alloy",
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        modalities: Optional[List[str]] = None,
        on_audio_callback: Optional[Callable] = None,
        on_function_call_callback: Optional[Callable] = None,
        on_event_callback: Optional[Callable] = None,
        enable_server_vad: bool = True,
        enable_input_transcription: bool = True,
        initial_response: Optional[str] = None,
    ):
        """
        Initialize OpenAI WebRTC client.

        Args:
            api_key: OpenAI API key
            model: Model name (e.g., "gpt-realtime")
            voice: Voice name (e.g., "alloy", "echo", "shimmer")
            system_prompt: System instructions for the model
            tools: List of tool/function definitions
            modalities: ["audio", "text"] - supported modalities
            on_audio_callback: Called when audio received from OpenAI
            on_function_call_callback: Called when function call received
            on_event_callback: Called for all events from OpenAI
            enable_server_vad: Use server-side voice activity detection
            enable_input_transcription: Enable Whisper transcription of user audio
            initial_response: Optional greeting message
        """
        # Configuration
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.modalities = modalities or ["audio", "text"]
        self.enable_server_vad = enable_server_vad
        self.enable_input_transcription = enable_input_transcription
        self.initial_response = initial_response

        # Callbacks
        self.on_audio_callback = on_audio_callback
        self.on_function_call_callback = on_function_call_callback
        self.on_event_callback = on_event_callback

        # Connection state
        self.pc: Optional[RTCPeerConnection] = None
        self.audio_track: Optional[AudioTrack] = None
        self.data_channel = None
        self.session_id: Optional[str] = None
        self._data_channel_ready = asyncio.Event()

        # Debug counters
        self._sent_frame_count = 0

    # ========================================================================
    # Connection Management
    # ========================================================================

    async def connect(self):
        """Establish WebRTC connection to OpenAI"""
        logger.info(f"[OpenAI Client] Connecting to {self.model} with voice={self.voice}")

        # Step 1: Get ephemeral session token
        token = await self._create_session()

        # Step 2: Create peer connection
        self.pc = RTCPeerConnection()
        self._setup_peer_connection_handlers()

        # Step 3: Add outbound audio track
        self.audio_track = AudioTrack()
        self.pc.addTrack(self.audio_track)

        # Step 4: Exchange SDP (offer/answer)
        await self._exchange_sdp(token)

        logger.info(f"[OpenAI Client] ✅ Connected successfully")
        logger.info(f"[OpenAI Client]    Session ID: {self.session_id}")
        logger.info(f"[OpenAI Client]    Connection state: {self.pc.connectionState}")
        logger.info(f"[OpenAI Client]    Data channel: {self.data_channel.label if self.data_channel else 'None'}")

    async def close(self):
        """Close WebRTC connection"""
        if self.pc:
            await self.pc.close()
            logger.info("[OpenAI Client] Connection closed")

    # ========================================================================
    # Session Creation
    # ========================================================================

    async def _create_session(self) -> str:
        """Create ephemeral session and return client secret token"""
        url = "https://api.openai.com/v1/realtime/sessions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "voice": self.voice,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()

                self.session_id = data["id"]
                client_secret = data["client_secret"]["value"]

                logger.info(f"[OpenAI Client] Session created: {self.session_id}")
                return client_secret

    # ========================================================================
    # WebRTC Setup
    # ========================================================================

    def _setup_peer_connection_handlers(self):
        """Set up WebRTC peer connection event handlers"""

        @self.pc.on("connectionstatechange")
        async def on_connection_state_change():
            state = self.pc.connectionState
            logger.info(f"[OpenAI Client] Connection state: {state}")
            if state == "failed":
                logger.error("[OpenAI Client] ❌ Connection failed!")

        @self.pc.on("iceconnectionstatechange")
        async def on_ice_state_change():
            logger.info(f"[OpenAI Client] ICE state: {self.pc.iceConnectionState}")

        @self.pc.on("track")
        def on_track(track):
            logger.info(f"[OpenAI Client] 🔊 Received {track.kind} track")
            if track.kind == "audio":
                asyncio.create_task(self._handle_inbound_audio(track))

        @self.pc.on("datachannel")
        def on_datachannel(channel):
            # OpenAI may create data channel (alternative to client-created)
            logger.info(f"[OpenAI Client] Data channel received from OpenAI: {channel.label}")
            self.data_channel = channel
            self._setup_data_channel_handlers(channel)

    def _setup_data_channel_handlers(self, channel):
        """Set up data channel event handlers"""

        @channel.on("open")
        def on_open():
            logger.info(f"[OpenAI Client] ✅ Data channel opened: {channel.label}")
            self._configure_session()
            self._data_channel_ready.set()

        @channel.on("close")
        def on_close():
            logger.warning(f"[OpenAI Client] Data channel closed: {channel.label}")

        @channel.on("error")
        def on_error(error):
            logger.error(f"[OpenAI Client] Data channel error: {error}")

        @channel.on("message")
        def on_message(message):
            try:
                event = json.loads(message)
                self._handle_event(event)
            except Exception as e:
                logger.error(f"[OpenAI Client] Error handling message: {e}")
                logger.error(f"[OpenAI Client] Message: {message[:200]}...")

    def _configure_session(self):
        """Send session configuration to OpenAI after data channel opens"""
        if not self.data_channel or self.data_channel.readyState != "open":
            logger.warning("[OpenAI Client] Cannot configure - data channel not open")
            return

        # Build session update
        session_config = {
            "voice": self.voice,
            "modalities": self.modalities,
        }

        # Add system instructions
        if self.system_prompt:
            session_config["instructions"] = self.system_prompt

        # Configure tools
        if self.tools:
            session_config["tools"] = self.tools
            logger.info(f"[OpenAI Client] Registering {len(self.tools)} tools")

        # Configure turn detection (VAD)
        if self.enable_server_vad:
            session_config["turn_detection"] = {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 800,
            }
        else:
            session_config["turn_detection"] = None

        # Enable input transcription
        if self.enable_input_transcription:
            session_config["input_audio_transcription"] = {
                "model": "whisper-1"
            }

        # Send session.update
        self._send_event({
            "type": "session.update",
            "session": session_config,
        })

        # Send initial greeting if configured
        if self.initial_response:
            self._send_event({
                "type": "response.create",
                "response": {
                    "instructions": self.initial_response
                },
            })

    async def _exchange_sdp(self, token: str):
        """Exchange SDP offer/answer with OpenAI"""

        # Create data channel BEFORE creating offer (required by OpenAI)
        logger.info("[OpenAI Client] Creating data channel...")
        self.data_channel = self.pc.createDataChannel("oai-events")
        self._setup_data_channel_handlers(self.data_channel)

        # Create and set local offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)

        # Wait for ICE gathering to complete
        await _wait_for_ice_gathering(self.pc)

        # Send offer to OpenAI and get answer
        url = f"https://api.openai.com/v1/realtime?model={self.model}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/sdp",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=offer.sdp) as resp:
                resp.raise_for_status()
                answer_sdp = await resp.text()

        # Set remote description
        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await self.pc.setRemoteDescription(answer)

        logger.info("[OpenAI Client] SDP exchange complete")

    # ========================================================================
    # Audio Handling
    # ========================================================================

    async def _handle_inbound_audio(self, track: MediaStreamTrack):
        """Handle incoming audio from OpenAI (assistant speaking)"""
        frame_count = 0
        try:
            while True:
                frame = await track.recv()
                frame_count += 1

                # Log first frame for debugging
                if frame_count == 1:
                    logger.info(f"[OpenAI Client] First audio frame received:")
                    logger.info(f"[OpenAI Client]    Sample rate: {frame.sample_rate} Hz")
                    logger.info(f"[OpenAI Client]    Samples: {frame.samples}")
                    logger.info(f"[OpenAI Client]    Format: {frame.format.name}")
                    logger.info(f"[OpenAI Client]    Layout: {frame.layout.name}")

                # Forward to callback
                if self.on_audio_callback:
                    if asyncio.iscoroutinefunction(self.on_audio_callback):
                        await self.on_audio_callback(frame)
                    else:
                        self.on_audio_callback(frame)

        except Exception as e:
            logger.error(f"[OpenAI Client] Error receiving audio: {e}")

    async def send_audio_frame(self, audio_data):
        """Send audio frame or raw PCM to OpenAI (user speaking)"""
        if not self.audio_track:
            logger.warning("[OpenAI Client] No audio track - cannot send audio")
            return

        await self.audio_track.send(audio_data)

        # Log first few frames
        self._sent_frame_count += 1
        if self._sent_frame_count <= 3:
            logger.info(f"[OpenAI Client] Sent audio frame #{self._sent_frame_count} to OpenAI")

    async def send_audio(self, audio_data: bytes):
        """Compatibility wrapper for sending raw PCM bytes"""
        await self.send_audio_frame(audio_data)

    # ========================================================================
    # Event Handling
    # ========================================================================

    def _handle_event(self, event: Dict):
        """Handle events received from OpenAI data channel"""
        event_type = event.get("type")

        # Forward all events to callback
        if self.on_event_callback:
            self.on_event_callback(event)

        # Handle specific event types
        if event_type == "response.function_call_arguments.done":
            # Function call completed
            if self.on_function_call_callback:
                asyncio.create_task(self.on_function_call_callback(event))

        elif event_type == "error":
            logger.error(f"[OpenAI Client] Error event: {event.get('error', event)}")

    def _send_event(self, event: Dict):
        """Send event to OpenAI via data channel"""
        if not self.data_channel or self.data_channel.readyState != "open":
            logger.warning(f"[OpenAI Client] Cannot send event - channel not ready: {event.get('type')}")
            return

        try:
            self.data_channel.send(json.dumps(event))
        except Exception as e:
            logger.error(f"[OpenAI Client] Error sending event: {e}")
            raise

    # ========================================================================
    # Public API Methods
    # ========================================================================

    async def send_text(self, text: str, timeout: float = 5.0):
        """
        Send user text message to OpenAI.

        Args:
            text: User message text
            timeout: Seconds to wait for data channel ready
        """
        if not text.strip():
            return

        # Wait for data channel to be ready
        try:
            await asyncio.wait_for(self._data_channel_ready.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise RuntimeError("Data channel not ready after timeout")

        # Send conversation item
        self._send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "input_text",
                "text": text,
            },
        })

        # Request response
        self._send_event({
            "type": "response.create",
            "response": {
                "modalities": self.modalities,
            },
        })

        logger.info(f"[OpenAI Client] Sent text: {text[:50]}...")

    async def send_function_result(self, call_id: str, result: str):
        """
        Send function call result back to OpenAI.

        Args:
            call_id: Function call ID from OpenAI
            result: Result to send (will be JSON-encoded)
        """
        if not self._data_channel_ready.is_set():
            logger.warning("[OpenAI Client] Sending function result before channel ready")

        self._send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result),
            },
        })

        logger.info(f"[OpenAI Client] Sent function result for call_id={call_id}")

    async def commit_audio_buffer(self):
        """
        Manually commit audio buffer and request response.

        Used when turn detection is disabled (manual mode).
        Tells OpenAI: "User is done speaking, please respond now."
        """
        if not self.data_channel or self.data_channel.readyState != "open":
            logger.warning("[OpenAI Client] Cannot commit - data channel not open")
            return

        logger.info("[OpenAI Client] 🎤 Committing audio buffer (user done speaking)")

        self._send_event({"type": "input_audio_buffer.commit"})
        self._send_event({"type": "response.create"})

    async def interrupt_response(self):
        """Cancel current assistant response (user started speaking)"""
        self._send_event({"type": "response.cancel"})
        logger.info("[OpenAI Client] Response interrupted")

    async def clear_audio_buffer(self):
        """Clear uncommitted audio buffer"""
        self._send_event({"type": "input_audio_buffer.clear"})
        logger.info("[OpenAI Client] Audio buffer cleared")

    async def forward_message_to_voice(self, role: str, content: str):
        """
        Forward a message to the voice model (for nested agent integration).

        This creates a conversation item without requesting an immediate response.
        Used to feed context from nested agents into the voice model's conversation history.

        Args:
            role: Message role ('user', 'assistant', or 'system')
            content: Message content
        """
        if not self._data_channel_ready.is_set():
            logger.warning("[OpenAI Client] Cannot forward message - channel not ready")
            return

        self._send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": role,
                "content": [{"type": "input_text", "text": content}],
            },
        })

        logger.info(f"[OpenAI Client] Forwarded {role} message to voice: {content[:50]}...")


# ============================================================================
# Utility Functions
# ============================================================================

async def _wait_for_ice_gathering(pc: RTCPeerConnection, timeout: float = 10.0):
    """Wait for ICE gathering to complete"""
    if pc.iceGatheringState == "complete":
        return

    event = asyncio.Event()

    def check_state():
        if pc.iceGatheringState == "complete":
            event.set()

    pc.onicegatheringstatechange = check_state

    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("[OpenAI Client] ICE gathering timeout - proceeding anyway")


# Export for backward compatibility
wait_for_ice_gathering_complete = _wait_for_ice_gathering
