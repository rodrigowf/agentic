import { useRef, useCallback } from 'react';
import { getHttpBase } from '../../../utils/urlBuilder';

const REALTIME_TOOLS = [
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

/**
 * OpenAI WebRTC connection management
 * This hook can be replaced with alternative connection implementations
 *
 * Interface contract:
 * - connect({ voiceConfig, replayItems, onEvent, onTrack, executeToolCall })
 * - disconnect()
 * - sendMessage(text)
 * - getDataChannel() -> returns data channel for direct access
 */
export const useOpenAIWebRTC = ({ recordEvent }) => {
  const peerRef = useRef(null);
  const dataChannelRef = useRef(null);
  const audioRef = useRef(null);
  const responseStreamRef = useRef(null);

  const backendBase = getHttpBase();

  // Post SDP offer and get answer from OpenAI via backend proxy
  const postSdpOffer = useCallback(async (mediaAddr, sessionId, clientSecret, sdp) => {
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
    // Unwrap JSON if needed
    if (bodyText.trim().startsWith('{')) {
      try {
        const obj = JSON.parse(bodyText);
        if (typeof obj.detail === 'string' && obj.detail.trim().startsWith('v=')) {
          return obj.detail;
        }
      } catch {}
    }
    return bodyText;
  }, [backendBase]);

  // Helper: wait for ICE gathering
  const waitForIceGathering = useCallback((pc) => new Promise((resolve) => {
    if (pc.iceGatheringState === 'complete') return resolve();
    const check = () => {
      if (pc.iceGatheringState === 'complete') {
        pc.removeEventListener('icegatheringstatechange', check);
        resolve();
      }
    };
    pc.addEventListener('icegatheringstatechange', check);
  }), []);

  /**
   * Connect to OpenAI Realtime API via WebRTC
   * @param {Object} options
   * @param {Object} options.voiceConfig - Voice configuration (voice, agentName, systemPrompt)
   * @param {Array} options.replayItems - History items to replay
   * @param {Function} options.onEvent - Callback for data channel events
   * @param {Function} options.onTrack - Callback for audio tracks
   * @param {Function} options.executeToolCall - Tool execution callback
   * @param {MediaStream} options.audioStream - Audio stream to send
   * @returns {Promise<Object>} { sessionId, peerConnection, dataChannel }
   */
  const connect = useCallback(async ({
    voiceConfig,
    replayItems = [],
    onEvent,
    onTrack,
    executeToolCall,
    audioStream,
  }) => {
    const voice = voiceConfig.voice || 'alloy';
    const systemPrompt = voiceConfig.systemPromptContent || '';
    const agentName = voiceConfig.agentName || 'MainConversation';

    // Request realtime session token
    const tokenUrl = `${backendBase}/api/realtime/token/openai?model=gpt-realtime&voice=${encodeURIComponent(voice)}&agent_name=${encodeURIComponent(agentName)}${systemPrompt ? `&system_prompt=${encodeURIComponent(systemPrompt)}` : ''}`;
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
      throw new Error(`Token response was not JSON. Body: ${tokenBody.slice(0, 200)}`);
    }

    const { id: sessionId, client_secret: clientSecret, media_addr: mediaAddr } = tokenJson;
    if (!sessionId || !clientSecret) {
      throw new Error(`Invalid token payload: ${JSON.stringify(tokenJson)}`);
    }

    // Create peer connection
    const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
    peerRef.current = pc;

    // Create data channel for OAI events
    const dataChannel = pc.createDataChannel('oai-events');
    dataChannelRef.current = dataChannel;

    // Setup data channel handlers
    dataChannel.onopen = () => {
      try {
        // Announce tools
        dataChannel.send(JSON.stringify({ type: 'session.update', session: { tools: REALTIME_TOOLS } }));

        // Replay history
        if (replayItems && replayItems.length > 0) {
          replayItems.forEach((item) => {
            try {
              dataChannel.send(JSON.stringify({ type: 'conversation.item.create', item }));
            } catch (err) {
              console.error('Failed to replay history item', err);
            }
          });
          void recordEvent('controller', 'history_replay', { count: replayItems.length });
        }
      } catch (err) {
        console.error('Data channel onopen error', err);
      }
    };

    dataChannel.onmessage = async (event) => {
      try {
        const payload = JSON.parse(event.data);
        void recordEvent('voice', payload?.type || 'data_channel', payload);

        // Forward to event handler
        if (onEvent) {
          await onEvent(payload, { executeToolCall });
        }
      } catch (e) {
        void recordEvent('voice', 'parse_error', { raw: event.data });
      }
    };

    // Handle incoming audio tracks
    pc.ontrack = (evt) => {
      if (audioRef.current) {
        audioRef.current.srcObject = evt.streams[0];
      }
      responseStreamRef.current = evt.streams[0];
      console.log('[OpenAI] Response stream received');

      if (onTrack) {
        onTrack(evt);
      }
    };

    // Add audio stream to peer
    if (audioStream) {
      for (const track of audioStream.getAudioTracks()) {
        pc.addTrack(track, audioStream);
      }
    }

    // Create offer and exchange SDP
    const offer = await pc.createOffer({ offerToReceiveAudio: true });
    await pc.setLocalDescription(offer);
    await waitForIceGathering(pc);

    const answerSdpRaw = await postSdpOffer(mediaAddr, sessionId, clientSecret, pc.localDescription.sdp);
    let answerSdp = (typeof answerSdpRaw === 'string' ? answerSdpRaw : String(answerSdpRaw || ''))
      .replace(/^\uFEFF/, '');

    // Normalize line endings
    answerSdp = answerSdp
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .split('\n')
      .map((l) => l.replace(/[\t ]+$/g, ''))
      .join('\r\n');

    await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

    console.log('[OpenAI] WebRTC connection established');

    return { sessionId, peerConnection: pc, dataChannel };
  }, [backendBase, postSdpOffer, waitForIceGathering, recordEvent]);

  /**
   * Disconnect and cleanup
   */
  const disconnect = useCallback(() => {
    if (peerRef.current) {
      peerRef.current.getSenders().forEach((sender) => {
        if (sender.track) sender.track.stop();
      });
      try {
        peerRef.current.close();
      } catch {}
    }
    peerRef.current = null;
    dataChannelRef.current = null;
    responseStreamRef.current = null;
  }, []);

  /**
   * Send a text message to the voice model
   */
  const sendMessage = useCallback((text) => {
    if (dataChannelRef.current && dataChannelRef.current.readyState === 'open') {
      dataChannelRef.current.send(JSON.stringify({
        type: 'conversation.item.create',
        item: { type: 'message', role: 'user', content: [{ type: 'input_text', text }] },
      }));
      dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
      void recordEvent('user', 'voice_user_message', { text });
      return true;
    }
    return false;
  }, [recordEvent]);

  /**
   * Get current data channel for direct access
   */
  const getDataChannel = useCallback(() => dataChannelRef.current, []);

  /**
   * Get response stream for mobile relay
   */
  const getResponseStream = useCallback(() => responseStreamRef.current, []);

  /**
   * Set audio element ref for playback
   */
  const setAudioElement = useCallback((element) => {
    audioRef.current = element;
  }, []);

  return {
    connect,
    disconnect,
    sendMessage,
    getDataChannel,
    getResponseStream,
    setAudioElement,
    peerRef,
    dataChannelRef,
  };
};

export default useOpenAIWebRTC;
