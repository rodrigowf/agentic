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

  // Utility: post SDP offer and get answer from OpenAI using client secret
  const postSdpOffer = async (mediaAddr, sessionId, clientSecret, sdp) => {
    const url = `https://${mediaAddr}/v1/realtime?session_id=${encodeURIComponent(sessionId)}`;
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${clientSecret}`,
        'Content-Type': 'application/sdp'
      },
      body: sdp,
    });
    if (!resp.ok) throw new Error(`Realtime SDP exchange failed: ${resp.status}`);
    const answerSdp = await resp.text();
    return answerSdp;
  };

  const startSession = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setError(null);
    try {
      // Request a new realtime session from our backend (mounted under /api/realtime)
      const tokenResp = await fetch(`/api/realtime/token/openai?model=gpt-4o-realtime-preview-2025-06-03&voice=onyx`);
      if (!tokenResp.ok) throw new Error(`Failed to fetch token: ${tokenResp.status}`);
      const { id: sessionId, client_secret: clientSecret, media_addr: mediaAddr } = await tokenResp.json();

      const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
      peerRef.current = pc;

      // Create a data channel to send/receive OAI events
      const dataChannel = pc.createDataChannel('oai-events');
      dataChannelRef.current = dataChannel;
      dataChannel.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setMessages((msgs) => [...msgs, payload]);
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
      const answerSdp = await postSdpOffer(mediaAddr, sessionId, clientSecret, pc.localDescription.sdp);
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

      // Open nested team WebSocket in parallel and forward TextMessages to Realtime
      const wsBase = (process.env.REACT_APP_WS_URL || 'ws://localhost:8000');
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
