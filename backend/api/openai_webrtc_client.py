"""
backend/api/openai_webrtc_client.py
OpenAI Realtime API WebRTC client using aiortc
"""

import asyncio
import logging
from fractions import Fraction
from typing import Callable, List, Optional

from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
import aiohttp
import json
import numpy as np
from av import AudioFrame

logger = logging.getLogger(__name__)

class OpenAIWebRTCClient:
    """Manages WebRTC connection to OpenAI Realtime API"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-realtime",
        voice: str = "alloy",
        on_audio_callback: Optional[Callable] = None,
        on_function_call_callback: Optional[Callable] = None,
        on_event_callback: Optional[Callable] = None,
        system_prompt: Optional[str] = None,
        modalities: Optional[List[str]] = None,
        enable_server_vad: bool = True,
        initial_response: Optional[str] = "Inicie a conversa com uma breve saudação e convide a pessoa a falar.",
    ):
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.on_audio_callback = on_audio_callback
        self.on_function_call_callback = on_function_call_callback
        self.on_event_callback = on_event_callback
        self.system_prompt = system_prompt
        self.modalities = modalities or ["audio", "text"]
        self.enable_server_vad = enable_server_vad
        self.initial_response = initial_response

        self.pc: Optional[RTCPeerConnection] = None
        self.audio_track: Optional[MediaStreamTrack] = None
        self.data_channel = None
        self.session_id: Optional[str] = None
        self._data_channel_ready: asyncio.Event = asyncio.Event()

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
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"!!! Peer connection state changed: {self.pc.connectionState}")
            if self.pc.connectionState == "failed":
                logger.error("!!! Peer connection failed!")

        @self.pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            logger.info(f"!!! ICE connection state changed: {self.pc.iceConnectionState}")

        @self.pc.on("track")
        def on_track(track):
            logger.info(f"Received track: {track.kind}")
            if track.kind == "audio":
                asyncio.create_task(self._handle_audio_track(track))

        @self.pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(f"!!! DATA CHANNEL RECEIVED FROM OPENAI: {channel.label}")
            # OpenAI created a data channel (alternative path)
            self.data_channel = channel

            @channel.on("message")
            def on_message(message):
                logger.info(f"!!! DATA CHANNEL MESSAGE (from OpenAI-created channel)")
                self._handle_openai_event(json.loads(message))

        # Step 5: Exchange SDP
        await self._exchange_sdp(token)

        logger.info(f"!!! Successfully connected to OpenAI")
        logger.info(f"!!! Peer connection state: {self.pc.connectionState}")
        logger.info(f"!!! ICE connection state: {self.pc.iceConnectionState}")
        logger.info(f"!!! Data channel: {self.data_channel}")

    async def _get_ephemeral_token(self) -> str:
        """Get ephemeral token from OpenAI API"""
        url = "https://api.openai.com/v1/realtime/sessions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "voice": self.voice,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as resp:
                resp_data = await resp.json()
                logger.info(f"!!! Session response: {json.dumps(resp_data, indent=2)}")
                self.session_id = resp_data["id"]
                return resp_data["client_secret"]["value"]

    async def _exchange_sdp(self, token: str):
        """Exchange SDP offer/answer with OpenAI"""
        # Create data channel for events BEFORE creating offer
        # This is required by OpenAI's WebRTC implementation
        logger.info("Creating data channel for OpenAI events...")
        self.data_channel = self.pc.createDataChannel("oai-events")
        logger.info(f"Data channel created: {self.data_channel.label}, state: {self.data_channel.readyState}")

        # Set up state change handler
        @self.data_channel.on("open")
        def on_open():
            logger.info(f"!!! DATA CHANNEL OPENED: {self.data_channel.label}")
            try:
                session_update = {
                    "type": "session.update",
                    "session": {
                        "voice": self.voice,
                        "modalities": self.modalities,
                        # Enable input audio transcription to get user speech transcripts
                        "input_audio_transcription": {
                            "model": "whisper-1"
                        },
                    },
                }
                if self.system_prompt:
                    session_update["session"]["instructions"] = self.system_prompt

                # Configure turn detection based on enable_server_vad setting
                # When enabled: Model automatically responds when it detects end of speech
                # When disabled: Manual response.create events needed (for push-to-talk)
                if self.enable_server_vad:
                    # Use server VAD with moderate settings
                    # threshold: 0.5 (default sensitivity)
                    # silence_duration_ms: 800 (wait 0.8s of silence before responding)
                    # create_response: true (automatically respond)
                    session_update["session"]["turn_detection"] = {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 800,
                        "create_response": True
                    }
                else:
                    # Disable automatic responses - requires manual response.create events
                    session_update["session"]["turn_detection"] = None
                logger.info(f"!!! Sending session.update with transcription enabled: {json.dumps(session_update, indent=2)}")
                self.data_channel.send(json.dumps(session_update))
                if self.initial_response:
                    initial_response = {
                        "type": "response.create",
                        "response": {"instructions": self.initial_response},
                    }
                    self.data_channel.send(json.dumps(initial_response))
            finally:
                self._data_channel_ready.set()

        @self.data_channel.on("close")
        def on_close():
            logger.warning(f"!!! DATA CHANNEL CLOSED: {self.data_channel.label}")

        @self.data_channel.on("error")
        def on_error(error):
            logger.error(f"!!! DATA CHANNEL ERROR: {error}")

        # Set up message handler
        @self.data_channel.on("message")
        def on_message(message):
            logger.info(f"!!! DATA CHANNEL MESSAGE RECEIVED (client-created channel)")
            logger.info(f"!!! Message type: {type(message)}, length: {len(message) if hasattr(message, '__len__') else 'N/A'}")
            logger.info(f"!!! Message preview: {str(message)[:200]}...")
            try:
                event = json.loads(message)
                logger.info(f"!!! Event parsed successfully: {event.get('type')}")
                self._handle_openai_event(event)
                logger.info(f"!!! Event handled successfully")
            except Exception as e:
                logger.error(f"!!! Error handling data channel message: {e}")
                logger.error(f"!!! Full message: {message}")
                import traceback
                logger.error(f"!!! Traceback: {traceback.format_exc()}")

        # Create offer (must be AFTER data channel creation)
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)

        # Wait for ICE gathering to avoid missing candidates in SDP
        await wait_for_ice_gathering_complete(self.pc)

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
        frame_count = 0
        while True:
            try:
                frame = await track.recv()
                frame_count += 1

                # Log first frame to debug audio parameters
                if frame_count == 1:
                    sr = getattr(frame, "sample_rate", None)
                    samples = getattr(frame, "samples", None)
                    format_str = getattr(frame, "format", None)
                    layout = getattr(frame, "layout", None)
                    logger.info(f"[OpenAI Audio] First frame: sample_rate={sr}, samples={samples}, format={format_str}, layout={layout}")

                # Forward raw audio frame to callback
                if self.on_audio_callback:
                    if asyncio.iscoroutinefunction(self.on_audio_callback):
                        await self.on_audio_callback(frame)
                    else:
                        self.on_audio_callback(frame)

            except Exception as e:
                logger.error(f"Error receiving audio: {e}")
                break

    def _handle_openai_event(self, event: dict):
        """Handle events from OpenAI data channel"""
        event_type = event.get("type")
        logger.info(f"!!! OpenAI Event: {event_type}")

        # Record all events
        if self.on_event_callback:
            logger.info(f"!!! Calling event callback for: {event_type}")
            self.on_event_callback(event)
        else:
            logger.warning(f"!!! No event callback registered!")

        if event_type == "response.function_call_arguments.done":
            # Function call received
            if self.on_function_call_callback:
                asyncio.create_task(
                    self.on_function_call_callback(event)
                )

        elif event_type == "error":
            logger.error(f"OpenAI error: {event}")

    async def send_audio_frame(self, audio_data):
        """Send audio to OpenAI"""
        if self.audio_track:
            await self.audio_track.send(audio_data)
            # Log first few frames
            if not hasattr(self, '_sent_frame_count'):
                self._sent_frame_count = 0
            self._sent_frame_count += 1
            if self._sent_frame_count <= 3:
                logger.info(f"[OpenAI Client] Sent audio frame #{self._sent_frame_count} to OpenAI")
        else:
            logger.warning("[OpenAI Client] No audio_track available, cannot send audio to OpenAI")

    async def send_audio(self, audio_data: bytes):
        """Compatibility wrapper for sending raw PCM bytes"""
        await self.send_audio_frame(audio_data)

    async def commit_audio_buffer(self):
        """
        Manually commit the audio buffer and trigger a response.
        Used in MANUAL MODE when turn detection is disabled.
        This tells OpenAI: "User is done speaking, please respond now."
        """
        if not self.data_channel or self.data_channel.readyState != "open":
            logger.warning("[OpenAI Client] Cannot commit audio - data channel not open")
            return

        logger.info("[OpenAI Client] 🎤 Committing audio buffer (user done speaking)")
        self.data_channel.send(json.dumps({
            "type": "input_audio_buffer.commit"
        }))

        # Immediately request a response
        self.data_channel.send(json.dumps({
            "type": "response.create"
        }))

    async def send_function_result(self, call_id: str, result: str):
        """Send function call result to OpenAI"""
        if not self.data_channel:
            return

        payload = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result)
            }
        }

        if not self._data_channel_ready.is_set():
            logger.warning("Data channel not marked ready; sending function result anyway.")

        try:
            self.data_channel.send(json.dumps(payload))
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to send function result over data channel: %s", exc)
            raise

    async def send_text(self, text: str, timeout: float = 5.0) -> None:
        """Send a user text message over the Realtime data channel."""
        if not text:
            return
        if not self.data_channel:
            raise RuntimeError("Data channel is not ready")

        try:
            await asyncio.wait_for(self._data_channel_ready.wait(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("Data channel not ready") from exc

        payloads = [
            {"type": "conversation.item.create", "item": {"type": "input_text", "text": text}},
            {"type": "response.create", "response": {"modalities": self.modalities}},
        ]

        for payload in payloads:
            try:
                self.data_channel.send(json.dumps(payload))
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to send payload over data channel: %s", exc)
                raise

    async def close(self):
        """Close connection"""
        if self.pc:
            await self.pc.close()
            logger.info("Closed OpenAI connection")


class AudioTrack(MediaStreamTrack):
    """Custom audio track for sending audio to OpenAI"""
    kind = "audio"

    def __init__(self, sample_rate: int = 48000):
        super().__init__()
        # CRITICAL: OpenAI expects 48000 Hz input audio (despite docs saying 24000 Hz)
        # Sending 24000 Hz causes OpenAI to interpret it incorrectly
        self.queue = asyncio.Queue()
        self._timestamp = 0
        self._sample_rate = sample_rate

    async def recv(self):
        """Called by aiortc to get next audio frame"""
        frame = await self.queue.get()
        return frame

    def _ensure_frame(self, audio_data) -> AudioFrame:
        """Normalize incoming audio to AudioFrame with correct timing"""
        if isinstance(audio_data, AudioFrame):
            sample_rate = getattr(audio_data, "sample_rate", None) or self._sample_rate
            array = audio_data.to_ndarray()
        else:
            sample_rate = self._sample_rate
            array = np.frombuffer(audio_data, dtype=np.int16).reshape(1, -1)

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


async def wait_for_ice_gathering_complete(pc: RTCPeerConnection, timeout: float = 10.0) -> None:
    """Wait for ICE gathering to complete with a timeout."""
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
        logger.warning("ICE gathering timeout reached; proceeding with current SDP")
