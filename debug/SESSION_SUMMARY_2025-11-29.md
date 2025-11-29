# Development Session Summary - 2025-11-29

## Overview

Successfully completed three major fixes for the mobile voice interface:
1. Fixed echo feedback issue
2. Configured nginx for HTTPS WebRTC signaling  
3. Debugged and documented HTTPS access workflow

**Status:** ✅ All features working perfectly!

---

## Issue 1: Echo Feedback on Mobile

**Problem:** Mobile was hearing echo of its own voice

**Root Cause:** Desktop was sending TWO audio tracks to mobile:
- Desktop microphone (which included mobile's voice) ← Echo source
- OpenAI response audio

**Solution:** Desktop now ONLY sends OpenAI response to mobile

**Files Changed:**
- `frontend/src/features/voice/pages/VoiceAssistant.js:1319` - Removed desktop mic from mobile peer
- `frontend/src/features/voice/pages/MobileVoice.js:423` - Simplified audio playback

**Technical Detail:** Switched from Web Audio API to HTMLAudioElement because Web Audio API has issues with multiple MediaStreamSource objects connected to same GainNode.

---

## Issue 2: HTTPS WebRTC Signaling

**Problem:** Mobile voice page not working via HTTPS from smartphone

**Root Cause:** Nginx missing `/api/realtime/webrtc-signal/` endpoint configuration

**Solution:** Added nginx location block for WebRTC signaling

**Files Changed:**
- `nginx.conf` - Added WebRTC signaling location block (lines 85-96)
- `reload-nginx.sh` - Created helper script to reload nginx

**Critical Discovery:** Both desktop and mobile MUST use same domain (both via HTTPS) for WebRTC signaling to work. Mixed origins (localhost HTTP + HTTPS domain) causes connection failure.

---

## Issue 3: Desktop Using Localhost

**Problem:** Desktop using `http://localhost:3000` while mobile using `https://192.168.0.25`

**Root Cause:** Different origins prevent WebRTC peer connection establishment

**Solution:** Both must use `https://192.168.0.25`

**Debugging Process:**
1. ADB showed mobile page loading successfully
2. Nginx logs showed mobile connecting (HTTP 101 WebSocket upgrade)
3. Backend logs showed only mobile registered for signaling
4. `ss` command showed all connections from 127.0.0.1 (localhost)
5. Conclusion: Desktop not using HTTPS through nginx

---

## Debugging Tools Used

### 1. ADB Remote Debugging
```bash
adb devices
adb forward tcp:9222 localabstract:chrome_devtools_remote
curl -s http://localhost:9222/json | python3 -m json.tool | grep url
```

### 2. Nginx Log Analysis
```bash
tail -f logs/nginx-access.log | grep webrtc-signal
# Expected: HTTP 101 for both desktop and mobile
```

### 3. Backend Log Analysis
```bash
grep "registered for signaling" /tmp/backend.log | tail -5
# Must see both desktop and mobile
```

### 4. Network Connection Analysis
```bash
ss -tn | grep ":8000" | grep ESTAB
# 127.0.0.1 = localhost (wrong)
# 192.168.0.x = network (correct)
```

---

## Key Learnings

1. **WebRTC requires origin consistency** - Both peers must use same protocol and domain
2. **Nginx logs are fastest** - See network activity immediately, faster than ADB
3. **Backend logs show peer registration** - Verify both desktop and mobile connected
4. **ss command identifies connection source** - Quickly distinguish localhost vs network
5. **Web Audio API limitations** - Multiple MediaStreamSource objects cause conflicts

---

## Documentation Created

1. `debug/MOBILE_VOICE_FIXES.md` - Audio playback fixes (echo + HTMLAudioElement)
2. `debug/HTTPS_MOBILE_VOICE_FIX.md` - Nginx configuration fix
3. `debug/MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md` - Complete debugging workflow with ADB
4. `reload-nginx.sh` - Helper script to reload nginx
5. Updated `CLAUDE.md` - Added HTTPS access section and recent changes

---

## Architecture Understanding

**WebRTC Flow:**
```
Desktop (https://192.168.0.25/voice)
    ↓ WSS
Nginx → Backend → OpenAI
    ↑ WSS
Mobile (https://192.168.0.25/mobile-voice)

Both peers register via:
/api/realtime/webrtc-signal/{conversation_id}/{desktop|mobile}

Once both registered:
→ Peer-to-peer WebRTC connection established
→ Mobile mic → Desktop → OpenAI → Mobile speaker
```

**Audio Flow (After Echo Fix):**
```
Mobile Device:
  Microphone → WebRTC → Desktop

Desktop:
  Mobile audio → OpenAI Realtime API
  OpenAI response → WebRTC → Mobile ✅
  Desktop mic → (NOT sent to mobile) ✅ Echo eliminated!

Mobile Device:
  WebRTC → HTMLAudioElement → Speaker
```

---

## Testing Workflow

**Correct Setup:**
```bash
# 1. Desktop (HTTPS via nginx)
https://192.168.0.25/voice/233e0f64-f053-49b2-bab9-5aa474e629c2

# 2. Mobile (HTTPS via nginx)
https://192.168.0.25/mobile-voice/233e0f64-f053-49b2-bab9-5aa474e629c2

# 3. Verify both peers connected
grep "registered for signaling" /tmp/backend.log | tail -2
# Should see: desktop registered
# Should see: mobile registered
```

**Monitoring:**
```bash
# Watch WebRTC connections
tail -f logs/nginx-access.log | grep webrtc-signal

# Expected output:
# 192.168.0.25 - "GET /api/realtime/webrtc-signal/.../desktop" 101
# 192.168.0.16 - "GET /api/realtime/webrtc-signal/.../mobile" 101
```

---

## Files Modified Summary

| File | Change | Purpose |
|------|--------|---------|
| `VoiceAssistant.js:1319` | Removed desktop mic from mobile peer | Echo fix |
| `MobileVoice.js:423` | Use HTMLAudioElement instead of Web Audio API | Audio playback fix |
| `nginx.conf:85-96` | Added WebRTC signaling location | HTTPS support |
| `reload-nginx.sh` | Created helper script | Nginx reload |
| `CLAUDE.md:1557-1628` | Added HTTPS access section | Documentation |
| `CLAUDE.md:2126-2171` | Added recent changes entry | Documentation |

---

## Success Metrics

✅ **Echo eliminated** - Mobile no longer hears itself  
✅ **HTTPS working** - Mobile can access via `https://192.168.0.25`  
✅ **WebRTC signaling** - Both desktop and mobile register as peers  
✅ **Bidirectional audio** - Speak on mobile, hear response on mobile  
✅ **Fully documented** - Complete debugging workflow and setup instructions  

---

## Future Reference

**Quick Debug Checklist:**
- [ ] Backend running? `ps aux | grep uvicorn`
- [ ] Nginx running? `ps aux | grep nginx`
- [ ] Desktop using HTTPS? Check URL starts with `https://192.168.0.25`
- [ ] Mobile using HTTPS? Check URL starts with `https://192.168.0.25`
- [ ] Both peers registered? `grep "registered for signaling" /tmp/backend.log`
- [ ] WebSocket upgrades? `tail nginx-access.log | grep "101"`
- [ ] No echo? Desktop should NOT send desktop mic to mobile

**Related Documentation:**
- `CLAUDE.md` - Main development guide
- `debug/HTTPS_MOBILE_VOICE_FIX.md` - Nginx fix
- `debug/MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md` - Debugging workflow
- `debug/MOBILE_VOICE_FIXES.md` - Audio fixes
- `docs/URL_RESOLUTION_STRATEGY.md` - URL builder documentation

---

**Session Date:** 2025-11-29  
**Duration:** ~2 hours  
**Outcome:** ✅ Complete success - All features working!  
