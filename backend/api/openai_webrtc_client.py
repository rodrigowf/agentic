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
import numpy as np
from av import AudioFrame

logger = logging.getLogger(__name__)

class OpenAIWebRTCClient:
    """Manages WebRTC connection to OpenAI Realtime API"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-realtime-preview-2024-12-17",
        voice: str = "alloy",
        on_audio_callback: Optional[Callable] = None,
        on_function_call_callback: Optional[Callable] = None,
        on_event_callback: Optional[Callable] = None
    ):
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.on_audio_callback = on_audio_callback
        self.on_function_call_callback = on_function_call_callback
        self.on_event_callback = on_event_callback

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
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "voice": self.voice
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
                    # Convert to PCM16 bytes
                    pcm16 = (audio_data * 32767).astype(np.int16)

                    # Call callback (handle both sync and async)
                    if asyncio.iscoroutinefunction(self.on_audio_callback):
                        await self.on_audio_callback(pcm16.tobytes())
                    else:
                        self.on_audio_callback(pcm16.tobytes())

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
        self._timestamp = 0
        self._sample_rate = 24000  # OpenAI uses 24kHz

    async def recv(self):
        """Called by aiortc to get next audio frame"""
        audio_data = await self.queue.get()

        # Convert bytes to numpy array (PCM16)
        pcm16 = np.frombuffer(audio_data, dtype=np.int16)

        # Create AudioFrame with s16 format (required by Opus encoder)
        frame = AudioFrame.from_ndarray(
            pcm16.reshape(1, -1),  # (channels, samples)
            format='s16',  # Signed 16-bit (required by Opus encoder)
            layout='mono'
        )
        frame.sample_rate = self._sample_rate
        frame.pts = self._timestamp

        # Update timestamp
        self._timestamp += frame.samples

        return frame

    async def send(self, audio_data: bytes):
        """Send audio frame"""
        await self.queue.put(audio_data)
