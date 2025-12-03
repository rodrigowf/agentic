# Frontend Logging System

**Date:** 2025-12-03
**Status:** Implemented and Active

---

## Overview

A centralized logging system that forwards all frontend console messages to the backend in real-time, allowing you to see browser logs in the backend terminal while testing.

---

## Architecture

```
Browser Console
    ↓
logger.js (intercepts console.log/warn/error)
    ↓
POST /api/frontend-logs
    ↓
Backend Terminal
```

---

## Implementation

### Backend Endpoint

**Location:** `backend/main.py` (lines 859-883)

```python
@app.post("/api/frontend-logs")
async def frontend_logs(log_data: dict):
    """
    Receive console logs from frontend for debugging.
    Frontend sends: {level: 'log'|'warn'|'error', message: str, data: any}
    """
    level = log_data.get("level", "log")
    message = log_data.get("message", "")
    data = log_data.get("data")

    # Format the log message
    log_msg = f"[FRONTEND {level.upper()}] {message}"
    if data:
        log_msg += f" | Data: {data}"

    # Log to backend with appropriate level
    if level == "error":
        logger.error(log_msg)
    elif level == "warn":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

    return {"status": "logged"}
```

### Frontend Logger Utility

**Location:** `frontend/src/utils/logger.js`

**Key Features:**
1. **Console Interception** - Overwrites global console object
2. **Context-aware Logging** - Each component can have its own logger
3. **Fire-and-forget** - Doesn't block UI if backend unreachable
4. **Metadata Included** - Timestamp and URL included with each log

**Usage:**

```javascript
// Option 1: Use global console (automatically forwarded)
console.log('This will appear in backend logs');
console.error('This error appears in backend');

// Option 2: Create component-specific logger
import { createLogger } from '../utils/logger';

const logger = createLogger('MyComponent');
logger.log('Component-specific log');
logger.error('Component error');
```

### Frontend Integration

**Location:** `frontend/src/index.js` (lines 6-9)

```javascript
import { interceptConsole } from './utils/logger';

// Intercept all console logs and send to backend for debugging
interceptConsole();
```

This runs **before** the React app mounts, capturing ALL console messages throughout the application.

---

## How It Works

### Console Interception

When `interceptConsole()` is called:

1. Saves original console functions
2. Replaces console.log/warn/error with wrapped versions
3. Wrapped functions:
   - Call original function (displays in browser)
   - Send log to backend via fetch (non-blocking)

### Log Format

**Sent to backend:**
```json
{
  "level": "log|warn|error",
  "message": "The log message",
  "data": ["additional", "data"],
  "timestamp": "2025-12-03T02:10:00.000Z",
  "url": "http://localhost:3000/voice-webrtc"
}
```

**Displayed in backend:**
```
2025-12-03 02:10:00,123 - main - INFO - [FRONTEND LOG] Session created | Data: ['uuid-123']
2025-12-03 02:10:01,456 - main - ERROR - [FRONTEND ERROR] Data channel error | Data: [...]
```

---

## Benefits

### For Development

✅ **See browser console in terminal** - No need to switch between browser DevTools and terminal
✅ **Mobile debugging** - See mobile browser logs on desktop terminal
✅ **Persistent logs** - Backend logs can be saved to file
✅ **Multi-client debugging** - See logs from multiple browsers/devices in one place

### For Testing

✅ **Real-time monitoring** - Watch frontend behavior while testing
✅ **Error detection** - Immediately see JavaScript errors
✅ **WebRTC debugging** - Track data channel events, audio streaming, etc.
✅ **No manual setup** - Works automatically for all components

---

## Usage Examples

### Example 1: Component-Specific Logger

```javascript
// VoiceAssistantWebRTC.js
import { createLogger } from '../../../utils/logger';

const logger = createLogger('VoiceAssistantWebRTC');

function VoiceAssistantWebRTC() {
  const startSession = async () => {
    logger.log('Starting session...');
    // Backend sees: [FRONTEND LOG] [VoiceAssistantWebRTC] Starting session...
  };
}
```

### Example 2: Global Console (Automatic)

```javascript
// Any component
function MyComponent() {
  console.log('Component mounted');
  // Backend sees: [FRONTEND LOG] Component mounted

  console.error('Something went wrong');
  // Backend sees: [FRONTEND ERROR] Something went wrong
}
```

### Example 3: Mobile Voice Testing

```javascript
// MobileVoice.js on smartphone
console.log('Mobile session started:', sessionId);
// Desktop terminal sees: [FRONTEND LOG] Mobile session started: abc-123
```

---

## Watching Logs

### Backend Terminal

When backend is running:

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
uvicorn main:app --reload
```

You'll see:

```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://127.0.0.1:8000
2025-12-03 02:10:00,123 - main - INFO - [FRONTEND LOG] [VoiceAssistantWebRTC] Session created | Data: ['uuid-123']
2025-12-03 02:10:00,456 - main - INFO - [FRONTEND LOG] [VoiceAssistantWebRTC] Data channel opened
2025-12-03 02:10:01,789 - main - INFO - [FRONTEND LOG] [VoiceAssistantWebRTC] WebRTC setup complete
```

### Log File (Optional)

To save logs to file:

```bash
uvicorn main:app --reload 2>&1 | tee logs/frontend-logs.txt
```

Or use the existing log file:

```bash
tail -f /tmp/backend_webrtc.log | grep FRONTEND
```

---

## Performance

**Minimal overhead:**
- Fire-and-forget HTTP requests (no waiting)
- Fails silently if backend unreachable
- Doesn't block React rendering
- Only sends on actual console calls (not continuous polling)

**Network usage:**
- ~100-500 bytes per log message
- Only during active debugging
- No impact on production build (if logging removed)

---

## Disabling for Production

### Option 1: Conditional Interception

Edit `frontend/src/index.js`:

```javascript
// Only intercept in development
if (process.env.NODE_ENV === 'development') {
  interceptConsole();
}
```

### Option 2: Remove Completely

Remove from `frontend/src/index.js`:

```javascript
// Comment out or remove
// import { interceptConsole } from './utils/logger';
// interceptConsole();
```

---

## Troubleshooting

### Logs Not Appearing in Backend

**Check:**
1. Backend is running: `curl http://localhost:8000/api/agents`
2. Frontend can reach backend: Check browser Network tab
3. Console interception is enabled: Check `index.js`

**Fix:**
```bash
# Restart backend
cd backend && source venv/bin/activate && uvicorn main:app --reload
```

### Too Much Noise in Logs

**Filter frontend logs:**

```bash
# Only show frontend logs
tail -f /tmp/backend_webrtc.log | grep FRONTEND

# Exclude frontend logs
tail -f /tmp/backend_webrtc.log | grep -v FRONTEND
```

### Backend Unreachable Warnings

If you see in browser console:
```
Failed to send log to backend: NetworkError
```

This is normal if:
- Backend is not running
- Testing offline
- CORS issue

The warning is harmless and doesn't affect functionality.

---

## Files Modified

**Created:**
- `frontend/src/utils/logger.js` - Logger utility

**Modified:**
- `frontend/src/index.js` - Added interceptConsole()
- `frontend/src/features/voice/pages/VoiceAssistantWebRTC.js` - Uses logger
- `backend/main.py` - Added /api/frontend-logs endpoint

---

## Future Enhancements

Potential improvements:

- 🔮 **Log Levels Filter** - Backend setting to show only errors/warnings
- 🔮 **Session Correlation** - Tag logs with session ID
- 🔮 **Structured Logging** - Send more metadata (component stack, props)
- 🔮 **WebSocket Streaming** - Real-time log streaming instead of HTTP
- 🔮 **Log Persistence** - Store frontend logs in database
- 🔮 **Log Viewer UI** - Web-based log viewer

---

**Last Updated:** 2025-12-03
**Status:** Active and working
**Next:** Test with frontend voice session
