# Voice Assistant Modular Architecture

## Overview

The VoiceAssistant component has been fully modularized to separate concerns and enable easy swapping of the WebRTC connection implementation. The architecture follows a **separation of concerns** pattern where each module has a single, well-defined responsibility.

## Module Structure

```
frontend/src/features/voice/
├── hooks/                           # Custom hooks for state and logic
│   ├── useVoiceSession.js          # Session state management
│   ├── useConversationStore.js     # Conversation persistence & events
│   ├── useOpenAIWebRTC.js          # ⭐ OpenAI WebRTC connection (REPLACEABLE)
│   ├── useOpenAIEventHandler.js    # OpenAI event processing
│   ├── useAudioMixer.js            # Audio mixing (desktop + mobile)
│   ├── useNestedWebSocket.js       # Nested team WebSocket
│   ├── useClaudeCodeWebSocket.js   # Claude Code WebSocket
│   └── useMobileWebRTC.js          # Mobile WebRTC signaling
├── utils/                           # Utility functions
│   ├── voiceForwarding.js          # Message forwarding logic
│   └── toolExecution.js            # Tool call execution
├── pages/
│   └── VoiceAssistant.js           # Main component (UI only)
└── VOICE_ARCHITECTURE.md           # This file
```

---

## Module Responsibilities

### 1. `useVoiceSession.js` - Session State Management

**Purpose:** Core session state and lifecycle management

**State:**
- `isRunning` - Session active/inactive
- `isMuted` - Desktop microphone muted
- `isSpeakerMuted` - Desktop speaker muted
- `transcript` - Text input buffer
- `error` - Error messages
- `noMicrophoneMode` - No desktop mic available
- `voiceConfig` - Voice configuration (agentName, voice, systemPrompt)

**Refs:**
- `toolCallsRef` - Accumulating function-call arguments
- `lastVoiceToolCallRef` - Last tool call for autopause detection
- `hasSpokenMidRef` - Mid-run narration flag
- `runCompletedRef` - Run completion flag

**Methods:**
- `resetSessionState()` - Reset all state on disconnect

---

### 2. `useConversationStore.js` - Conversation Persistence

**Purpose:** Manage conversation data, event storage, and WebSocket streaming

**State:**
- `conversation` - Conversation metadata
- `conversationLoading` - Loading state
- `conversationError` - Error state
- `messages` - All conversation events
- `remoteSessionActive` - Another tab is running

**Refs:**
- `eventsMapRef` - Event deduplication map
- `streamRef` - WebSocket connection
- `replayQueueRef` - History items for replay

**Methods:**
- `recordEvent(source, type, payload)` - Persist event to SQLite
- `buildReplayItems()` - Build history items for session start
- `upsertEvents(events)` - Merge events into message list

**Lifecycle:**
- Auto-loads conversation on mount
- Auto-connects to event stream WebSocket
- Auto-cleanup on unmount

---

### 3. ⭐ `useOpenAIWebRTC.js` - OpenAI WebRTC Connection (REPLACEABLE)

**Purpose:** OpenAI Realtime API connection via WebRTC

**Interface Contract (for alternative implementations):**

```javascript
const {
  connect,          // (options) => Promise<{ sessionId, peerConnection, dataChannel }>
  disconnect,       // () => void
  sendMessage,      // (text) => boolean
  getDataChannel,   // () => RTCDataChannel
  getResponseStream, // () => MediaStream
  setAudioElement,  // (element) => void
  peerRef,
  dataChannelRef,
} = useOpenAIWebRTC({ recordEvent });
```

**Connect Options:**
- `voiceConfig` - Voice settings (voice, agentName, systemPrompt)
- `replayItems` - History to replay on connection
- `onEvent` - Callback for data channel events
- `onTrack` - Callback for audio track received
- `executeToolCall` - Tool execution callback
- `audioStream` - Audio stream to send

**Key Features:**
- SDP exchange via backend proxy
- ICE gathering
- Tool announcements on channel open
- History replay
- Event parsing and forwarding

**To Replace This Module:**

1. Create a new hook (e.g., `useCustomWebRTC.js`)
2. Implement the same interface contract
3. Replace `import useOpenAIWebRTC` with your custom hook
4. No other changes needed!

**Example Replacement:**

```javascript
// Before:
import useOpenAIWebRTC from '../hooks/useOpenAIWebRTC';

// After:
import useCustomWebRTC from '../hooks/useCustomWebRTC';

// Usage stays the same:
const webrtc = useCustomWebRTC({ recordEvent });
```

---

### 4. `useOpenAIEventHandler.js` - OpenAI Event Processing

**Purpose:** Handle OpenAI Realtime API events (tool calls, argument deltas)

**Methods:**
- `handleEvent(payload, { executeToolCall })` - Process OpenAI data channel event

**Supported Events:**
- `response.output_item.added` - New function call
- `response.function_call_arguments.delta` - Argument chunk
- `response.function_call_arguments.done` - Execute tool
- Legacy: `response.function_call`, `response.function_call.arguments.delta`, `response.function_call.completed`

---

### 5. `useAudioMixer.js` - Audio Mixing

**Purpose:** Mix desktop + mobile microphone audio streams

**Methods:**
- `initializeMixer()` - Returns `{ audioContext, mixerStream, micStream, hasMicrophone }`
- `toggleDesktopMute(newMutedState)` - Mute/unmute desktop mic
- `connectMobileAudio(stream)` - Connect mobile audio to mixer
- `cleanup()` - Stop and cleanup audio resources

**Refs:**
- `audioContextRef` - Web Audio API context
- `micStreamRef` - Desktop microphone stream
- `mixerDestinationRef` - Mixed output destination
- `desktopGainNodeRef` - Desktop volume control
- `mobileGainNodeRef` - Mobile volume control

**Key Features:**
- Silent stream fallback if no microphone
- Independent gain control for desktop/mobile
- No-mic mode detection

---

### 6. `useNestedWebSocket.js` - Nested Team WebSocket

**Purpose:** Manage nested team agent WebSocket connection

**Methods:**
- `connect(agentName)` - Connect to nested team
- `disconnect()` - Close connection
- `sendMessage(text)` - Send user message to team
- `setupNestedWebSocketHandlers(ws)` - Setup event handlers

**Event Handling:**
- `TextMessage` - Team agent messages → forward to voice
- `ToolCallRequestEvent` - Tool start → forward to voice
- `ToolCallExecutionEvent` - Tool result/error → forward to voice
- `system` - System events (run finished, interrupted, errors)
- TERMINATE detection → trigger final summary

**Refs:**
- `nestedWsRef` - WebSocket instance

---

### 7. `useClaudeCodeWebSocket.js` - Claude Code WebSocket

**Purpose:** Manage Claude Code self-editor WebSocket connection

**Methods:**
- `connect()` - Connect to Claude Code
- `disconnect()` - Close connection
- `sendMessage(text)` - Send instruction to Claude Code

**Event Handling:**
- `TextMessage` - Claude Code messages → forward to voice
- `TaskResult` - Task completion/error → forward to voice

**Refs:**
- `claudeCodeWsRef` - WebSocket instance

---

### 8. `useMobileWebRTC.js` - Mobile WebRTC Signaling

**Purpose:** Desktop-mobile WebRTC peer connection for mobile microphone

**Methods:**
- `connect()` - Connect signaling WebSocket
- `disconnect()` - Close connection and peer
- `setupMobileWebRTC(responseStream)` - Create peer with OpenAI response
- `addResponseTrack(responseStream)` - Dynamically add track & renegotiate

**Key Features:**
- Wait for `peer_joined` before creating offer
- Mix mobile microphone into desktop mixer
- Send only OpenAI response to mobile (no desktop mic = no echo)
- Automatic renegotiation when adding tracks

**Refs:**
- `mobileAudioWsRef` - Signaling WebSocket
- `mobileWebRTCPeerRef` - RTCPeerConnection to mobile

---

### 9. `voiceForwarding.js` - Voice Message Forwarding

**Purpose:** Forward messages from nested team/claude to voice model

**Factory:** `createVoiceForwarder(deps)`

**Methods:**
- `forwardToVoice(role, text, metadata)` - Forward message to voice
- `notifyVoiceOfError(message, metadata)` - Forward error to voice

**Key Logic:**
- Detect error kinds → auto-request response
- Detect first tool completion → mid-run narration
- Replay queue management
- Response request logic

---

### 10. `toolExecution.js` - Tool Execution

**Purpose:** Execute tool calls from voice model

**Factory:** `createToolExecutor(deps)`

**Methods:**
- `executeToolCall(callId, name, argsObj)` - Execute a tool

**Supported Tools:**
- `send_to_nested` - Send message to nested team
- `send_to_claude_code` - Send instruction to Claude Code
- `pause` - Pause nested team (with autopause window)
- `reset` - Reset nested team connection
- `pause_claude_code` - Pause Claude Code

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    VoiceAssistant.js (UI)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
┌────────────┐ ┌──────────────┐ ┌─────────────┐
│  Session   │ │ Conversation │ │    Audio    │
│   State    │ │    Store     │ │    Mixer    │
└────────────┘ └──────────────┘ └─────────────┘
         │             │             │
         └─────────────┼─────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
┌────────────┐ ┌──────────────┐ ┌─────────────┐
│  OpenAI    │ │   Nested     │ │   Mobile    │
│  WebRTC    │ │   WebSocket  │ │   WebRTC    │
│ (Replace)  │ │              │ │             │
└────────────┘ └──────────────┘ └─────────────┘
         │             │             │
         └─────────────┼─────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
┌────────────┐ ┌──────────────┐ ┌─────────────┐
│   Voice    │ │     Tool     │ │  Event      │
│ Forwarding │ │  Execution   │ │  Handler    │
└────────────┘ └──────────────┘ └─────────────┘
```

---

## Replacing OpenAI WebRTC Connection

### Step-by-Step Guide

**1. Create New Hook**

Create `frontend/src/features/voice/hooks/useCustomWebRTC.js`:

```javascript
import { useRef, useCallback } from 'react';

export const useCustomWebRTC = ({ recordEvent }) => {
  const peerRef = useRef(null);
  const dataChannelRef = useRef(null);

  const connect = useCallback(async ({
    voiceConfig,
    replayItems,
    onEvent,
    onTrack,
    executeToolCall,
    audioStream,
  }) => {
    // Your custom WebRTC implementation
    // Must return: { sessionId, peerConnection, dataChannel }
  }, []);

  const disconnect = useCallback(() => {
    // Your cleanup logic
  }, []);

  const sendMessage = useCallback((text) => {
    // Send message via your connection
    return true; // or false if failed
  }, []);

  const getDataChannel = useCallback(() => dataChannelRef.current, []);
  const getResponseStream = useCallback(() => null, []);
  const setAudioElement = useCallback((element) => {}, []);

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

export default useCustomWebRTC;
```

**2. Replace Import in VoiceAssistant.js**

```javascript
// Change this line:
import useOpenAIWebRTC from '../hooks/useOpenAIWebRTC';

// To:
import useCustomWebRTC from '../hooks/useCustomWebRTC';

// And change this line:
const webrtc = useOpenAIWebRTC({ recordEvent });

// To:
const webrtc = useCustomWebRTC({ recordEvent });
```

**3. That's It!**

Everything else continues to work. The UI, event handling, tool execution, WebSocket connections—all unchanged.

---

## Testing Strategy

**Unit Tests:**
- Test each hook independently with mock dependencies
- Test utility functions (voiceForwarding, toolExecution)

**Integration Tests:**
- Test hook composition (e.g., session + audio + webrtc)
- Test event flow (OpenAI event → tool execution → WebSocket)

**E2E Tests:**
- Full voice session lifecycle
- Tool calls and responses
- Mobile connection and audio mixing
- Error scenarios

---

## Benefits of This Architecture

✅ **Separation of Concerns** - Each module has one responsibility
✅ **Easy to Test** - Mock dependencies, test in isolation
✅ **Easy to Replace** - Swap OpenAI WebRTC without touching other code
✅ **Reusable** - Hooks can be used in other components
✅ **Maintainable** - Changes are localized to specific modules
✅ **Scalable** - Add new features without modifying existing code

---

## Future Enhancements

**Possible Improvements:**

1. **Alternative Connections:**
   - Backend-forwarded WebRTC (via backend proxy)
   - WebSocket-only connection (no WebRTC)
   - Twilio/Agora/custom voice providers

2. **Audio Enhancements:**
   - Noise suppression
   - Echo cancellation tuning
   - Audio preprocessing pipeline

3. **State Management:**
   - Redux/Zustand for complex state
   - Persistent session recovery
   - Multi-tab synchronization

4. **Monitoring:**
   - Connection quality metrics
   - Latency tracking
   - Error rate monitoring

---

**Last Updated:** 2025-12-02
**Author:** Claude (Anthropic)
