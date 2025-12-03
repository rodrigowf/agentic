import { useRef, useCallback, useState, useEffect } from 'react';
import { getWsUrl } from '../../../utils/urlBuilder';

/**
 * Pipecat WebSocket Audio Hook
 *
 * Self-hosted voice assistant using Pipecat + FastAPI WebSocket
 * - No Daily.co dependency
 * - No WebRTC complexity (no SDP, no ICE)
 * - Direct WebSocket audio streaming (PCM16)
 *
 * Interface contract:
 * - connect({ conversationId, voiceConfig })
 * - disconnect()
 * - queueAudio(pcm16Array) - for playback
 * - getConnectionState() - returns WebSocket readyState
 */
export const usePipecatWebSocket = () => {
  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const audioProcessorRef = useRef(null);
  const playbackBufferRef = useRef([]);
  const isPlayingRef = useRef(false);
  const [connectionState, setConnectionState] = useState('closed'); // 'connecting', 'open', 'closed', 'error'

  /**
   * Convert Float32Array (-1.0 to 1.0) to PCM16 Int16Array
   */
  const float32ToPCM16 = useCallback((float32Array) => {
    const pcm16 = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return pcm16;
  }, []);

  /**
   * Convert PCM16 Int16Array to Float32Array (-1.0 to 1.0)
   */
  const pcm16ToFloat32 = useCallback((pcm16Array) => {
    const float32 = new Float32Array(pcm16Array.length);
    for (let i = 0; i < pcm16Array.length; i++) {
      float32[i] = pcm16Array[i] / (pcm16Array[i] < 0 ? 0x8000 : 0x7FFF);
    }
    return float32;
  }, []);

  /**
   * Play queued audio buffers sequentially
   */
  const playNextBuffer = useCallback((isSpeakerMuted) => {
    if (isSpeakerMuted || !audioContextRef.current || isPlayingRef.current) return;

    if (playbackBufferRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }

    isPlayingRef.current = true;
    const pcm16 = playbackBufferRef.current.shift();

    try {
      // Convert PCM16 to Float32
      const float32 = pcm16ToFloat32(pcm16);

      // Create audio buffer
      const audioBuffer = audioContextRef.current.createBuffer(
        1, // mono
        float32.length,
        24000 // OpenAI uses 24kHz
      );
      audioBuffer.getChannelData(0).set(float32);

      // Create source and play
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);

      source.onended = () => {
        isPlayingRef.current = false;
        playNextBuffer(isSpeakerMuted); // Play next buffer
      };

      source.start();
    } catch (err) {
      console.error('[PipecatWS] Error playing audio:', err);
      isPlayingRef.current = false;
      playNextBuffer(isSpeakerMuted); // Try next buffer
    }
  }, [pcm16ToFloat32]);

  /**
   * Queue audio buffer for playback
   */
  const queueAudio = useCallback((pcm16Array, isSpeakerMuted = false) => {
    playbackBufferRef.current.push(pcm16Array);
    playNextBuffer(isSpeakerMuted);
  }, [playNextBuffer]);

  /**
   * Connect to Pipecat WebSocket backend
   * @param {Object} options
   * @param {string} options.conversationId - Conversation ID for event persistence
   * @param {Object} options.voiceConfig - Voice configuration (voice, agentName, systemPrompt)
   * @param {Function} options.onMessage - Callback for text messages (events, transcriptions)
   * @param {Function} options.onError - Callback for errors
   * @param {boolean} options.isSpeakerMuted - Speaker mute state
   * @returns {Promise<Object>} { ws, audioContext, micStream }
   */
  const connect = useCallback(async ({
    conversationId,
    voiceConfig,
    onMessage,
    onError,
    isSpeakerMuted = false,
  }) => {
    try {
      console.log('[PipecatWS] Connecting...');
      setConnectionState('connecting');

      // Create audio context
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000 // OpenAI Realtime uses 24kHz
      });
      audioContextRef.current = audioContext;

      // Get microphone
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 24000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      micStreamRef.current = stream;

      // Mute by default
      stream.getAudioTracks().forEach(track => track.enabled = false);

      // Create WebSocket connection
      const wsUrl = getWsUrl(`/api/realtime/pipecat/ws/${conversationId}?voice=${voiceConfig.voice || 'alloy'}&agent_name=${voiceConfig.agentName || 'MainConversation'}`);
      console.log('[PipecatWS] Connecting to:', wsUrl);

      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      // WebSocket event handlers
      ws.onopen = () => {
        console.log('[PipecatWS] Connected');
        setConnectionState('open');

        // Set up audio capture
        const source = audioContext.createMediaStreamSource(stream);

        // Use ScriptProcessor for audio capture (deprecated but widely supported)
        // TODO: Migrate to AudioWorklet for better performance
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        audioProcessorRef.current = processor;

        processor.onaudioprocess = (e) => {
          if (ws.readyState === WebSocket.OPEN) {
            const float32 = e.inputBuffer.getChannelData(0);
            const pcm16 = float32ToPCM16(float32);
            ws.send(pcm16.buffer);
          }
        };

        source.connect(processor);
        processor.connect(audioContext.destination);
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          // Received audio from OpenAI
          const pcm16 = new Int16Array(event.data);
          queueAudio(pcm16, isSpeakerMuted);
        } else {
          // Received text event (function calls, transcriptions, etc.)
          try {
            const data = JSON.parse(event.data);
            console.log('[PipecatWS] Event:', data);
            if (onMessage) onMessage(data);
          } catch (err) {
            console.error('[PipecatWS] Failed to parse message:', err);
          }
        }
      };

      ws.onerror = (event) => {
        console.error('[PipecatWS] Error:', event);
        setConnectionState('error');
        if (onError) onError(new Error('WebSocket connection error'));
      };

      ws.onclose = (event) => {
        console.log('[PipecatWS] Disconnected:', event.code, event.reason);
        setConnectionState('closed');

        if (!event.wasClean && onError) {
          onError(new Error(`WebSocket closed unexpectedly: ${event.reason || 'Unknown reason'}`));
        }
      };

      return { ws, audioContext, micStream: stream };

    } catch (err) {
      console.error('[PipecatWS] Connect error:', err);
      setConnectionState('error');
      if (onError) onError(err);
      throw err;
    }
  }, [float32ToPCM16, queueAudio]);

  /**
   * Disconnect from Pipecat WebSocket
   */
  const disconnect = useCallback(() => {
    console.log('[PipecatWS] Disconnecting...');

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Stop audio processor
    if (audioProcessorRef.current) {
      audioProcessorRef.current.disconnect();
      audioProcessorRef.current = null;
    }

    // Stop microphone
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(track => track.stop());
      micStreamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Clear playback buffer
    playbackBufferRef.current = [];
    isPlayingRef.current = false;

    setConnectionState('closed');
  }, []);

  /**
   * Toggle microphone mute state
   */
  const toggleMute = useCallback((isMuted) => {
    if (micStreamRef.current) {
      micStreamRef.current.getAudioTracks().forEach(track => {
        track.enabled = !isMuted;
      });
      console.log('[PipecatWS] Microphone', isMuted ? 'muted' : 'unmuted');
    }
  }, []);

  /**
   * Update speaker mute state (affects playback)
   */
  const updateSpeakerMute = useCallback((isMuted) => {
    if (isMuted) {
      // Clear playback buffer when muting speaker
      playbackBufferRef.current = [];
      isPlayingRef.current = false;
    }
    console.log('[PipecatWS] Speaker', isMuted ? 'muted' : 'unmuted');
  }, []);

  /**
   * Get connection state
   */
  const getConnectionState = useCallback(() => {
    return connectionState;
  }, [connectionState]);

  /**
   * Get WebSocket instance
   */
  const getWebSocket = useCallback(() => {
    return wsRef.current;
  }, []);

  /**
   * Get microphone stream
   */
  const getMicStream = useCallback(() => {
    return micStreamRef.current;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connect,
    disconnect,
    toggleMute,
    updateSpeakerMute,
    queueAudio,
    getConnectionState,
    getWebSocket,
    getMicStream,
    connectionState,
  };
};

export default usePipecatWebSocket;
