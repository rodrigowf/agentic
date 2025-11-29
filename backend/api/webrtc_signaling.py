"""
WebRTC Signaling Server for Mobile Voice

Provides signaling (SDP offer/answer exchange and ICE candidate exchange)
for peer-to-peer WebRTC audio connections between desktop and mobile.
"""

import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebRTCSignalingRoom:
    """Manages WebRTC signaling for a single conversation"""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.peers: Dict[str, WebSocket] = {}  # peerId -> WebSocket

    async def register_peer(self, peer_id: str, websocket: WebSocket):
        """Register a peer in this room"""
        self.peers[peer_id] = websocket
        logger.info(f"[WebRTC Signaling] Peer '{peer_id}' joined conversation {self.conversation_id}")
        logger.info(f"[WebRTC Signaling] Active peers: {list(self.peers.keys())}")

    async def unregister_peer(self, peer_id: str):
        """Unregister a peer from this room"""
        if peer_id in self.peers:
            del self.peers[peer_id]
            logger.info(f"[WebRTC Signaling] Peer '{peer_id}' left conversation {self.conversation_id}")
            logger.info(f"[WebRTC Signaling] Active peers: {list(self.peers.keys())}")

    async def relay_message(self, from_peer_id: str, message: dict):
        """Relay signaling message to the other peer"""
        # Send to all peers except the sender
        for peer_id, websocket in self.peers.items():
            if peer_id != from_peer_id:
                try:
                    await websocket.send_json(message)
                    logger.debug(f"[WebRTC Signaling] Relayed {message.get('type')} from {from_peer_id} to {peer_id}")
                except Exception as e:
                    logger.error(f"[WebRTC Signaling] Failed to relay to {peer_id}: {e}")

    def is_empty(self) -> bool:
        """Check if room has no peers"""
        return len(self.peers) == 0


class WebRTCSignalingManager:
    """Manages WebRTC signaling rooms for all conversations"""

    def __init__(self):
        self.rooms: Dict[str, WebRTCSignalingRoom] = {}  # conversation_id -> room

    def get_room(self, conversation_id: str) -> WebRTCSignalingRoom:
        """Get or create a signaling room for a conversation"""
        if conversation_id not in self.rooms:
            self.rooms[conversation_id] = WebRTCSignalingRoom(conversation_id)
            logger.info(f"[WebRTC Signaling] Created room for conversation {conversation_id}")
        return self.rooms[conversation_id]

    def cleanup_room(self, conversation_id: str):
        """Remove empty rooms to free memory"""
        if conversation_id in self.rooms and self.rooms[conversation_id].is_empty():
            del self.rooms[conversation_id]
            logger.info(f"[WebRTC Signaling] Cleaned up empty room {conversation_id}")


# Global signaling manager
signaling_manager = WebRTCSignalingManager()


async def handle_webrtc_signaling(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for WebRTC signaling

    Handles:
    - Peer registration
    - SDP offer/answer exchange
    - ICE candidate exchange
    """
    await websocket.accept()

    peer_id = None
    room = signaling_manager.get_room(conversation_id)

    try:
        while True:
            # Receive signaling message
            message = await websocket.receive_json()
            message_type = message.get('type')

            if message_type == 'register':
                # Register peer in room
                peer_id = message.get('peerId', 'unknown')
                await room.register_peer(peer_id, websocket)

                # Send acknowledgment
                await websocket.send_json({
                    'type': 'registered',
                    'peerId': peer_id,
                    'activePeers': list(room.peers.keys())
                })

            elif message_type in ['offer', 'answer', 'ice-candidate']:
                # Relay signaling message to other peer(s)
                if peer_id:
                    await room.relay_message(peer_id, message)
                else:
                    logger.warning(f"[WebRTC Signaling] Received {message_type} before registration")

            else:
                logger.warning(f"[WebRTC Signaling] Unknown message type: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"[WebRTC Signaling] Peer {peer_id} disconnected from {conversation_id}")
    except Exception as e:
        logger.error(f"[WebRTC Signaling] Error: {e}")
    finally:
        # Unregister peer and cleanup
        if peer_id:
            await room.unregister_peer(peer_id)
        signaling_manager.cleanup_room(conversation_id)
