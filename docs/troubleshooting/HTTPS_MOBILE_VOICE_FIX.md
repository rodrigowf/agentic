# HTTPS Mobile Voice Fix - 2025-11-29

## Problem

Mobile voice page not working when accessed via HTTPS from smartphone (`https://192.168.0.25/mobile-voice/...`).

**Root Cause:** Nginx configuration was missing the WebRTC signaling endpoint for the new mobile voice feature.

## What Was Missing

The frontend uses:
```
wss://192.168.0.25/api/realtime/webrtc-signal/{conversation_id}/{peer_id}
```

But nginx.conf only had:
```
location /api/webrtc-signal/ {  ← OLD endpoint (missing /realtime/)
```

## Fix Applied

**File:** `/home/rodrigo/agentic/nginx.conf`

**Added:** New location block for the WebRTC signaling endpoint:

```nginx
# WebRTC signaling WebSocket (NEW - for mobile voice)
location /api/realtime/webrtc-signal/ {
    proxy_pass http://backend/api/realtime/webrtc-signal/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
}
```

## How to Apply

**YOU MUST RELOAD NGINX for changes to take effect:**

```bash
cd /home/rodrigo/agentic
./reload-nginx.sh
```

Or manually:
```bash
sudo kill -HUP $(cat /home/rodrigo/agentic/nginx.pid)
```

## Backend Endpoints

The mobile voice feature uses these endpoints (all under `/api/realtime`):

| Endpoint | Type | Purpose |
|----------|------|---------|
| `/api/realtime/conversations` | GET | List conversations |
| `/api/realtime/conversations/{id}` | GET | Get conversation details |
| `/api/realtime/webrtc-signal/{id}/{peer}` | WebSocket | WebRTC signaling (CRITICAL) |
| `/api/realtime/conversations/{id}/stream` | WebSocket | Event stream |
| `/api/realtime/token/openai` | GET | Get OpenAI token |
| `/api/realtime/sdp-offer` | POST | SDP offer exchange |

The general `/api` location block handles most of these, but WebSocket endpoints need explicit configuration for proper `Upgrade` header handling.

## Testing

After reloading nginx:

### 1. From Desktop (Local)
```
http://localhost:3000/mobile-voice/233e0f64-f053-49b2-bab9-5aa474e629c2
```
Should work (no changes needed, already working).

### 2. From Smartphone (HTTPS)
```
https://192.168.0.25/mobile-voice/233e0f64-f053-49b2-bab9-5aa474e629c2
```
Should now work after nginx reload!

## Verification

Check browser console on smartphone:
- ✅ No "Mixed Content" errors
- ✅ WebSocket connection successful
- ✅ WebRTC peer connection established
- ✅ Audio playback works

Check nginx logs:
```bash
tail -f /home/rodrigo/agentic/logs/nginx-access.log
tail -f /home/rodrigo/agentic/logs/nginx-error.log
```

Look for:
- WebSocket upgrade requests to `/api/realtime/webrtc-signal/`
- HTTP 101 Switching Protocols responses
- No 404 or 502 errors

## URL Resolution

The app now uses the centralized URL builder (`frontend/src/utils/urlBuilder.js`):

**When accessed via HTTPS (`https://192.168.0.25`):**
- REST API: `https://192.168.0.25/api/...`
- WebSockets: `wss://192.168.0.25/api/...`
- All routed through nginx proxy

**When accessed via HTTP (`http://192.168.0.25:3000`):**
- REST API: `http://192.168.0.25:8000/api/...`
- WebSockets: `ws://192.168.0.25:8000/api/...`
- Direct to backend (no nginx)

## Troubleshooting

If still not working:

1. **Check nginx is running:**
   ```bash
   ps aux | grep nginx
   ```

2. **Verify nginx config:**
   ```bash
   nginx -t -c /home/rodrigo/agentic/nginx.conf 2>&1 | grep syntax
   ```

3. **Check frontend URL detection:**
   Visit `https://192.168.0.25/debug-network` to see detected URLs

4. **Enable ADB debugging:**
   ```bash
   adb devices
   adb logcat browser:V *:S
   ```

5. **Check WebSocket in browser:**
   Open DevTools → Network → WS tab → Look for `webrtc-signal` connection

## Files Changed

1. ✅ `/home/rodrigo/agentic/nginx.conf` - Added WebRTC signaling location block
2. ✅ `/home/rodrigo/agentic/reload-nginx.sh` - Created reload helper script
3. ✅ `/home/rodrigo/agentic/debug/HTTPS_MOBILE_VOICE_FIX.md` - This doc

## Related Documentation

- `/home/rodrigo/agentic/docs/URL_RESOLUTION_STRATEGY.md`
- `/home/rodrigo/agentic/docs/URL_FIX_IMPLEMENTATION.md`
- `/home/rodrigo/agentic/debug/MOBILE_VOICE_FIXES.md`


---

## IMPORTANT: Desktop Must Be Running!

The mobile-voice page is a **remote microphone interface**. It requires:

1. ✅ **Desktop voice session running** - Open on desktop browser: `https://192.168.0.25/voice/233e0f64-f053-49b2-bab9-5aa474e629c2`
2. ✅ **Click green play button on desktop** - Start the voice session
3. ✅ **Then open mobile page** - `https://192.168.0.25/mobile-voice/233e0f64-f053-49b2-bab9-5aa474e629c2`
4. ✅ **Click green play button on mobile** - Connect as remote microphone

### Architecture

```
Mobile Device (Microphone)
     ↓ WebRTC
Desktop Browser (Running OpenAI Realtime Voice Session)
     ↓ WebRTC
OpenAI Realtime API
     ↓ Audio Response
Desktop Browser (Plays response + sends to mobile)
     ↓ WebRTC
Mobile Device (Speaker - hears OpenAI response)
```

### Verification from nginx logs:

The logs show mobile is connecting successfully:
```bash
tail -f /home/rodrigo/agentic/logs/nginx-access.log | grep webrtc-signal
```

You should see BOTH:
- `192.168.0.16` (mobile) → `/api/realtime/webrtc-signal/.../mobile`
- `192.168.0.25` (desktop) → `/api/realtime/webrtc-signal/.../desktop`

If you only see mobile, **the desktop voice session is not running!**

