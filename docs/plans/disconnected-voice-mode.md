# Disconnected Voice Mode Implementation Plan

## Goal
Add a non-realtime voice input capability to the Voice page that:
1. **Push-to-talk mic button** - Records audio only while pressed
2. **Disconnected mode** - Uses OpenAI Chat Completions API with `gpt-4o-audio-preview` instead of WebRTC
3. **Shared history** - Integrates with existing voice conversation storage
4. **Audio response playback** - TTS audio output from the model
5. **UI visibility** - Controls only visible when WebRTC is disconnected

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Voice Page (VoiceAssistant.js)              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐    ┌─────────────────────────────────┐   │
│  │ WebRTC Controls  │    │  Disconnected Voice Controls    │   │
│  │ (isRunning=true) │    │  (isRunning=false && !remote)   │   │
│  └──────────────────┘    └─────────────────────────────────┘   │
│                                      │                          │
│                          ┌───────────┴───────────┐              │
│                          │  PushToTalkButton     │              │
│                          │  - MediaRecorder      │              │
│                          │  - Audio visualization│              │
│                          └───────────┬───────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│  POST /api/realtime/conversations/{id}/audio-message            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. Receive base64 audio (WAV)                            │  │
│  │  2. Build conversation history from stored events         │  │
│  │  3. Call OpenAI Chat Completions API (gpt-4o-audio)       │  │
│  │  4. Store user message + response as events               │  │
│  │  5. Return text + audio response                          │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Backend - Audio Message Endpoint

**File:** `backend/api/realtime_voice_webrtc.py`

Create a new endpoint for disconnected audio messages:

```python
@router.post("/api/realtime/conversations/{conversation_id}/audio-message")
async def send_audio_message(
    conversation_id: str,
    request: AudioMessageRequest  # { audio_base64: str, format: str }
):
    """
    Send an audio message to the conversation using Chat Completions API.
    Returns both text and audio response.
    """
    # 1. Get conversation and build history
    # 2. Call OpenAI Chat Completions with audio
    # 3. Store events (user audio, assistant response)
    # 4. Return { text: str, audio_base64: str, format: str }
```

**New file:** `backend/api/audio_chat_handler.py`

Modular handler for audio chat completions:

```python
import openai
import base64
from typing import List, Dict, Optional, Tuple

class AudioChatHandler:
    """Handles non-realtime audio chat using OpenAI Chat Completions API"""

    def __init__(self, model: str = "gpt-4o-audio-preview", voice: str = "alloy"):
        self.model = model
        self.voice = voice
        self.client = openai.AsyncOpenAI()

    async def send_audio_message(
        self,
        audio_base64: str,
        conversation_history: List[Dict],
        system_prompt: str
    ) -> Tuple[str, str]:  # (text_response, audio_base64_response)
        """
        Send audio input, get text + audio output.
        """
        messages = self._build_messages(conversation_history, system_prompt, audio_base64)

        response = await self.client.chat.completions.create(
            model=self.model,
            modalities=["text", "audio"],
            audio={"voice": self.voice, "format": "wav"},
            messages=messages
        )

        text = response.choices[0].message.content or ""
        audio_data = response.choices[0].message.audio.data if response.choices[0].message.audio else ""

        return text, audio_data
```

### Step 2: Backend - History Builder

**Add to:** `backend/api/audio_chat_handler.py`

```python
def _build_messages(
    self,
    conversation_history: List[Dict],
    system_prompt: str,
    current_audio_base64: str
) -> List[Dict]:
    """
    Build OpenAI messages array from stored conversation events.
    """
    messages = [{"role": "system", "content": system_prompt}]

    for event in conversation_history:
        event_type = event.get("type", "")
        payload = event.get("payload", {}) or event.get("data", {})

        if event_type == "voice_user_message":
            # User spoke - text transcript
            text = payload.get("text") or payload.get("transcript", "")
            if text:
                messages.append({"role": "user", "content": text})

        elif event_type == "disconnected_user_audio":
            # User audio from disconnected mode (stored as base64)
            audio_data = payload.get("audio_base64", "")
            transcript = payload.get("transcript", "")
            if transcript:
                messages.append({"role": "user", "content": transcript})
            # Note: We could include audio reference but text is more reliable for history

        elif event_type == "voice_assistant_message":
            text = payload.get("text", "")
            if text:
                messages.append({"role": "assistant", "content": text})

        elif event_type == "disconnected_assistant_response":
            text = payload.get("text", "")
            if text:
                messages.append({"role": "assistant", "content": text})

    # Add current audio input
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "input_audio",
                "input_audio": {
                    "data": current_audio_base64,
                    "format": "wav"
                }
            }
        ]
    })

    return messages
```

### Step 3: Frontend - API Function

**File:** `frontend/src/api.js`

Add new API function:

```javascript
// Disconnected voice - send audio message
export const sendAudioMessage = (conversationId, payload) =>
  API.post(`${VOICE_BASE}/conversations/${conversationId}/audio-message`, payload);
```

### Step 4: Frontend - Push-to-Talk Hook

**New file:** `frontend/src/features/voice/hooks/usePushToTalk.js`

```javascript
import { useState, useRef, useCallback } from 'react';

/**
 * Hook for push-to-talk audio recording
 * Records audio while button is pressed, returns base64 WAV
 */
export default function usePushToTalk({ onRecordingComplete, onError }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsProcessing(true);
        try {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
          // Convert to WAV for OpenAI
          const wavBlob = await convertToWav(blob);
          const base64 = await blobToBase64(wavBlob);
          onRecordingComplete?.(base64);
        } catch (err) {
          onError?.(err);
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);
    } catch (err) {
      onError?.(err);
    }
  }, [onRecordingComplete, onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsRecording(false);
  }, []);

  return {
    isRecording,
    isProcessing,
    startRecording,
    stopRecording,
    stream: streamRef.current
  };
}

// Helper: Convert blob to base64
async function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// Helper: Convert webm to WAV using AudioContext
async function convertToWav(webmBlob) {
  const arrayBuffer = await webmBlob.arrayBuffer();
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

  // Convert to WAV
  const wavBuffer = audioBufferToWav(audioBuffer);
  return new Blob([wavBuffer], { type: 'audio/wav' });
}

// Helper: AudioBuffer to WAV format
function audioBufferToWav(buffer) {
  const numChannels = 1; // Mono
  const sampleRate = buffer.sampleRate;
  const format = 1; // PCM
  const bitDepth = 16;

  const data = buffer.getChannelData(0);
  const dataLength = data.length * (bitDepth / 8);
  const bufferLength = 44 + dataLength;

  const arrayBuffer = new ArrayBuffer(bufferLength);
  const view = new DataView(arrayBuffer);

  // WAV header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataLength, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, format, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numChannels * (bitDepth / 8), true);
  view.setUint16(32, numChannels * (bitDepth / 8), true);
  view.setUint16(34, bitDepth, true);
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  // Write audio data
  let offset = 44;
  for (let i = 0; i < data.length; i++) {
    const sample = Math.max(-1, Math.min(1, data[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
    offset += 2;
  }

  return arrayBuffer;
}

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}
```

### Step 5: Frontend - Push-to-Talk Button Component

**New file:** `frontend/src/features/voice/components/PushToTalkButton.js`

```javascript
import React from 'react';
import { Box, IconButton, Typography, CircularProgress } from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import AudioVisualizer from './AudioVisualizer';

/**
 * Push-to-talk button for disconnected voice mode
 * Press and hold to record, release to send
 */
export default function PushToTalkButton({
  isRecording,
  isProcessing,
  isSending,
  onPressStart,
  onPressEnd,
  disabled,
  stream
}) {
  const isActive = isRecording || isProcessing || isSending;

  const handleMouseDown = (e) => {
    e.preventDefault();
    if (!disabled && !isProcessing && !isSending) {
      onPressStart?.();
    }
  };

  const handleMouseUp = (e) => {
    e.preventDefault();
    if (isRecording) {
      onPressEnd?.();
    }
  };

  const handleTouchStart = (e) => {
    e.preventDefault();
    if (!disabled && !isProcessing && !isSending) {
      onPressStart?.();
    }
  };

  const handleTouchEnd = (e) => {
    e.preventDefault();
    if (isRecording) {
      onPressEnd?.();
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        p: 3,
        borderRadius: 2,
        bgcolor: (theme) =>
          theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Typography variant="subtitle2" color="text.secondary">
        {isRecording ? 'Recording... Release to send' :
         isProcessing ? 'Processing...' :
         isSending ? 'Sending...' :
         'Press and hold to speak'}
      </Typography>

      <IconButton
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        disabled={disabled || isProcessing || isSending}
        sx={{
          width: 80,
          height: 80,
          bgcolor: isRecording ? 'error.main' : 'primary.main',
          color: 'white',
          transition: 'all 0.2s ease',
          transform: isRecording ? 'scale(1.1)' : 'scale(1)',
          animation: isRecording ? 'pulse 1s ease-in-out infinite' : 'none',
          '@keyframes pulse': {
            '0%, 100%': { boxShadow: '0 0 0 0 rgba(244, 67, 54, 0.7)' },
            '50%': { boxShadow: '0 0 0 12px rgba(244, 67, 54, 0)' },
          },
          '&:hover': {
            bgcolor: isRecording ? 'error.dark' : 'primary.dark',
          },
          '&:disabled': {
            bgcolor: 'action.disabledBackground',
          },
        }}
      >
        {isProcessing || isSending ? (
          <CircularProgress size={32} sx={{ color: 'white' }} />
        ) : (
          <MicIcon sx={{ fontSize: 40 }} />
        )}
      </IconButton>

      {/* Audio visualizer when recording */}
      {isRecording && stream && (
        <AudioVisualizer stream={stream} isActive={true} isMuted={false} />
      )}
    </Box>
  );
}
```

### Step 6: Frontend - Disconnected Voice Controls Component

**New file:** `frontend/src/features/voice/components/DisconnectedVoiceControls.js`

```javascript
import React, { useState, useRef, useCallback } from 'react';
import { Box, Alert } from '@mui/material';
import PushToTalkButton from './PushToTalkButton';
import usePushToTalk from '../hooks/usePushToTalk';
import { sendAudioMessage, appendVoiceConversationEvent } from '../../../api';

/**
 * Controls for disconnected (non-WebRTC) voice mode
 * Visible when WebRTC session is not active
 */
export default function DisconnectedVoiceControls({
  conversationId,
  voiceConfig,
  onError,
  onResponseAudio
}) {
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const audioRef = useRef(null);

  const handleRecordingComplete = useCallback(async (audioBase64) => {
    if (!conversationId) {
      setError('No conversation selected');
      return;
    }

    setIsSending(true);
    setError(null);

    try {
      // Send audio to backend
      const response = await sendAudioMessage(conversationId, {
        audio_base64: audioBase64,
        format: 'wav',
        voice: voiceConfig?.voice || 'alloy'
      });

      const { text, audio_base64: responseAudio, transcript } = response.data;

      // Play response audio if available
      if (responseAudio && audioRef.current) {
        const audioData = `data:audio/wav;base64,${responseAudio}`;
        audioRef.current.src = audioData;
        audioRef.current.play().catch(console.warn);
      }

      onResponseAudio?.(responseAudio);

    } catch (err) {
      console.error('[DisconnectedVoice] Failed to send audio:', err);
      const detail = err?.response?.data?.detail || err.message;
      setError(detail);
      onError?.(err);
    } finally {
      setIsSending(false);
    }
  }, [conversationId, voiceConfig, onResponseAudio, onError]);

  const handleError = useCallback((err) => {
    console.error('[DisconnectedVoice] Recording error:', err);
    setError(err.message || 'Recording failed');
    onError?.(err);
  }, [onError]);

  const {
    isRecording,
    isProcessing,
    startRecording,
    stopRecording,
    stream
  } = usePushToTalk({
    onRecordingComplete: handleRecordingComplete,
    onError: handleError
  });

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <PushToTalkButton
        isRecording={isRecording}
        isProcessing={isProcessing}
        isSending={isSending}
        onPressStart={startRecording}
        onPressEnd={stopRecording}
        disabled={!conversationId}
        stream={stream}
      />

      {/* Hidden audio element for playback */}
      <audio ref={audioRef} style={{ display: 'none' }} />
    </Box>
  );
}
```

### Step 7: Frontend - Integrate into VoiceControlPanel

**File:** `frontend/src/features/voice/components/VoiceControlPanel.js`

Add the disconnected controls when WebRTC is not active:

```javascript
import DisconnectedVoiceControls from './DisconnectedVoiceControls';

// ... existing code ...

// Inside the component, after WebRTC controls section:
{!isRunning && !remoteSessionActive && !conversationError && (
  <Box sx={{ mt: 2 }}>
    <DisconnectedVoiceControls
      conversationId={conversationId}
      voiceConfig={voiceConfig}
      onError={(err) => setError(err.message)}
    />
  </Box>
)}
```

### Step 8: Backend Schema Updates

**File:** `backend/config/schemas.py`

Add request/response models:

```python
class AudioMessageRequest(BaseModel):
    audio_base64: str
    format: str = "wav"
    voice: str = "alloy"

class AudioMessageResponse(BaseModel):
    text: str
    audio_base64: Optional[str] = None
    transcript: Optional[str] = None  # User's speech transcript
```

---

## File Changes Summary

### New Files
1. `backend/api/audio_chat_handler.py` - AudioChatHandler class
2. `frontend/src/features/voice/hooks/usePushToTalk.js` - Recording hook
3. `frontend/src/features/voice/components/PushToTalkButton.js` - UI component
4. `frontend/src/features/voice/components/DisconnectedVoiceControls.js` - Container component

### Modified Files
1. `backend/api/realtime_voice_webrtc.py` - Add `/audio-message` endpoint
2. `backend/config/schemas.py` - Add request/response models
3. `frontend/src/api.js` - Add `sendAudioMessage` function
4. `frontend/src/features/voice/components/VoiceControlPanel.js` - Integrate disconnected controls
5. `frontend/src/features/voice/pages/VoiceAssistant.js` - Pass `conversationId` to control panel

---

## Event Types for Storage

New event types to store in conversation history:

```
disconnected_user_audio     - User's audio input (with transcript)
disconnected_assistant_response - Assistant's text + audio response
```

These integrate seamlessly with existing `voice_user_message` and `voice_assistant_message` events.

---

## Testing Plan

1. **Unit tests** for `usePushToTalk` hook
2. **Integration test** for audio endpoint
3. **Manual testing**:
   - Record audio, verify WAV conversion
   - Send to backend, verify response
   - Play audio response
   - Check conversation history includes new events

---

## Future Enhancements

- Keyboard shortcut (Space bar) to trigger recording
- Visual waveform of recorded audio before sending
- Retry failed requests
- Offline queue for poor connectivity
