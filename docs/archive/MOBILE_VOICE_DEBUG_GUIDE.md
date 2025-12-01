# Mobile Voice Debugging Guide

## Summary of Changes

I've added **comprehensive logging** throughout the mobile voice audio flow to trace exactly where audio is breaking. The logs now track:

### Mobile → Desktop Flow (Mobile Mic Audio)
- **Mobile sending**: Logs every 50 chunks + voice detection
- **Desktop receiving**: Logs every 50 chunks + voice detection with mixer status

### Desktop → Mobile Flow (OpenAI Response Audio)
- **Desktop relaying**: Logs every 10 chunks of OpenAI response to mobile
- **Mobile receiving**: Already had good logs for this

### Desktop Mute Button
- Logs desktop mic gain, mobile gain, and mixer status when toggled

---

## New Log Messages to Watch For

### On Mobile Page Console:

```javascript
// Connection state (every ~1.7 seconds)
[MobileMic→Desktop] Chunk #50, WS state: 1, muted: false

// When you speak (voice > -40 dB)
[MobileMic→Desktop] VOICE DETECTED! Level: -15.3 dB, sending 16384 samples

// If NOT sending
[MobileMic→Desktop] NOT SENDING - Reason: Muted
[MobileMic→Desktop] NOT SENDING - Reason: WebSocket not open
```

### On Desktop Page Console:

```javascript
// Receiving mobile mic audio (every ~1.7 seconds)
[Desktop←MobileMic] Received chunk #50, size: 32768 bytes

// When mobile speaks (voice > -40 dB)
[Desktop←MobileMic] VOICE! @12.345s - -15.3 dB, 16384 samples, gain: 1, mixer tracks: 1

// When desktop mic is muted
[DesktopMute] Desktop mic gain set to: 0
[DesktopMute] Mobile gain still at: 1
[DesktopMute] Mixer still active, stream tracks: 1

// Relaying OpenAI response to mobile (every 10th chunk)
[OpenAI→Mobile] Relaying response chunk #10, 16384 samples
```

---

## Testing Procedure

### Step 1: Manual Testing with Enhanced Logs

1. **Refresh both pages** to load new code with logging
2. **Open Desktop browser DevTools** (F12) → Console tab
3. **Open Mobile browser (or Chrome Remote DevTools)** → Console tab
4. **Start desktop session** (unmuted)
5. **Start mobile session** (unmute mic after starting)
6. **Speak into mobile** and watch for:
   - Mobile: `[MobileMic→Desktop] VOICE DETECTED!`
   - Desktop: `[Desktop←MobileMic] VOICE!`
7. **Mute desktop mic** and watch for:
   - Desktop: `[DesktopMute] Desktop mic gain set to: 0`
   - Desktop: `[DesktopMute] Mobile gain still at: 1`
8. **Speak into mobile again** and verify:
   - Mobile still shows `VOICE DETECTED!`
   - Desktop still shows `Received chunk #...`
   - Desktop still shows `VOICE!` when you speak

### Step 2: Automated E2E Testing

Run the Puppeteer E2E test:

```bash
cd /home/rodrigo/agentic/debug
node test_mobile_voice_e2e.js
```

The test will:
1. Open desktop and mobile pages
2. Start both sessions
3. Monitor console logs
4. Mute desktop mic
5. Verify mobile mic still works
6. Generate a test report

**Note:** The test requires puppeteer to be installed:
```bash
cd /home/rodrigo/agentic/debug
npm install puppeteer
```

---

## Debugging Checklist

Use this to diagnose issues:

### Issue: Mobile mic not sending audio

Check mobile console for:
- ✅ `[MobileMic→Desktop] Chunk #...` → WebSocket is sending
- ❌ `NOT SENDING - Reason: Muted` → Unmute mobile mic button
- ❌ `NOT SENDING - Reason: WebSocket not open` → Check backend connection

### Issue: Desktop not receiving mobile mic

Check desktop console for:
- ✅ `[Desktop←MobileMic] Received chunk #...` → Audio is arriving
- ❌ No logs at all → WebSocket connection broken
- ⚠️ Receiving chunks but no `VOICE!` → Mobile is muted or too quiet

### Issue: Desktop mute affecting mobile

Check desktop console after muting:
- ✅ `Desktop mic gain set to: 0` → Desktop muted correctly
- ✅ `Mobile gain still at: 1` → Mobile NOT affected
- ✅ `Mixer still active, stream tracks: 1` → Mixer working
- ❌ `Mobile gain still at: 0` → BUG! Mobile gain was changed

### Issue: Mobile not receiving OpenAI response

Check desktop console for:
- ✅ `[OpenAI→Mobile] Relaying response chunk #...` → Response is being sent
- ❌ No relay logs → OpenAI response not arriving or not being relayed

Check mobile console for:
- ✅ `[MobileVoice] Scheduled desktop audio chunk at ...` → Audio arriving
- ❌ No scheduled chunks → Not receiving from desktop

### Issue: Mobile speaker muted

Check mobile UI:
- 🔊 Green volume icon → Speaker unmuted ✅
- 🔇 Orange volume icon → Speaker muted ❌ (click to unmute)

---

## Expected Flow (Visual)

```
┌─────────────────────────────────────────────────────────────┐
│                    MOBILE → DESKTOP → OPENAI                │
└─────────────────────────────────────────────────────────────┘

Mobile Mic
    ↓
[MobileMic→Desktop] VOICE DETECTED! -15.3 dB
    ↓
WebSocket /audio-relay/{id}/mobile
    ↓
[Desktop←MobileMic] VOICE! -15.3 dB, gain: 1
    ↓
mobileGainNode (gain: 1) → mixerDestination
    ↓
(Desktop mic: desktopGain = 0 if muted)
    ↓
Mixed Stream → OpenAI via WebRTC
    ↓
OpenAI Response


┌─────────────────────────────────────────────────────────────┐
│                    OPENAI → DESKTOP → MOBILE                │
└─────────────────────────────────────────────────────────────┘

OpenAI Response (WebRTC)
    ↓
Desktop <audio> element (plays locally)
    ↓
[OpenAI→Mobile] Relaying response chunk #10
    ↓
WebSocket /audio-relay/{id}/desktop
    ↓
[MobileVoice] Scheduled desktop audio chunk at 12.345s
    ↓
Mobile Speaker (via AudioBufferSource)
```

---

## Key Files Modified

1. **frontend/src/features/voice/pages/MobileVoice.js**
   - Added voice detection logging (lines 444-487)
   - Added audio level calculation (dB)
   - Added WebSocket state monitoring

2. **frontend/src/features/voice/pages/VoiceAssistant.js**
   - Added mobile mic reception logging (lines 966-1031)
   - Added voice detection on desktop side
   - Added mixer status tracking
   - Enhanced desktop mute logging (lines 1311-1336)

3. **debug/test_mobile_voice_e2e.js** (NEW)
   - Puppeteer E2E test for bidirectional audio
   - Automated testing of mute functionality
   - Console log analysis

4. **debug/MOBILE_VOICE_DEBUG_GUIDE.md** (THIS FILE)
   - Complete debugging documentation

---

## Next Steps

1. **Test manually** with the new logging
2. **Share console logs** showing the exact issue:
   - What do you see on mobile console when you speak?
   - What do you see on desktop console when mobile speaks?
   - What happens after desktop mic is muted?

3. **Run E2E test** (optional) for automated validation

4. **Based on logs**, we can pinpoint the EXACT breakpoint in the audio chain

---

## Quick Test Commands

```bash
# Kill background processes (if any)
pkill -f capture_mobile_errors

# Open Chrome with remote debugging (for mobile testing)
chromium-browser --remote-debugging-port=9222 http://localhost:3000/mobile-voice &

# Inspect mobile Chrome via DevTools
chromium-browser --app=http://localhost:9222

# Run E2E test
cd /home/rodrigo/agentic/debug
node test_mobile_voice_e2e.js
```

---

## Expected Console Output (Success Case)

### Mobile Console (when speaking):
```
[MobileMic→Desktop] Chunk #50, WS state: 1, muted: false
[MobileMic→Desktop] VOICE DETECTED! Level: -18.2 dB, sending 16384 samples
[MobileMic→Desktop] VOICE DETECTED! Level: -15.7 dB, sending 16384 samples
[MobileMic→Desktop] Chunk #100, WS state: 1, muted: false
```

### Desktop Console (when mobile speaks):
```
[Desktop←MobileMic] Received chunk #50, size: 32768 bytes
[Desktop←MobileMic] VOICE! @5.123s - -18.2 dB, 16384 samples, gain: 1, mixer tracks: 1
[Desktop←MobileMic] VOICE! @5.465s - -15.7 dB, 16384 samples, gain: 1, mixer tracks: 1
[Desktop←MobileMic] Received chunk #100, size: 32768 bytes
```

### Desktop Console (after muting desktop mic):
```
[DesktopMute] Desktop mic gain set to: 0
[DesktopMute] Mobile gain still at: 1
[DesktopMute] Mixer still active, stream tracks: 1
```

### Desktop Console (when OpenAI responds):
```
[OpenAI→Mobile] Relaying response chunk #10, 16384 samples
[OpenAI→Mobile] Relaying response chunk #20, 16384 samples
```

### Mobile Console (when receiving response):
```
[MobileVoice] Scheduled desktop audio chunk at 8.123 s
[MobileVoice] Scheduled desktop audio chunk at 8.464 s
[MobileVoice] Scheduled desktop audio chunk at 8.805 s
```

---

## Contact

If you see different logs than expected, **copy and paste them** and we can diagnose the exact issue!
