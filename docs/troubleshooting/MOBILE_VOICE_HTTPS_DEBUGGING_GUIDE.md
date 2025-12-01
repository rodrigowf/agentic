# Mobile Voice HTTPS Debugging Guide - 2025-11-29

Successfully debugged mobile voice interface via HTTPS using ADB, nginx logs, and backend logs.

## Root Causes Fixed

1. **Nginx missing WebRTC endpoint** - Added `/api/realtime/webrtc-signal/` configuration
2. **Desktop using localhost** - Both desktop and mobile must use `https://192.168.0.25`
3. **Echo issue** - Desktop now only sends OpenAI response, not desktop mic

## ADB Debugging Workflow

```bash
# Connect and forward DevTools
adb devices
adb forward tcp:9222 localabstract:chrome_devtools_remote

# List open tabs
curl -s http://localhost:9222/json | python3 -m json.tool | grep url
```

## Nginx Log Analysis

```bash
# Real-time monitoring
tail -f /home/rodrigo/agentic/logs/nginx-access.log | grep webrtc-signal

# Check for both peers
# Expected: Both desktop and mobile show HTTP 101 (WebSocket upgrade)
```

## Backend Log Analysis

```bash
# Check peer registration
grep "registered for signaling" /tmp/backend.log | tail -5

# Should see BOTH desktop and mobile registered
```

## Network Connection Analysis

```bash
# Check where connections come from
ss -tn | grep ":8000" | grep ESTAB

# 127.0.0.1 = localhost (HTTP dev)
# 192.168.0.x = network (HTTPS nginx)
```

## Key Discovery

Desktop was using `http://localhost:3000` while mobile used `https://192.168.0.25`
**Different origins = WebRTC signaling fails!**

**Solution:** Both must use `https://192.168.0.25`

## Testing Workflow

1. **Desktop:** `https://192.168.0.25/voice/{conversation_id}` - Start session
2. **Mobile:** `https://192.168.0.25/mobile-voice/{conversation_id}` - Connect
3. **Verify:** `tail -f nginx-access.log | grep webrtc-signal` - See both peers

## Key Learnings

- **HTTPS consistency required** - Both peers must use same origin
- **Nginx logs are fastest** - See network activity immediately
- **Backend logs show peer registration** - Verify both desktop/mobile connected
- **ss command shows connection source** - Identify localhost vs network
- **ADB for browser console** - Only needed for detailed debugging

**Status:** ✅ WORKING - 2025-11-29
