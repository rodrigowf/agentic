# Desktop Speaker Mute Button Fix

## Issue

The desktop speaker mute button (volume icon) was not working because `desktopGainNodeRef` was **never assigned** a gain node.

## Root Cause

Previously, the OpenAI response audio was played directly through the `<audio>` element:

```javascript
pc.ontrack = (evt) => {
  audioRef.current.srcObject = evt.streams[0];  // Direct playback, no gain control!
};
```

The `toggleSpeakerMute()` function tried to control a gain node that didn't exist:

```javascript
if (desktopGainNodeRef.current) {  // ← Always null!
  desktopGainNodeRef.current.gain.value = newMutedState ? 0.0 : 1.0;
}
```

## Fix Applied

Created an AudioContext audio chain for desktop speaker playback:

```javascript
pc.ontrack = (evt) => {
  // Create audio context for desktop speaker gain control
  const desktopSpeakerContext = new AudioContext();
  const desktopSpeakerSource = desktopSpeakerContext.createMediaStreamSource(evt.streams[0]);
  const desktopSpeakerGain = desktopSpeakerContext.createGain();

  // Connect: source → gain → destination (speakers)
  desktopSpeakerSource.connect(desktopSpeakerGain);
  desktopSpeakerGain.connect(desktopSpeakerContext.destination);
  desktopSpeakerGain.gain.value = 1.0; // Start unmuted

  // Store gain node ref for speaker mute control
  desktopGainNodeRef.current = desktopSpeakerGain;
};
```

Now the speaker mute button can control the gain:

```javascript
toggleSpeakerMute() {
  desktopGainNodeRef.current.gain.value = muted ? 0.0 : 1.0;  // ← Works now!
}
```

## Architecture

**Before (Broken):**
```
OpenAI Response Stream → <audio> element → Desktop Speakers
                                            (no gain control)
```

**After (Fixed):**
```
OpenAI Response Stream → MediaStreamSource
                              ↓
                         desktopSpeakerGain (gain node, controllable!)
                              ↓
                    AudioContext.destination → Desktop Speakers
```

## Files Modified

1. **frontend/src/features/voice/pages/VoiceAssistant.js**
   - Line 760-772: Created desktop speaker audio chain with gain control
   - Line 770: Assigned `desktopGainNodeRef.current`
   - Line 1391-1394: Added logging for speaker mute toggle

## Testing

1. **Refresh desktop page** to load the fix
2. **Start voice session**
3. **Wait for OpenAI response** - You should see:
   ```
   [Desktop] OpenAI response audio chain created: source → gain → speakers
   ```
4. **Click speaker mute button** (volume icon) - You should see:
   ```
   [DesktopSpeaker] MUTED - gain set to 0
   ```
5. **Verify:** Desktop should be silent, mobile still plays (if connected)
6. **Click speaker unmute** - You should see:
   ```
   [DesktopSpeaker] UNMUTED - gain set to 1
   ```
7. **Verify:** Desktop plays audio again

## Expected Console Output

### Session Start:
```
[Desktop] OpenAI response audio chain created: source → gain → speakers
```

### Speaker Mute:
```
[DesktopSpeaker] MUTED - gain set to 0
```

### Speaker Unmute:
```
[DesktopSpeaker] UNMUTED - gain set to 1
```

### If Clicked Before Session Started:
```
[DesktopSpeaker] Gain node not initialized yet - speaker mute will not work
```

## Use Cases

**Use Case 1: Mobile as Wireless Mic Only**
- Desktop mic: Muted
- Desktop speaker: Muted ← Now works!
- Mobile mic: Unmuted
- Mobile speaker: Unmuted
- **Result:** Speak into mobile, hear response from mobile

**Use Case 2: Desktop Only (Ignore Mobile)**
- Desktop mic: Unmuted
- Desktop speaker: Unmuted
- Mobile mic: Muted
- Mobile speaker: Muted
- **Result:** Speak into desktop, hear response from desktop

**Use Case 3: Both Active (Testing)**
- Desktop mic: Muted
- Desktop speaker: Unmuted
- Mobile mic: Unmuted
- Mobile speaker: Unmuted
- **Result:** Speak into mobile, hear response from BOTH (doubled audio - by design)

## Related Issues

- **Mobile mic mute bug** - Fixed in [MOBILE_MIC_FIX_SUMMARY.md](MOBILE_MIC_FIX_SUMMARY.md)
- **Doubled audio** - Not a bug, use speaker mute buttons as shown above

---

**Last Updated:** 2025-11-29
**Status:** Fixed and ready for testing
