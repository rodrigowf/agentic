"""
backend/api/browser_connection_manager.py

BrowserConnectionManager - Manages N frontend WebRTC connections per conversation.

Architecture:
- Each conversation can have multiple browser tabs connected
- Each browser connection has its own RTCPeerConnection
- Audio from browsers is forwarded to the shared OpenAI session
- Audio from OpenAI is broadcast to ALL connected browsers
- Browsers can connect/disconnect independently without affecting others
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Awaitable, Callable, Dict, Optional, Set

import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import AudioFrame, AudioResampler

from .openai_webrtc_client import wait_for_ice_gathering_complete

logger = logging.getLogger(__name__)


class AudioFrameSourceTrack(MediaStreamTrack):
    """
    Audio source track that feeds AudioFrames to a browser peer connection.
    Used to send OpenAI assistant audio to the browser.
    """

    kind = "audio"

    def __init__(self, sample_rate: int = 48000):
        super().__init__()
        self.sample_rate = sample_rate
        self.queue: asyncio.Queue[AudioFrame] = asyncio.Queue()
        self._timestamp = 0
        self._frame_count = 0

    def _to_mono(self, frame: AudioFrame) -> AudioFrame:
        """Convert frame to mono with proper timestamps."""
        try:
            if frame.layout.name == "mono":
                mono = frame
            else:
                resampler = AudioResampler(format="s16", layout="mono")
                mono_frames = resampler.resample(frame)
                mono = next(iter(mono_frames))

            sr = getattr(frame, "sample_rate", None) or self.sample_rate
            mono.sample_rate = sr
            mono.time_base = Fraction(1, sr)
            mono.pts = self._timestamp
            self._timestamp += mono.samples

            return mono
        except Exception as exc:
            logger.error(f"Failed to normalize audio frame: {exc}")
            return frame

    async def send_frame(self, frame: AudioFrame) -> None:
        """Queue a frame for sending to the browser."""
        self._frame_count += 1
        await self.queue.put(self._to_mono(frame))

    async def recv(self) -> AudioFrame:
        """Called by aiortc to get the next frame."""
        return await self.queue.get()


@dataclass
class BrowserConnection:
    """Represents a single browser WebRTC connection."""

    connection_id: str
    conversation_id: str
    pc: RTCPeerConnection
    audio_source: AudioFrameSourceTrack
    audio_forward_task: Optional[asyncio.Task] = None
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())

    async def send_audio(self, frame: AudioFrame) -> None:
        """Send audio frame to this browser."""
        await self.audio_source.send_frame(frame)

    async def close(self) -> None:
        """Close this browser connection."""
        if self.audio_forward_task:
            self.audio_forward_task.cancel()
            try:
                await self.audio_forward_task
            except asyncio.CancelledError:
                pass

        try:
            await self.pc.close()
        except Exception as exc:
            logger.error(f"Error closing peer connection {self.connection_id}: {exc}")


class BrowserConnectionManager:
    """
    Manages multiple browser WebRTC connections for a single conversation.

    Each conversation has one BrowserConnectionManager that:
    - Tracks all connected browser tabs
    - Forwards browser audio to the OpenAI session
    - Broadcasts OpenAI audio to all connected browsers
    """

    def __init__(
        self,
        conversation_id: str,
        on_browser_audio: Optional[Callable[[AudioFrame], Awaitable[None]]] = None,
    ):
        """
        Initialize the connection manager.

        Args:
            conversation_id: The conversation this manager belongs to
            on_browser_audio: Callback when audio received from any browser
                             (used to forward to OpenAI session)
        """
        self.conversation_id = conversation_id
        self.on_browser_audio = on_browser_audio
        self._connections: Dict[str, BrowserConnection] = {}
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        """Number of active browser connections."""
        return len(self._connections)

    @property
    def connection_ids(self) -> Set[str]:
        """Set of active connection IDs."""
        return set(self._connections.keys())

    async def add_connection(self, offer_sdp: str) -> tuple[str, str]:
        """
        Add a new browser connection.

        Args:
            offer_sdp: SDP offer from the browser

        Returns:
            Tuple of (connection_id, answer_sdp)
        """
        connection_id = str(uuid.uuid4())
        logger.info(f"[BrowserMgr {self.conversation_id}] Adding connection {connection_id[:8]}...")

        # Create peer connection
        pc = RTCPeerConnection()

        # Create audio source track for sending OpenAI audio to browser
        audio_source = AudioFrameSourceTrack(sample_rate=48000)
        pc.addTrack(audio_source)

        # Set up track handler for receiving browser audio
        audio_forward_task = None

        @pc.on("track")
        def on_track(track: MediaStreamTrack):
            nonlocal audio_forward_task
            if track.kind == "audio":
                logger.info(f"[BrowserMgr {self.conversation_id}] Audio track from {connection_id[:8]}")
                audio_forward_task = asyncio.create_task(
                    self._forward_browser_audio(connection_id, track)
                )
                # Store task reference in connection
                conn = self._connections.get(connection_id)
                if conn:
                    conn.audio_forward_task = audio_forward_task

        @pc.on("connectionstatechange")
        async def on_state_change():
            state = pc.connectionState
            logger.info(f"[BrowserMgr {self.conversation_id}] Connection {connection_id[:8]} state: {state}")
            if state in ("failed", "closed", "disconnected"):
                # Auto-cleanup on disconnect
                await self.remove_connection(connection_id)

        # Process SDP offer
        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))

        # Check for existing tracks (some browsers include them before ontrack fires)
        for transceiver in pc.getTransceivers():
            if transceiver.receiver and transceiver.receiver.track:
                track = transceiver.receiver.track
                if track.kind == "audio" and audio_forward_task is None:
                    logger.info(f"[BrowserMgr {self.conversation_id}] Found existing audio track")
                    audio_forward_task = asyncio.create_task(
                        self._forward_browser_audio(connection_id, track)
                    )

        # Create and send answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await wait_for_ice_gathering_complete(pc)

        answer_sdp = pc.localDescription.sdp if pc.localDescription else answer.sdp

        # Store connection
        connection = BrowserConnection(
            connection_id=connection_id,
            conversation_id=self.conversation_id,
            pc=pc,
            audio_source=audio_source,
            audio_forward_task=audio_forward_task,
        )

        async with self._lock:
            self._connections[connection_id] = connection

        logger.info(f"[BrowserMgr {self.conversation_id}] ✅ Connection {connection_id[:8]} added (total: {self.connection_count})")

        return connection_id, answer_sdp

    async def remove_connection(self, connection_id: str) -> bool:
        """
        Remove a browser connection.

        Args:
            connection_id: ID of the connection to remove

        Returns:
            True if connection was removed, False if not found
        """
        async with self._lock:
            connection = self._connections.pop(connection_id, None)

        if connection:
            await connection.close()
            logger.info(f"[BrowserMgr {self.conversation_id}] Connection {connection_id[:8]} removed (remaining: {self.connection_count})")
            return True

        return False

    async def broadcast_audio(self, frame: AudioFrame) -> None:
        """
        Broadcast audio frame to ALL connected browsers.

        Called when OpenAI sends assistant audio.
        """
        async with self._lock:
            connections = list(self._connections.values())

        if not connections:
            return

        # Send to all connections in parallel
        tasks = [conn.send_audio(frame) for conn in connections]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _forward_browser_audio(self, connection_id: str, track: MediaStreamTrack) -> None:
        """
        Forward audio from a browser to the OpenAI session.

        Args:
            connection_id: ID of the source connection
            track: Audio track from the browser
        """
        frame_count = 0
        try:
            while True:
                frame = await track.recv()
                frame_count += 1

                # Log first frame and periodic stats
                if frame_count == 1:
                    array = frame.to_ndarray()
                    logger.info(f"[BrowserMgr {self.conversation_id}] First frame from {connection_id[:8]}:")
                    logger.info(f"  samples={frame.samples}, rate={frame.sample_rate}, layout={frame.layout.name}")
                    logger.info(f"  Array shape: {array.shape}, non-zero: {np.count_nonzero(array)}/{array.size}")

                if frame_count % 100 == 0:
                    logger.debug(f"[BrowserMgr {self.conversation_id}] Forwarded {frame_count} frames from {connection_id[:8]}")

                # Forward to OpenAI session
                if self.on_browser_audio:
                    await self.on_browser_audio(frame)

        except asyncio.CancelledError:
            logger.info(f"[BrowserMgr {self.conversation_id}] Audio forwarding stopped for {connection_id[:8]} after {frame_count} frames")
        except Exception as exc:
            logger.error(f"[BrowserMgr {self.conversation_id}] Error forwarding audio from {connection_id[:8]}: {exc}")

    async def close_all(self) -> None:
        """Close all browser connections."""
        async with self._lock:
            connections = list(self._connections.values())
            self._connections.clear()

        for conn in connections:
            try:
                await conn.close()
            except Exception as exc:
                logger.error(f"Error closing connection {conn.connection_id}: {exc}")

        logger.info(f"[BrowserMgr {self.conversation_id}] All connections closed")

    def get_connection(self, connection_id: str) -> Optional[BrowserConnection]:
        """Get a specific connection by ID."""
        return self._connections.get(connection_id)


# ============================================================================
# Per-Conversation Manager Registry
# ============================================================================

_managers: Dict[str, BrowserConnectionManager] = {}
_managers_lock = asyncio.Lock()


async def get_or_create_manager(
    conversation_id: str,
    on_browser_audio: Optional[Callable] = None,
) -> BrowserConnectionManager:
    """
    Get or create a BrowserConnectionManager for a conversation.

    Args:
        conversation_id: Conversation ID
        on_browser_audio: Callback for browser audio

    Returns:
        BrowserConnectionManager for the conversation
    """
    async with _managers_lock:
        if conversation_id not in _managers:
            _managers[conversation_id] = BrowserConnectionManager(
                conversation_id=conversation_id,
                on_browser_audio=on_browser_audio,
            )
            logger.info(f"[BrowserMgr] Created manager for conversation {conversation_id}")
        else:
            # Update callback if provided
            if on_browser_audio:
                _managers[conversation_id].on_browser_audio = on_browser_audio
        return _managers[conversation_id]


async def get_manager(conversation_id: str) -> Optional[BrowserConnectionManager]:
    """Get existing manager for a conversation (if any)."""
    async with _managers_lock:
        return _managers.get(conversation_id)


async def remove_manager(conversation_id: str) -> bool:
    """Remove and close manager for a conversation."""
    async with _managers_lock:
        manager = _managers.pop(conversation_id, None)

    if manager:
        await manager.close_all()
        return True
    return False
