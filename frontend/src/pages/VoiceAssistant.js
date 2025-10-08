import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';
import {
  Box,
  Paper,
  Stack,
  Typography,
  Button,
  TextField,
  Chip,
  Alert,
} from '@mui/material';
import RunConsole from '../components/RunConsole';
import ConversationHistory from '../components/ConversationHistory';
import {
  appendVoiceConversationEvent,
  getVoiceConversation,
  connectVoiceConversationStream,
} from '../api';

const MAX_REPLAY_ITEMS = 50;

/**
 * A simple React component that demonstrates how to connect to the
 * OpenAI realtime API using WebRTC and, in parallel, subscribe to the
 * backend nested team WebSocket stream. Any TextMessage from the nested
 * team is forwarded immediately to the OpenAI Realtime data channel so
 * the voice model narrates and stays in sync.
 */
function VoiceAssistant() {
  const { conversationId } = useParams();
  const [conversation, setConversation] = useState(null);
  const [conversationLoading, setConversationLoading] = useState(true);
  const [conversationError, setConversationError] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const peerRef = useRef(null);
  const dataChannelRef = useRef(null);
  const nestedWsRef = useRef(null);
  const [sharedNestedWs, setSharedNestedWs] = useState(null);
  const audioRef = useRef(null);
  const streamRef = useRef(null);
  const eventsMapRef = useRef(new Map());
  const replayQueueRef = useRef([]);

  // Track accumulating function-call arguments by call id
  const toolCallsRef = useRef({});
  const hasSpokenMidRef = useRef(false);
  const runCompletedRef = useRef(false);

  const formatTimestamp = useCallback((value) => {
    if (!value) return '';
    try {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return String(value);
      const now = new Date();
      const sameDay = date.toDateString() === now.toDateString();
      const options = sameDay
        ? { hour: 'numeric', minute: '2-digit', second: '2-digit' }
        : { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' };
      return new Intl.DateTimeFormat(undefined, options).format(date);
    } catch (e) {
      return String(value);
    }
  }, []);

  const conversationTitle = useMemo(() => {
    if (!conversation) {
      return conversationId ? `Conversation ${conversationId}` : 'Voice Assistant Conversation';
    }
    const title = conversation.title
      || conversation.name
      || conversation.display_name
      || conversation?.metadata?.title;
    if (title) return title;
    if (conversationId) return `Conversation ${conversationId}`;
    return 'Voice Assistant Conversation';
  }, [conversation, conversationId]);

  const nestedHighlights = useMemo(() => {
    if (!messages || messages.length === 0) return [];
    return messages
      .filter((msg) => (msg?.source || '').toLowerCase() === 'nested')
      .filter((msg) => {
        const type = (msg?.type || '').toLowerCase();
        return type.includes('textmessage') || type === 'text_message';
      })
      .slice(-25);
  }, [messages]);

  const buildReplayItems = useCallback(() => {
    if (!messages || messages.length === 0) return [];
    const items = [];
    messages.forEach((msg) => {
      if (!msg || !msg.data) return;
      const sourceLower = (msg.source || '').toLowerCase();
      const typeLower = (msg.type || '').toLowerCase();
      if (sourceLower === 'user' && typeLower === 'voice_user_message') {
        const text = msg.data?.text || msg.data?.transcript || msg.data?.message;
        if (text) {
          items.push({
            type: 'message',
            role: 'user',
            content: [{ type: 'input_text', text }],
          });
        }
      }
  if (sourceLower === 'controller' && (typeLower === 'voice_forward' || typeLower === 'voice_forward_pending')) {
        const text = msg.data?.text || msg.data?.message;
        if (text) {
          const item = {
            type: 'message',
            role: msg.data?.role || 'system',
            content: [{ type: 'input_text', text }],
          };
          if (msg.data?.metadata && Object.keys(msg.data.metadata).length > 0) {
            item.metadata = msg.data.metadata;
          }
          items.push(item);
        }
      }
    });
    return items;
  }, [messages]);

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

  const recordEvent = useCallback(async (source, type, payload) => {
    if (!conversationId) return null;
    try {
      const res = await appendVoiceConversationEvent(conversationId, {
        source,
        type,
        payload,
      });
      const normalized = normalizeEvent(res.data);
      if (normalized) {
        upsertEvents([normalized]);
        setConversation((prev) => (prev ? { ...prev, updated_at: normalized.timestamp } : prev));
      }
      return normalized;
    } catch (err) {
      console.error('Failed to persist conversation event', err);
      return null;
    }
  }, [conversationId, normalizeEvent, upsertEvents]);

  const forwardToVoice = useCallback((role, rawText, metadata = {}) => {
    const text = (rawText ?? '').toString().trim();
    if (!text) return;
    const item = {
      type: 'message',
      role: role || 'system',
      content: [{ type: 'input_text', text }],
    };
    if (metadata && Object.keys(metadata).length > 0) {
      item.metadata = metadata;
    }

    let cloneForQueue = item;
    try {
      cloneForQueue = JSON.parse(JSON.stringify(item));
    } catch {
      cloneForQueue = { ...item };
    }
    replayQueueRef.current = [...(replayQueueRef.current || []), cloneForQueue].slice(-MAX_REPLAY_ITEMS);

    const channel = dataChannelRef.current;
    if (!channel || channel.readyState !== 'open') {
      void recordEvent('controller', 'voice_forward_pending', { role, text, metadata });
      return;
    }

    try {
      channel.send(JSON.stringify({ type: 'conversation.item.create', item }));
      channel.send(JSON.stringify({ type: 'response.create' }));
      hasSpokenMidRef.current = true;
      void recordEvent('controller', 'voice_forward', { role, text, metadata, item });
    } catch (err) {
      console.error('Failed to forward to voice', err);
      void recordEvent('controller', 'voice_forward_error', {
        role,
        text,
        metadata,
        error: err?.message || String(err),
      });
    }
  }, [recordEvent]);

  const remoteSessionActive = useMemo(() => {
    let lastStart = null;
    let lastStop = null;
    messages.forEach((msg) => {
      if ((msg.source || '').toLowerCase() !== 'controller') return;
      if ((msg.type || '').toLowerCase() === 'session_started') {
        lastStart = msg.timestamp;
      }
      if ((msg.type || '').toLowerCase() === 'session_stopped' || (msg.type || '').toLowerCase() === 'session_error') {
        lastStop = msg.timestamp;
      }
    });
    if (!lastStart) return false;
    if (!lastStop) return true;
    return new Date(lastStart).getTime() > new Date(lastStop).getTime();
  }, [messages]);
  const sessionLocked = isRunning || remoteSessionActive;

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

    socket.onerror = (event) => {
      console.error('Conversation stream error', event);
    };

    socket.onclose = () => {
      if (streamRef.current === socket) {
        streamRef.current = null;
      }
    };

    return () => {
      try {
        socket.close();
      } catch (e) {
        /* noop */
      }
      if (streamRef.current === socket) {
        streamRef.current = null;
      }
    };
  }, [conversationId, normalizeEvent, upsertEvents]);

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

  // Resolve backend base URLs
  const backendBase = (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000');
  const derivedWsBase = (() => {
    try {
      const u = new URL(backendBase);
      const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProto}//${u.host}`;
    } catch {
      return 'ws://localhost:8000';
    }
  })();

  // Tool definitions exposed to the Realtime model
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
      name: 'pause',
      description: 'Request the controller to pause the current nested conversation (best effort).',
      parameters: { type: 'object', properties: {}, additionalProperties: false },
    },
    {
      type: 'function',
      name: 'reset',
      description: 'Reset the nested team conversation state (best effort).',
      parameters: { type: 'object', properties: {}, additionalProperties: false },
    },
  ];

  // Utility: post SDP offer and get answer from OpenAI using our backend proxy (main.py at localhost:8000)
  const postSdpOffer = async (mediaAddr, sessionId, clientSecret, sdp) => {
    const url = `${backendBase}/api/realtime/sdp`;
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ media_addr: mediaAddr, session_id: sessionId, client_secret: clientSecret, sdp }),
    });
    const bodyText = await resp.text();
    if (!resp.ok) {
      let detail = bodyText;
      try { const j = JSON.parse(bodyText); detail = j.detail ?? j; } catch {}
      const snippet = typeof detail === 'string' ? detail.slice(0, 300) : JSON.stringify(detail).slice(0, 300);
      throw new Error(`SDP exchange failed: ${resp.status} ${snippet}`);
    }
    // Some servers/frameworks may wrap plain SDP in a JSON { detail: "..." }
    // Unwrap it when detected.
    if (bodyText.trim().startsWith('{')) {
      try {
        const obj = JSON.parse(bodyText);
        if (typeof obj.detail === 'string' && obj.detail.trim().startsWith('v=')) {
          return obj.detail;
        }
      } catch {}
    }
    return bodyText; // Backend returns application/sdp
  };

  const startSession = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setError(null);
    try {
      const historyItems = buildReplayItems();
      replayQueueRef.current = (historyItems || []).slice(-MAX_REPLAY_ITEMS);
      // Request a new realtime session from our backend (mounted under /api/realtime)
      const voice = (process.env.REACT_APP_VOICE || 'alloy');
      const tokenUrl = `${backendBase}/api/realtime/token/openai?model=gpt-realtime&voice=${encodeURIComponent(voice)}`;
      const tokenResp = await fetch(tokenUrl);
      const tokenBody = await tokenResp.text();
      if (!tokenResp.ok) {
        let detail = tokenBody;
        try { const j = JSON.parse(tokenBody); detail = j.detail ? JSON.stringify(j.detail) : JSON.stringify(j); } catch {}
        throw new Error(`Failed to fetch token: ${tokenResp.status} ${detail?.slice ? detail.slice(0, 300) : detail}`);
      }
      let tokenJson;
      try {
        tokenJson = JSON.parse(tokenBody);
      } catch (e) {
        throw new Error(`Token response was not JSON. URL=${tokenUrl}. Body (first 200 chars): ${tokenBody.slice(0, 200)}`);
      }
      const { id: sessionId, client_secret: clientSecret, media_addr: mediaAddr } = tokenJson;
      if (!sessionId || !clientSecret) {
        throw new Error(`Invalid token payload: ${JSON.stringify(tokenJson)}`);
      }

      const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
      peerRef.current = pc;

      // Create a data channel to send/receive OAI events
      const dataChannel = pc.createDataChannel('oai-events');
      dataChannelRef.current = dataChannel;

      // On open, announce tool availability to the model
      dataChannel.onopen = () => {
        try {
          dataChannel.send(JSON.stringify({ type: 'session.update', session: { tools: realtimeTools } }));
          const queued = replayQueueRef.current || [];
          if (queued.length > 0) {
            queued.forEach((item) => {
              try {
                dataChannel.send(JSON.stringify({ type: 'conversation.item.create', item }));
              } catch (err) {
                console.error('Failed to replay history item', err);
              }
            });
            void recordEvent('controller', 'history_replay', { count: queued.length });
            replayQueueRef.current = [];
          }
        } catch {}
      };

      dataChannel.onmessage = async (event) => {
        try {
          const payload = JSON.parse(event.data);
          void recordEvent('voice', payload?.type || 'data_channel', payload);

          // Handle function-call events (support current schema)
          const t = payload?.type;
          // New schema: function call item added to response output
          if (t === 'response.output_item.added' && payload?.item?.type === 'function_call') {
            const callItem = payload.item;
            const name = callItem?.name;
            const callId = callItem?.call_id;
            if (name && callId) toolCallsRef.current[callId] = { name, args: '' };
            return;
          }
          // New schema: argument deltas come via response.function_call_arguments.delta
          if (t === 'response.function_call_arguments.delta') {
            const id = payload?.call_id || payload?.function_call_id || payload?.id;
            const delta = payload?.delta || payload?.arguments || '';
            if (id && toolCallsRef.current[id]) toolCallsRef.current[id].args += String(delta);
            return;
          }
          // New schema: arguments done (finalize and execute)
          if (t === 'response.function_call_arguments.done') {
            const id = payload?.call_id || payload?.function_call_id || payload?.id;
            const entry = id ? toolCallsRef.current[id] : undefined;
            if (entry) {
              let argsObj = {};
              try { argsObj = entry.args ? JSON.parse(entry.args) : {}; } catch {}
              const result = await executeToolCall(id, entry.name, argsObj);
              // Do not send unsupported 'tool.output' events. For our side-effect tools, we also avoid auto response.create here.
              delete toolCallsRef.current[id];
            }
            return;
          }

          // Legacy schema support (older events)
          if (t === 'response.function_call') {
            const id = payload?.id || payload?.function_call_id || payload?.call_id;
            const name = payload?.name;
            if (id && name) toolCallsRef.current[id] = { name, args: '' };
            return;
          }
          if (t === 'response.function_call.arguments.delta') {
            const id = payload?.id || payload?.function_call_id || payload?.call_id;
            const delta = payload?.delta || payload?.arguments || '';
            if (id && toolCallsRef.current[id]) toolCallsRef.current[id].args += String(delta);
            return;
          }
          if (t === 'response.function_call.completed') {
            const id = payload?.id || payload?.function_call_id || payload?.call_id;
            const entry = id ? toolCallsRef.current[id] : undefined;
            if (entry) {
              let argsObj = {};
              try { argsObj = entry.args ? JSON.parse(entry.args) : {}; } catch {}
              const result = await executeToolCall(id, entry.name, argsObj);
              // No 'tool.output' and no auto response here.
              delete toolCallsRef.current[id];
            }
            return;
          }
        } catch (e) {
          void recordEvent('voice', 'parse_error', { raw: event.data });
        }
      };

      // Play remote audio
      pc.ontrack = (evt) => { if (audioRef.current) audioRef.current.srcObject = evt.streams[0]; };

      // Attach microphone audio
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      for (const track of stream.getAudioTracks()) pc.addTrack(track, stream);

      // Helper: wait for ICE gathering to complete before sending offer
      const waitForIceGathering = () => new Promise((resolve) => {
        if (pc.iceGatheringState === 'complete') return resolve();
        const check = () => { if (pc.iceGatheringState === 'complete') { pc.removeEventListener('icegatheringstatechange', check); resolve(); } };
        pc.addEventListener('icegatheringstatechange', check);
      });

      // Create offer and complete SDP exchange via HTTP POST
      const offer = await pc.createOffer({ offerToReceiveAudio: true });
      await pc.setLocalDescription(offer);
      await waitForIceGathering();
      const answerSdpRaw = await postSdpOffer(mediaAddr, sessionId, clientSecret, pc.localDescription.sdp);
      let answerSdp = (typeof answerSdpRaw === 'string' ? answerSdpRaw : String(answerSdpRaw || ''))
        .replace(/^\uFEFF/, '');
      // Normalize line endings to CRLF and trim trailing spaces
      answerSdp = answerSdp
        .replace(/\r\n/g, '\n')     // unify CRLF to LF
        .replace(/\r/g, '\n')        // unify CR to LF
        .split('\n')
        .map((l) => l.replace(/[\t ]+$/g, '')) // trim right only
        .join('\r\n');

      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

      // Open nested team WebSocket in parallel and forward TextMessages to Realtime
      const wsBase = (process.env.REACT_APP_WS_URL || derivedWsBase);
      const nestedUrl = `${wsBase}/api/runs/MainConversation`;
      const ws = new WebSocket(nestedUrl);
      nestedWsRef.current = ws;
      setSharedNestedWs(ws);
      hasSpokenMidRef.current = false; // reset for new connection
      runCompletedRef.current = false;
  void recordEvent('controller', 'session_started', { voice, sessionId });

      // Do NOT auto-start a run; wait for explicit user_message or Run action
      ws.onopen = () => {
        void recordEvent('nested', 'system', { message: 'Nested connection established. Awaiting task or user_message.' });
      };
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          void recordEvent('nested', msg.type || 'event', msg);
          const type = (msg.type || '').toLowerCase();
          if (type === 'textmessage' && msg.data && msg.data.content && dataChannelRef.current) {
            // Forward nested text with more context about the speaker
            const content = msg.data.content;
            const source = msg.data.source || 'Agent';
            const text = `[TEAM ${source}] ${content}`;
            forwardToVoice('system', text, { source, kind: 'team_text' });
            // Detect termination marker inside team content
            try {
              const cstr = String(content || '');
              if (!runCompletedRef.current && /\bTERMINATE\b/i.test(cstr)) {
                forwardToVoice('system', '[RUN_FINISHED] Team signaled termination. Please provide a concise final summary.', { trigger: 'team_terminate' });
                dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
                runCompletedRef.current = true;
                hasSpokenMidRef.current = false;
              }
            } catch {}
            return;
          }
          // Handle other message types with context
          if (type === 'toolcallrequestevent' && msg.data && dataChannelRef.current) {
            const toolName = msg.data.name || 'unknown_tool';
            const source = msg.data.source || 'Agent';
            const text = `[TEAM ${source}] Using tool: ${toolName}`;
            forwardToVoice('system', text, { source, kind: 'team_tool_start' });
            return;
          }
          if (type === 'toolcallexecutionevent' && msg.data && dataChannelRef.current) {
            const result = msg.data.result || 'completed';
            const source = msg.data.source || 'Agent';
            const text = `[TEAM ${source}] Tool completed: ${typeof result === 'string' ? result.slice(0, 200) : 'success'}`;
            forwardToVoice('system', text, { source, kind: 'team_tool_done' });
            return;
          }
          // Detect run completion and trigger final summary (guard against duplicate triggers)
          if (type === 'system' && msg.data && typeof msg.data.message === 'string' && msg.data.message.includes('Agent run finished')) {
            if (!runCompletedRef.current && dataChannelRef.current) {
              forwardToVoice('system', '[RUN_FINISHED] Team has completed the task. Please provide a summary.', { trigger: 'team_finished' });
              dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
              hasSpokenMidRef.current = false; // ready for next task
              runCompletedRef.current = true;
            }
            return;
          }
          // Treat explicit interruption as a finish signal for narration
          if (type === 'system' && msg.data && typeof msg.data.message === 'string' && /run (interrupted|cancelled|canceled)/i.test(msg.data.message)) {
            if (dataChannelRef.current && !runCompletedRef.current) {
              forwardToVoice('system', '[RUN_FINISHED] Team run was interrupted. Provide a brief status of what was achieved so far.', { trigger: 'team_interrupted' });
              dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
              hasSpokenMidRef.current = false;
              runCompletedRef.current = true;
            }
            return;
          }
        } catch (e) {
          void recordEvent('nested', 'parse_error', { raw: event.data });
        }
      };
      ws.onerror = () => { void recordEvent('nested', 'error', { message: 'WebSocket error' }); };
      ws.onclose = () => {
        void recordEvent('nested', 'system', { message: 'WebSocket closed' });
        // If the run ended without the explicit finished marker, still prompt a summary
        if (dataChannelRef.current && !runCompletedRef.current) {
          forwardToVoice('system', '[RUN_FINISHED] Team connection closed. Provide the final summary based on received context.', { trigger: 'team_socket_closed' });
          dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
          runCompletedRef.current = true;
          hasSpokenMidRef.current = false;
        }
      };

    } catch (err) {
      // Surface first 200 chars of SDP if available
      try {
        void recordEvent('controller', 'sdp_debug', { detail: (err?.detail || err?.message || '').toString().slice(0, 200) });
      } catch {}
      void recordEvent('controller', 'session_error', { message: err.message || String(err) });
      setError(err.message || String(err));
      setIsRunning(false);
    }
  };

  // Execute a completed tool call from the voice model
  const executeToolCall = async (callId, name, argsObj) => {
    try {
      if (name === 'send_to_nested') {
        const text = (argsObj && typeof argsObj.text === 'string') ? argsObj.text : '';
        if (!text) throw new Error('Missing text');
        if (nestedWsRef.current && nestedWsRef.current.readyState === WebSocket.OPEN) {
          hasSpokenMidRef.current = false; // new task; allow one mid-run narration
          runCompletedRef.current = false; // new task; clear completion flag
          nestedWsRef.current.send(JSON.stringify({ type: 'user_message', data: text }));
          void recordEvent('controller', 'tool_exec', { tool: name, args: argsObj });
          return { ok: true };
        } else {
          throw new Error('Nested WebSocket not connected');
        }
      }
      if (name === 'pause') {
        // Send cancel command to the nested WebSocket to pause the current run
        if (nestedWsRef.current && nestedWsRef.current.readyState === WebSocket.OPEN) {
          nestedWsRef.current.send(JSON.stringify({ type: 'cancel' }));
          void recordEvent('controller', 'tool_exec', { tool: name, message: 'Pause command sent to nested team' });
        } else {
          void recordEvent('controller', 'tool_exec', { tool: name, message: 'No active nested connection to pause' });
        }
        return { ok: true };
      }
      if (name === 'reset') {
        // Best effort: close and reopen WS without auto-running
        try { if (nestedWsRef.current) nestedWsRef.current.close(); } catch {}
        const wsBase = (process.env.REACT_APP_WS_URL || derivedWsBase);
        const nestedUrl = `${wsBase}/api/runs/MainConversation`;
        const ws = new WebSocket(nestedUrl);
        nestedWsRef.current = ws;
        setSharedNestedWs(ws);
        hasSpokenMidRef.current = false;
        runCompletedRef.current = false;
        ws.onopen = () => {
          void recordEvent('nested', 'system', { message: 'Nested connection reset. Awaiting task or user_message.' });
        };
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            void recordEvent('nested', msg.type || 'event', msg);
            const type = (msg.type || '').toLowerCase();
            if (type === 'textmessage' && msg.data && msg.data.content && dataChannelRef.current) {
              // Forward nested text with more context about the speaker
              const content = msg.data.content;
              const source = msg.data.source || 'Agent';
              const text = `[TEAM ${source}] ${content}`;
              forwardToVoice('system', text, { source, kind: 'team_text' });
              // Detect termination marker inside team content
              try {
                const cstr = String(content || '');
                if (!runCompletedRef.current && /\bTERMINATE\b/i.test(cstr)) {
                  forwardToVoice('system', '[RUN_FINISHED] Team signaled termination. Please provide a concise final summary.', { trigger: 'team_terminate' });
                  dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
                  runCompletedRef.current = true;
                  hasSpokenMidRef.current = false;
                }
              } catch {}
              return;
            }
            // Handle other message types with context
            if (type === 'toolcallrequestevent' && msg.data && dataChannelRef.current) {
              const toolName = msg.data.name || 'unknown_tool';
              const source = msg.data.source || 'Agent';
              const text = `[TEAM ${source}] Using tool: ${toolName}`;
              forwardToVoice('system', text, { source, kind: 'team_tool_start' });
              return;
            }
            if (type === 'toolcallexecutionevent' && msg.data && dataChannelRef.current) {
              const result = msg.data.result || 'completed';
              const source = msg.data.source || 'Agent';
              const text = `[TEAM ${source}] Tool completed: ${typeof result === 'string' ? result.slice(0, 200) : 'success'}`;
              forwardToVoice('system', text, { source, kind: 'team_tool_done' });
              return;
            }
            // Detect run completion and trigger final summary
            if (type === 'system' && msg.data && typeof msg.data.message === 'string' && msg.data.message.includes('Agent run finished')) {
              if (!runCompletedRef.current && dataChannelRef.current) {
                forwardToVoice('system', '[RUN_FINISHED] Team has completed the task. Please provide a summary.', { trigger: 'team_finished' });
                dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
                hasSpokenMidRef.current = false;
                runCompletedRef.current = true;
              }
              return;
            }
            if (type === 'system' && msg.data && typeof msg.data.message === 'string' && /run (interrupted|cancelled|canceled)/i.test(msg.data.message)) {
              if (dataChannelRef.current && !runCompletedRef.current) {
                forwardToVoice('system', '[RUN_FINISHED] Team run was interrupted. Provide a brief status of what was achieved so far.', { trigger: 'team_interrupted' });
                dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
                hasSpokenMidRef.current = false;
                runCompletedRef.current = true;
              }
              return;
            }
          } catch (e) {
            void recordEvent('nested', 'parse_error', { raw: event.data });
          }
        };
        ws.onerror = () => { void recordEvent('nested', 'error', { message: 'WebSocket error' }); };
        ws.onclose = () => {
          void recordEvent('nested', 'system', { message: 'WebSocket closed' });
          if (dataChannelRef.current && !runCompletedRef.current) {
            forwardToVoice('system', '[RUN_FINISHED] Team connection closed. Provide the final summary based on received context.', { trigger: 'team_socket_closed' });
            dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
            runCompletedRef.current = true;
            hasSpokenMidRef.current = false;
          }
        };
        void recordEvent('controller', 'tool_exec', { tool: name });
        return { ok: true };
      }
      throw new Error(`Unknown tool: ${name}`);
    } catch (e) {
      const message = String(e?.message || e);
      void recordEvent('controller', 'tool_error', { tool: name, error: message });
      return { ok: false, error: message };
    }
  };

  const stopSession = () => {
    setIsRunning(false);
    void recordEvent('controller', 'session_stopped', {});
    if (nestedWsRef.current) { try { nestedWsRef.current.close(); } catch {} nestedWsRef.current = null; }
    setSharedNestedWs(null);
    hasSpokenMidRef.current = false;
    runCompletedRef.current = false;
    if (peerRef.current) {
      peerRef.current.getSenders().forEach((sender) => { if (sender.track) sender.track.stop(); });
      try { peerRef.current.close(); } catch {}
    }
    peerRef.current = null;
    dataChannelRef.current = null;
  };

  const sendText = () => {
    if (dataChannelRef.current && transcript.trim()) {
      // Follow recommended event pattern: add a conversation item, then request a response
      dataChannelRef.current.send(JSON.stringify({
        type: 'conversation.item.create',
        item: { type: 'message', role: 'user', content: [{ type: 'input_text', text: transcript }] },
      }));
      dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
      void recordEvent('user', 'voice_user_message', { text: transcript });
      setTranscript('');
    }
  };

  const sendToNested = () => {
    if (nestedWsRef.current && nestedWsRef.current.readyState === WebSocket.OPEN && transcript.trim()) {
      try {
        // Use incremental turn without restarting: 'user_message'
        nestedWsRef.current.send(JSON.stringify({ type: 'user_message', data: transcript }));
        void recordEvent('controller', 'system', { message: `Queued user_message to nested: ${transcript}` });
        setTranscript('');
      } catch (e) {
        void recordEvent('controller', 'error', { message: `Failed to send to nested: ${e.message}` });
      }
    }
  };

  useEffect(() => () => stopSession(), []);

  return (
    <Stack spacing={2}>
      <Box component={Paper} sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h5" noWrap>{conversationTitle}</Typography>
          <Typography variant="body2" color="text.secondary">Realtime voice with nested team controller</Typography>
          {conversation?.id && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
              Conversation ID: {conversation.id}
            </Typography>
          )}
          {conversation?.updated_at && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
              Updated {formatTimestamp(conversation.updated_at)}
            </Typography>
          )}
        </Box>
        <Chip
          label={isRunning ? 'Voice connected' : remoteSessionActive ? 'Voice active elsewhere' : 'Voice idle'}
          color={isRunning ? 'success' : remoteSessionActive ? 'warning' : 'default'}
          sx={{ ml: 'auto' }}
        />
        <Chip
          label={conversationError ? 'History error' : conversationLoading ? 'Syncing history' : 'History synced'}
          color={conversationError ? 'error' : conversationLoading ? 'warning' : 'info'}
        />
        <Button component={RouterLink} to="/voice" variant="outlined" size="small">
          Back to conversations
        </Button>
        <audio ref={audioRef} autoPlay />
  <Button variant="contained" onClick={startSession} disabled={sessionLocked || conversationLoading || Boolean(conversationError)}>Start</Button>
        <Button variant="contained" color="error" onClick={stopSession} disabled={!isRunning}>Stop</Button>
      </Box>

      {!isRunning && remoteSessionActive && !conversationError && (
        <Alert severity="info">Another tab is currently running this voice session. You can monitor live updates here.</Alert>
      )}

      {conversationError && (
        <Alert severity="error">
          {conversationError} — <Button color="inherit" size="small" component={RouterLink} to="/voice">Return to list</Button>
        </Alert>
      )}

      {error && (
        <Alert severity="error">{error}</Alert>
      )}

      <Box component={Paper} sx={{ p: 2, display: 'flex', gap: 1, alignItems: 'flex-start' }}>
        <TextField
          fullWidth
          label="Message"
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="Type a message to send to Voice or Nested"
          multiline
          minRows={2}
          maxRows={8}
        />
        <Stack direction="column" spacing={1}>
          <Button variant="contained" color="success" onClick={sendText} disabled={!isRunning || !transcript.trim()}>Send to Voice</Button>
          <Button variant="contained" color="secondary" onClick={sendToNested} disabled={!isRunning || !transcript.trim() || !nestedWsRef.current}>Send to Nested</Button>
        </Stack>
      </Box>
      <ConversationHistory
        messages={messages}
        conversationLoading={conversationLoading}
        isRunning={isRunning}
        formatTimestamp={formatTimestamp}
      />

      <Box component={Paper} sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>Nested agent outputs</Typography>
        {nestedHighlights.length === 0 ? (
          <Typography variant="body2" color="text.secondary">No nested text messages yet.</Typography>
        ) : (
          nestedHighlights.slice(-5).map((msg, idx) => (
            <Box key={msg.id ?? `nested-${idx}`} sx={{ mb: idx === nestedHighlights.length - 1 ? 0 : 1.5 }}>
              <Typography variant="caption" color="text.secondary">
                {formatTimestamp(msg.timestamp)} — {msg.data?.data?.source || 'Agent'}
              </Typography>
              <Typography variant="body2">{msg.data?.data?.content || JSON.stringify(msg.data)}</Typography>
            </Box>
          ))
        )}
      </Box>

      {/* Embedded nested team console, sharing the same WebSocket */}
      {sharedNestedWs && (
        <Box component={Paper} sx={{ p: 1 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>Nested Team Console</Typography>
          <RunConsole nested agentName="MainConversation" sharedSocket={sharedNestedWs} readOnlyControls />
        </Box>
      )}
    </Stack>
  );
}

export default VoiceAssistant;
