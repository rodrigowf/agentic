# WebRTC + Nested Agents Integration

**Date:** 2025-12-04
**Status:** Complete - Ready for Implementation
**Author:** Claude (Sonnet 4.5)

---

## Executive Summary

This document describes the complete integration of the backend-controlled WebRTC voice architecture with the nested agent system. The integration enables voice-controlled agentic workflows while maintaining clean architecture.

## Architecture Overview

### Current State (Before Integration)

```
┌─────────────┐                 ┌──────────────┐                 ┌─────────────┐
│   Browser   │◄───WebRTC──────►│   Backend    │◄───WebRTC──────►│   OpenAI    │
│  (Audio I/O)│                 │    Bridge    │                 │  Realtime   │
└─────────────┘                 └──────────────┘                 └─────────────┘
                                        │
                                        │ (No tool execution)
                                        ▼
                                   ❌ Tools Not Connected
```

### Integrated State (After Integration)

```
┌─────────────┐                 ┌──────────────────────────────────┐                 ┌─────────────┐
│   Browser   │◄───WebRTC──────►│      Backend Bridge              │◄───WebRTC──────►│   OpenAI    │
│  (Audio I/O)│                 │                                  │                 │  Realtime   │
└─────────────┘                 │  ┌────────────────────────────┐  │                 └─────────────┘
                                │  │   OpenAI WebRTC Client     │  │
                                │  │   (with tools config)      │  │
                                │  └────────────┬───────────────┘  │
                                │               │                  │
                                │  ┌────────────▼───────────────┐  │
                                │  │   Function Call Handler     │  │
                                │  └────────────┬───────────────┘  │
                                │               │                  │
                                │        ┌──────┴───────┐          │
                                │        │              │          │
                                │   ┌────▼────┐   ┌────▼────┐     │
                                │   │ Nested  │   │ Claude  │     │
                                │   │  Agent  │   │  Code   │     │
                                │   │   WS    │   │   WS    │     │
                                │   └────┬────┘   └────┬────┘     │
                                │        │             │          │
                                └────────┼─────────────┼──────────┘
                                         │             │
                                         ▼             ▼
                                 ┌───────────┐   ┌──────────┐
                                 │  Nested   │   │  Claude  │
                                 │  Agents   │   │   Code   │
                                 │   Team    │   │ Self-Edit│
                                 └─────┬─────┘   └────┬─────┘
                                       │              │
                                       └───Events─────┘
                                             │
                                    ┌────────▼─────────┐
                                    │  Event Forwarding│
                                    │   to OpenAI      │
                                    │  (Voice Narration)│
                                    └──────────────────┘
```

---

## Implementation Details

### 1. Tool Definitions

Tools exposed to OpenAI Realtime API:

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
        "description": "Send a self-editing instruction to Claude Code",
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
        "description": "Pause the current nested conversation",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "type": "function",
        "name": "reset",
        "description": "Reset the nested team conversation state",
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

### 2. Backend Bridge Session Extension

The `BridgeSession` class will be extended with:

#### New Attributes
```python
# WebSocket connections
self.nested_ws: Optional[WebSocket] = None
self.claude_code_ws: Optional[WebSocket] = None

# WebSocket message handlers (background tasks)
self.nested_ws_task: Optional[asyncio.Task] = None
self.claude_code_ws_task: Optional[asyncio.Task] = None

# WebSocket URLs
self.backend_base_url: str = "ws://localhost:8000"  # Or from env
```

#### New Methods

**`async def _connect_nested_websocket()`**
- Connects to `/api/runs/{agent_name}` WebSocket
- Starts background task to listen for messages
- Handles connection errors gracefully

**`async def _handle_nested_message(message: Dict)`**
- Processes incoming nested agent events
- Formats events for voice narration
- Forwards to OpenAI via `forward_message_to_voice()`
- Key event types:
  - `TextMessage` → `[TEAM Agent] message`
  - `ToolCallExecutionEvent` → `[TEAM Tool] result`
  - `TaskResult` → `[TEAM] Final result`

**`async def _connect_claude_code_websocket()`**
- Connects to `/api/runs/ClaudeCode` WebSocket
- Starts background task to listen for messages
- Handles connection errors gracefully

**`async def _handle_claude_code_message(message: Dict)`**
- Processes Claude Code events
- Formats as `[CODE ClaudeCode] action`
- Forwards to OpenAI for narration

**`async def execute_tool_call(call_id: str, tool_name: str, arguments: Dict)`**
- Main tool execution dispatcher
- Handles all 5 tool types
- Sends results back to OpenAI
- Records events in conversation store

### 3. Tool Execution Logic

#### `send_to_nested`
```python
if self.nested_ws and self.nested_ws.open:
    await self.nested_ws.send_text(json.dumps({
        "type": "user_message",
        "data": arguments["text"]
    }))
    return {"success": True}
return {"success": False, "error": "Nested WebSocket not connected"}
```

#### `send_to_claude_code`
```python
if self.claude_code_ws and self.claude_code_ws.open:
    await self.claude_code_ws.send_text(json.dumps({
        "type": "user_message",
        "data": arguments["text"]
    }))
    return {"success": True}
return {"success": False, "error": "Claude Code WebSocket not connected"}
```

#### `pause`, `reset`, `pause_claude_code`
Similar pattern - send control messages over respective WebSocket

### 4. Event Forwarding

Events from nested agents are formatted and forwarded to OpenAI:

```python
async def _forward_nested_event_to_voice(self, event: Dict):
    """
    Convert nested agent event to voice-friendly message.
    Forward to OpenAI without requesting immediate response.
    """
    event_type = event.get("type", "").lower()

    # Format based on event type
    if event_type == "textmessage":
        agent = event["data"]["source"]
        content = event["data"]["content"]
        message = f"[TEAM {agent}] {content}"

    elif event_type == "toolcallexecutionevent":
        tool_name = event["data"]["name"]
        result = event["data"]["result"]
        message = f"[TEAM {tool_name}] {result}"

    elif event_type == "taskresult":
        outcome = event["data"]["outcome"]
        summary = event["data"]["message"]
        message = f"[TEAM] Task {outcome}: {summary}"

    else:
        return  # Ignore other event types

    # Forward to OpenAI (no immediate response request)
    if self.openai_client:
        await self.openai_client.forward_message_to_voice("system", message)
```

### 5. Session Lifecycle

**Startup Sequence:**
```python
async def start(self, offer_sdp: str) -> str:
    # 1. Connect to OpenAI (with tools configured)
    self.openai_client = OpenAIWebRTCClient(
        api_key=api_key,
        model=self.model,
        voice=self.voice,
        tools=REALTIME_TOOLS,  # ← Tools configured here
        system_prompt=self.system_prompt,
        on_audio_callback=self.handle_openai_audio,
        on_function_call_callback=self.handle_function_call,
        on_event_callback=self._handle_openai_event,
    )
    await self.openai_client.connect()

    # 2. Set up browser WebRTC
    # ... (existing code)

    # 3. Connect to nested agent WebSocket
    await self._connect_nested_websocket()

    # 4. Connect to Claude Code WebSocket
    await self._connect_claude_code_websocket()

    # 5. Return SDP answer
    return local_sdp
```

**Shutdown Sequence:**
```python
async def close(self):
    # Stop WebSocket listener tasks
    if self.nested_ws_task:
        self.nested_ws_task.cancel()

    if self.claude_code_ws_task:
        self.claude_code_ws_task.cancel()

    # Close WebSocket connections
    if self.nested_ws:
        await self.nested_ws.close()

    if self.claude_code_ws:
        await self.claude_code_ws.close()

    # Close WebRTC connections
    # ... (existing code)
```

---

## Data Flow Example

### Voice Command → Tool Execution → Voice Response

1. **User speaks:** "Create a weather app"

2. **OpenAI transcribes and processes:**
   - Whisper transcribes audio to text
   - Realtime model decides to call `send_to_nested`

3. **Backend receives function call:**
   ```python
   handle_function_call(event={
       "type": "response.function_call_arguments.done",
       "call_id": "call_abc123",
       "name": "send_to_nested",
       "arguments": "{\"text\": \"Create a weather app\"}"
   })
   ```

4. **Backend executes tool:**
   ```python
   execute_tool_call("call_abc123", "send_to_nested", {"text": "Create a weather app"})
   # → Sends to nested_ws
   ```

5. **Nested agent processes request:**
   - Manager delegates to appropriate agent
   - Agent uses tools (code generation, file operations, etc.)
   - Events stream back via WebSocket

6. **Backend forwards events to voice:**
   ```python
   _handle_nested_message({
       "type": "TextMessage",
       "data": {
           "source": "Engineer",
           "content": "I'll create the weather app using React and OpenWeather API..."
       }
   })
   # → Forwards to OpenAI as "[TEAM Engineer] I'll create..."
   ```

7. **OpenAI narrates progress:**
   - Voice model receives context
   - Decides when to speak
   - Generates audio response: "The team is working on your weather app..."

8. **Final result delivered:**
   ```python
   _handle_nested_message({
       "type": "TaskResult",
       "data": {
           "outcome": "success",
           "message": "Weather app created at src/WeatherApp.js"
       }
   })
   # → "[TEAM] Task success: Weather app created at src/WeatherApp.js"
   # → OpenAI narrates: "The weather app has been successfully created!"
   ```

---

## Frontend Updates

### Minimal Changes Required

The frontend (`VoiceAssistantModular.js`) requires **minimal changes** because:

1. **WebRTC audio** - Already working ✅
2. **Event display** - Already working via conversation stream ✅
3. **Tool execution** - Now handled by backend ✅

**Optional improvements:**
- Remove unused tool execution code from frontend
- Simplify component (already mostly done)

### No Breaking Changes

- Old `VoiceAssistant.js` continues to work
- New `VoiceAssistantModular.js` gets nested agent support
- User can choose which to use

---

## Testing Strategy

### Unit Tests

1. **WebSocket Connection Tests**
   - Test nested agent WebSocket connection
   - Test Claude Code WebSocket connection
   - Test reconnection logic

2. **Tool Execution Tests**
   - Test each tool individually
   - Test error handling
   - Test WebSocket disconnection scenarios

3. **Event Forwarding Tests**
   - Test message formatting
   - Test event filtering
   - Test OpenAI forwarding

### Integration Tests

1. **End-to-End Voice Flow**
   - User speaks → Tool execution → Voice response
   - Verify audio quality maintained
   - Verify events recorded correctly

2. **Nested Agent Integration**
   - Send task to nested agent
   - Verify events forwarded to voice
   - Verify voice narrates progress

3. **Claude Code Integration**
   - Send code modification request
   - Verify Claude Code executes
   - Verify changes narrated

### Manual Testing Script

```bash
# 1. Start backend
cd backend
source venv/bin/activate
uvicorn main:app --reload

# 2. Start frontend
cd frontend
~/.nvm/versions/node/v22.21.1/bin/npm start

# 3. Open browser
open http://localhost:3000/agentic/voice

# 4. Test voice commands:
# - "Create a simple todo list app"  (→ send_to_nested)
# - "Add a README file"               (→ send_to_claude_code)
# - "Pause the current task"          (→ pause)
# - "Reset everything"                (→ reset)

# 5. Verify:
# - Audio works in both directions
# - Voice narrates agent progress
# - Events show in conversation history
# - Database records all events
```

---

## Benefits of This Architecture

1. **Clean Separation** - Backend owns all orchestration
2. **Scalable** - Easy to add more tools/agents
3. **Maintainable** - Single source of truth for tool logic
4. **Secure** - WebSocket connections internal to backend
5. **Observable** - All events recorded in conversation store
6. **Flexible** - Easy to swap OpenAI model or add providers

---

## Files Modified

### Backend
- ✅ `backend/api/openai_webrtc_client.py` - Refactored (complete)
- 🔄 `backend/api/realtime_voice_webrtc.py` - Integration (next)

### Frontend
- 🔄 `frontend/src/features/voice/pages/VoiceAssistantModular.js` - Minor cleanup (optional)

### Documentation
- ✅ `INTEGRATION_PLAN.md` - Overall plan
- ✅ `WEBRTC_NESTED_INTEGRATION.md` - This file
- 🔄 `CLAUDE.md` - Update with new architecture

---

## Implementation Checklist

- [x] Analyze architecture differences
- [x] Refactor OpenAI WebRTC client
- [x] Create integration documentation
- [x] Implement BridgeSession WebSocket connections
- [x] Implement tool execution logic
- [x] Implement event forwarding
- [x] Add tool definitions to OpenAI client
- [x] Add send_function_call_result method to OpenAI client
- [x] Test WebSocket connections
- [x] Test tool execution
- [x] Test event forwarding
- [x] Test session lifecycle
- [x] Create comprehensive unit tests (15 tests, all passing)
- [ ] End-to-end testing with live voice
- [ ] Update CLAUDE.md

---

## Implementation Complete

**Date:** 2025-12-04
**Status:** ✅ Implementation Complete - Ready for Testing

### What Was Implemented

1. **Tool Definitions** - 5 tools configured for OpenAI Realtime API:
   - `send_to_nested` - Send tasks to nested agents team
   - `send_to_claude_code` - Send code modification requests
   - `pause` - Pause nested agents
   - `reset` - Reset nested agents state
   - `pause_claude_code` - Pause Claude Code

2. **BridgeSession Extensions**:
   - Added WebSocket connection management
   - Implemented tool execution handlers
   - Added event forwarding from nested agents to voice
   - Proper lifecycle management (startup + cleanup)

3. **OpenAI Client Enhancement**:
   - Added `send_function_call_result()` method
   - Already had `forward_message_to_voice()` for event streaming

4. **Testing**:
   - 15 comprehensive unit tests
   - All tests passing ✅
   - Test coverage:
     - Tool definitions structure
     - Session initialization
     - Tool execution (all 5 tools)
     - Event forwarding (nested agents + Claude Code)
     - Session lifecycle cleanup

### Files Modified

**Backend:**
- ✅ `backend/api/openai_webrtc_client.py` - Added `send_function_call_result()`
- ✅ `backend/api/realtime_voice_webrtc.py` - Full integration implementation
- ✅ `backend/tests/test_webrtc_nested_integration.py` - Comprehensive test suite

**Documentation:**
- ✅ `WEBRTC_NESTED_INTEGRATION.md` - This file (updated)
- 🔄 `CLAUDE.md` - Needs update with new architecture

### Next Steps

1. **Manual Testing** - Test with live voice interaction:
   ```bash
   # Start backend
   cd backend && source venv/bin/activate && uvicorn main:app --reload

   # Start frontend
   cd frontend && ~/.nvm/versions/node/v22.21.1/bin/npm start

   # Test voice commands:
   # - "Create a todo list app" (→ send_to_nested)
   # - "Add a README" (→ send_to_claude_code)
   # - "Pause" (→ pause)
   ```

2. **Verify WebSocket Connections** - Ensure nested agents and Claude Code endpoints exist

3. **Test Event Streaming** - Verify voice narrates agent progress

4. **Optimize Voice Narration** - Adjust event formatting and timing

5. **Update Documentation** - Update CLAUDE.md with new capabilities

---

**Status:** ✅ **IMPLEMENTATION COMPLETE**
**Testing:** ✅ **Unit tests passing (15/15)**
**Next:** Manual E2E testing with live voice
**Risk Level:** Low (backward compatible, no breaking changes)

