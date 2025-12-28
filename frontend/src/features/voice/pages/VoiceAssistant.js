import React, { useEffect, useRef, useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Box, useTheme, useMediaQuery } from '@mui/material';
import VoiceConfigEditor from '../components/VoiceConfigEditor';
import useTVNavigation from '../hooks/useTVNavigation';
import useKeyboardNavigation from '../../../hooks/useKeyboardNavigation';
import {
  getVoiceConversation,
  appendVoiceConversationEvent,
  connectVoiceConversationStream,
  startVoiceWebRTCBridge,
  stopVoiceWebRTCBridge,
  disconnectVoiceWebRTC,
  sendVoiceWebRTCText,
  getVoiceSessionStatus,
  sendTextMessage,
  getSelectedVoiceConfig
} from '../../../api';
import { getWsUrl } from '../../../utils/urlBuilder';
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
  const [voiceConfig, setVoiceConfig] = useState({
    agentName: 'MainConversation',
    systemPromptFile: 'default.txt',
    systemPromptContent: '',
    voice: 'cedar',
    memoryFilePath: 'backend/data/memory/short_term_memory.txt',
  });
  const [noMicrophoneMode, setNoMicrophoneMode] = useState(false);
  const [backendSessionActive, setBackendSessionActive] = useState(false); // Real-time backend status
  const [isStarting, setIsStarting] = useState(false); // Loading state for start button
  const [isSendingDisconnected, setIsSendingDisconnected] = useState(false); // Disconnected text sending state

  // ============================================
  // Refs
  // ============================================
  // Connection refs
  const peerConnectionRef = useRef(null);
  const connectionIdRef = useRef(null); // Backend connection ID for this browser
  const streamRef = useRef(null); // Conversation stream

  // Audio refs
  const micStreamRef = useRef(null);
  const fallbackAudioContextRef = useRef(null);
  const audioRef = useRef(null);

  // Event tracking refs
  const toolCallsRef = useRef({});
  const replayQueueRef = useRef([]);
  const eventsMapRef = useRef(new Map());
  const hasSpokenMidRef = useRef(false);
  const runCompletedRef = useRef(false);

  // ============================================
  // Helper: Record Event (store in voice conversation feed)
  // ============================================
  const recordEvent = useCallback(
    async (source, type, payload) => {
      if (!conversationId) return;
      try {
        await appendVoiceConversationEvent(conversationId, {
          source,
          type,
          payload,
        });
      } catch (err) {
        console.error('Failed to record event', err);
      }
    },
    [conversationId]
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
  // Remote Session Detection (uses backend status, not just events)
  // ============================================
  const remoteSessionActive = React.useMemo(() => {
    if (isRunning) return false;
    // Use the real backend status instead of computing from stored events
    return backendSessionActive;
  }, [isRunning, backendSessionActive]);

  const sessionLocked = isRunning || remoteSessionActive;

  // ============================================
  // Load Voice Config from Backend
  // ============================================
  useEffect(() => {
    const loadVoiceConfig = async () => {
      try {
        const response = await getSelectedVoiceConfig();
        const config = response.data?.config;
        if (config) {
          setVoiceConfig({
            agentName: config.agent_name || 'MainConversation',
            systemPromptFile: config.system_prompt_file || 'default.txt',
            systemPromptContent: '',
            voice: config.voice || 'cedar',
            memoryFilePath: config.memory_file_path || 'backend/data/memory/short_term_memory.txt',
          });
          console.log('[VoiceAssistant] Loaded voice config from backend:', config.voice, config.agent_name);
        }
      } catch (err) {
        console.warn('[VoiceAssistant] Failed to load voice config from backend, using defaults:', err.message);
      }
    };
    loadVoiceConfig();
  }, []);

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
  // Check Backend Session Status (real-time)
  // ============================================
  useEffect(() => {
    if (!conversationId) {
      setBackendSessionActive(false);
      return;
    }
    let cancelled = false;

    const checkStatus = async () => {
      try {
        const res = await getVoiceSessionStatus(conversationId);
        if (cancelled) return;
        // Backend returns { active: boolean, openai_connected: boolean, ... }
        setBackendSessionActive(res.data?.active === true && res.data?.openai_connected === true);
      } catch (err) {
        // If the endpoint fails (404 or error), session is not active
        if (!cancelled) setBackendSessionActive(false);
      }
    };

    // Check immediately on load
    checkStatus();

    // Also check periodically in case session state changes externally
    const interval = setInterval(checkStatus, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [conversationId]);

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
  // WebRTC Bridge (backend-controlled)
  // ============================================
  const ensureMicrophoneStream = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setNoMicrophoneMode(false);
      return stream;
    } catch (err) {
      console.warn('[Voice] No microphone available, using silent track', err);
      setNoMicrophoneMode(true);
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      gainNode.gain.value = 0;
      oscillator.connect(gainNode);
      const destination = ctx.createMediaStreamDestination();
      gainNode.connect(destination);
      oscillator.start();
      fallbackAudioContextRef.current = ctx;
      return destination.stream;
    }
  }, []);

  const attachRemoteAudio = useCallback((stream) => {
    if (!audioRef.current) return;
    audioRef.current.srcObject = stream;
    audioRef.current.muted = isSpeakerMuted;
    const playPromise = audioRef.current.play();
    if (playPromise?.catch) {
      playPromise.catch((err) => {
        console.warn('[Voice] Failed to start remote audio playback', err);
      });
    }
  }, [isSpeakerMuted]);

  const stopSession = useCallback(async (skipBackend = false) => {
    console.log('[Voice] Stop session');

    const pc = peerConnectionRef.current;
    if (pc) {
      pc.getSenders().forEach((sender) => sender.track?.stop());
      pc.getReceivers().forEach((receiver) => receiver.track?.stop());
      pc.close();
      peerConnectionRef.current = null;
    }

    if (audioRef.current) {
      audioRef.current.srcObject = null;
    }

    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }

    if (fallbackAudioContextRef.current) {
      try {
        fallbackAudioContextRef.current.close();
      } catch (err) {
        console.warn('Failed to close fallback audio context', err);
      }
      fallbackAudioContextRef.current = null;
    }

    // Disconnect this browser from the backend (doesn't stop the whole session)
    if (!skipBackend && connectionIdRef.current) {
      try {
        console.log('[Voice] Disconnecting browser connection:', connectionIdRef.current);
        await disconnectVoiceWebRTC(connectionIdRef.current);
      } catch (err) {
        console.warn('Failed to disconnect from backend:', err);
      }
      connectionIdRef.current = null;
    }

    setIsRunning(false);
    setIsMuted(false);
    setIsSpeakerMuted(false);
    setTranscript('');
  }, []);

  /**
   * Force stop the entire conversation (all browsers + OpenAI session)
   */
  const forceStopSession = useCallback(async () => {
    if (!conversationId) return;
    console.log('[Voice] Force stopping entire conversation:', conversationId);

    try {
      await stopVoiceWebRTCBridge(conversationId);
      console.log('[Voice] ✅ Conversation force stopped');
      // Immediately update state - don't wait for the 5-second status check
      setBackendSessionActive(false);
    } catch (err) {
      console.warn('Failed to force stop conversation:', err);
      // Still update state even on error - the session is likely not active
      setBackendSessionActive(false);
    }
  }, [conversationId]);

  const startSession = useCallback(async () => {
    if (isRunning || isStarting || !conversationId) return;
    setError(null);
    setIsStarting(true);
    let bridgeStarted = false;
    try {
      const localStream = await ensureMicrophoneStream();
      micStreamRef.current = localStream;

      const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
      peerConnectionRef.current = pc;

      console.log('='.repeat(60));
      console.log('[Frontend WebRTC] 🎤 Adding local audio tracks to peer connection');
      const tracks = localStream.getTracks();
      console.log(`[Frontend WebRTC] Local stream has ${tracks.length} tracks:`);
      tracks.forEach((track, idx) => {
        console.log(`[Frontend WebRTC]   Track ${idx}: kind=${track.kind}, id=${track.id}, enabled=${track.enabled}`);
        pc.addTrack(track, localStream);
        console.log(`[Frontend WebRTC]   ✅ Track ${idx} added to peer connection`);
      });
      console.log('='.repeat(60));

      pc.ontrack = (event) => {
        console.log('[Frontend WebRTC] 🔊 Remote track received:', event.track.kind);
        const remoteStream = event.streams?.[0] || new MediaStream([event.track]);
        attachRemoteAudio(remoteStream);
      };

      pc.onconnectionstatechange = () => {
        console.log('[WebRTC Bridge] Connection state:', pc.connectionState);
        if (pc.connectionState === 'failed') {
          setError('WebRTC connection failed');
        }
      };

      const offer = await pc.createOffer({ offerToReceiveAudio: true, offerToReceiveVideo: false });
      await pc.setLocalDescription(offer);
      console.log('[Frontend WebRTC] ✅ Created offer, local description set');
      console.log('[Frontend WebRTC] Offer has sendrecv?', offer.sdp.includes('a=sendrecv'));
      console.log('[Frontend WebRTC] Offer has recvonly?', offer.sdp.includes('a=recvonly'));

      // Config is loaded from backend's selected config file, only send conversation_id and offer
      const response = await startVoiceWebRTCBridge({
        conversation_id: conversationId,
        offer: offer.sdp,
      });

      const answerSdp = response?.data?.answer;
      const sessionId = response?.data?.session_id; // This is our connection_id
      if (!answerSdp) {
        throw new Error('Invalid SDP answer from backend');
      }
      bridgeStarted = true;
      connectionIdRef.current = sessionId; // Store connection ID for disconnect

      console.log('[Frontend WebRTC] ✅ Received answer from backend, connection_id:', sessionId);
      console.log('[Frontend WebRTC] Answer has sendrecv?', answerSdp.includes('a=sendrecv'));
      console.log('[Frontend WebRTC] Answer has recvonly?', answerSdp.includes('a=recvonly'));
      await pc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
      console.log('[Frontend WebRTC] ✅ Remote description (answer) set');

      setIsRunning(true);
      setIsMuted(false);
      setIsSpeakerMuted(false);
    } catch (err) {
      console.error('[Voice] Failed to start WebRTC bridge', err);
      setError(err.message || 'Failed to start session');
      await stopSession(!bridgeStarted);
    } finally {
      setIsStarting(false);
    }
  }, [attachRemoteAudio, conversationId, ensureMicrophoneStream, isRunning, stopSession, recordEvent]);

  // ============================================
  // Toggle Mute
  // ============================================
  const toggleMute = useCallback(() => {
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    if (micStreamRef.current) {
      micStreamRef.current.getAudioTracks().forEach((track) => {
        track.enabled = !newMuted;
      });
    }
  }, [isMuted]);

  // ============================================
  // Toggle Speaker Mute
  // ============================================
  const toggleSpeakerMute = useCallback(() => {
    const newMuted = !isSpeakerMuted;
    setIsSpeakerMuted(newMuted);
    if (audioRef.current) {
      audioRef.current.muted = newMuted;
      if (!newMuted) {
        const playPromise = audioRef.current.play();
        if (playPromise?.catch) {
          playPromise.catch((err) => console.warn('Failed to resume audio', err));
        }
      }
    }
  }, [isSpeakerMuted]);

  // ============================================
  // Send Text to Voice
  // ============================================
  const sendText = useCallback(async () => {
    const text = transcript.trim();
    if (!text) return;
    if (!conversationId) {
      setError('Missing conversation id.');
      return;
    }
    if (!isRunning) {
      setError('Start the voice session before sending text.');
      return;
    }
    try {
      setError(null);
      await sendVoiceWebRTCText(conversationId, { text });
      setTranscript('');
    } catch (err) {
      console.error('[Voice] Failed to send text over WebRTC bridge', err);
      const detail = err?.response?.data?.detail;
      setError(detail || err.message || 'Failed to send text');
    }
  }, [conversationId, isRunning, transcript, sendVoiceWebRTCText]);

  // ============================================
  // Send to Nested
  // ============================================
  const sendToNested = async () => {
    if (!transcript.trim() || !conversationId) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/realtime/webrtc/bridge/${conversationId}/send-to-nested`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: transcript }),
      });
      if (!response.ok) {
        throw new Error(`Failed to send: ${response.statusText}`);
      }
      console.log('[Send] Sent to nested team:', transcript);
      setTranscript('');
    } catch (err) {
      console.error('[Send] Failed to send to nested:', err);
      setError(err.message || 'Failed to send to nested team');
    }
  };

  // ============================================
  // Send to Claude Code
  // ============================================
  const sendToClaude = async () => {
    if (!transcript.trim() || !conversationId) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/realtime/webrtc/bridge/${conversationId}/send-to-claude-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: transcript }),
      });
      if (!response.ok) {
        throw new Error(`Failed to send: ${response.statusText}`);
      }
      console.log('[Send] Sent to Claude Code:', transcript);
      setTranscript('');
    } catch (err) {
      console.error('[Send] Failed to send to Claude Code:', err);
      setError(err.message || 'Failed to send to Claude Code');
    }
  };

  // ============================================
  // Send to Disconnected Mode (non-WebRTC)
  // ============================================
  const sendToDisconnected = useCallback(async () => {
    const text = transcript.trim();
    if (!text || !conversationId) return;

    setIsSendingDisconnected(true);
    setError(null);

    try {
      const response = await sendTextMessage(conversationId, {
        text,
        voice: voiceConfig?.voice || 'cedar',
        include_audio: true
      });

      const { text: responseText, audio_base64: responseAudio } = response.data;

      console.log('[DisconnectedVoice] Text response received:', {
        text: responseText || '(empty)',
        textLength: responseText?.length || 0,
        hasAudio: !!responseAudio,
        audioLength: responseAudio?.length || 0,
      });

      // Clear input
      setTranscript('');

      // Play response audio if available
      if (responseAudio && audioRef.current) {
        const audioData = `data:audio/wav;base64,${responseAudio}`;
        audioRef.current.src = audioData;

        try {
          await audioRef.current.play();
        } catch (playError) {
          console.warn('[DisconnectedVoice] Audio playback failed:', playError);
        }
      }

    } catch (err) {
      console.error('[DisconnectedVoice] Failed to send text:', err);
      const detail = err?.response?.data?.detail || err.message || 'Failed to send text';
      setError(detail);
    } finally {
      setIsSendingDisconnected(false);
    }
  }, [transcript, conversationId, voiceConfig]);

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
  }, [isRunning, stopSession]);

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
    isStarting,
    isMuted,
    isSpeakerMuted,
    sessionLocked,
    remoteSessionActive,
    noMicrophoneMode,
    voiceConfig,
    setConfigEditorOpen,
    conversationError,
    error,
    setError,
    transcript,
    setTranscript,
    onSendToVoice: sendText,
    onSendToNested: sendToNested,
    onSendToClaude: sendToClaude,
    onSendToDisconnected: sendToDisconnected,
    isSendingDisconnected,
    nestedWsConnected: isRunning, // Connected via backend
    claudeCodeWsConnected: isRunning, // Connected via backend
    onStart: startSession,
    onStop: stopSession,
    onForceStop: forceStopSession,
    onToggleMute: toggleMute,
    onToggleSpeakerMute: toggleSpeakerMute,
    conversationId,
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
        {/* Note: Mobile drawer with conversations list is handled by VoiceDashboard parent component */}

        {/* Mobile layout */}
        <MobileVoiceLayout
          messages={messages}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
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
