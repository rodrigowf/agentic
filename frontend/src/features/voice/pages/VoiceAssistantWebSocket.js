import React, { useEffect, useRef, useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Box, useTheme, useMediaQuery, Drawer, IconButton } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import VoiceConfigEditor from '../components/VoiceConfigEditor';
import useTVNavigation from '../hooks/useTVNavigation';
import useKeyboardNavigation from '../../../hooks/useKeyboardNavigation';
import { getVoiceConversation, appendVoiceConversationEvent, connectVoiceConversationStream } from '../../../api';
import { getHttpBase, getWsUrl } from '../../../utils/urlBuilder';
import { truncateText, safeStringify, formatTimestamp } from '../utils/helpers';

// Import layouts
import DesktopVoiceLayout from '../components/DesktopVoiceLayout';
import MobileVoiceLayout from '../components/MobileVoiceLayout';

/**
 * VoiceAssistantWebSocket - Pipecat + FastAPI WebSocket version (self-hosted)
 *
 * This version uses Pipecat on the backend with FastAPI WebSocket transport.
 * Much simpler than WebRTC - just WebSocket + audio capture/playback.
 *
 * Key features:
 * - ✅ Self-hosted (no Daily.co or external services)
 * - ✅ Zero cost (no per-minute charges)
 * - ✅ Privacy (audio stays local)
 * - ✅ Pipecat benefits (function calling, pipeline, event handling)
 * - ✅ Simpler code (~500 lines vs 768 lines WebRTC)
 *
 * Backend: backend/api/realtime_voice_pipecat_ws.py
 * Endpoint: wss://192.168.0.200/api/realtime/pipecat/ws/{conversationId}?voice=alloy
 */
function VoiceAssistantWebSocket({ nested = false, onConversationUpdate }) {
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
  const [configEditorOpen, setConfigEditorOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [voiceConfig, setVoiceConfig] = useState({
    agentName: 'MainConversation',
    systemPromptFile: 'default.txt',
    systemPromptContent: '',
    voice: 'alloy',
  });

  // ============================================
  // Refs
  // ============================================
  const wsRef = useRef(null); // WebSocket connection to Pipecat backend
  const nestedWsRef = useRef(null); // WebSocket for nested team events
  const claudeCodeWsRef = useRef(null); // WebSocket for Claude Code events
  const [sharedNestedWs, setSharedNestedWs] = useState(null);
  const [sharedClaudeCodeWs, setSharedClaudeCodeWs] = useState(null);
  const streamRef = useRef(null); // Microphone stream
  const audioContextRef = useRef(null); // Audio context for capture/playback
  const audioProcessorRef = useRef(null); // Script processor for audio capture
  const audioSourceRef = useRef(null); // Media stream source
  const playbackQueueRef = useRef([]); // Queue for audio playback
  const isPlayingRef = useRef(false); // Playback state
  const eventsMapRef = useRef(new Map());

  // ============================================
  // Helper: Record Event
  // ============================================
  const recordEvent = useCallback(
    async (source, type, payload) => {
      console.log(`[Event] ${source}:${type}`, payload);
      // Backend records events automatically, but we can also record from frontend if needed
    },
    []
  );

  // ============================================
  // Audio Conversion Helpers
  // ============================================

  /**
   * Convert Float32Array (from AudioContext) to PCM16 Int16Array
   * OpenAI Realtime API expects PCM16 at 24kHz mono
   */
  const float32ToPCM16 = useCallback((float32Array) => {
    const pcm16 = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      // Clamp to [-1, 1]
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      // Convert to 16-bit integer
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return pcm16.buffer; // Return ArrayBuffer for WebSocket.send()
  }, []);

  /**
   * Convert PCM16 Int16Array to Float32Array for playback
   */
  const pcm16ToFloat32 = useCallback((pcm16Array) => {
    const float32 = new Float32Array(pcm16Array.length);
    for (let i = 0; i < pcm16Array.length; i++) {
      const int16 = pcm16Array[i];
      // Convert to [-1, 1] range
      float32[i] = int16 / (int16 < 0 ? 0x8000 : 0x7FFF);
    }
    return float32;
  }, []);

  // ============================================
  // Audio Playback
  // ============================================

  /**
   * Play PCM16 audio data through speakers
   */
  const playAudio = useCallback((pcm16ArrayBuffer) => {
    if (isSpeakerMuted) {
      console.log('[Audio] Skipping playback (speaker muted)');
      return;
    }

    try {
      // Ensure audio context exists
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 24000
        });
      }

      const audioContext = audioContextRef.current;

      // Convert PCM16 to Float32
      const pcm16 = new Int16Array(pcm16ArrayBuffer);
      const float32 = pcm16ToFloat32(pcm16);

      // Create audio buffer
      const audioBuffer = audioContext.createBuffer(1, float32.length, 24000);
      audioBuffer.getChannelData(0).set(float32);

      // Add to playback queue
      playbackQueueRef.current.push(audioBuffer);

      // Start playback if not already playing
      if (!isPlayingRef.current) {
        playNextChunk();
      }
    } catch (err) {
      console.error('[Audio] Playback error:', err);
    }
  }, [isSpeakerMuted, pcm16ToFloat32]);

  /**
   * Play next chunk from queue
   */
  const playNextChunk = useCallback(() => {
    if (playbackQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }

    isPlayingRef.current = true;
    const audioBuffer = playbackQueueRef.current.shift();

    const audioContext = audioContextRef.current;
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);

    // Play next chunk when this one ends
    source.onended = () => {
      playNextChunk();
    };

    source.start();
  }, []);

  // ============================================
  // Audio Capture
  // ============================================

  /**
   * Start capturing microphone audio and sending to WebSocket
   */
  const startAudioCapture = useCallback(async () => {
    try {
      console.log('[Audio] Starting microphone capture...');

      // Get microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 24000, // Match OpenAI's expected rate
          channelCount: 1, // Mono
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      streamRef.current = stream;

      // Create audio context
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000
      });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      audioSourceRef.current = source;

      // Create script processor for audio processing
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      audioProcessorRef.current = processor;

      processor.onaudioprocess = (e) => {
        // Only send if WebSocket is open and mic is not muted
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && !isMuted) {
          const inputData = e.inputBuffer.getChannelData(0);
          const pcm16 = float32ToPCM16(inputData);
          wsRef.current.send(pcm16);
        }
      };

      // Connect audio graph
      source.connect(processor);
      processor.connect(audioContext.destination);

      console.log('[Audio] Microphone capture started');
    } catch (err) {
      console.error('[Audio] Failed to start microphone:', err);
      setError(`Microphone error: ${err.message}`);
    }
  }, [isMuted, float32ToPCM16]);

  /**
   * Stop audio capture
   */
  const stopAudioCapture = useCallback(() => {
    console.log('[Audio] Stopping microphone capture...');

    // Stop microphone tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    // Disconnect audio nodes
    if (audioSourceRef.current) {
      audioSourceRef.current.disconnect();
      audioSourceRef.current = null;
    }

    if (audioProcessorRef.current) {
      audioProcessorRef.current.disconnect();
      audioProcessorRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    console.log('[Audio] Microphone capture stopped');
  }, []);

  // ============================================
  // WebSocket Connection
  // ============================================

  /**
   * Connect to Pipecat WebSocket backend
   */
  const connectWebSocket = useCallback(() => {
    try {
      const wsBaseUrl = getWsUrl();
      const wsUrl = `${wsBaseUrl}/api/realtime/pipecat/ws/${conversationId}?voice=${voiceConfig.voice}&agent_name=${voiceConfig.agentName}`;

      console.log('[WebSocket] Connecting to:', wsUrl);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] Connected to Pipecat backend');
        setIsRunning(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        // Receive audio data from backend (PCM16)
        if (event.data instanceof ArrayBuffer) {
          // Audio data - play it
          playAudio(event.data);
        } else if (typeof event.data === 'string') {
          // JSON event (transcriptions, function calls, etc.)
          try {
            const eventData = JSON.parse(event.data);
            console.log('[WebSocket] Received event:', eventData);

            // Handle different event types
            if (eventData.type === 'transcription') {
              setTranscript(prev => prev + ' ' + eventData.text);
            } else if (eventData.type === 'function_call') {
              console.log('[Function] Called:', eventData.name, eventData.arguments);
            }
          } catch (err) {
            console.warn('[WebSocket] Failed to parse event:', err);
          }
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Closed:', event.code, event.reason);
        setIsRunning(false);
        stopAudioCapture();
      };

    } catch (err) {
      console.error('[WebSocket] Connection failed:', err);
      setError(`Connection failed: ${err.message}`);
    }
  }, [conversationId, voiceConfig.voice, voiceConfig.agentName, playAudio, stopAudioCapture]);

  /**
   * Disconnect WebSocket
   */
  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) {
      console.log('[WebSocket] Disconnecting...');
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // ============================================
  // Session Control
  // ============================================

  /**
   * Start voice session
   */
  const startSession = useCallback(async () => {
    try {
      console.log('[Session] Starting...');

      // Connect WebSocket first
      connectWebSocket();

      // Wait for WebSocket to connect
      await new Promise((resolve, reject) => {
        const checkConnection = setInterval(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            clearInterval(checkConnection);
            resolve();
          }
        }, 100);

        // Timeout after 10 seconds
        setTimeout(() => {
          clearInterval(checkConnection);
          reject(new Error('WebSocket connection timeout'));
        }, 10000);
      });

      // Start audio capture
      await startAudioCapture();

      console.log('[Session] Started successfully');
      recordEvent('controller', 'session_started', { conversationId });
    } catch (err) {
      console.error('[Session] Failed to start:', err);
      setError(`Failed to start session: ${err.message}`);
      setIsRunning(false);
    }
  }, [conversationId, connectWebSocket, startAudioCapture, recordEvent]);

  /**
   * Stop voice session
   */
  const stopSession = useCallback(() => {
    console.log('[Session] Stopping...');

    // Stop audio capture
    stopAudioCapture();

    // Disconnect WebSocket
    disconnectWebSocket();

    // Clear playback queue
    playbackQueueRef.current = [];
    isPlayingRef.current = false;

    setIsRunning(false);
    console.log('[Session] Stopped');
    recordEvent('controller', 'session_stopped', { conversationId });
  }, [conversationId, stopAudioCapture, disconnectWebSocket, recordEvent]);

  /**
   * Toggle microphone mute
   */
  const toggleMute = useCallback(() => {
    setIsMuted(prev => !prev);
    console.log('[Mic]', isMuted ? 'Unmuted' : 'Muted');
  }, [isMuted]);

  /**
   * Toggle speaker mute
   */
  const toggleSpeakerMute = useCallback(() => {
    setIsSpeakerMuted(prev => !prev);
    console.log('[Speaker]', isSpeakerMuted ? 'Unmuted' : 'Muted');
  }, [isSpeakerMuted]);

  // ============================================
  // Load Conversation
  // ============================================
  useEffect(() => {
    if (!conversationId) {
      setConversationLoading(false);
      return;
    }

    const loadConversation = async () => {
      try {
        setConversationLoading(true);
        const conv = await getVoiceConversation(conversationId);
        setConversation(conv);
        setConversationError(null);
      } catch (err) {
        console.error('Failed to load conversation:', err);
        setConversationError('Failed to load conversation');
      } finally {
        setConversationLoading(false);
      }
    };

    loadConversation();
  }, [conversationId]);

  // ============================================
  // Connect to Nested Team & Claude Code WebSockets
  // ============================================
  useEffect(() => {
    if (!conversationId || !isRunning) return;

    // Connect to nested team WebSocket
    if (!nestedWsRef.current) {
      const wsUrl = `${getWsUrl()}/api/conversation-stream/${conversationId}`;
      const ws = connectVoiceConversationStream(conversationId);
      nestedWsRef.current = ws;
      setSharedNestedWs(ws);

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          eventsMapRef.current.set(message.id || Date.now(), message);
          setMessages(prev => [...prev, { source: 'nested', ...message }]);
        } catch (err) {
          console.error('[Nested WS] Parse error:', err);
        }
      };
    }

    // Connect to Claude Code WebSocket
    if (!claudeCodeWsRef.current) {
      const wsUrl = `${getWsUrl()}/api/runs/ClaudeCode`;
      const ws = new WebSocket(wsUrl);
      claudeCodeWsRef.current = ws;
      setSharedClaudeCodeWs(ws);

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          eventsMapRef.current.set(message.id || Date.now(), message);
          setMessages(prev => [...prev, { source: 'claude_code', ...message }]);
        } catch (err) {
          console.error('[Claude Code WS] Parse error:', err);
        }
      };
    }

    // Cleanup on unmount or when stopping
    return () => {
      if (nestedWsRef.current) {
        nestedWsRef.current.close();
        nestedWsRef.current = null;
      }
      if (claudeCodeWsRef.current) {
        claudeCodeWsRef.current.close();
        claudeCodeWsRef.current = null;
      }
    };
  }, [conversationId, isRunning]);

  // ============================================
  // Cleanup on Unmount
  // ============================================
  useEffect(() => {
    return () => {
      stopSession();
    };
  }, [stopSession]);

  // ============================================
  // Navigation Hooks
  // ============================================
  useTVNavigation({ isRunning, mainTab, viewTab });
  useKeyboardNavigation({
    onStartStop: () => (isRunning ? stopSession() : startSession()),
    onMuteToggle: toggleMute,
  });

  // ============================================
  // Render
  // ============================================

  // Select layout based on screen size
  const Layout = isMobile ? MobileVoiceLayout : DesktopVoiceLayout;

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Config Editor Drawer */}
      <Drawer
        anchor="right"
        open={configEditorOpen}
        onClose={() => setConfigEditorOpen(false)}
        sx={{ zIndex: 1300 }}
      >
        <VoiceConfigEditor
          config={voiceConfig}
          onConfigChange={setVoiceConfig}
          onClose={() => setConfigEditorOpen(false)}
        />
      </Drawer>

      {/* Main Layout */}
      <Layout
        isRunning={isRunning}
        isMuted={isMuted}
        isSpeakerMuted={isSpeakerMuted}
        transcript={transcript}
        messages={messages}
        error={error}
        conversation={conversation}
        conversationLoading={conversationLoading}
        conversationError={conversationError}
        viewTab={viewTab}
        mainTab={mainTab}
        voiceConfig={voiceConfig}
        sharedNestedWs={sharedNestedWs}
        sharedClaudeCodeWs={sharedClaudeCodeWs}
        onStartSession={startSession}
        onStopSession={stopSession}
        onToggleMute={toggleMute}
        onToggleSpeakerMute={toggleSpeakerMute}
        onViewTabChange={setViewTab}
        onMainTabChange={setMainTab}
        onConfigEditorOpen={() => setConfigEditorOpen(true)}
      />
    </Box>
  );
}

export default VoiceAssistantWebSocket;
