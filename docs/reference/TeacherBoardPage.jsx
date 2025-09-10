import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AppBar, Toolbar, Typography, Box, Divider, LinearProgress, Snackbar, Alert } from '@mui/material';
import Board from './Board.jsx';
import ChatControls from './ChatControls.jsx';
import { useModel } from '../context/ModelContext.jsx';

const backend = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const TeacherBoardPage = ({ onBack }) => {
  const { provider, model } = useModel();
  const [sections, setSections] = useState([]);
  const [messages, setMessages] = useState([]); // store conversation
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [voiceActive, setVoiceActive] = useState(false);
  const pcRef = useRef(null);
  const localStreamRef = useRef(null);
  const audioRef = useRef(null);
  const functionCallStateRef = useRef({}); // call_id -> { name, argsStr }

  const updateSection = useCallback((id, content) => {
    setSections(prev => {
      const idx = prev.findIndex(s => s.id === id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = { ...next[idx], content };
        return next;
      }
      return [...prev, { id, content }];
    });
  }, []);

  const appendPlain = useCallback((text, role = 'assistant') => {
    const id = `sec-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
    setSections(prev => [...prev, { id, content: `<p>${(text||'').replace(/\n/g,'<br/>')}</p>` }]);
    setMessages(prev => [...prev, { role, content: text }]);
  }, []);

  const sendMessage = async (message) => {
    if (!message) return;
    console.log('[Tutor] Sending message', message);
    setMessages(prev => [...prev, { role: 'user', content: message }]);
    setLoading(true);
    setError(null);
    try {
      const recent = [...messages, { role: 'user', content: message }].slice(-16);
      const board_state = sections.map(s => ({ section_id: s.id, content: s.content }));
      const payload = { provider, model, messages: recent, board_state };
      console.log('[Tutor] /chat payload', payload);
      const r = await fetch(`${backend}/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await r.json();
      console.log('[Tutor] /chat response status', r.status, 'data', data);
      if (!r.ok) throw new Error(data.detail || data.error || 'Request failed');
      if (data.function_call) {
        const { name, args } = data.function_call;
        console.log('[Tutor] Function call received', name, args);
        if (name === 'upsert_board_section' && args.section_id && args.content) {
          setSections(prev => {
            const idx = prev.findIndex(p => p.id === args.section_id);
            if (idx >= 0) {
              const next = [...prev];
              if (args.mode === 'append') {
                next[idx] = { ...next[idx], content: next[idx].content + args.content };
              } else {
                next[idx] = { ...next[idx], content: args.content };
              }
              return next;
            }
            return [...prev, { id: args.section_id, content: args.content }];
          });
          setMessages(prev => [...prev, { role: 'assistant', content: `[Upserted section ${args.section_id}]` }]);
        } else if (name === 'delete_board_section' && args.section_id) {
          setSections(prev => prev.filter(p => p.id !== args.section_id));
          setMessages(prev => [...prev, { role: 'assistant', content: `[Deleted section ${args.section_id}]` }]);
        } else {
          appendPlain(JSON.stringify(data.function_call));
        }
      } else if (data.answer) {
        appendPlain(data.answer);
      } else {
        appendPlain('[Empty response]');
      }
      if (data.board) {
        setSections(data.board.map(s => ({ id: s.section_id, content: s.content })));
      }
    } catch (e) {
      console.error('[Tutor] Chat error', e);
      setError(e.message + ' (retry later)');
    } finally {
      setLoading(false);
    }
  };

  // Voice handling (OpenAI only for MVP)
  const startVoice = async () => {
    console.log('[Tutor] startVoice invoked');
    if (provider !== 'openai') {
      setError('Voice only implemented for OpenAI in MVP');
      return;
    }
    try {
      // Pick a realtime-capable model (fallback if selected model is not a realtime variant)
      const realtimeModel = /realtime/i.test(model) ? model : 'gpt-4o-realtime-preview';
      if (realtimeModel !== model) {
        console.log('[Tutor] Selected model not realtime capable, using fallback', realtimeModel);
      }
      const tokenResp = await fetch(`${backend}/token/openai?model=${encodeURIComponent(realtimeModel)}`);
      const tokenData = await tokenResp.json();
      console.log('[Tutor] token response', tokenData);
      if (!tokenData.ephemeral_token) throw new Error('Failed to get token');
      const ephemeral = tokenData.ephemeral_token;

      const pc = new RTCPeerConnection();
      pcRef.current = pc;
      console.log('[Tutor] RTCPeerConnection created');

      // Create a data channel early so it is negotiated in SDP
      const dc = pc.createDataChannel('oai-events');
      dc.onopen = () => console.log('[Tutor] datachannel open');
      dc.onmessage = (e) => {
        console.log('[Tutor] datachannel message', e.data);
        try {
          const msg = JSON.parse(e.data);
          // VERBOSE trace of function call lifecycle
          if (msg.type === 'response.output_item.added' && msg.item?.type === 'function_call') {
            const callId = msg.item.call_id;
            functionCallStateRef.current[callId] = { name: msg.item.name, argsStr: '' };
            console.log('[Tutor][fn] added call', callId, 'name', msg.item.name);
          }
          else if (msg.type === 'response.output_item.delta' && msg.item?.type === 'function_call') {
            const callId = msg.item.call_id;
            const deltaArgs = msg.delta?.arguments || msg.delta || '';
            if (!functionCallStateRef.current[callId]) functionCallStateRef.current[callId] = { name: msg.item.name, argsStr: '' };
            functionCallStateRef.current[callId].argsStr += deltaArgs;
            console.log('[Tutor][fn] delta call', callId, 'len+=', deltaArgs.length, 'total', functionCallStateRef.current[callId].argsStr.length);
          }
          else if (msg.type === 'response.function_call.delta') { // legacy / alternate naming
            const callId = msg.call_id;
            if (!functionCallStateRef.current[callId]) functionCallStateRef.current[callId] = { name: msg.name, argsStr: '' };
            functionCallStateRef.current[callId].argsStr += msg.delta || '';
            console.log('[Tutor][fn] delta(legacy) call', callId, 'chunk len', (msg.delta||'').length);
          }
          else if (msg.type === 'response.output_item.done' && msg.item?.type === 'function_call') {
            const callId = msg.item.call_id;
            const state = functionCallStateRef.current[callId];
            if (state) {
              // Prefer final arguments field if present
              const finalArgsStr = msg.item.arguments && msg.item.arguments.length ? msg.item.arguments : state.argsStr;
              console.log('[Tutor][fn] done call', callId, 'final length', finalArgsStr.length);
              let parsed = null;
              try { parsed = JSON.parse(finalArgsStr); } catch (err) { console.warn('[Tutor][fn] JSON parse error (done)', err, finalArgsStr); }
              if (parsed) applyFunctionCall(state.name, parsed);
              delete functionCallStateRef.current[callId];
            }
          }
          else if (msg.type === 'response.function_call.completed') { // alternate completion event
            const callId = msg.call_id;
            const state = functionCallStateRef.current[callId];
            if (state) {
              console.log('[Tutor][fn] completed event', callId, 'len', state.argsStr.length);
              let parsed = null;
              try { parsed = JSON.parse(state.argsStr || '{}'); } catch (err) { console.warn('[Tutor][fn] JSON parse error (completed)', err); }
              if (parsed) applyFunctionCall(state.name, parsed);
              delete functionCallStateRef.current[callId];
            }
          }
          else if (msg.type === 'response.function_call.output_parsed' || msg.type === 'function_call') {
            // Fallback immediate parsed payload
            const name = msg.name || msg.function_call?.name;
            const args = msg.arguments || msg.args || msg.function_call?.arguments;
            if (args && typeof args === 'string') {
              try { applyFunctionCall(name, JSON.parse(args)); return; } catch {/*ignored*/}
            }
            if (name && args && typeof args === 'object') applyFunctionCall(name, args);
          }
        } catch (err) { console.warn('[Tutor] datachannel parse error', err); }
      };

      function applyFunctionCall(name, parsed) {
        if (!parsed) return;
        console.log('[Tutor][fn] apply', name, parsed);
        if (name === 'upsert_board_section' && parsed.section_id && parsed.content) {
          fetch(`${backend}/board/upsert`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ section_id: parsed.section_id, content: parsed.content, mode: parsed.mode || 'replace' }) })
            .then(r=>r.json()).then(d=>{ console.log('[Tutor][fn] upsert response', d); if (d.board) setSections(d.board.map(s=>({ id: s.section_id, content: s.content }))); })
            .catch(err=>console.warn('[Tutor][fn] upsert error', err));
        } else if (name === 'delete_board_section' && parsed.section_id) {
          fetch(`${backend}/board/${encodeURIComponent(parsed.section_id)}`, { method:'DELETE' })
            .then(r=>r.json()).then(d=>{ console.log('[Tutor][fn] delete response', d); if (d.board) setSections(d.board.map(s=>({ id: s.section_id, content: s.content }))); })
            .catch(err=>console.warn('[Tutor][fn] delete error', err));
        }
      }

      // Ensure we negotiate receiving audio from the model
      pc.addTransceiver('audio', { direction: 'recvonly' });

      pc.ontrack = (ev) => {
        console.log('[Tutor] ontrack event', ev.streams?.length);
        if (audioRef.current) audioRef.current.srcObject = ev.streams[0];
      };
      pc.onconnectionstatechange = () => console.log('[Tutor] Peer connection state', pc.connectionState);

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('[Tutor] Microphone stream acquired');
      localStreamRef.current = stream;
      // Add mic track (sendonly) AFTER adding recvonly transceiver above
      stream.getAudioTracks().forEach(t => pc.addTrack(t, stream));

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      console.log('[Tutor] LocalDescription set (length)', offer.sdp?.length);

      const sdpUrl = `https://api.openai.com/v1/realtime?model=${encodeURIComponent(realtimeModel)}`;
      const sdpResp = await fetch(sdpUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${ephemeral}`,
            // Beta header required for realtime
          'OpenAI-Beta': 'realtime=v1',
          'Content-Type': 'application/sdp',
          'Accept': 'application/sdp'
        },
        body: offer.sdp
      });
      console.log('[Tutor] SDP POST status', sdpResp.status);
      if (!sdpResp.ok) {
        const errTxt = await sdpResp.text();
        console.error('[Tutor] SDP error body', errTxt);
        throw new Error('SDP exchange failed: ' + errTxt.slice(0, 400));
      }
      const answerSDP = await sdpResp.text();
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSDP });
      console.log('[Tutor] RemoteDescription set, voice active');
      setVoiceActive(true);
    } catch (e) {
      console.error('[Tutor] Voice error', e);
      setError(e.message);
      stopVoice();
    }
  };

  const stopVoice = () => {
    console.log('[Tutor] stopVoice invoked');
    setVoiceActive(false);
    if (pcRef.current) pcRef.current.close();
    pcRef.current = null;
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(t => t.stop());
      localStreamRef.current = null;
    }
  };

  const toggleVoice = () => {
    if (voiceActive) stopVoice(); else startVoice();
  };

  useEffect(() => {
    // initial load of board from backend persistence
    fetch(`${backend}/board`).then(r=>r.json()).then(d=>{
      if (d.board) setSections(d.board.map(s=>({ id: s.section_id, content: s.content })));
    }).catch(()=>{});
  }, []);

  useEffect(() => () => stopVoice(), []);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flex: 1 }}>Teacher's Board - {provider}:{model}</Typography>
        </Toolbar>
      </AppBar>
      {loading && <LinearProgress />}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
        <Board sections={sections} />
        <audio ref={audioRef} autoPlay />
      </Box>
      <Divider />
      <ChatControls onSend={sendMessage} onToggleVoice={toggleVoice} voiceActive={voiceActive} disabled={loading} />
      <Snackbar open={!!error} autoHideDuration={6000} onClose={() => setError(null)}>
        <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>
      </Snackbar>
    </Box>
  );
};

export default TeacherBoardPage;
