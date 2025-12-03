import { useRef, useCallback } from 'react';
import { getHttpBase } from '../../../utils/urlBuilder';

/**
 * Backend WebRTC connection management
 *
 * New architecture: Frontend WebRTC → Backend → OpenAI WebRTC
 * - Backend handles event persistence
 * - All events stored in conversation database
 * - Better control over audio routing and tool execution
 *
 * Interface contract:
 * - connect({ conversationId, voiceConfig, onTrack })
 * - disconnect()
 * - sendAudio(audioData) - send audio to backend
 * - getSessionId() - returns current session ID
 */
export const useBackendWebRTC = () => {
  const peerRef = useRef(null);
  const sessionIdRef = useRef(null);
  const audioRef = useRef(null);

  const backendBase = getHttpBase();

  /**
   * Connect to backend WebRTC
   * @param {Object} options
   * @param {string} options.conversationId - Conversation ID for event persistence
   * @param {Object} options.voiceConfig - Voice configuration (voice, agentName, systemPrompt)
   * @param {Function} options.onTrack - Callback for incoming audio tracks
   * @param {MediaStream} options.audioStream - Audio stream to send
   * @returns {Promise<Object>} { sessionId, peerConnection }
   */
  const connect = useCallback(async ({
    conversationId,
    voiceConfig,
    onTrack,
    audioStream,
  }) => {
    // Create backend session
    const sessionResp = await fetch(`${backendBase}/api/realtime/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_id: conversationId,
        voice: voiceConfig.voice || 'alloy',
        agent_name: voiceConfig.agentName || 'MainConversation',
        system_prompt: voiceConfig.systemPromptContent || '',
      }),
    });

    if (!sessionResp.ok) {
      const errorText = await sessionResp.text();
      throw new Error(`Failed to create backend session: ${sessionResp.status} ${errorText}`);
    }

    const sessionData = await sessionResp.json();
    const sessionId = sessionData.session_id;
    sessionIdRef.current = sessionId;

    console.log('[BackendWebRTC] Created session:', sessionId);

    // Create peer connection
    const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
    peerRef.current = pc;

    // Handle incoming audio tracks
    pc.ontrack = (evt) => {
      console.log('[BackendWebRTC] Received audio track from backend');
      if (audioRef.current) {
        audioRef.current.srcObject = evt.streams[0];
      }
      if (onTrack) {
        onTrack(evt);
      }
    };

    // Add outgoing audio stream
    if (audioStream) {
      for (const track of audioStream.getAudioTracks()) {
        pc.addTrack(track, audioStream);
      }
    }

    // Helper: wait for ICE gathering
    const waitForIceGathering = () => new Promise((resolve) => {
      if (pc.iceGatheringState === 'complete') return resolve();
      const check = () => {
        if (pc.iceGatheringState === 'complete') {
          pc.removeEventListener('icegatheringstatechange', check);
          resolve();
        }
      };
      pc.addEventListener('icegatheringstatechange', check);
    });

    // Create offer and exchange SDP
    const offer = await pc.createOffer({ offerToReceiveAudio: true });
    await pc.setLocalDescription(offer);
    await waitForIceGathering();

    // Send SDP offer to backend
    const sdpResp = await fetch(`${backendBase}/api/realtime/sdp/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/sdp' },
      body: pc.localDescription.sdp,
    });

    if (!sdpResp.ok) {
      throw new Error(`SDP exchange failed: ${sdpResp.status}`);
    }

    const answerSdp = await sdpResp.text();

    // Set remote description
    await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

    console.log('[BackendWebRTC] WebRTC connection established');

    return { sessionId, peerConnection: pc };
  }, [backendBase]);

  /**
   * Disconnect and cleanup
   */
  const disconnect = useCallback(async () => {
    if (peerRef.current) {
      peerRef.current.getSenders().forEach((sender) => {
        if (sender.track) sender.track.stop();
      });
      try {
        peerRef.current.close();
      } catch {}
    }

    // Delete backend session
    if (sessionIdRef.current) {
      try {
        await fetch(`${backendBase}/api/realtime/session/${sessionIdRef.current}`, {
          method: 'DELETE',
        });
        console.log('[BackendWebRTC] Session deleted:', sessionIdRef.current);
      } catch (err) {
        console.warn('[BackendWebRTC] Failed to delete session:', err);
      }
    }

    peerRef.current = null;
    sessionIdRef.current = null;
  }, [backendBase]);

  /**
   * Get current session ID
   */
  const getSessionId = useCallback(() => sessionIdRef.current, []);

  /**
   * Set audio element ref for playback
   */
  const setAudioElement = useCallback((element) => {
    audioRef.current = element;
  }, []);

  return {
    connect,
    disconnect,
    getSessionId,
    setAudioElement,
    peerRef,
  };
};

export default useBackendWebRTC;
