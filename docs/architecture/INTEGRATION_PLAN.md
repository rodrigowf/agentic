# Voice WebRTC + Nested Agents Integration Plan

**Date:** 2025-12-04
**Status:** In Progress

## Overview

Integrate the new backend-controlled WebRTC voice architecture with the existing nested agent system to enable voice-controlled agentic workflows.

## Architecture Components

### Current Working System (New)
- **Backend WebRTC Bridge** (`backend/api/realtime_voice_webrtc.py`)
  - Holds WebRTC connection to OpenAI Realtime API
  - Frontend connects to backend via WebRTC for audio
  - Function call detection exists but tools not executed

### Required Integration (From Old System)
- **Nested Agent WebSocket** (`/api/runs/{agent_name}`)
  - Multi-agent team execution
  - Tool execution and event streaming

- **Claude Code WebSocket** (`/api/runs/ClaudeCode`)
  - Self-editing code modifications
  - Event streaming for code changes

## Integration Strategy

### Phase 1: Backend Enhancement
**File:** `backend/api/realtime_voice_webrtc.py`

1. **Add WebSocket Management to BridgeSession**
   ```python
   self.nested_ws: Optional[WebSocket] = None
   self.claude_code_ws: Optional[WebSocket] = None
   self.nested_ws_task: Optional[asyncio.Task] = None
   self.claude_code_ws_task: Optional[asyncio.Task] = None
   ```

2. **Create WebSocket Client Functions**
   - `_connect_nested_websocket()` - Connect to nested agent
   - `_connect_claude_code_websocket()` - Connect to Claude Code
   - `_handle_nested_message()` - Process nested agent events
   - `_handle_claude_code_message()` - Process Claude Code events

3. **Implement Tool Execution**
   - Update `handle_function_call()` to execute tools
   - Tool: `send_to_nested` → Send message to nested WebSocket
   - Tool: `send_to_claude_code` → Send message to Claude Code WebSocket
   - Tool: `pause` → Send pause command to nested WebSocket
   - Tool: `reset` → Send reset command to nested WebSocket
   - Tool: `pause_claude_code` → Send pause command to Claude Code WebSocket

4. **Add Event Forwarding**
   - Forward nested team `TextMessage` events to OpenAI
   - Format as `[TEAM Agent] message` for voice narration
   - Forward tool execution events as `[TEAM Tool] result`
   - Forward Claude Code events as `[CODE ClaudeCode] message`

5. **Update Tool Definitions**
   - Add `realtimeTools` list to OpenAI session
   - Send via `session.update` on data channel open

### Phase 2: Frontend Updates
**File:** `frontend/src/features/voice/pages/VoiceAssistantModular.js`

1. **Keep Current WebRTC Logic**
   - No changes to `startVoiceWebRTCBridge()` call
   - Backend handles all WebSocket connections

2. **Display Nested Events**
   - Events already flow via conversation stream WebSocket
   - Current UI components already display them
   - No changes needed - just works!

3. **Optional: Direct WebSocket Connection**
   - Frontend can ALSO connect to nested WebSocket directly
   - For immediate UI updates (redundant but faster)
   - Use existing `useConversationStore` hook patterns

### Phase 3: Tool Definitions
**Location:** Backend OpenAI client initialization

```python
REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "send_to_nested",
        "description": "Send a user message to the nested agents team via WebSocket",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The user message to send"}
            },
            "required": ["text"]
        }
    },
    {
        "type": "function",
        "name": "send_to_claude_code",
        "description": "Send a self-editing instruction to Claude Code to modify the codebase",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The instruction for Claude Code"}
            },
            "required": ["text"]
        }
    },
    {
        "type": "function",
        "name": "pause",
        "description": "Pause the current nested conversation when the user explicitly asks",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "type": "function",
        "name": "reset",
        "description": "Reset the nested team conversation state when the user explicitly asks",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "type": "function",
        "name": "pause_claude_code",
        "description": "Pause/interrupt the currently running Claude Code task",
        "parameters": {"type": "object", "properties": {}}
    }
]
```

## Data Flow

```
User Voice Input
  ↓
Browser → Backend WebRTC Bridge → OpenAI Realtime API
                ↓
         Function Call Detected
                ↓
         Backend Executes Tool
                ↓
    send_to_nested("Create a weather app")
                ↓
         Nested Agent WebSocket
                ↓
         Agent Team Executes
                ↓
         TextMessage Events
                ↓
    Backend Formats as "[TEAM Agent] ..."
                ↓
    Forwards to OpenAI via Data Channel
                ↓
         OpenAI Narrates Result
                ↓
         Audio Returned to User
```

## Benefits

1. **Clean Separation** - Backend handles all agent orchestration
2. **Unified WebRTC** - Single WebRTC connection for audio
3. **Event Streaming** - Real-time updates via conversation stream
4. **Backward Compatible** - Old VoiceAssistant still works
5. **Production Ready** - Backend WebRTC is stable and tested

## Implementation Checklist

- [x] Analyze architecture differences
- [ ] Add WebSocket management to BridgeSession
- [ ] Implement tool execution logic
- [ ] Add event forwarding to OpenAI
- [ ] Configure tool definitions in OpenAI session
- [ ] Test tool execution flow
- [ ] Test event forwarding
- [ ] Update VoiceDashboardModular routing
- [ ] End-to-end testing with nested agents

## Files Modified

### Backend
- `backend/api/realtime_voice_webrtc.py` - Main integration
- `backend/api/openai_webrtc_client.py` - Tool definitions support (already exists)

### Frontend
- `frontend/src/features/voice/pages/VoiceAssistantModular.js` - Minor updates
- `frontend/src/features/voice/pages/VoiceDashboardModular.js` - Update imports

### Documentation
- `INTEGRATION_PLAN.md` - This file
- `CLAUDE.md` - Update with new architecture

## Testing Strategy

1. **Unit Tests**
   - Test WebSocket connection logic
   - Test tool execution
   - Test event forwarding

2. **Integration Tests**
   - Full voice → nested agent → voice flow
   - Tool execution with real agent
   - Event streaming verification

3. **Manual Testing**
   - Voice command: "Create a weather app"
   - Verify nested agent executes
   - Verify voice narrates progress
   - Verify final result is spoken

## Rollout Plan

1. **Phase 1** - Backend only (current)
2. **Phase 2** - Frontend integration
3. **Phase 3** - Update VoiceDashboard routing
4. **Phase 4** - Replace old VoiceAssistant completely

## Notes

- Keep old `VoiceAssistant.js` as reference until fully migrated
- Use `VoiceAssistantModular.js` as new default
- Backend WebSocket connections are internal-only (not exposed to frontend directly)
- All events flow through conversation stream WebSocket for consistency
