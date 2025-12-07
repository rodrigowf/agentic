import { useRef, useCallback } from 'react';
import { getWsUrl } from '../../../utils/urlBuilder';

/**
 * Mobile WebRTC signaling for desktop-mobile audio connection
 */
export const useMobileWebRTC = ({ conversationId, recordEvent, audioContextRef, mobileGainNodeRef }) => {
  const mobileAudioWsRef = useRef(null);
  const mobileWebRTCPeerRef = useRef(null);

  /**
   * Setup mobile WebRTC peer connection
   */
  const setupMobileWebRTC = useCallback((responseStream) => {
    console.log('[MobileWebRTC Setup] Starting, ws exists:', !!mobileAudioWsRef.current, ', peer exists:', !!mobileWebRTCPeerRef.current);
    if (!mobileAudioWsRef.current) {
      console.warn('[MobileWebRTC Setup] Aborted - no signaling WebSocket');
      return;
    }
    if (mobileWebRTCPeerRef.current) {
      console.warn('[MobileWebRTC Setup] Aborted - peer connection already exists');
      return;
    }

    console.log('[MobileWebRTC Setup] Creating new RTCPeerConnection...');
    const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
    mobileWebRTCPeerRef.current = pc;

    // Forward ICE candidates via signaling WS
    pc.onicecandidate = (e) => {
      if (e.candidate && mobileAudioWsRef.current?.readyState === WebSocket.OPEN) {
        mobileAudioWsRef.current.send(JSON.stringify({ type: 'candidate', candidate: e.candidate }));
      }
    };

    // When mobile sends its microphone track, mix it into desktop mixer
    pc.ontrack = (evt) => {
      const stream = evt.streams[0];
      if (!audioContextRef.current || !mobileGainNodeRef.current) return;
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(mobileGainNodeRef.current);
      console.log('[MobileWebRTC] Received mobile audio track and mixed into desktop');
    };

    // ONLY send OpenAI response audio to mobile (NOT desktop mic - prevents echo)
    if (responseStream) {
      const openAITracks = responseStream.getAudioTracks();
      console.log('[MobileWebRTC Setup] Found OpenAI response stream with', openAITracks.length, 'audio track(s)');
      for (const track of openAITracks) {
        pc.addTrack(track, responseStream);
        console.log('[MobileWebRTC Setup] Added OpenAI track - id:', track.id, 'enabled:', track.enabled, 'muted:', track.muted, 'readyState:', track.readyState);
      }
    } else {
      console.log('[MobileWebRTC Setup] No OpenAI response stream available yet');
    }

    // Create and send offer to mobile
    console.log('[MobileWebRTC Setup] Creating offer...');
    pc.createOffer({ offerToReceiveAudio: true }).then((offer) => {
      console.log('[MobileWebRTC Setup] Offer created, setting local description...');
      return pc.setLocalDescription(offer).then(() => {
        console.log('[MobileWebRTC Setup] Local description set, sending offer to mobile...');
        if (mobileAudioWsRef.current?.readyState === WebSocket.OPEN) {
          mobileAudioWsRef.current.send(JSON.stringify({ type: 'offer', sdp: offer.sdp }));
          console.log('[MobileWebRTC Setup] Offer sent successfully!');
        } else {
          console.error('[MobileWebRTC Setup] Cannot send offer - signaling WS not open, state:', mobileAudioWsRef.current?.readyState);
        }
      });
    }).catch((err) => {
      console.error('[MobileWebRTC] Failed to create/send offer', err);
    });
  }, [audioContextRef, mobileGainNodeRef]);

  /**
   * Connect to mobile signaling WebSocket
   */
  const connect = useCallback(() => {
    const mobileSignalingUrl = getWsUrl(`/realtime/webrtc-signal/${conversationId}/desktop`);
    const mobileSignalingWs = new WebSocket(mobileSignalingUrl);
    mobileAudioWsRef.current = mobileSignalingWs;

    mobileSignalingWs.onopen = () => {
      console.log('[MobileWebRTC] Desktop signaling connected');
      console.log('[MobileWebRTC] Waiting for mobile peer to join before creating offer...');
      void recordEvent('controller', 'mobile_signaling_connected', { message: 'Desktop WebRTC signaling connected' });
    };

    mobileSignalingWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        // Handle peer_joined notification
        if (msg.type === 'peer_joined') {
          if (!mobileWebRTCPeerRef.current) {
            console.log('[MobileWebRTC] Mobile peer joined! Creating offer now...');
            // Will call setupMobileWebRTC from parent with response stream
          } else {
            console.log('[MobileWebRTC] Mobile peer joined but connection already exists, ignoring');
          }
          return;
        }

        const mpc = mobileWebRTCPeerRef.current;
        if (!mpc) {
          console.warn('[MobileWebRTC] Received signaling message but peer not ready', msg.type);
          return;
        }

        if (msg.type === 'answer' && msg.sdp) {
          console.log('[MobileWebRTC] Received answer from mobile, setting remote description');
          mpc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: msg.sdp }))
            .then(() => console.log('[MobileWebRTC] Remote description set successfully'))
            .catch(err => console.error('[MobileWebRTC] Failed to set remote description:', err));
        } else if (msg.type === 'candidate' && msg.candidate) {
          console.log('[MobileWebRTC] Received ICE candidate from mobile');
          mpc.addIceCandidate(new RTCIceCandidate(msg.candidate))
            .catch(err => console.error('[MobileWebRTC] Failed to add ICE candidate:', err));
        } else {
          console.warn('[MobileWebRTC] Unknown signaling message type:', msg.type);
        }
      } catch (err) {
        console.error('[MobileWebRTC] Failed to parse signaling message:', err);
      }
    };

    mobileSignalingWs.onerror = (errEvent) => {
      console.error('[MobileWebRTC] Signaling error:', errEvent);
      void recordEvent('controller', 'mobile_signaling_error', { message: 'Desktop WebRTC signaling error' });
    };

    mobileSignalingWs.onclose = () => {
      console.log('[MobileWebRTC] Signaling closed');
      void recordEvent('controller', 'mobile_signaling_closed', { message: 'Desktop WebRTC signaling closed' });
    };

    return mobileSignalingWs;
  }, [conversationId, recordEvent]);

  /**
   * Disconnect and cleanup mobile WebRTC
   */
  const disconnect = useCallback(() => {
    if (mobileAudioWsRef.current) {
      try {
        mobileAudioWsRef.current.close();
      } catch {}
      mobileAudioWsRef.current = null;
    }
    if (mobileWebRTCPeerRef.current) {
      try {
        mobileWebRTCPeerRef.current.close();
      } catch {}
      mobileWebRTCPeerRef.current = null;
    }
  }, []);

  /**
   * Dynamically add response track for renegotiation
   */
  const addResponseTrack = useCallback((responseStream) => {
    if (mobileWebRTCPeerRef.current && responseStream) {
      console.log('[MobileWebRTC] Mobile peer exists, adding OpenAI response track dynamically');
      const tracksBefore = mobileWebRTCPeerRef.current.getSenders().length;

      for (const track of responseStream.getAudioTracks()) {
        mobileWebRTCPeerRef.current.addTrack(track, responseStream);
      }

      const tracksAfter = mobileWebRTCPeerRef.current.getSenders().length;
      console.log('[MobileWebRTC] Added OpenAI response track. Senders before:', tracksBefore, 'after:', tracksAfter);

      // Renegotiate to send the new track to mobile
      console.log('[MobileWebRTC] Starting renegotiation...');
      mobileWebRTCPeerRef.current.createOffer().then((offer) => {
        console.log('[MobileWebRTC] Renegotiation offer created');
        return mobileWebRTCPeerRef.current.setLocalDescription(offer);
      }).then(() => {
        console.log('[MobileWebRTC] Local description set for renegotiation');
        if (mobileAudioWsRef.current?.readyState === WebSocket.OPEN) {
          mobileAudioWsRef.current.send(JSON.stringify({
            type: 'offer',
            sdp: mobileWebRTCPeerRef.current.localDescription.sdp
          }));
          console.log('[MobileWebRTC] Sent renegotiation offer with OpenAI response track to mobile');
        } else {
          console.error('[MobileWebRTC] Cannot send renegotiation offer - signaling WebSocket not open, state:', mobileAudioWsRef.current?.readyState);
        }
      }).catch((err) => {
        console.error('[MobileWebRTC] Failed to renegotiate after adding track:', err);
      });
    } else {
      console.log('[MobileWebRTC] NOT adding track dynamically - mobile peer exists:', !!mobileWebRTCPeerRef.current, 'response stream exists:', !!responseStream);
    }
  }, []);

  return {
    connect,
    disconnect,
    setupMobileWebRTC,
    addResponseTrack,
    mobileAudioWsRef,
    mobileWebRTCPeerRef,
  };
};

export default useMobileWebRTC;
