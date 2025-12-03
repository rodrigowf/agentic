# WebSocket Integration into VoiceAssistantModular.js

## Goal
Add WebSocket transport mode to VoiceAssistantModular.js so users can toggle between WebRTC (current) and WebSocket (Pipecat).

## Changes Needed

### 1. Add transport field to voiceConfig (line 54-60)
```javascript
const [voiceConfig, setVoiceConfig] = useState({
  agentName: 'MainConversation',
  systemPromptFile: 'default.txt',
  systemPromptContent: '',
  voice: 'alloy',
  transport: 'websocket', // NEW: 'webrtc' or 'websocket'
});
```

### 2. Add WebSocket refs (after line 87)
```javascript
const wsRef = useRef(null); // WebSocket connection to Pipecat
const audioProcessorRef = useRef(null); // Script processor for WebSocket audio
const audioSourceRef = useRef(null); // Media stream source
const playbackQueueRef = useRef([]); // Audio playback queue
const isPlayingRef = useRef(false); // Playback state
```

### 3. Add audio conversion helpers (after line 132)
```javascript
// Float32 → PCM16 for sending
const float32ToPCM16 = useCallback((float32Array) => {
  const pcm16 = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return pcm16.buffer;
}, []);

// PCM16 → Float32 for playback
const pcm16ToFloat32 = useCallback((pcm16Array) => {
  const float32 = new Float32Array(pcm16Array.length);
  for (let i = 0; i < pcm16Array.length; i++) {
    const int16 = pcm16Array[i];
    float32[i] = int16 / (int16 < 0 ? 0x8000 : 0x7FFF);
  }
  return float32;
}, []);
```

### 4. Add WebSocket audio playback (after audio conversion helpers)
```javascript
const playAudio = useCallback((pcm16ArrayBuffer) => {
  if (isSpeakerMuted) return;

  const audioContext = audioContextRef.current;
  if (!audioContext) return;

  const pcm16 = new Int16Array(pcm16ArrayBuffer);
  const float32 = pcm16ToFloat32(pcm16);

  const audioBuffer = audioContext.createBuffer(1, float32.length, 24000);
  audioBuffer.getChannelData(0).set(float32);

  playbackQueueRef.current.push(audioBuffer);
  if (!isPlayingRef.current) playNextChunk();
}, [isSpeakerMuted, pcm16ToFloat32]);

const playNextChunk = useCallback(() => {
  if (playbackQueueRef.current.length === 0) {
    isPlayingRef.current = false;
    return;
  }
  isPlayingRef.current = true;
  const audioBuffer = playbackQueueRef.current.shift();
  const audioContext = audioContextRef.current;
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.onended = () => playNextChunk();
  source.start();
}, []);
```

### 5. Add startSessionWebSocket function (after line 495)
```javascript
const startSessionWebSocket = async () => {
  if (isRunning) return;
  setIsRunning(true);
  setIsMuted(false);
  setError(null);

  try {
    console.log('[WebSocket] Starting session...');

    // Create audio context
    const audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 24000
    });
    audioContextRef.current = audioContext;

    // Get microphone
    let micStream;
    try {
      micStream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 24000, channelCount: 1, echoCancellation: true }
      });
      micStreamRef.current = micStream;
      setNoMicrophoneMode(false);
    } catch (micError) {
      console.warn('[WebSocket] No microphone:', micError);
      setNoMicrophoneMode(true);
      return;
    }

    // Connect WebSocket
    const wsUrl = `${getWsUrl()}/api/realtime/pipecat/ws/${conversationId}?voice=${voiceConfig.voice}&agent_name=${voiceConfig.agentName}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
      recordEvent('controller', 'session_started', { transport: 'websocket' });
    };

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        playAudio(event.data); // Play received audio
      } else if (typeof event.data === 'string') {
        try {
          const data = JSON.parse(event.data);
          console.log('[WebSocket] Event:', data);
        } catch {}
      }
    };

    ws.onerror = (err) => {
      console.error('[WebSocket] Error:', err);
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      console.log('[WebSocket] Closed');
      setIsRunning(false);
    };

    // Wait for connection
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Connection timeout')), 10000);
      ws.addEventListener('open', () => {
        clearTimeout(timeout);
        resolve();
      });
    });

    // Start audio capture
    const source = audioContext.createMediaStreamSource(micStream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);

    processor.onaudioprocess = (e) => {
      if (ws.readyState === WebSocket.OPEN && !isMuted) {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = float32ToPCM16(inputData);
        ws.send(pcm16);
      }
    };

    source.connect(processor);
    processor.connect(audioContext.destination);

    audioSourceRef.current = source;
    audioProcessorRef.current = processor;

    console.log('[WebSocket] Session started');
  } catch (err) {
    console.error('[WebSocket] Failed to start:', err);
    setError(err.message || 'Failed to start WebSocket session');
    setIsRunning(false);
  }
};
```

### 6. Add stopSessionWebSocket function (after startSessionWebSocket)
```javascript
const stopSessionWebSocket = () => {
  console.log('[WebSocket] Stopping session...');

  // Close WebSocket
  if (wsRef.current) {
    wsRef.current.close();
    wsRef.current = null;
  }

  // Stop microphone
  if (micStreamRef.current) {
    micStreamRef.current.getTracks().forEach(track => track.stop());
    micStreamRef.current = null;
  }

  // Disconnect audio nodes
  if (audioSourceRef.current) {
    audioSourceRef.current.disconnect();
    audioSourceRef.current = null;
  }

  if (audioProcessorRef.current) {
    audioProcessorRef.current.disconnect();
    audioProcessorRef.current = null;
  }

  // Close audio context
  if (audioContextRef.current) {
    audioContextRef.current.close();
    audioContextRef.current = null;
  }

  // Clear playback queue
  playbackQueueRef.current = [];
  isPlayingRef.current = false;

  recordEvent('controller', 'session_stopped', {});
  setIsRunning(false);
};
```

### 7. Update startSession to route based on transport (replace line 362)
```javascript
const startSession = async () => {
  if (voiceConfig.transport === 'websocket') {
    return startSessionWebSocket();
  }
  return startSessionWebRTC(); // Rename existing startSession to startSessionWebRTC
};
```

### 8. Update stopSession to route based on transport (replace line 501)
```javascript
const stopSession = async () => {
  if (voiceConfig.transport === 'websocket') {
    return stopSessionWebSocket();
  }
  return stopSessionWebRTC(); // Rename existing stopSession to stopSessionWebRTC
};
```

### 9. Update VoiceConfigEditor to include transport toggle
Add a toggle in VoiceConfigEditor.js:
```javascript
<FormControl fullWidth>
  <InputLabel>Transport</InputLabel>
  <Select value={transport} onChange={(e) => setTransport(e.target.value)}>
    <MenuItem value="webrtc">WebRTC (Direct OpenAI)</MenuItem>
    <MenuItem value="websocket">WebSocket (Pipecat)</MenuItem>
  </Select>
</FormControl>
```

## Testing
1. Open http://localhost:3001/agentic/voice-modular/
2. Click config (gear icon)
3. Change Transport to "WebSocket (Pipecat)"
4. Start session
5. Should connect to Pipecat backend via WebSocket

## Benefits
- Same UI for both transports
- Easy A/B testing
- Gradual migration path
- No separate routes needed
