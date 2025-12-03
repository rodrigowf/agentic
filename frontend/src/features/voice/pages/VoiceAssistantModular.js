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
  const peerRef = useRef(null);
  const dataChannelRef = useRef(null);
  const backendSessionIdRef = useRef(null); // Backend WebRTC session ID
  const nestedWsRef = useRef(null);
  const [sharedNestedWs, setSharedNestedWs] = useState(null);
  const claudeCodeWsRef = useRef(null);
  const [sharedClaudeCodeWs, setSharedClaudeCodeWs] = useState(null);
  const audioRef = useRef(null);
  const streamRef = useRef(null);
  const micStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const desktopSourceRef = useRef(null);
  const desktopGainNodeRef = useRef(null);
  const mixerRef = useRef(null);
  const toolCallsRef = useRef({});
  const replayQueueRef = useRef([]);
  const eventsMapRef = useRef(new Map());
  const hasSpokenMidRef = useRef(false);
  const runCompletedRef = useRef(false);
  const mobileWebRTCPeerRef = useRef(null);
  const mobileAudioWsRef = useRef(null);
  const mobileGainNodeRef = useRef(null);
  const responseStreamRef = useRef(null);

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
      id: evt.id,
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
  // Start Session (Backend WebRTC Implementation)
  // ============================================
  const startSession = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setIsMuted(false);
    setError(null);

    try {
      const backendBase = getHttpBase();
      const agentName = voiceConfig.agentName || 'MainConversation';

      // Set up audio context
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;

      // Try to get desktop microphone
      let micStream = null;
      let hasMicrophone = false;
      try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        micStreamRef.current = micStream;
        hasMicrophone = true;
        setNoMicrophoneMode(false);
        console.log('[BackendWebRTC] Desktop microphone acquired');
      } catch (micError) {
        console.warn('[BackendWebRTC] No microphone, creating silent audio:', micError.message);
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        gainNode.gain.value = 0;
        oscillator.connect(gainNode);
        const silentDestination = audioContext.createMediaStreamDestination();
        gainNode.connect(silentDestination);
        oscillator.start();
        micStream = silentDestination.stream;
        micStreamRef.current = micStream;
        hasMicrophone = false;
        setNoMicrophoneMode(true);
      }

      // Create mixer (for future mobile support)
      const mixerDestination = audioContext.createMediaStreamDestination();
      const desktopGain = audioContext.createGain();
      const desktopSource = audioContext.createMediaStreamSource(micStream);
      desktopSource.connect(desktopGain);
      desktopGain.connect(mixerDestination);
      desktopGain.gain.value = hasMicrophone ? 1.0 : 0.0;
      desktopSourceRef.current = { source: desktopSource, gain: desktopGain, hasMicrophone };

      const mixedStream = mixerDestination.stream;

      // Connect to backend WebRTC
      const backendSessionResp = await fetch(`${backendBase}/api/realtime/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          voice: voiceConfig.voice || 'alloy',
          agent_name: agentName,
          system_prompt: voiceConfig.systemPromptContent || '',
        }),
      });

      if (!backendSessionResp.ok) {
        const errorText = await backendSessionResp.text();
        throw new Error(`Failed to create backend session: ${backendSessionResp.status} ${errorText}`);
      }

      const backendSessionData = await backendSessionResp.json();
      const backendSessionId = backendSessionData.session_id;
      backendSessionIdRef.current = backendSessionId;
      console.log('[BackendWebRTC] Created backend session:', backendSessionId);

      // Create peer connection to backend
      const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
      peerRef.current = pc;

      // Handle incoming audio from backend (OpenAI audio)
      pc.ontrack = (evt) => {
        if (audioRef.current) {
          audioRef.current.srcObject = evt.streams[0];
        }
        responseStreamRef.current = evt.streams[0];
        console.log('[BackendWebRTC] Received audio stream from backend');
      };

      // Add outgoing audio stream (microphone → backend)
      for (const track of mixedStream.getAudioTracks()) {
        pc.addTrack(track, mixedStream);
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

      // Create offer and exchange SDP with backend
      const offer = await pc.createOffer({ offerToReceiveAudio: true });
      await pc.setLocalDescription(offer);
      await waitForIceGathering();

      const sdpResp = await fetch(`${backendBase}/api/realtime/sdp/${backendSessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: pc.localDescription.sdp,
      });

      if (!sdpResp.ok) {
        throw new Error(`SDP exchange failed: ${sdpResp.status}`);
      }

      const answerSdp = await sdpResp.text();
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

      console.log('[BackendWebRTC] WebRTC connection established');

      // Record session start
      void recordEvent('controller', 'session_started', {
        backend_session_id: backendSessionId,
        voice: voiceConfig.voice || 'alloy',
        agent_name: agentName,
      });

      console.log('[Modular] Session started successfully with backend WebRTC');
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

    // Delete backend session
    if (backendSessionIdRef.current) {
      try {
        const backendBase = getHttpBase();
        await fetch(`${backendBase}/api/realtime/session/${backendSessionIdRef.current}`, {
          method: 'DELETE',
        });
        console.log('[BackendWebRTC] Session deleted:', backendSessionIdRef.current);
      } catch (err) {
        console.warn('[BackendWebRTC] Failed to delete session:', err);
      }
      backendSessionIdRef.current = null;
    }

    // Close peer connection
    if (peerRef.current) {
      peerRef.current.getSenders().forEach((sender) => {
        if (sender.track) sender.track.stop();
      });
      try { peerRef.current.close(); } catch {}
      peerRef.current = null;
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

    void recordEvent('controller', 'session_stopped', {});
    setIsRunning(false);
  };

  // ============================================
  // Toggle Mute
  // ============================================
  const toggleMute = () => {
    const newMuted = !isMuted;
    setIsMuted(newMuted);

    // Control desktop microphone gain
    if (desktopSourceRef.current?.gain) {
      desktopSourceRef.current.gain.gain.value = newMuted ? 0.0 : 1.0;
    }

    console.log(`[Modular] Mute toggled: ${newMuted}`);
  };

  // ============================================
  // Toggle Speaker Mute
  // ============================================
  const toggleSpeakerMute = () => {
    const newMuted = !isSpeakerMuted;
    setIsSpeakerMuted(newMuted);
    if (audioRef.current) {
      audioRef.current.muted = newMuted;
    }
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
