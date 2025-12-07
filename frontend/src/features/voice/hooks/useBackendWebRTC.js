import { useRef, useCallback, useState } from 'react';
import { getHttpBase } from '../../../utils/urlBuilder';

/**
 * Backend WebRTC connection management for multi-frontend architecture.
 *
 * Architecture: Frontend WebRTC → Backend → OpenAI WebRTC
 * - Multiple browser tabs can connect to the same conversation
 * - Each tab gets its own WebRTC connection to the backend
 * - Backend manages ONE shared OpenAI session per conversation
 * - Audio from any browser → OpenAI
 * - Audio from OpenAI → broadcast to ALL connected browsers
 *
 * Interface:
 * - connect({ conversationId, voiceConfig, onTrack, audioStream })
 * - disconnect()
 * - getConnectionId() - returns this browser's connection ID
 * - isConnected - connection state
 */
export const useBackendWebRTC = () => {
  const peerRef = useRef(null);
  const connectionIdRef = useRef(null);
  const conversationIdRef = useRef(null);
  const audioElementRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);

  const backendBase = getHttpBase();

  /**
   * Connect to backend WebRTC
   * @param {Object} options
   * @param {string} options.conversationId - Conversation ID for event persistence
   * @param {Object} options.voiceConfig - Voice configuration (voice, agentName, systemPrompt)
   * @param {Function} options.onTrack - Callback for incoming audio tracks
   * @param {MediaStream} options.audioStream - Audio stream to send
   * @param {Function} options.onConnectionStateChange - Callback for connection state changes
   * @returns {Promise<Object>} { connectionId, peerConnection }
   */
  const connect = useCallback(async ({
    conversationId,
    voiceConfig,
    onTrack,
    audioStream,
    onConnectionStateChange,
  }) => {
    console.log('[BackendWebRTC] Connecting to conversation:', conversationId);
    conversationIdRef.current = conversationId;

    // Create peer connection
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    });
    peerRef.current = pc;

    // Handle connection state changes
    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      console.log('[BackendWebRTC] Connection state:', state);

      if (state === 'connected') {
        setIsConnected(true);
      } else if (state === 'disconnected' || state === 'failed' || state === 'closed') {
        setIsConnected(false);
      }

      if (onConnectionStateChange) {
        onConnectionStateChange(state);
      }
    };

    // Handle incoming audio tracks from backend (OpenAI assistant audio)
    pc.ontrack = (evt) => {
      console.log('[BackendWebRTC] Received audio track from backend');

      // Auto-connect to audio element if set
      if (audioElementRef.current && evt.streams[0]) {
        audioElementRef.current.srcObject = evt.streams[0];
        audioElementRef.current.play().catch((err) => {
          console.warn('[BackendWebRTC] Auto-play blocked:', err);
        });
      }

      if (onTrack) {
        onTrack(evt);
      }
    };

    // Add outgoing audio track (microphone → backend → OpenAI)
    if (audioStream) {
      for (const track of audioStream.getAudioTracks()) {
        console.log('[BackendWebRTC] Adding audio track:', track.label);
        pc.addTrack(track, audioStream);
      }
    } else {
      console.warn('[BackendWebRTC] No audio stream provided');
    }

    // Helper: wait for ICE gathering to complete
    const waitForIceGathering = () =>
      new Promise((resolve) => {
        if (pc.iceGatheringState === 'complete') return resolve();
        const check = () => {
          if (pc.iceGatheringState === 'complete') {
            pc.removeEventListener('icegatheringstatechange', check);
            resolve();
          }
        };
        pc.addEventListener('icegatheringstatechange', check);

        // Timeout after 5 seconds
        setTimeout(() => {
          pc.removeEventListener('icegatheringstatechange', check);
          resolve();
        }, 5000);
      });

    // Create SDP offer
    const offer = await pc.createOffer({ offerToReceiveAudio: true });
    await pc.setLocalDescription(offer);
    await waitForIceGathering();

    const localSdp = pc.localDescription?.sdp || offer.sdp;
    console.log('[BackendWebRTC] Sending SDP offer to backend...');

    // Send signaling request to backend
    const signalResp = await fetch(`${backendBase}/api/realtime/webrtc/signal`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: conversationId,
        offer: localSdp,
        voice: voiceConfig?.voice || 'alloy',
        agent_name: voiceConfig?.agentName || 'MainConversation',
        system_prompt: voiceConfig?.systemPromptContent || '',
      }),
    });

    if (!signalResp.ok) {
      const errorText = await signalResp.text();
      throw new Error(`Signaling failed: ${signalResp.status} ${errorText}`);
    }

    const signalData = await signalResp.json();
    const { connection_id: connectionId, answer: answerSdp } = signalData;
    connectionIdRef.current = connectionId;

    console.log('[BackendWebRTC] Received connection ID:', connectionId);
    console.log('[BackendWebRTC] Setting remote SDP answer...');

    // Set remote description
    await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

    console.log('[BackendWebRTC] ✅ WebRTC connection established');
    setIsConnected(true);

    return { connectionId, peerConnection: pc };
  }, [backendBase]);

  /**
   * Disconnect this browser from the conversation.
   * Other browsers remain connected.
   */
  const disconnect = useCallback(async () => {
    console.log('[BackendWebRTC] Disconnecting...');

    // Close local peer connection
    if (peerRef.current) {
      // Stop all tracks
      peerRef.current.getSenders().forEach((sender) => {
        if (sender.track) {
          sender.track.stop();
        }
      });

      try {
        peerRef.current.close();
      } catch (err) {
        console.warn('[BackendWebRTC] Error closing peer:', err);
      }
      peerRef.current = null;
    }

    // Notify backend to remove this connection
    if (connectionIdRef.current) {
      try {
        await fetch(`${backendBase}/api/realtime/webrtc/disconnect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ connection_id: connectionIdRef.current }),
        });
        console.log('[BackendWebRTC] Notified backend of disconnect');
      } catch (err) {
        console.warn('[BackendWebRTC] Failed to notify backend:', err);
      }
      connectionIdRef.current = null;
    }

    conversationIdRef.current = null;
    setIsConnected(false);
    console.log('[BackendWebRTC] Disconnected');
  }, [backendBase]);

  /**
   * Stop the entire conversation (closes all browsers + OpenAI session)
   */
  const stopConversation = useCallback(async () => {
    const conversationId = conversationIdRef.current;
    if (!conversationId) {
      console.warn('[BackendWebRTC] No conversation to stop');
      return;
    }

    console.log('[BackendWebRTC] Stopping entire conversation:', conversationId);

    // Close local connection first
    if (peerRef.current) {
      peerRef.current.getSenders().forEach((sender) => {
        if (sender.track) sender.track.stop();
      });
      try {
        peerRef.current.close();
      } catch {}
      peerRef.current = null;
    }

    // Tell backend to stop the conversation
    try {
      await fetch(`${backendBase}/api/realtime/webrtc/conversation/${conversationId}`, {
        method: 'DELETE',
      });
      console.log('[BackendWebRTC] Conversation stopped');
    } catch (err) {
      console.warn('[BackendWebRTC] Failed to stop conversation:', err);
    }

    connectionIdRef.current = null;
    conversationIdRef.current = null;
    setIsConnected(false);
  }, [backendBase]);

  /**
   * Get current connection ID
   */
  const getConnectionId = useCallback(() => connectionIdRef.current, []);

  /**
   * Get current conversation ID
   */
  const getConversationId = useCallback(() => conversationIdRef.current, []);

  /**
   * Set audio element for auto-playback
   */
  const setAudioElement = useCallback((element) => {
    audioElementRef.current = element;
  }, []);

  /**
   * Send text message to the conversation
   */
  const sendText = useCallback(async (text) => {
    const conversationId = conversationIdRef.current;
    if (!conversationId) {
      console.warn('[BackendWebRTC] No active conversation');
      return;
    }

    try {
      await fetch(`${backendBase}/api/realtime/webrtc/conversation/${conversationId}/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
    } catch (err) {
      console.error('[BackendWebRTC] Failed to send text:', err);
    }
  }, [backendBase]);

  /**
   * Commit audio buffer (manual VAD mode)
   */
  const commitAudio = useCallback(async () => {
    const conversationId = conversationIdRef.current;
    if (!conversationId) return;

    try {
      await fetch(`${backendBase}/api/realtime/webrtc/conversation/${conversationId}/commit`, {
        method: 'POST',
      });
    } catch (err) {
      console.error('[BackendWebRTC] Failed to commit audio:', err);
    }
  }, [backendBase]);

  /**
   * Get conversation status from backend
   */
  const getStatus = useCallback(async () => {
    const conversationId = conversationIdRef.current;
    if (!conversationId) return null;

    try {
      const resp = await fetch(
        `${backendBase}/api/realtime/webrtc/conversation/${conversationId}/status`
      );
      if (resp.ok) {
        return await resp.json();
      }
    } catch (err) {
      console.error('[BackendWebRTC] Failed to get status:', err);
    }
    return null;
  }, [backendBase]);

  return {
    // Connection management
    connect,
    disconnect,
    stopConversation,

    // State
    isConnected,
    getConnectionId,
    getConversationId,

    // Audio
    setAudioElement,
    peerRef,

    // Actions
    sendText,
    commitAudio,
    getStatus,
  };
};

export default useBackendWebRTC;
