import React, { useEffect, useRef, useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Box, useTheme, useMediaQuery } from '@mui/material';
import { getVoiceConversation } from '../../../api';
import { getWsUrl } from '../../../utils/urlBuilder';

// Import layouts (reuse from VoiceAssistantModular)
import DesktopVoiceLayout from '../components/DesktopVoiceLayout';
import MobileVoiceLayout from '../components/MobileVoiceLayout';

/**
 * VoiceAssistantPipecatWS - Pipecat + FastAPI WebSocket implementation
 *
 * Self-hosted voice assistant using:
 * - FastAPI WebSocket for audio transport (no WebRTC, no Daily)
 * - Pipecat framework for pipeline management
 * - OpenAI Realtime API for voice AI
 *
 * Audio Flow:
 * Browser mic → PCM16 → WebSocket → Pipecat → OpenAI → Pipecat → WebSocket → Browser speaker
 *
 * Advantages over WebRTC:
 * - Much simpler (no SDP, no ICE, no STUN)
 * - Self-hosted (no external dependencies)
 * - Zero cost (no Daily fees)
 * - Full privacy (audio stays local)
 */
function VoiceAssistantPipecatWS({ nested = false, onConversationUpdate }) {
  const { conversationId } = useParams();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // ============================================
  // State
  // ============================================
  const [conversation, setConversation] = useState(null);
  const [conversationLoading, setConversationLoading] = useState(true);
  const [conversationError, setConversationError] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const [viewTab, setViewTab] = useState(0);
  const [mainTab, setMainTab] = useState(3);
  const [voiceConfig, setVoiceConfig] = useState({
    agentName: 'MainConversation',
    voice: 'alloy',
  });

  // ============================================
  // Refs
  // ============================================
  const wsRef = useRef(null); // WebSocket connection
  const audioContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const audioProcessorRef = useRef(null);
  const playbackBufferRef = useRef([]); // Queue for incoming audio
  const isPlayingRef = useRef(false);
  const nestedWsRef = useRef(null);
  const claudeCodeWsRef = useRef(null);
  const [sharedNestedWs, setSharedNestedWs] = useState(null);
  const [sharedClaudeCodeWs, setSharedClaudeCodeWs] = useState(null);

  // ============================================
  // Audio Conversion Utilities
  // ============================================

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

  // ============================================
  // Load Conversation Metadata
  // ============================================
  useEffect(() => {
    if (!conversationId) return;

    const loadConversation = async () => {
      setConversationLoading(true);
      try {
        const data = await getVoiceConversation(conversationId);
        setConversation(data);
        setConversationError(null);
      } catch (err) {
        console.error('Failed to load conversation:', err);
        setConversationError(err.message);
      } finally {
        setConversationLoading(false);
      }
    };

    loadConversation();
  }, [conversationId]);

  // ============================================
  // Audio Playback System
  // ============================================

  /**
   * Play queued audio buffers sequentially
   */
  const playNextBuffer = useCallback(() => {
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
        playNextBuffer(); // Play next buffer
      };

      source.start();
    } catch (err) {
      console.error('Error playing audio:', err);
      isPlayingRef.current = false;
      playNextBuffer(); // Try next buffer
    }
  }, [isSpeakerMuted, pcm16ToFloat32]);

  /**
   * Queue audio buffer for playback
   */
  const queueAudio = useCallback((pcm16Array) => {
    playbackBufferRef.current.push(pcm16Array);
    playNextBuffer();
  }, [playNextBuffer]);

  // ============================================
  // WebSocket Connection
  // ============================================

  const startSession = useCallback(async () => {
    try {
      setError(null);
      console.log('[WebSocket] Starting Pipecat WebSocket session...');

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
      setIsMuted(true);

      // Create WebSocket connection
      const wsUrl = getWsUrl(`/api/realtime/pipecat/ws/${conversationId}?voice=${voiceConfig.voice}&agent_name=${voiceConfig.agentName}`);
      console.log('[WebSocket] Connecting to:', wsUrl);

      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      // WebSocket event handlers
      ws.onopen = () => {
        console.log('[WebSocket] Connected to Pipecat backend');
        setIsRunning(true);
        setError(null);

        // Set up audio capture
        const source = audioContext.createMediaStreamSource(stream);

        // Use ScriptProcessor for audio capture (deprecated but widely supported)
        // TODO: Migrate to AudioWorklet for better performance
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        audioProcessorRef.current = processor;

        processor.onaudioprocess = (e) => {
          if (ws.readyState === WebSocket.OPEN && !isMuted) {
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
          queueAudio(pcm16);
        } else {
          // Received text event (function calls, transcriptions, etc.)
          try {
            const data = JSON.parse(event.data);
            console.log('[WebSocket] Event:', data);

            // Add to messages for UI display
            setMessages(prev => [...prev, data]);

            // Handle transcription
            if (data.type === 'transcription') {
              setTranscript(data.text || '');
            }
          } catch (err) {
            console.error('[WebSocket] Failed to parse message:', err);
          }
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] Error:', event);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setIsRunning(false);

        if (!event.wasClean) {
          setError(`WebSocket closed unexpectedly: ${event.reason || 'Unknown reason'}`);
        }
      };

    } catch (err) {
      console.error('[WebSocket] Start session error:', err);
      setError(err.message);
      setIsRunning(false);
    }
  }, [conversationId, voiceConfig, isMuted, float32ToPCM16, queueAudio]);

  // ============================================
  // Stop Session
  // ============================================

  const stopSession = useCallback(() => {
    console.log('[WebSocket] Stopping session...');

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

    setIsRunning(false);
    setIsMuted(false);
    setIsSpeakerMuted(false);
    setTranscript('');
  }, []);

  // ============================================
  // Toggle Mute (Microphone)
  // ============================================

  const toggleMute = useCallback(() => {
    if (micStreamRef.current) {
      micStreamRef.current.getAudioTracks().forEach(track => {
        track.enabled = !track.enabled;
      });
      setIsMuted(!isMuted);
      console.log('[Audio] Microphone', isMuted ? 'unmuted' : 'muted');
    }
  }, [isMuted]);

  // ============================================
  // Toggle Speaker Mute
  // ============================================

  const toggleSpeakerMute = useCallback(() => {
    setIsSpeakerMuted(!isSpeakerMuted);

    // Clear playback buffer when muting speaker
    if (!isSpeakerMuted) {
      playbackBufferRef.current = [];
      isPlayingRef.current = false;
    }

    console.log('[Audio] Speaker', isSpeakerMuted ? 'unmuted' : 'muted');
  }, [isSpeakerMuted]);

  // ============================================
  // Cleanup on Unmount
  // ============================================

  useEffect(() => {
    return () => {
      stopSession();
    };
  }, [stopSession]);

  // ============================================
  // Render Layout
  // ============================================

  // Match VoiceAssistantModular's prop structure
  const controlPanelProps = {
    isRunning,
    isMuted,
    isSpeakerMuted,
    sessionLocked: false,
    remoteSessionActive: false,
    noMicrophoneMode: false,
    voiceConfig,
    setConfigEditorOpen: () => {},
    conversationError,
    error,
    transcript,
    setTranscript,
    onSendToVoice: () => {},
    onSendToNested: () => {},
    onSendToClaude: () => {},
    nestedWsConnected: !!sharedNestedWs,
    claudeCodeWsConnected: !!sharedClaudeCodeWs,
    onStart: startSession,
    onStop: stopSession,
    onToggleMute: toggleMute,
    onToggleSpeakerMute: toggleSpeakerMute,
    conversationLoading,
    messages,
    formatTimestamp: (ts) => new Date(ts).toLocaleTimeString(),
    micStream: null,
    isMobile,
  };

  if (isMobile) {
    return (
      <Box sx={{ height: '100vh', overflow: 'hidden' }}>
        <MobileVoiceLayout
          messages={messages}
          formatTimestamp={(ts) => new Date(ts).toLocaleTimeString()}
          truncateText={(text, len) => text?.length > len ? text.slice(0, len) + '...' : text}
          safeStringify={(obj) => JSON.stringify(obj)}
          sharedTeamWs={sharedNestedWs}
          agentName={voiceConfig.agentName}
          controlPanelProps={controlPanelProps}
          audioRef={null}
        />
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100vh', overflow: 'hidden' }}>
      <DesktopVoiceLayout
        messages={messages}
        formatTimestamp={(ts) => new Date(ts).toLocaleTimeString()}
        truncateText={(text, len) => text?.length > len ? text.slice(0, len) + '...' : text}
        safeStringify={(obj) => JSON.stringify(obj)}
        sharedTeamWs={sharedNestedWs}
        agentName={voiceConfig.agentName}
        controlPanelProps={controlPanelProps}
        audioRef={null}
      />
    </Box>
  );
}

export default VoiceAssistantPipecatWS;
