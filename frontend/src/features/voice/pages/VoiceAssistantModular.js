import React, { useEffect, useRef, useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Box, useTheme, useMediaQuery, Drawer, IconButton } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import VoiceConfigEditor from '../components/VoiceConfigEditor';
import useTVNavigation from '../hooks/useTVNavigation';
import useKeyboardNavigation from '../../../hooks/useKeyboardNavigation';
import { getVoiceConversation, appendVoiceConversationEvent, connectVoiceConversationStream } from '../../../api';
import { getHttpBase, getWsUrl } from '../../../utils/urlBuilder';
import { WebRTCPeerConnection } from '../../../utils/webrtcHelper';
import { truncateText, safeStringify, formatTimestamp } from '../utils/helpers';

// Import layouts
import DesktopVoiceLayout from '../components/DesktopVoiceLayout';
import MobileVoiceLayout from '../components/MobileVoiceLayout';

/**
 * VoiceAssistantModular - MODULAR version using the current working logic
 *
 * This is a simplified, refactored version that preserves the exact working logic
 * from the original VoiceAssistant.js but with better organization.
 *
 * Key differences from original:
 * - Uses layout components instead of inline JSX
 * - Cleaner state management
 * - Same WebRTC logic (direct OpenAI connection)
 * - Same tool execution logic
 * - Same mobile WebRTC logic
 *
 * TO BE REPLACED: Eventually this will use custom hooks (useOpenAIWebRTC, etc.)
 * but for now it preserves the exact working implementation.
 */
function VoiceAssistantModular({ nested = false, onConversationUpdate }) {
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
  const [noMicrophoneMode, setNoMicrophoneMode] = useState(false);

  // ============================================
  // Refs
  // ============================================
  // WebSocket refs
  const wsRef = useRef(null); // Pipecat WebSocket connection
  const nestedWsRef = useRef(null);
  const [sharedNestedWs, setSharedNestedWs] = useState(null);
  const claudeCodeWsRef = useRef(null);
  const [sharedClaudeCodeWs, setSharedClaudeCodeWs] = useState(null);
  const streamRef = useRef(null); // Conversation stream

  // Audio refs
  const micStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const audioProcessorRef = useRef(null);
  const playbackBufferRef = useRef([]);
  const isPlayingRef = useRef(false);
  const audioRef = useRef(null); // Not used in Pipecat, kept for compatibility

  // Event tracking refs
  const toolCallsRef = useRef({});
  const replayQueueRef = useRef([]);
  const eventsMapRef = useRef(new Map());
  const hasSpokenMidRef = useRef(false);
  const runCompletedRef = useRef(false);

  // ============================================
  // Helper: Record Event (DISABLED - Backend handles event recording)
  // ============================================
  const recordEvent = useCallback(
    async (source, type, payload) => {
      // Backend WebRTC records all events automatically via on_event_callback
      // No need to record from frontend
      console.log(`[Event] ${source}:${type}`, payload);
    },
    []
  );

  // ============================================
  // Helper: Normalize Events
  // ============================================
  const normalizeEvent = useCallback((evt) => {
    if (!evt) return null;
    return {
      id: evt.id || `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: evt.timestamp,
      source: evt.source,
      type: evt.type,
      data: evt.data || evt.payload,
    };
  }, []);

  // ============================================
  // Helper: Upsert Events (deduplicate)
  // ============================================
  const upsertEvents = useCallback((newEvents) => {
    setMessages((prev) => {
      newEvents.forEach((evt) => {
        if (evt.id) eventsMapRef.current.set(evt.id, evt);
      });
      const merged = Array.from(eventsMapRef.current.values());
      merged.sort((a, b) => {
        const at = new Date(a.timestamp).getTime();
        const bt = new Date(b.timestamp).getTime();
        if (at !== bt) return at - bt;
        return (a.id || 0) - (b.id || 0);
      });
      return merged;
    });
  }, []);

  // ============================================
  // Remote Session Detection
  // ============================================
  const remoteSessionActive = React.useMemo(() => {
    if (isRunning) return false;
    let lastStart = null;
    let lastStop = null;
    messages.forEach((msg) => {
      if ((msg.source || '').toLowerCase() !== 'controller') return;
      if ((msg.type || '').toLowerCase() === 'session_started') lastStart = msg.timestamp;
      if ((msg.type || '').toLowerCase() === 'session_stopped' || (msg.type || '').toLowerCase() === 'session_error') lastStop = msg.timestamp;
    });
    if (!lastStart) return false;
    if (!lastStop) return true;
    return new Date(lastStart).getTime() > new Date(lastStop).getTime();
  }, [messages, isRunning]);

  const sessionLocked = isRunning || remoteSessionActive;

  // ============================================
  // Conversation Stream (WebSocket for events)
  // ============================================
  useEffect(() => {
    if (!conversationId) return undefined;
    const socket = connectVoiceConversationStream(conversationId, { limit: 1000 });
    streamRef.current = socket;

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload?.type === 'history') {
          const normalized = (payload.events || []).map((evt) => normalizeEvent(evt)).filter(Boolean);
          if (normalized.length) upsertEvents(normalized);
          return;
        }
        if (payload?.type === 'event' && payload.event) {
          const normalized = normalizeEvent(payload.event);
          if (normalized) upsertEvents([normalized]);
        }
      } catch (err) {
        console.error('Failed to parse conversation stream message', err);
      }
    };

    socket.onerror = (event) => console.error('Conversation stream error', event);
    socket.onclose = () => {
      if (streamRef.current === socket) streamRef.current = null;
    };

    return () => {
      try {
        socket.close();
      } catch (e) {}
      if (streamRef.current === socket) streamRef.current = null;
    };
  }, [conversationId, normalizeEvent, upsertEvents]);

  // ============================================
  // Load Conversation
  // ============================================
  useEffect(() => {
    if (!conversationId) {
      setConversation(null);
      setConversationLoading(false);
      setConversationError('Missing conversation id in URL');
      return;
    }
    let cancelled = false;
    setConversationLoading(true);
    setConversationError(null);
    (async () => {
      try {
        const res = await getVoiceConversation(conversationId, { limit: 1000 });
        if (cancelled) return;
        const detail = res.data;
        setConversation(detail);
        eventsMapRef.current.clear();
        if (detail?.events?.length) {
          const normalized = detail.events.map((evt) => normalizeEvent(evt)).filter(Boolean);
          upsertEvents(normalized);
        } else {
          setMessages([]);
        }
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load conversation', err);
        setConversation(null);
        setConversationError(err?.response?.data?.detail || err.message || 'Conversation not found');
      } finally {
        if (!cancelled) setConversationLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [conversationId, normalizeEvent, upsertEvents]);

  // ============================================
  // Realtime Tools Configuration
  // ============================================
  const realtimeTools = [
    {
      type: 'function',
      name: 'send_to_nested',
      description: 'Send a user message to the nested agents team (MainConversation) via WebSocket.',
      parameters: {
        type: 'object',
        properties: { text: { type: 'string', description: 'The user message to send.' } },
        required: ['text'],
        additionalProperties: false,
      },
    },
    {
      type: 'function',
      name: 'send_to_claude_code',
      description: 'Send a self-editing instruction to Claude Code to modify the codebase. Use when the user asks to change, add, or fix code.',
      parameters: {
        type: 'object',
        properties: { text: { type: 'string', description: 'The instruction for Claude Code.' } },
        required: ['text'],
        additionalProperties: false,
      },
    },
    {
      type: 'function',
      name: 'pause',
      description: 'Request the controller to pause the current nested conversation when the user explicitly asks. Automatic calls right after sending a task are ignored.',
      parameters: { type: 'object', properties: {}, additionalProperties: false },
    },
    {
      type: 'function',
      name: 'reset',
      description: 'Reset the nested team conversation state when the user explicitly asks. Automatic calls right after sending a task are ignored.',
      parameters: { type: 'object', properties: {}, additionalProperties: false },
    },
    {
      type: 'function',
      name: 'pause_claude_code',
      description: 'Pause/interrupt the currently running Claude Code task. Use when the user explicitly asks to stop or cancel Claude Code.',
      parameters: { type: 'object', properties: {}, additionalProperties: false },
    },
  ];

  // ============================================
  // Tool Execution Logic
  // ============================================
  const executeToolCall = useCallback(
    async (callId, toolName, args) => {
      console.log(`[Tool] Executing: ${toolName}`, args);

      if (toolName === 'send_to_nested') {
        if (nestedWsRef.current?.readyState === WebSocket.OPEN) {
          try {
            nestedWsRef.current.send(JSON.stringify({ type: 'user_message', data: args.text || '' }));
            void recordEvent('controller', 'tool_send_to_nested', { text: args.text });
            return { success: true };
          } catch (err) {
            console.error('[Tool] send_to_nested failed:', err);
            return { success: false, error: String(err) };
          }
        }
        return { success: false, error: 'Nested WebSocket not connected' };
      }

      if (toolName === 'send_to_claude_code') {
        if (claudeCodeWsRef.current?.readyState === WebSocket.OPEN) {
          try {
            claudeCodeWsRef.current.send(JSON.stringify({ type: 'user_message', data: args.text || '' }));
            void recordEvent('controller', 'tool_send_to_claude_code', { text: args.text });
            return { success: true };
          } catch (err) {
            console.error('[Tool] send_to_claude_code failed:', err);
            return { success: false, error: String(err) };
          }
        }
        return { success: false, error: 'Claude Code WebSocket not connected' };
      }

      if (toolName === 'pause') {
        if (nestedWsRef.current?.readyState === WebSocket.OPEN) {
          try {
            nestedWsRef.current.send(JSON.stringify({ type: 'pause' }));
            void recordEvent('controller', 'tool_pause', {});
            return { success: true };
          } catch (err) {
            console.error('[Tool] pause failed:', err);
            return { success: false, error: String(err) };
          }
        }
        return { success: false, error: 'Nested WebSocket not connected' };
      }

      if (toolName === 'reset') {
        if (nestedWsRef.current?.readyState === WebSocket.OPEN) {
          try {
            nestedWsRef.current.send(JSON.stringify({ type: 'reset' }));
            void recordEvent('controller', 'tool_reset', {});
            return { success: true };
          } catch (err) {
            console.error('[Tool] reset failed:', err);
            return { success: false, error: String(err) };
          }
        }
        return { success: false, error: 'Nested WebSocket not connected' };
      }

      if (toolName === 'pause_claude_code') {
        if (claudeCodeWsRef.current?.readyState === WebSocket.OPEN) {
          try {
            claudeCodeWsRef.current.send(JSON.stringify({ type: 'pause' }));
            void recordEvent('controller', 'tool_pause_claude_code', {});
            return { success: true };
          } catch (err) {
            console.error('[Tool] pause_claude_code failed:', err);
            return { success: false, error: String(err) };
          }
        }
        return { success: false, error: 'Claude Code WebSocket not connected' };
      }

      return { success: false, error: `Unknown tool: ${toolName}` };
    },
    [recordEvent]
  );

  // ============================================
  // Audio Conversion Utilities (Pipecat WebSocket)
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
  // Audio Playback System (Pipecat WebSocket)
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
      console.error('[Audio] Error playing audio:', err);
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
  // Start Session (Pipecat WebSocket Implementation)
  // ============================================
  const startSession = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setIsMuted(true); // Start muted by default
    setError(null);

    try {
      const agentName = voiceConfig.agentName || 'MainConversation';
      console.log('[PipecatWS] Starting Pipecat WebSocket session...');

      // Create audio context
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000 // OpenAI Realtime uses 24kHz
      });
      audioContextRef.current = audioContext;

      // Try to get microphone
      let micStream = null;
      let hasMicrophone = false;
      try {
        micStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 24000,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });
        micStreamRef.current = micStream;
        hasMicrophone = true;
        setNoMicrophoneMode(false);
        console.log('[PipecatWS] Desktop microphone acquired');

        // Mute by default
        micStream.getAudioTracks().forEach(track => track.enabled = false);
      } catch (micError) {
        console.warn('[PipecatWS] No microphone available:', micError.message);
        setNoMicrophoneMode(true);
        hasMicrophone = false;
        // Create silent stream
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        gainNode.gain.value = 0;
        oscillator.connect(gainNode);
        const silentDestination = audioContext.createMediaStreamDestination();
        gainNode.connect(silentDestination);
        oscillator.start();
        micStream = silentDestination.stream;
        micStreamRef.current = micStream;
      }

      // Create WebSocket connection
      // Note: getWsUrl already adds '/api', so we pass '/realtime/pipecat-simple/ws/...' not '/api/realtime/...'
      // Using simple router which directly proxies to OpenAI without Pipecat pipeline
      const wsUrl = getWsUrl(`/realtime/pipecat-simple/ws/${conversationId}?voice=${voiceConfig.voice || 'alloy'}&agent_name=${agentName}`);
      console.log('[PipecatWS] Connecting to:', wsUrl);

      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      // WebSocket event handlers
      ws.onopen = () => {
        console.log('[PipecatWS] Connected to Pipecat backend');
        setError(null);

        if (hasMicrophone) {
          // Set up audio capture
          const source = audioContext.createMediaStreamSource(micStream);

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
        }

        // Record session start
        void recordEvent('controller', 'session_started', {
          voice: voiceConfig.voice || 'alloy',
          agent_name: agentName,
          transport: 'pipecat_websocket',
        });
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
            console.log('[PipecatWS] Event:', data);

            // Handle nested team events
            if (data.type === 'nested_event' && data.event) {
              console.log('[PipecatWS] Nested team event:', data.event);
              // Forward to nested team messages
              const nestedEvent = normalizeEvent({
                ...data.event,
                source: 'nested',
                timestamp: new Date().toISOString()
              });
              if (nestedEvent) {
                upsertEvents([nestedEvent]);
              }
              return;
            }

            // Handle Claude Code events
            if (data.type === 'claude_code_event' && data.event) {
              console.log('[PipecatWS] Claude Code event:', data.event);
              // Forward to Claude Code messages
              const claudeEvent = normalizeEvent({
                ...data.event,
                source: 'claude_code',
                timestamp: new Date().toISOString()
              });
              if (claudeEvent) {
                upsertEvents([claudeEvent]);
              }
              return;
            }

            // Add to messages for UI display
            setMessages(prev => [...prev, {
              ...data,
              source: data.source || 'pipecat',
              timestamp: data.timestamp || new Date().toISOString()
            }]);

            // Handle transcription
            if (data.type === 'transcription') {
              setTranscript(data.text || '');
            }
          } catch (err) {
            console.error('[PipecatWS] Failed to parse message:', err);
          }
        }
      };

      ws.onerror = (event) => {
        console.error('[PipecatWS] WebSocket error:', event);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log('[PipecatWS] Disconnected:', event.code, event.reason);
        setIsRunning(false);

        if (!event.wasClean) {
          setError(`WebSocket closed unexpectedly: ${event.reason || 'Unknown reason'}`);
        }
      };

      console.log('[Modular] Session started successfully with Pipecat WebSocket');
    } catch (err) {
      console.error('[Modular] Failed to start session:', err);
      setError(err.message || 'Failed to start session');
      setIsRunning(false);
    }
  };

  // ============================================
  // Stop Session
  // ============================================
  const stopSession = async () => {
    console.log('[Modular] Stop session');

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
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      try { audioContextRef.current.close(); } catch {}
      audioContextRef.current = null;
    }

    // Clear playback buffer
    playbackBufferRef.current = [];
    isPlayingRef.current = false;

    void recordEvent('controller', 'session_stopped', {});
    setIsRunning(false);
    setIsMuted(false);
    setIsSpeakerMuted(false);
    setTranscript('');
  };

  // ============================================
  // Toggle Mute
  // ============================================
  const toggleMute = () => {
    const newMuted = !isMuted;
    setIsMuted(newMuted);

    // Control microphone track enabled state
    if (micStreamRef.current) {
      micStreamRef.current.getAudioTracks().forEach(track => {
        track.enabled = !newMuted;
      });
    }

    console.log(`[Modular] Mute toggled: ${newMuted}`);
  };

  // ============================================
  // Toggle Speaker Mute
  // ============================================
  const toggleSpeakerMute = () => {
    const newMuted = !isSpeakerMuted;
    setIsSpeakerMuted(newMuted);

    // Clear playback buffer when muting speaker
    if (newMuted) {
      playbackBufferRef.current = [];
      isPlayingRef.current = false;
    }

    console.log(`[Audio] Speaker ${newMuted ? 'muted' : 'unmuted'}`);
  };

  // ============================================
  // Send Text to Voice
  // ============================================
  const sendText = () => {
    if (!transcript.trim()) return;
    if (dataChannelRef.current?.readyState === 'open') {
      try {
        dataChannelRef.current.send(JSON.stringify({
          type: 'conversation.item.create',
          item: { type: 'message', role: 'user', content: [{ type: 'input_text', text: transcript }] },
        }));
        dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
        void recordEvent('user', 'voice_user_message', { text: transcript });
        setTranscript('');
      } catch (err) {
        console.error('[Send] Failed to send text:', err);
      }
    }
  };

  // ============================================
  // Send to Nested
  // ============================================
  const sendToNested = () => {
    if (!transcript.trim()) return;
    if (nestedWsRef.current?.readyState === WebSocket.OPEN) {
      try {
        nestedWsRef.current.send(JSON.stringify({ type: 'user_message', data: transcript }));
        void recordEvent('controller', 'manual_send_to_nested', { text: transcript });
        setTranscript('');
      } catch (err) {
        console.error('[Send] Failed to send to nested:', err);
      }
    }
  };

  // ============================================
  // Send to Claude Code
  // ============================================
  const sendToClaude = () => {
    if (!transcript.trim()) return;
    if (claudeCodeWsRef.current?.readyState === WebSocket.OPEN) {
      try {
        claudeCodeWsRef.current.send(JSON.stringify({ type: 'user_message', data: transcript }));
        void recordEvent('controller', 'manual_send_to_claude_code', { text: transcript });
        setTranscript('');
      } catch (err) {
        console.error('[Send] Failed to send to Claude Code:', err);
      }
    }
  };

  // ============================================
  // Keyboard Shortcuts
  // ============================================
  useKeyboardNavigation({
    enabled: true,
    shortcuts: {
      'ctrl+enter': sendText,
      'ctrl+shift+enter': sendToNested,
      'ctrl+alt+enter': sendToClaude,
      'ctrl+m': toggleMute,
      'ctrl+shift+m': toggleSpeakerMute,
    },
  });

  // ============================================
  // TV Navigation
  // ============================================
  useTVNavigation({ enabled: !nested });

  // ============================================
  // Cleanup
  // ============================================
  useEffect(() => {
    return () => {
      if (isRunning) stopSession();
    };
  }, [isRunning]);

  // ============================================
  // Notify Parent
  // ============================================
  useEffect(() => {
    if (onConversationUpdate && conversation) {
      onConversationUpdate(conversation);
    }
  }, [conversation, onConversationUpdate]);

  // ============================================
  // Control Panel Props
  // ============================================
  const controlPanelProps = {
    isRunning,
    isMuted,
    isSpeakerMuted,
    sessionLocked,
    remoteSessionActive,
    noMicrophoneMode,
    voiceConfig,
    setConfigEditorOpen,
    conversationError,
    error,
    transcript,
    setTranscript,
    onSendToVoice: sendText,
    onSendToNested: sendToNested,
    onSendToClaude: sendToClaude,
    nestedWsConnected: !!sharedNestedWs,
    claudeCodeWsConnected: !!sharedClaudeCodeWs,
    onStart: startSession,
    onStop: stopSession,
    onToggleMute: toggleMute,
    onToggleSpeakerMute: toggleSpeakerMute,
    conversationLoading,
    messages,
    formatTimestamp,
    micStream: micStreamRef.current,
    isMobile,
  };

  // ============================================
  // Render Mobile Layout
  // ============================================
  if (isMobile) {
    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
        {/* Mobile drawer button */}
        <IconButton
          onClick={() => setDrawerOpen(!drawerOpen)}
          sx={{ position: 'absolute', top: 8, left: 8, zIndex: 1300, bgcolor: 'background.paper' }}
        >
          <MenuIcon />
        </IconButton>

        {/* Mobile drawer */}
        <Drawer anchor="left" open={drawerOpen} onClose={() => setDrawerOpen(false)}>
          <Box sx={{ width: 250, p: 2 }}>
            {/* Drawer content if needed */}
          </Box>
        </Drawer>

        {/* Mobile layout */}
        <MobileVoiceLayout
          messages={messages}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
          sharedTeamWs={sharedNestedWs}
          agentName={voiceConfig.agentName}
          controlPanelProps={controlPanelProps}
          audioRef={audioRef}
        />

        {/* Config editor */}
        <VoiceConfigEditor
          open={configEditorOpen}
          onClose={() => setConfigEditorOpen(false)}
          initialConfig={voiceConfig}
          onSave={(newConfig) => {
            setVoiceConfig(newConfig);
            setConfigEditorOpen(false);
          }}
        />
      </Box>
    );
  }

  // ============================================
  // Render Desktop Layout
  // ============================================
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Desktop layout */}
      <DesktopVoiceLayout
        messages={messages}
        formatTimestamp={formatTimestamp}
        truncateText={truncateText}
        safeStringify={safeStringify}
        sharedTeamWs={sharedNestedWs}
        agentName={voiceConfig.agentName}
        controlPanelProps={controlPanelProps}
        audioRef={audioRef}
      />

      {/* Config editor */}
      <VoiceConfigEditor
        open={configEditorOpen}
        onClose={() => setConfigEditorOpen(false)}
        initialConfig={voiceConfig}
        onSave={(newConfig) => {
          setVoiceConfig(newConfig);
          setConfigEditorOpen(false);
        }}
      />
    </Box>
  );
}

export default VoiceAssistantModular;
