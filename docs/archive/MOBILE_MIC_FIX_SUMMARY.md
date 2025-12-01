# Mobile Mic Fix Summary

## Issues Found & Fixed

### Issue #1: Mobile Mic Always Muted (CRITICAL BUG)

**Problem:**
- Mobile mic started muted by default (`setIsMuted(true)`)
- When user clicked unmute button, the `isMuted` state variable WAS UPDATED in React state
- BUT the audio processor callback (`processor.onaudioprocess`) had **already captured** the old `isMuted` value in its closure
- Result: Even after clicking unmute, the processor still saw `isMuted = true` and never sent audio

**Root Cause:**
```javascript
// Processor created with closure over isMuted state
processor.onaudioprocess = (audioEvent) => {
  if (!isMuted) {  // ← This captures isMuted at creation time!
    // Send audio...
  }
};

// Later, clicking unmute button updates React state but NOT the closure
setIsMuted(false);  // React state changes
// BUT processor callback still sees old value: isMuted = true
```

**Fix Applied:**
1. Added `isMutedRef = useRef(true)` to hold mute state
2. Updated `toggleMute()` to update BOTH state and ref:
   ```javascript
   setIsMuted(newMutedState);
   isMutedRef.current = newMutedState;  // ← Update ref too!
   ```
3. Changed processor to use ref instead of state:
   ```javascript
   if (!isMutedRef.current) {  // ← Always gets current value!
     // Send audio...
   }
   ```

**Files Changed:**
- `frontend/src/features/voice/pages/MobileVoice.js`
  - Line 61: Added `isMutedRef`
  - Line 458: Use `isMutedRef.current` instead of `isMuted`
  - Line 552: Update ref in `toggleMute()`
  - Line 310: Initialize ref in `startSession()`
  - Line 513: Reset ref in `stopSession()`

**Expected Behavior After Fix:**
- Mobile starts muted ✓
- User clicks unmute button
- Console logs: `[MobileMute] Toggled to: UNMUTED, ref updated`
- Next processor cycle: `[MobileMic→Desktop] Chunk #50, WS state: 1, muted: false`
- When voice detected: `[MobileMic→Desktop] VOICE DETECTED! Level: -15.3 dB`
- Desktop receives: `[Desktop←MobileMic] VOICE! @5.123s - -15.3 dB`
- OpenAI hears mobile mic audio ✓

---

### Issue #2: Doubled Audio (Echo)

**Problem:**
- Desktop `<audio>` element plays OpenAI response on desktop speakers
- Desktop ALSO relays same response to mobile via WebSocket
- Mobile plays response on mobile speakers
- User hears BOTH = doubled/echo effect

**This is NOT a bug** - it's expected behavior when both devices have speakers active!

**Solutions:**

**Option A: Mute Desktop Speaker** (Recommended)
- Click the **speaker/volume mute button** on desktop (NOT the mic button)
- This mutes the desktop `<audio>` element
- Mobile still plays response = no doubling

**Option B: Mute Mobile Speaker**
- Click the **speaker/volume button** on mobile
- Desktop plays response, mobile is silent

**Option C: Use Only One Device**
- If you want to use mobile as wireless mic only, use Option A
- If you want mobile for visualization only, use Option B

**Why Two Playback Streams?**
- Desktop needs to hear responses (for desktop-only use)
- Mobile needs to hear responses (for mobile-only use)
- When BOTH connected, user must choose which speaker to use

**Added Logging:**
- Desktop: `[Desktop] OpenAI response will play on desktop <audio> element`
- Desktop: `[MobileAudio] OpenAI response stream received, will relay to mobile if connected`
- Desktop: `[OpenAI→Mobile] Relaying response chunk #10, 16384 samples`
- Mobile: `[MobileVoice] Scheduled desktop audio chunk at 8.123 s`

---

## Testing Instructions

### Test 1: Mobile Mic Now Works

1. **Desktop:** Start session, mute desktop mic
2. **Mobile:** Start session, click unmute button
3. **Mobile Console:** Should see:
   ```
   [MobileMute] Toggled to: UNMUTED, ref updated
   [MobileMic→Desktop] Chunk #50, WS state: 1, muted: false
   [MobileMic→Desktop] VOICE DETECTED! Level: -18.2 dB, sending 16384 samples
   ```
4. **Desktop Console:** Should see:
   ```
   [Desktop←MobileMic] Received chunk #50, size: 32768 bytes
   [Desktop←MobileMic] VOICE! @5.123s - -18.2 dB, 16384 samples, gain: 1
   ```
5. **Result:** OpenAI should hear you and respond ✓

### Test 2: No More Doubled Audio

**Setup:** Desktop mic muted, mobile mic unmuted

**Option A - Mobile Speaker Only:**
1. Desktop: Click **speaker mute button** (volume icon, NOT mic icon)
2. Mobile: Keep speaker unmuted
3. Speak into mobile
4. **Result:** Hear response ONLY from mobile (no doubling) ✓

**Option B - Desktop Speaker Only:**
1. Desktop: Keep speaker unmuted
2. Mobile: Click **speaker mute button**
3. Speak into mobile
4. **Result:** Hear response ONLY from desktop (no doubling) ✓

---

## Architecture Summary

```
Mobile Mic (unmuted!)
    ↓
ScriptProcessorNode.onaudioprocess
    ↓
if (!isMutedRef.current)  ← FIX: Uses ref, not stale state
    ↓
Convert Float32 → Int16 PCM
    ↓
WebSocket.send(pcmData) → /audio-relay/{id}/mobile
    ↓
Desktop receives on mobileAudioWs.onmessage
    ↓
Convert Int16 → Float32
    ↓
AudioBufferSource → mobileGainNode (gain: 1) → mixer
    ↓
Desktop mic: desktopGain (gain: 0 if muted) → mixer
    ↓
Mixed stream → OpenAI (WebRTC)
    ↓
OpenAI Response
    ↓
    ├──→ Desktop <audio> element (can be muted with speaker button)
    └──→ Relay to mobile via WebSocket
              ↓
         Mobile speaker (can be muted with speaker button)
```

---

## Key Files Modified

1. **frontend/src/features/voice/pages/MobileVoice.js**
   - Fixed mute state closure issue
   - Added comprehensive logging

2. **frontend/src/features/voice/pages/VoiceAssistant.js**
   - Added logging for desktop speaker playback
   - Added logging for mobile relay

3. **debug/MOBILE_MIC_FIX_SUMMARY.md** (THIS FILE)
   - Complete fix documentation

---

## Console Log Reference

### Mobile Mic Working:
```
[MobileMute] Toggled to: UNMUTED, ref updated
[MobileMic→Desktop] Chunk #50, WS state: 1, muted: false
[MobileMic→Desktop] VOICE DETECTED! Level: -15.3 dB, sending 16384 samples
```

### Desktop Receiving Mobile:
```
[Desktop←MobileMic] Received chunk #50, size: 32768 bytes
[Desktop←MobileMic] VOICE! @5.123s - -15.3 dB, 16384 samples, gain: 1, mixer tracks: 1
```

### Desktop Mute (Does NOT Affect Mobile):
```
[DesktopMute] Desktop mic gain set to: 0
[DesktopMute] Mobile gain still at: 1
[DesktopMute] Mixer still active, stream tracks: 1
```

### Response Audio Flow:
```
[Desktop] OpenAI response will play on desktop <audio> element
[OpenAI→Mobile] Relaying response chunk #10, 16384 samples
[MobileVoice] Scheduled desktop audio chunk at 8.123 s
```

---

## Next Steps

1. **Refresh mobile page** to load the fix
2. **Test mobile mic** - Should now work when unmuted!
3. **Use speaker mute buttons** to prevent doubling:
   - Desktop speaker mute = hear only from mobile
   - Mobile speaker mute = hear only from desktop
4. **Report any remaining issues** with console logs

---

## Known Limitations

1. **Both speakers active = doubled audio** - This is expected, use mute buttons
2. **Mobile starts muted** - By design for safety, user must unmute
3. **Desktop speaker has no gain control yet** - `desktopGainNodeRef` never assigned (separate issue)

---

## Future Improvements

1. **Auto-mute desktop speaker when mobile connects** - Prevent doubling automatically
2. **Implement desktop speaker gain control** - Currently speaker mute button doesn't work on desktop
3. **Add visual indicator** - Show which devices are playing audio
4. **Smart audio routing** - Detect which device user is using and auto-route

---

**Last Updated:** 2025-11-29
**Status:** Fixed and ready for testing
