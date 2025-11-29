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
} from '../../../api';
import { getHttpBase, getWsUrl } from '../../../utils/urlBuilder';

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
  const audioRelayWsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const eventsMapRef = useRef(new Map());
  const speakerGainNodeRef = useRef(null); // For speaker mute control
  const audioBufferQueueRef = useRef([]); // Buffer queue for smoother playback
  const isPlayingRef = useRef(false); // Track if currently playing audio
  const minBufferThreshold = 3; // Wait for 3 chunks before starting (adaptive buffering)
  const isMutedRef = useRef(true); // Ref for mute state (avoids closure issues)

  // Audio analysis for visualization
  const audioContextRef = useRef(null);
  const analyzerRef = useRef(null);
  const dataArrayRef = useRef(null);
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

      // Auto-select if only one active conversation and no selection yet
      // Use functional update to get current value without dependency
      setSelectedConversationId((currentId) => {
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
    const interval = setInterval(fetchConversations, 10000); // Refresh every 10s
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
      const source = audioContext.createMediaElementSource(audioRef.current);
      source.connect(analyzer);
      analyzer.connect(audioContext.destination);

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
        if (audioContext) {
          audioContext.close();
        }
      };
    } catch (err) {
      // Fallback if MediaElementSource fails
      console.warn('Could not create speaker analyzer', err);
      return undefined;
    }
  }, [isRunning]);

  // Start voice session - use WebRTC for high-quality peer-to-peer audio
  const startSession = async () => {
    if (isRunning || !selectedConversationId) return;
    setIsRunning(true);
    setIsMuted(true); // Start muted
    isMutedRef.current = true; // Also update ref
    setError(null);

    try {
      // Get microphone access
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error(
          'Microphone access not available. ' +
          'Mobile browsers require HTTPS for microphone access. ' +
          'Please access this page via HTTPS or use desktop Chrome which allows localhost access.'
        );
      }

      // QUALITY-FOCUSED: Request highest quality audio settings
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000,  // Request higher sample rate (48kHz instead of 44.1kHz)
          channelCount: 1,
          sampleSize: 16,
          latency: 0.02,  // 20ms latency is acceptable for quality
        }
      });
      micStreamRef.current = stream;

      // Mute by default
      stream.getAudioTracks().forEach((track) => {
        track.enabled = false; // Muted
      });

      // Create audio context for speaker playback
      if (!window.mobilePlaybackContext) {
        window.mobilePlaybackContext = new (window.AudioContext || window.webkitAudioContext)();
        const gainNode = window.mobilePlaybackContext.createGain();
        gainNode.connect(window.mobilePlaybackContext.destination);
        speakerGainNodeRef.current = gainNode;
      }

      // Resume AudioContext (Chrome autoplay policy requires user gesture)
      if (window.mobilePlaybackContext.state === 'suspended') {
        await window.mobilePlaybackContext.resume();
        console.log('[MobileVoice] AudioContext resumed - audio playback enabled');
      }

      // Connect to audio relay WebSocket to send mic audio to desktop
      const audioRelayUrl = getWsUrl(`/realtime/audio-relay/${selectedConversationId}/mobile`);
      const audioRelayWs = new WebSocket(audioRelayUrl);
      audioRelayWs.binaryType = 'arraybuffer';
      audioRelayWsRef.current = audioRelayWs;

      console.log('[MobileVoice] Connecting to audio relay:', audioRelayUrl);

      // Track next scheduled audio time to prevent overlap
      let nextAudioTime = 0;

      audioRelayWs.onopen = () => {
        console.log('[MobileVoice] Audio relay connected - ready to send microphone audio');
        // Initialize audio timeline to current time when connection opens
        nextAudioTime = window.mobilePlaybackContext.currentTime;
        console.log('[MobileVoice] Audio timeline initialized at', nextAudioTime.toFixed(3), 's');
        void recordEvent('controller', 'mobile_audio_relay_connected', { conversationId: selectedConversationId });
      };

      audioRelayWs.onmessage = (event) => {
        try {
          // Receive desktop audio (OpenAI response) from desktop
          const rawData = event.data;

          if (!(rawData instanceof ArrayBuffer)) {
            console.warn('[MobileVoice] Received non-ArrayBuffer data:', typeof rawData);
            return;
          }

          const audioContext = window.mobilePlaybackContext;
          const gainNode = speakerGainNodeRef.current;

          if (!audioContext || !gainNode) {
            console.error('[MobileVoice] Audio context not initialized');
            return;
          }

          // Convert Int16Array PCM to Float32Array
          const pcmData = new Int16Array(rawData);
          const floatData = new Float32Array(pcmData.length);
          for (let i = 0; i < pcmData.length; i++) {
            floatData[i] = pcmData[i] / 32768.0;
          }

          // Create audio buffer
          const audioBuffer = audioContext.createBuffer(1, floatData.length, 48000);
          audioBuffer.getChannelData(0).set(floatData);

          // Schedule audio to play sequentially (prevent overlap)
          const currentTime = audioContext.currentTime;
          const bufferDuration = audioBuffer.duration;

          // If we're behind, catch up to current time
          if (nextAudioTime < currentTime) {
            nextAudioTime = currentTime;
          }

          const source = audioContext.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(gainNode);
          source.start(nextAudioTime);

          // Update next audio time for sequential playback
          nextAudioTime += bufferDuration;

          console.log('[MobileVoice] Scheduled desktop audio chunk at', nextAudioTime.toFixed(3), 's');
        } catch (err) {
          console.error('[MobileVoice] Failed to process desktop audio:', err);
        }
      };

      audioRelayWs.onerror = (err) => {
        console.error('[MobileVoice] Audio relay error:', err);
        void recordEvent('controller', 'mobile_audio_relay_error', { message: String(err) });
      };

      audioRelayWs.onclose = () => {
        console.log('[MobileVoice] Audio relay closed');
        void recordEvent('controller', 'mobile_audio_relay_closed', {});
      };

      // Create audio processor to send microphone audio to desktop via WebSocket
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const micSource = audioContext.createMediaStreamSource(stream);
      // Use 16384 samples = ~340ms at 48kHz (matches desktop settings)
      const processor = audioContext.createScriptProcessor(16384, 1, 1);

      micSource.connect(processor);
      processor.connect(audioContext.destination);

      let mobileMicChunkCount = 0;
      let mobileMicLastLogTime = 0;

      processor.onaudioprocess = (audioEvent) => {
        mobileMicChunkCount++;
        const now = Date.now();

        // Log connection state every 50 chunks (~1.7s)
        if (mobileMicChunkCount % 50 === 0) {
          console.log(`[MobileMic→Desktop] Chunk #${mobileMicChunkCount}, WS state: ${audioRelayWsRef.current?.readyState}, muted: ${isMutedRef.current}`);
        }

        // Only send if unmuted and WebSocket is open (use ref to avoid closure stale state)
        if (audioRelayWsRef.current?.readyState === WebSocket.OPEN && !isMutedRef.current) {
          const inputData = audioEvent.inputBuffer.getChannelData(0);

          // Calculate RMS level to detect actual voice
          let sumSquares = 0;
          for (let i = 0; i < inputData.length; i++) {
            sumSquares += inputData[i] * inputData[i];
          }
          const rms = Math.sqrt(sumSquares / inputData.length);
          const dbLevel = 20 * Math.log10(rms + 1e-10);

          // Convert Float32Array to Int16Array PCM
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            const s = Math.max(-1, Math.min(1, inputData[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }

          // Send to desktop
          audioRelayWsRef.current.send(pcmData.buffer);

          // Log when voice detected (> -40 dB) but max once per 500ms
          if (dbLevel > -40 && (now - mobileMicLastLogTime) > 500) {
            console.log(`[MobileMic→Desktop] VOICE DETECTED! Level: ${dbLevel.toFixed(1)} dB, sending ${pcmData.length} samples`);
            mobileMicLastLogTime = now;
          }
        } else if (mobileMicChunkCount % 50 === 0) {
          // Log why we're NOT sending
          const reason = audioRelayWsRef.current?.readyState !== WebSocket.OPEN ? 'WebSocket not open' : 'Muted';
          console.warn(`[MobileMic→Desktop] NOT SENDING - Reason: ${reason}`);
        }
      };

      // Store for cleanup
      mediaRecorderRef.current = { processor, audioContext };

      void recordEvent('controller', 'mobile_session_started', { conversationId: selectedConversationId });
      console.log('[MobileVoice] Session started successfully with audio relay');
    } catch (err) {
      void recordEvent('controller', 'mobile_session_error', { message: err.message || String(err) });
      setError(err.message || String(err));
      setIsRunning(false);
      setIsMuted(true);
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((track) => track.stop());
        micStreamRef.current = null;
      }
    }
  };

  // Stop voice session
  const stopSession = () => {
    setIsRunning(false);
    setIsMuted(true);
    isMutedRef.current = true;
    void recordEvent('controller', 'mobile_session_stopped', {});

    // Stop microphone
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((track) => track.stop());
      micStreamRef.current = null;
    }

    // Close audio relay WebSocket
    if (audioRelayWsRef.current) {
      try {
        audioRelayWsRef.current.close();
      } catch {}
      audioRelayWsRef.current = null;
    }

    // Stop audio processor
    if (mediaRecorderRef.current) {
      const { processor, audioContext } = mediaRecorderRef.current;
      if (processor) {
        processor.disconnect();
      }
      if (audioContext) {
        audioContext.close();
      }
      mediaRecorderRef.current = null;
    }

    setMicLevel(0);
    setSpeakerLevel(0);
  };

  // Toggle microphone mute
  const toggleMute = () => {
    if (!micStreamRef.current) return;

    setIsMuted((prevMuted) => {
      const newMutedState = !prevMuted;

      // Update ref immediately (for processor callback)
      isMutedRef.current = newMutedState;

      // Also update track enabled state
      const audioTracks = micStreamRef.current.getAudioTracks();
      audioTracks.forEach((track) => {
        track.enabled = !newMutedState;
      });

      console.log(`[MobileMute] Toggled to: ${newMutedState ? 'MUTED' : 'UNMUTED'}, ref updated`);
      void recordEvent('controller', newMutedState ? 'mobile_microphone_muted' : 'mobile_microphone_unmuted', {});
      return newMutedState;
    });
  };

  // Toggle speaker mute
  const toggleSpeakerMute = () => {
    setIsSpeakerMuted((prevMuted) => {
      const newMutedState = !prevMuted;

      // Update gain node volume
      if (speakerGainNodeRef.current) {
        speakerGainNodeRef.current.gain.value = newMutedState ? 0 : 1;
      }

      void recordEvent('controller', newMutedState ? 'mobile_speaker_muted' : 'mobile_speaker_unmuted', {});
      return newMutedState;
    });
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
          value={selectedConversationId}
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
                color={isSpeakerMuted ? 'warning' : 'info'}
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
