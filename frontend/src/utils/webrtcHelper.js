/**
 * WebRTC Helper for Peer-to-Peer Audio Connection
 *
 * Provides high-quality audio streaming between desktop and mobile
 * with built-in jitter buffering, echo cancellation, and packet loss recovery.
 */

import { getWsUrl } from './urlBuilder';

export class WebRTCPeerConnection {
  constructor(conversationId, peerId, onRemoteStream, onError) {
    this.conversationId = conversationId;
    this.peerId = peerId; // "desktop" or "mobile"
    this.onRemoteStream = onRemoteStream;
    this.onError = onError;

    this.peerConnection = null;
    this.signalingWs = null;
    this.localStream = null;
  }

  /**
   * Initialize WebRTC connection with local audio stream
   */
  async connect(localStream) {
    this.localStream = localStream;

    // Create RTCPeerConnection with STUN servers for NAT traversal
    const configuration = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
      ],
    };

    this.peerConnection = new RTCPeerConnection(configuration);

    // Add local stream to peer connection
    this.localStream.getTracks().forEach(track => {
      this.peerConnection.addTrack(track, this.localStream);
    });

    // Handle remote stream
    this.peerConnection.ontrack = (event) => {
      console.log('[WebRTC] Received remote track');
      if (this.onRemoteStream) {
        this.onRemoteStream(event.streams[0]);
      }
    };

    // Handle ICE candidates
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        console.log('[WebRTC] Sending ICE candidate');
        this.sendSignaling({
          type: 'ice-candidate',
          candidate: event.candidate,
        });
      }
    };

    // Handle connection state changes
    this.peerConnection.onconnectionstatechange = () => {
      console.log('[WebRTC] Connection state:', this.peerConnection.connectionState);
      if (this.peerConnection.connectionState === 'failed') {
        if (this.onError) {
          this.onError(new Error('WebRTC connection failed'));
        }
      }
    };

    // Connect to signaling server
    await this.connectSignaling();

    // If we're the desktop, create and send offer
    if (this.peerId === 'desktop') {
      await this.createOffer();
    }
  }

  /**
   * Connect to WebSocket signaling server
   */
  async connectSignaling() {
    return new Promise((resolve, reject) => {
      const signalingUrl = getWsUrl(`/webrtc-signal/${this.conversationId}`);
      this.signalingWs = new WebSocket(signalingUrl);

      this.signalingWs.onopen = () => {
        console.log('[WebRTC] Signaling connected');
        // Register with server
        this.sendSignaling({
          type: 'register',
          peerId: this.peerId,
        });
        resolve();
      };

      this.signalingWs.onerror = (error) => {
        console.error('[WebRTC] Signaling error:', error);
        reject(error);
      };

      this.signalingWs.onmessage = async (event) => {
        try {
          const message = JSON.parse(event.data);
          await this.handleSignalingMessage(message);
        } catch (err) {
          console.error('[WebRTC] Failed to handle signaling message:', err);
        }
      };
    });
  }

  /**
   * Handle incoming signaling messages
   */
  async handleSignalingMessage(message) {
    const { type } = message;

    if (type === 'offer') {
      console.log('[WebRTC] Received offer');
      await this.peerConnection.setRemoteDescription(new RTCSessionDescription(message.sdp));
      const answer = await this.peerConnection.createAnswer();
      await this.peerConnection.setLocalDescription(answer);
      this.sendSignaling({
        type: 'answer',
        sdp: answer,
      });
    } else if (type === 'answer') {
      console.log('[WebRTC] Received answer');
      await this.peerConnection.setRemoteDescription(new RTCSessionDescription(message.sdp));
    } else if (type === 'ice-candidate') {
      console.log('[WebRTC] Received ICE candidate');
      await this.peerConnection.addIceCandidate(new RTCIceCandidate(message.candidate));
    }
  }

  /**
   * Create and send SDP offer
   */
  async createOffer() {
    try {
      const offer = await this.peerConnection.createOffer({
        offerToReceiveAudio: true,
      });
      await this.peerConnection.setLocalDescription(offer);

      this.sendSignaling({
        type: 'offer',
        sdp: offer,
      });

      console.log('[WebRTC] Sent offer');
    } catch (err) {
      console.error('[WebRTC] Failed to create offer:', err);
      if (this.onError) {
        this.onError(err);
      }
    }
  }

  /**
   * Send signaling message through WebSocket
   */
  sendSignaling(message) {
    if (this.signalingWs && this.signalingWs.readyState === WebSocket.OPEN) {
      this.signalingWs.send(JSON.stringify(message));
    } else {
      console.warn('[WebRTC] Signaling WebSocket not ready');
    }
  }

  /**
   * Close connection and cleanup
   */
  close() {
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    if (this.signalingWs) {
      this.signalingWs.close();
      this.signalingWs = null;
    }

    console.log('[WebRTC] Connection closed');
  }
}
