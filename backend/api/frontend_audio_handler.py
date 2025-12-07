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

        # Handle incoming audio tracks from frontend
        @self.pc.on("track")
        def on_track(track):
            logger.info(f"Received audio track from frontend: {track.kind}")

            if track.kind == "audio":
                # Start receiving audio frames
                asyncio.create_task(self._receive_audio(track))

        # Set remote description (offer from frontend)
        offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
        await self.pc.setRemoteDescription(offer)

        # Create answer
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        logger.info("SDP answer created")
        return self.pc.localDescription.sdp

    async def _receive_audio(self, track):
        """Receive audio frames from frontend track"""
        try:
            while True:
                frame = await track.recv()

                # Convert frame to bytes (PCM audio)
                # aiortc provides AudioFrame objects
                if hasattr(frame, 'to_ndarray'):
                    import numpy as np
                    audio_array = frame.to_ndarray()
                    audio_bytes = audio_array.tobytes()

                    # Forward to callback
                    if self.on_audio_callback:
                        await self.on_audio_callback(audio_bytes)
        except Exception as e:
            logger.error(f"Error receiving audio from frontend: {e}")

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
