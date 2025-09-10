import React, { useState, useRef, useEffect } from 'react';
import { Box, Paper, Stack, Typography, Button, TextField, Chip, Alert } from '@mui/material';

/**
 * A simple React component that demonstrates how to connect to the
 * OpenAI realtime API using WebRTC and, in parallel, subscribe to the
 * backend nested team WebSocket stream. Any TextMessage from the nested
 * team is forwarded immediately to the OpenAI Realtime data channel so
 * the voice model narrates and stays in sync.
 */
function VoiceAssistant() {
  const [isRunning, setIsRunning] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const peerRef = useRef(null);
  const dataChannelRef = useRef(null);
  const nestedWsRef = useRef(null);
  const audioRef = useRef(null);

  // Track accumulating function-call arguments by call id
  const toolCallsRef = useRef({});

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

  // Execute a completed tool call from the voice model
  const executeToolCall = async (callId, name, argsObj) => {
    try {
      if (name === 'send_to_nested') {
        const text = (argsObj && typeof argsObj.text === 'string') ? argsObj.text : '';
        if (!text) throw new Error('Missing text');
        if (nestedWsRef.current && nestedWsRef.current.readyState === WebSocket.OPEN) {
          nestedWsRef.current.send(JSON.stringify({ type: 'user_message', data: text }));
          setMessages((prev) => [...prev, { source: 'controller', type: 'tool_exec', tool: name, args: argsObj }]);
          return { ok: true };
        } else {
          throw new Error('Nested WebSocket not connected');
        }
      }
      if (name === 'pause') {
        // No explicit pause endpoint; best effort: notify UI and model
        setMessages((prev) => [...prev, { source: 'controller', type: 'tool_exec', tool: name }]);
        return { ok: true };
      }
      if (name === 'reset') {
        // Best effort: close and reopen WS
        try { if (nestedWsRef.current) nestedWsRef.current.close(); } catch {}
        const wsBase = (process.env.REACT_APP_WS_URL || derivedWsBase);
        const nestedUrl = `${wsBase}/api/runs/MainConversation`;
        const ws = new WebSocket(nestedUrl);
        nestedWsRef.current = ws;
        ws.onopen = () => { ws.send(JSON.stringify({ type: 'run', data: '' })); };
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            setMessages((prev) => [...prev, { source: 'nested', ...msg }]);
            const type = (msg.type || '').toLowerCase();
            if (type === 'textmessage' && msg.data && msg.data.content && dataChannelRef.current) {
              dataChannelRef.current.send(JSON.stringify({ type: 'input_text', text: msg.data.content }));
              dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
            }
          } catch (e) {
            setMessages((prev) => [...prev, { source: 'nested', type: 'parse_error', raw: event.data }]);
          }
        };
        ws.onerror = () => { setMessages((prev) => [...prev, { source: 'nested', type: 'error', data: 'WebSocket error' }]); };
        ws.onclose = () => { setMessages((prev) => [...prev, { source: 'nested', type: 'system', data: 'WebSocket closed' }]); };
        setMessages((prev) => [...prev, { source: 'controller', type: 'tool_exec', tool: name }]);
        return { ok: true };
      }
      throw new Error(`Unknown tool: ${name}`);
    } catch (e) {
      return { ok: false, error: String(e?.message || e) };
    }
  };

  const startSession = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setError(null);
    try {
      // Request a new realtime session from our backend (mounted under /api/realtime)
      const voice = (process.env.REACT_APP_VOICE || 'alloy');
      const tokenUrl = `${backendBase}/api/realtime/token/openai?model=gpt-4o-realtime-preview-2025-06-03&voice=${encodeURIComponent(voice)}`;
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
        } catch {}
      };

      dataChannel.onmessage = async (event) => {
        try {
          const payload = JSON.parse(event.data);
          setMessages((msgs) => [...msgs, payload]);

          // Handle function-call events
          const t = payload?.type;
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
              if (dataChannelRef.current) {
                dataChannelRef.current.send(JSON.stringify({ type: 'tool.output', tool_call_id: id, output: JSON.stringify(result) }));
                dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
              }
              delete toolCallsRef.current[id];
            }
            return;
          }
        } catch (e) {
          setMessages((msgs) => [...msgs, { type: 'unknown', raw: event.data }]);
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

      ws.onopen = () => { ws.send(JSON.stringify({ type: 'run', data: '' })); };
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          setMessages((prev) => [...prev, { source: 'nested', ...msg }]);
          const type = (msg.type || '').toLowerCase();
          if (type === 'textmessage' && msg.data && msg.data.content && dataChannelRef.current) {
            // Forward nested text to voice model
            dataChannelRef.current.send(JSON.stringify({ type: 'input_text', text: msg.data.content }));
            dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
          }
        } catch (e) {
          setMessages((prev) => [...prev, { source: 'nested', type: 'parse_error', raw: event.data }]);
        }
      };
      ws.onerror = () => { setMessages((prev) => [...prev, { source: 'nested', type: 'error', data: 'WebSocket error' }]); };
      ws.onclose = () => { setMessages((prev) => [...prev, { source: 'nested', type: 'system', data: 'WebSocket closed' }]); };

    } catch (err) {
      console.error(err);
      // Surface first 200 chars of SDP if available
      try {
        setMessages((prev) => [...prev, { source: 'controller', type: 'sdp_debug', data: (err?.detail || err?.message || '').toString().slice(0, 200) }]);
      } catch {}
      setError(err.message || String(err));
      setIsRunning(false);
    }
  };

  const stopSession = () => {
    setIsRunning(false);
    if (nestedWsRef.current) { try { nestedWsRef.current.close(); } catch {} nestedWsRef.current = null; }
    if (peerRef.current) {
      peerRef.current.getSenders().forEach((sender) => { if (sender.track) sender.track.stop(); });
      try { peerRef.current.close(); } catch {}
    }
    peerRef.current = null;
    dataChannelRef.current = null;
  };

  const sendText = () => {
    if (dataChannelRef.current && transcript.trim()) {
      // Follow recommended event pattern: send text, then request a response
      dataChannelRef.current.send(JSON.stringify({ type: 'input_text', text: transcript }));
      dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
      setTranscript('');
    }
  };

  const sendToNested = () => {
    if (nestedWsRef.current && nestedWsRef.current.readyState === WebSocket.OPEN && transcript.trim()) {
      try {
        // Use incremental turn without restarting: 'user_message'
        nestedWsRef.current.send(JSON.stringify({ type: 'user_message', data: transcript }));
        setMessages((prev) => [...prev, { source: 'controller', type: 'system', data: `Queued user_message to nested: ${transcript}` }]);
        setTranscript('');
      } catch (e) {
        setMessages((prev) => [...prev, { source: 'controller', type: 'error', data: `Failed to send to nested: ${e.message}` }]);
      }
    }
  };

  useEffect(() => () => stopSession(), []);

  return (
    <Stack spacing={2}>
      <Box component={Paper} sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box>
          <Typography variant="h5">Voice Assistant</Typography>
          <Typography variant="body2" color="text.secondary">Realtime voice with nested team controller</Typography>
        </Box>
        <Chip label={isRunning ? 'Connected' : 'Disconnected'} color={isRunning ? 'success' : 'default'} sx={{ ml: 'auto' }} />
        <audio ref={audioRef} autoPlay />
        <Button variant="contained" onClick={startSession} disabled={isRunning}>Start</Button>
        <Button variant="contained" color="error" onClick={stopSession} disabled={!isRunning}>Stop</Button>
      </Box>

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

      <Box component={Paper} sx={{ p: 2, height: 360, overflowY: 'auto' }}>
        {messages.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            {isRunning ? 'Waiting for messages...' : 'Click Start to begin a voice session.'}
          </Typography>
        ) : (
          messages.map((msg, idx) => (
            <Box key={idx} sx={{ mb: 1 }}>
              <Typography variant="caption" color="text.secondary">{msg.source || msg.type || 'event'}</Typography>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{JSON.stringify(msg, null, 2)}</pre>
            </Box>
          ))
        )}
      </Box>
    </Stack>
  );
}

export default VoiceAssistant;
