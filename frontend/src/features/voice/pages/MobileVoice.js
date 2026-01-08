import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  Chip,
  Alert,
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import VolumeOffIcon from '@mui/icons-material/VolumeOff';
import StopIcon from '@mui/icons-material/Stop';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import {
  listVoiceConversations,
  getVoiceConversation,
  connectVoiceConversationStream,
  appendVoiceConversationEvent,
  cleanupInactiveConversations,
  startVoiceWebRTCBridge,
  disconnectVoiceWebRTC,
  stopVoiceWebRTCBridge,
} from '../../../api';
import { getHttpBase } from '../../../utils/urlBuilder';

/**
 * MobileVoice - Mobile-optimized remote microphone interface
 *
 * Simple, clean interface for using mobile as a wireless mic
 * for an existing voice conversation running on another device.
 */
function MobileVoice() {
  const { conversationId: urlConversationId } = useParams();
  const navigate = useNavigate();

  // Conversation state
  const [conversations, setConversations] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(urlConversationId || '');
  const [conversation, setConversation] = useState(null);
  const [conversationError, setConversationError] = useState(null);
  const [messages, setMessages] = useState([]);

  // Session state
  const [isRunning, setIsRunning] = useState(false);
  const [isMuted, setIsMuted] = useState(true); // Start muted
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false); // Speaker not muted by default
  const [error, setError] = useState(null);

  // Audio streaming refs
  const audioRef = useRef(null);
  const micStreamRef = useRef(null);
  const streamRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const connectionIdRef = useRef(null); // Backend connection ID
  const eventsMapRef = useRef(new Map());
  const fallbackAudioContextRef = useRef(null);

  // Audio analysis for visualization
  const audioContextRef = useRef(null);
  const analyzerRef = useRef(null);
  const dataArrayRef = useRef(null);
  const mediaElementSourceRef = useRef(null); // Track if MediaElementSource already created
  const [micLevel, setMicLevel] = useState(0);
  const [speakerLevel, setSpeakerLevel] = useState(0);
  const animationFrameRef = useRef(null);

  // Use centralized URL builder
  const backendBase = getHttpBase();

  // Normalize event from stream
  const normalizeEvent = useCallback((event) => {
    if (!event) return null;
    const { id, timestamp, source, type, payload } = event;
    return {
      id,
      timestamp,
      source,
      type,
      data: payload ?? {},
    };
  }, []);

  // Upsert events into state
  const upsertEvents = useCallback((incoming) => {
    if (!incoming || incoming.length === 0) return;
    const map = eventsMapRef.current;
    incoming.forEach((item) => {
      if (!item || typeof item.id === 'undefined' || item.id === null) return;
      map.set(item.id, item);
    });
    const sorted = Array.from(map.values()).sort((a, b) => {
      const aId = typeof a.id === 'number' ? a.id : Number(a.id) || 0;
      const bId = typeof b.id === 'number' ? b.id : Number(b.id) || 0;
      return aId - bId;
    });
    setMessages(sorted);
  }, []);

  // Record event to database
  const recordEvent = useCallback(async (source, type, payload) => {
    if (!selectedConversationId) return null;
    try {
      const res = await appendVoiceConversationEvent(selectedConversationId, {
        source,
        type,
        payload,
      });
      const normalized = normalizeEvent(res.data);
      if (normalized) {
        upsertEvents([normalized]);
      }
      return normalized;
    } catch (err) {
      console.error('Failed to persist conversation event', err);
      return null;
    }
  }, [selectedConversationId, normalizeEvent, upsertEvents]);

  // Load conversations list
  const fetchConversations = useCallback(async () => {
    try {
      const res = await listVoiceConversations();
      const convs = res.data ?? [];
      console.log('[MobileVoice] Fetched conversations:', convs.length, convs);
      setConversations(convs);

      // Check if currently selected conversation still exists
      // Use functional update to get current value without dependency
      setSelectedConversationId((currentId) => {
        // If current ID is not in the list, clear it
        if (currentId && !convs.find(c => c.id === currentId)) {
          console.warn('[MobileVoice] Selected conversation no longer exists, clearing selection');
          navigate('/mobile-voice', { replace: true });
          return null;
        }

        // Auto-select if only one active conversation and no selection yet
        if (!currentId && convs.length === 1) {
          const onlyConv = convs[0];
          console.log('[MobileVoice] Auto-selecting conversation:', onlyConv.id, onlyConv.name);
          navigate(`/mobile-voice/${onlyConv.id}`, { replace: true });
          return onlyConv.id;
        }
        return currentId;
      });
    } catch (err) {
      console.error('[MobileVoice] Failed to load conversations', err);
    }
  }, [navigate]);

  // Load conversation details and subscribe to stream
  useEffect(() => {
    if (!selectedConversationId) return undefined;

    let cancelled = false;

    // Load conversation details
    (async () => {
      try {
        const res = await getVoiceConversation(selectedConversationId, { limit: 100 });
        if (cancelled) return;
        const detail = res.data;
        setConversation(detail);
        setConversationError(null);
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

        // If conversation doesn't exist (404), clear the selection and URL
        if (err?.response?.status === 404) {
          console.warn('[MobileVoice] Conversation not found (404), clearing selection');
          setSelectedConversationId(null);
          navigate('/mobile-voice', { replace: true });
        }
      }
    })();

    // Subscribe to event stream
    const socket = connectVoiceConversationStream(selectedConversationId, { limit: 100 });
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

    socket.onerror = (event) => {
      console.error('Conversation stream error', event);
    };

    socket.onclose = () => {
      if (streamRef.current === socket) {
        streamRef.current = null;
      }
    };

    return () => {
      cancelled = true;
      try {
        socket.close();
      } catch (e) {
        /* noop */
      }
      if (streamRef.current === socket) {
        streamRef.current = null;
      }
    };
  }, [selectedConversationId, normalizeEvent, upsertEvents]);

  // Load conversations on mount
  useEffect(() => {
    fetchConversations();
    const interval = setInterval(fetchConversations, 30000); // Refresh every 30s (reduced from 10s)
    return () => clearInterval(interval);
  }, [fetchConversations]);

  // Audio level monitoring
  useEffect(() => {
    if (!isRunning || !micStreamRef.current) return undefined;

    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const analyzer = audioContext.createAnalyser();
    analyzer.fftSize = 256;
    const bufferLength = analyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const source = audioContext.createMediaStreamSource(micStreamRef.current);
    source.connect(analyzer);

    audioContextRef.current = audioContext;
    analyzerRef.current = analyzer;
    dataArrayRef.current = dataArray;

    const updateLevels = () => {
      if (!analyzerRef.current || !dataArrayRef.current) return;

      analyzerRef.current.getByteFrequencyData(dataArrayRef.current);
      const average = dataArrayRef.current.reduce((a, b) => a + b, 0) / dataArrayRef.current.length;
      const normalized = Math.min(100, (average / 255) * 100);
      setMicLevel(isMuted ? 0 : normalized);

      animationFrameRef.current = requestAnimationFrame(updateLevels);
    };

    updateLevels();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [isRunning, isMuted]);

  // Speaker level monitoring (from remote audio)
  useEffect(() => {
    if (!isRunning || !audioRef.current) return undefined;

    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const analyzer = audioContext.createAnalyser();
    analyzer.fftSize = 256;
    const bufferLength = analyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    try {
      // Only create MediaElementSource once per audio element lifetime
      if (!mediaElementSourceRef.current) {
        const source = audioContext.createMediaElementSource(audioRef.current);
        source.connect(analyzer);
        analyzer.connect(audioContext.destination);
        mediaElementSourceRef.current = source;
        console.log('[MobileVoice] Created MediaElementSource for speaker analysis');
      }

      const updateSpeaker = () => {
        if (!analyzer) return;
        analyzer.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        const normalized = Math.min(100, (average / 255) * 100);
        setSpeakerLevel(normalized);
        requestAnimationFrame(updateSpeaker);
      };

      updateSpeaker();

      return () => {
        // Don't close the context or disconnect source - they may be reused
        // Only clean up on component unmount
      };
    } catch (err) {
      // Fallback if MediaElementSource fails
      console.warn('[MobileVoice] Could not create speaker analyzer', err);
      return undefined;
    }
  }, [isRunning]);

  // Helper: Get microphone or fallback to silent track
  const ensureMicrophoneStream = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000,
          channelCount: 1,
        }
      });
      return stream;
    } catch (err) {
      console.warn('[MobileVoice] No microphone available, using silent track', err);
      // Create silent audio track as fallback
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      gainNode.gain.value = 0; // Silent
      oscillator.connect(gainNode);
      const destination = ctx.createMediaStreamDestination();
      gainNode.connect(destination);
      oscillator.start();
      fallbackAudioContextRef.current = ctx;
      return destination.stream;
    }
  };

  // Helper: Attach remote audio stream to audio element
  const attachRemoteAudio = (stream) => {
    if (!audioRef.current) return;
    audioRef.current.srcObject = stream;
    audioRef.current.muted = isSpeakerMuted;
    const playPromise = audioRef.current.play();
    if (playPromise?.catch) {
      playPromise.catch((err) => {
        console.warn('[MobileVoice] Failed to start remote audio playback', err);
      });
    }
  };

  // Start voice session - connect to backend WebRTC bridge
  const startSession = async () => {
    if (isRunning || !selectedConversationId) return;
    setError(null);

    try {
      // Clean up inactive conversations (older than 30 minutes)
      try {
        const cleanupResult = await cleanupInactiveConversations(30);
        if (cleanupResult.data?.deleted_count > 0) {
          console.log(`[MobileVoice] Deleted ${cleanupResult.data.deleted_count} inactive conversations:`, cleanupResult.data.deleted_ids);
        }
      } catch (cleanupErr) {
        console.warn('[MobileVoice] Failed to cleanup inactive conversations:', cleanupErr);
      }

      // Get microphone stream (or fallback to silent)
      const localStream = await ensureMicrophoneStream();
      micStreamRef.current = localStream;

      // Create WebRTC peer connection
      const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
      peerConnectionRef.current = pc;

      // Add local microphone tracks
      console.log('[MobileVoice] Adding local audio tracks to peer connection');
      const tracks = localStream.getTracks();
      tracks.forEach((track, idx) => {
        console.log(`[MobileVoice] Track ${idx}: kind=${track.kind}, enabled=${track.enabled}`);
        pc.addTrack(track, localStream);
      });

      // Start muted
      tracks.forEach((track) => {
        track.enabled = false;
      });
      setIsMuted(true);

      // Handle remote audio track from backend (OpenAI responses)
      pc.ontrack = (event) => {
        console.log('[MobileVoice] Remote track received:', event.track.kind);
        const remoteStream = event.streams?.[0] || new MediaStream([event.track]);
        attachRemoteAudio(remoteStream);
      };

      // Monitor connection state
      pc.onconnectionstatechange = () => {
        console.log('[MobileVoice] Connection state:', pc.connectionState);
        if (pc.connectionState === 'failed') {
          setError('WebRTC connection failed');
        }
      };

      // Create offer
      const offer = await pc.createOffer({ offerToReceiveAudio: true, offerToReceiveVideo: false });
      await pc.setLocalDescription(offer);
      console.log('[MobileVoice] Created offer, local description set');

      // Send offer to backend and get answer
      const response = await startVoiceWebRTCBridge({
        conversation_id: selectedConversationId,
        offer: offer.sdp,
      });

      const answerSdp = response?.data?.answer;
      const sessionId = response?.data?.session_id;
      if (!answerSdp) {
        throw new Error('Invalid SDP answer from backend');
      }

      connectionIdRef.current = sessionId;
      console.log('[MobileVoice] Received answer from backend, connection_id:', sessionId);

      // Set remote description
      await pc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: answerSdp }));
      console.log('[MobileVoice] Remote description (answer) set');

      setIsRunning(true);
      void recordEvent('controller', 'mobile_session_started', { conversationId: selectedConversationId });
    } catch (err) {
      console.error('[MobileVoice] Failed to start session:', err);
      void recordEvent('controller', 'mobile_session_error', { message: err.message || String(err) });
      setError(err.message || String(err));

      // Cleanup on error
      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
      }
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((track) => track.stop());
        micStreamRef.current = null;
      }
      if (fallbackAudioContextRef.current) {
        fallbackAudioContextRef.current.close();
        fallbackAudioContextRef.current = null;
      }
    }
  };

  // Stop voice session
  const stopSession = async () => {
    console.log('[MobileVoice] Stop session');

    // Close peer connection
    const pc = peerConnectionRef.current;
    if (pc) {
      pc.getSenders().forEach((sender) => sender.track?.stop());
      pc.getReceivers().forEach((receiver) => receiver.track?.stop());
      pc.close();
      peerConnectionRef.current = null;
    }

    // Clear audio element
    if (audioRef.current) {
      audioRef.current.srcObject = null;
    }

    // Stop microphone
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }

    // Close fallback audio context
    if (fallbackAudioContextRef.current) {
      try {
        fallbackAudioContextRef.current.close();
      } catch (err) {
        console.warn('[MobileVoice] Failed to close fallback audio context', err);
      }
      fallbackAudioContextRef.current = null;
    }

    // Disconnect from backend
    if (connectionIdRef.current) {
      try {
        console.log('[MobileVoice] Disconnecting connection:', connectionIdRef.current);
        await disconnectVoiceWebRTC(connectionIdRef.current);
      } catch (err) {
        console.warn('[MobileVoice] Failed to disconnect from backend:', err);
      }
      connectionIdRef.current = null;
    }

    setIsRunning(false);
    setIsMuted(false);
    setIsSpeakerMuted(false);
    setMicLevel(0);
    setSpeakerLevel(0);
    void recordEvent('controller', 'mobile_session_stopped', {});
  };

  // Toggle microphone mute
  const toggleMute = () => {
    if (!micStreamRef.current) return;

    const newMuted = !isMuted;
    setIsMuted(newMuted);

    // Update track enabled state
    micStreamRef.current.getAudioTracks().forEach((track) => {
      track.enabled = !newMuted;
    });

    console.log(`[MobileVoice] Mic toggled to: ${newMuted ? 'MUTED' : 'UNMUTED'}`);
    void recordEvent('controller', newMuted ? 'mobile_microphone_muted' : 'mobile_microphone_unmuted', {});
  };

  // Toggle speaker mute
  const toggleSpeakerMute = () => {
    const newMuted = !isSpeakerMuted;
    setIsSpeakerMuted(newMuted);

    if (audioRef.current) {
      audioRef.current.muted = newMuted;
      if (!newMuted) {
        const playPromise = audioRef.current.play();
        if (playPromise?.catch) {
          playPromise.catch((err) => console.warn('[MobileVoice] Failed to resume audio', err));
        }
      }
    }

    console.log(`[MobileVoice] Speaker toggled to: ${newMuted ? 'MUTED' : 'UNMUTED'}`);
    void recordEvent('controller', newMuted ? 'mobile_speaker_muted' : 'mobile_speaker_unmuted', {});
  };

  // Handle conversation selection
  const handleConversationChange = (event) => {
    const newId = event.target.value;
    setSelectedConversationId(newId);
    navigate(`/mobile-voice/${newId}`);
  };

  // Cleanup on unmount
  useEffect(() => () => stopSession(), []);

  // Detect if desktop session is active
  const desktopSessionActive = React.useMemo(() => {
    let lastStart = null;
    let lastStop = null;
    messages.forEach((msg) => {
      if ((msg.source || '').toLowerCase() !== 'controller') return;
      const type = (msg.type || '').toLowerCase();
      if (type === 'session_started') {
        lastStart = msg.timestamp;
      }
      if (type === 'session_stopped' || type === 'session_error') {
        lastStop = msg.timestamp;
      }
    });
    if (!lastStart) return false;
    if (!lastStop) return true;
    return new Date(lastStart).getTime() > new Date(lastStop).getTime();
  }, [messages]);

  // Recent events for display
  const recentEvents = React.useMemo(() => {
    return messages
      .filter((msg) => {
        const source = (msg.source || '').toLowerCase();
        const type = (msg.type || '').toLowerCase();
        return (
          (source === 'nested' && type === 'textmessage') ||
          (source === 'claude_code' && type === 'textmessage') ||
          (source === 'controller' && type.includes('tool'))
        );
      })
      .slice(-5)
      .reverse();
  }, [messages]);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        bgcolor: 'background.default',
        display: 'flex',
        flexDirection: 'column',
        p: 2,
        pb: 4,
      }}
    >
      {/* Hidden audio element */}
      <audio ref={audioRef} autoPlay style={{ display: 'none' }} />

      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
          🎙️ Mobile Voice
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Remote microphone for voice conversations
        </Typography>
      </Box>

      {/* Conversation Selector */}
      <FormControl fullWidth sx={{ mb: 3 }}>
        <Select
          value={selectedConversationId || ''}
          onChange={handleConversationChange}
          displayEmpty
          disabled={isRunning}
          sx={{
            fontSize: '1.1rem',
            '& .MuiSelect-select': {
              py: 1.5,
            },
          }}
        >
          <MenuItem value="" disabled>
            <em>Select a conversation</em>
          </MenuItem>
          {conversations.map((conv) => (
            <MenuItem key={conv.id} value={conv.id}>
              {conv.name || `Conversation ${conv.id.slice(0, 8)}`}
            </MenuItem>
          ))}
          {conversations.length === 0 && (
            <MenuItem value="" disabled>
              No conversations available
            </MenuItem>
          )}
        </Select>
      </FormControl>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Conversation Error */}
      {conversationError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {conversationError}
        </Alert>
      )}

      {/* Status Info */}
      {desktopSessionActive && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Desktop session is active on this conversation
        </Alert>
      )}

      {/* Main Control Panel */}
      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px',
          gap: 3,
        }}
      >
        {/* Primary Button (Start/Stop) */}
        {!isRunning ? (
          <IconButton
            onClick={startSession}
            disabled={!selectedConversationId || Boolean(conversationError)}
            sx={{
              width: 120,
              height: 120,
              bgcolor: 'primary.main',
              color: 'white',
              boxShadow: 3,
              '&:hover': {
                bgcolor: 'primary.dark',
                transform: 'scale(1.05)',
                boxShadow: 6,
              },
              '&:active': {
                transform: 'scale(0.95)',
              },
              '&:disabled': {
                bgcolor: 'action.disabledBackground',
              },
              transition: 'all 0.2s ease',
            }}
          >
            <PlayArrowIcon sx={{ fontSize: 60 }} />
          </IconButton>
        ) : (
          <IconButton
            onClick={stopSession}
            sx={{
              width: 120,
              height: 120,
              bgcolor: 'error.main',
              color: 'white',
              boxShadow: 3,
              animation: 'pulse 2s ease-in-out infinite',
              '@keyframes pulse': {
                '0%, 100%': {
                  boxShadow: '0 0 0 0 rgba(244, 67, 54, 0.7)',
                },
                '50%': {
                  boxShadow: '0 0 0 12px rgba(244, 67, 54, 0)',
                },
              },
              '&:hover': {
                bgcolor: 'error.dark',
                transform: 'scale(1.05)',
              },
              '&:active': {
                transform: 'scale(0.95)',
              },
              transition: 'all 0.2s ease',
            }}
          >
            <StopIcon sx={{ fontSize: 60 }} />
          </IconButton>
        )}

        {/* Status Text */}
        <Typography variant="h6" color={isRunning ? 'success.main' : 'text.secondary'} sx={{ fontWeight: 500 }}>
          {isRunning ? 'Connected' : 'Tap to start'}
        </Typography>

        {/* Control Buttons Row */}
        {isRunning && (
          <Box sx={{ display: 'flex', gap: 3, alignItems: 'center' }}>
            {/* Microphone Mute/Unmute Button */}
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
              <IconButton
                onClick={toggleMute}
                sx={{
                  width: 100,
                  height: 100,
                  bgcolor: isMuted ? 'warning.main' : 'success.main',
                  color: 'white',
                  boxShadow: 3,
                  '&:hover': {
                    bgcolor: isMuted ? 'warning.dark' : 'success.dark',
                    transform: 'scale(1.05)',
                  },
                  '&:active': {
                    transform: 'scale(0.95)',
                  },
                  transition: 'all 0.2s ease',
                }}
              >
                {isMuted ? <MicOffIcon sx={{ fontSize: 50 }} /> : <MicIcon sx={{ fontSize: 50 }} />}
              </IconButton>
              <Chip
                label={isMuted ? 'Mic Off' : 'Mic On'}
                color={isMuted ? 'warning' : 'success'}
                size="small"
                sx={{ fontWeight: 500 }}
              />
            </Box>

            {/* Speaker Mute/Unmute Button */}
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
              <IconButton
                onClick={toggleSpeakerMute}
                sx={{
                  width: 100,
                  height: 100,
                  bgcolor: isSpeakerMuted ? 'warning.main' : 'info.main',
                  color: 'white',
                  boxShadow: 3,
                  '&:hover': {
                    bgcolor: isSpeakerMuted ? 'warning.dark' : 'info.dark',
                    transform: 'scale(1.05)',
                  },
                  '&:active': {
                    transform: 'scale(0.95)',
                  },
                  transition: 'all 0.2s ease',
                }}
              >
                {isSpeakerMuted ? <VolumeOffIcon sx={{ fontSize: 50 }} /> : <VolumeUpIcon sx={{ fontSize: 50 }} />}
              </IconButton>
              <Chip
                label={isSpeakerMuted ? 'Speaker Off' : 'Speaker On'}
                color={isSpeakerMuted ? 'warning' : 'success'}
                size="small"
                sx={{ fontWeight: 500 }}
              />
            </Box>
          </Box>
        )}

        {/* Dual Audio Visualizer */}
        {isRunning && (
          <Box sx={{ width: '100%', maxWidth: 400, mt: 2 }}>
            {/* Microphone Level */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                Microphone
              </Typography>
              <Box
                sx={{
                  height: 12,
                  bgcolor: 'rgba(0, 0, 0, 0.1)',
                  borderRadius: 1,
                  overflow: 'hidden',
                }}
              >
                <Box
                  sx={{
                    height: '100%',
                    width: `${micLevel}%`,
                    bgcolor: isMuted ? 'grey.400' : 'success.main',
                    transition: 'width 0.1s ease, background-color 0.3s ease',
                  }}
                />
              </Box>
            </Box>

            {/* Speaker Level */}
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                Speaker
              </Typography>
              <Box
                sx={{
                  height: 12,
                  bgcolor: 'rgba(0, 0, 0, 0.1)',
                  borderRadius: 1,
                  overflow: 'hidden',
                }}
              >
                <Box
                  sx={{
                    height: '100%',
                    width: `${speakerLevel}%`,
                    bgcolor: 'primary.main',
                    transition: 'width 0.1s ease',
                  }}
                />
              </Box>
            </Box>
          </Box>
        )}
      </Box>

      {/* Recent Activity */}
      {isRunning && recentEvents.length > 0 && (
        <Box sx={{ mt: 'auto', pt: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            Recent Activity
          </Typography>
          <Box
            sx={{
              bgcolor: (theme) =>
                theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
              borderRadius: 2,
              p: 2,
              maxHeight: 150,
              overflowY: 'auto',
            }}
          >
            {recentEvents.map((msg, idx) => {
              const source = msg.source || 'unknown';
              const content = msg.data?.content || msg.data?.message || msg.data?.text || 'Event';
              const truncated = content.length > 80 ? `${content.slice(0, 80)}...` : content;
              return (
                <Typography
                  key={msg.id || idx}
                  variant="body2"
                  sx={{
                    mb: 0.5,
                    color: 'text.secondary',
                    fontSize: '0.85rem',
                  }}
                >
                  <strong>{source}:</strong> {truncated}
                </Typography>
              );
            })}
          </Box>
        </Box>
      )}

      {/* Footer Info */}
      {conversation && (
        <Box sx={{ mt: 3, textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            {conversation.name || `Conversation ${conversation.id.slice(0, 8)}`}
          </Typography>
        </Box>
      )}
    </Box>
  );
}

export default MobileVoice;
