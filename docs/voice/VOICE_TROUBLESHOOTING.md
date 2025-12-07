# Voice System Troubleshooting Guide

**Last Updated:** 2025-12-05
**For:** WebRTC Voice Bridge Architecture

---

## Quick Diagnostics

### Is the backend running?
```bash
curl http://localhost:8000/api/agents
```
✅ Should return JSON with agents list
❌ Connection refused → Start backend with `./start-backend.sh`

### Is the frontend running?
```bash
curl http://localhost:3000
```
✅ Should return HTML
❌ Connection refused → Start frontend with `./start-frontend.sh`

### Is OPENAI_API_KEY set?
```bash
grep OPENAI_API_KEY backend/.env
```
✅ Should show: `OPENAI_API_KEY=sk-proj-...`
❌ Empty → Add key to `backend/.env`

---

## Common Issues

### 1. No Microphone Access

**Symptoms:**
- "Microphone permission denied" in browser console
- No green audio visualization bars
- Session starts but no audio sent

**Solutions:**

**Chrome:**
1. Click padlock icon in address bar
2. Click "Site settings"
3. Set Microphone to "Allow"
4. Refresh page

**Firefox:**
1. about:preferences#privacy
2. Scroll to Permissions → Microphone
3. Find localhost:3000 and set to Allow

**Mobile:**
- Requires HTTPS (WebRTC mic access blocked on HTTP)
- Use: `https://192.168.0.200/agentic/voice` (production)
- Or set up SSL certificates for local dev

### 2. No Audio from Assistant

**Symptoms:**
- User speech detected (green bars)
- No response audio (no blue bars)
- Backend logs show connection but no audio

**Diagnosis:**
```bash
# Check if OpenAI connection succeeded
tail -f /tmp/agentic-logs/backend.log | grep "OpenAI"

# Should see:
# ✅ "OpenAI WebRTC client connected"
# ✅ "OpenAI event: response.audio.delta"
```

**Solutions:**

**A) Verify API Key:**
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $(grep OPENAI_API_KEY backend/.env | cut -d'=' -f2)"
```
Should return list of models.

**B) Check Backend Logs for Errors:**
```bash
grep -i error /tmp/agentic-logs/backend.log
```

**C) Restart Session:**
1. Stop voice session in browser
2. Wait 5 seconds
3. Start new session

### 3. Slow Motion / Fast Audio

**Symptoms:**
- Audio plays too slow (robotic/deep voice)
- Audio plays too fast (chipmunk voice)

**Root Cause:**
Sample rate mismatch (see [Audio Fixes Log](technical/AUDIO_FIXES_LOG.md#fix-1-slow-motion-audio-sample-rate-mismatch))

**Diagnosis:**
```bash
# Check sample rates in logs
grep "sample_rate" /tmp/agentic-logs/backend.log | head -20
```

Should see consistent `48000 Hz` throughout.

**Solution:**
If you see mismatches, check:
- `AudioFrameSourceTrack` initialized with 48000 Hz
- OpenAI frames show 48000 Hz
- Browser connection negotiated 48000 Hz

### 4. Echo or Feedback

**Symptoms:**
- Hearing own voice back
- Looping/feedback sounds

**Solutions:**

**A) Use Headphones:**
- Prevents speaker output from reaching microphone

**B) Mute Desktop Speakers:**
- Click speaker icon in voice interface
- Or mute system audio output

**C) Check for Multiple Tabs:**
```bash
# Close duplicate voice assistant tabs
# Only one session per conversation
```

### 5. WebRTC Connection Fails

**Symptoms:**
- "Connecting..." stays forever
- ICE state stuck at "checking"
- Console shows: `ICE state: failed`

**Diagnosis:**
```javascript
// In browser console
console.log('ICE:', window.peerConnection?.iceConnectionState);
console.log('Connection:', window.peerConnection?.connectionState);

// Expected progression:
// new → checking → connected → completed
```

**Solutions:**

**A) Check Firewall:**
```bash
# Linux
sudo ufw status

# Allow port 8000
sudo ufw allow 8000

# macOS
sudo pfctl -s all
```

**B) Test STUN Server:**
```bash
# Install stun-test
npm install -g stun-test

# Test Google STUN
stun-test stun.l.google.com 19302
```

**C) Check Network:**
```bash
# Backend reachable?
curl http://localhost:8000/api/realtime/conversations
```

### 6. No User Transcripts

**Symptoms:**
- Assistant responds to speech
- But no user transcripts in conversation history
- Model seems to lack context

**Diagnosis:**
```bash
# Export conversations
python3 debug/export_voice_conversations.py

# Check for user transcripts
cat debug/db_exports/voice_conversations/*.json | \
  jq '.events[] | select(.type == "conversation.item.input_audio_transcription.completed")'
```

**Solution:**
Ensure `input_audio_transcription` is enabled in OpenAI client:
```python
# backend/api/openai_webrtc_client.py
"input_audio_transcription": {
    "model": "whisper-1"
}
```

See: [Audio Fixes Log - Fix #4](technical/AUDIO_FIXES_LOG.md#fix-4-input-audio-transcription-missing)

### 7. VAD Cuts Off Too Early

**Symptoms:**
- Assistant interrupts mid-sentence
- Have to speak in short bursts
- Natural pauses trigger cutoff

**Solution:**
Adjust VAD settings in `backend/api/openai_webrtc_client.py`:

```python
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,              # Lower = more sensitive
    "prefix_padding_ms": 300,      # Include lead-in
    "silence_duration_ms": 700     # Increase for longer pauses (default: 500)
}
```

See: [Audio Fixes Log - Fix #5](technical/AUDIO_FIXES_LOG.md#fix-5-vad-configuration-improvements)

### 8. Low Audio Levels

**Symptoms:**
- Assistant can barely hear user
- Have to shout to be detected
- VAD doesn't trigger

**Solution:**
Set input gain boost:

```bash
# backend/.env
VOICE_INPUT_GAIN=6.0  # Increase from default 4.0
```

Restart backend to apply.

### 9. Browser Audio Not Reaching Backend

**Symptoms:**
- Microphone visualization works in browser
- No frames logged in backend
- Assistant doesn't respond

**Diagnosis:**
```bash
# Check backend logs for browser audio
tail -f /tmp/agentic-logs/backend.log | grep "Browser Audio"

# Should see:
# ✅ "[Browser Audio] First frame received"
# ✅ "[Browser Audio] Forwarded {N} frames to OpenAI"
```

**Solution:**
See: [Audio Fixes Log - Fix #3](technical/AUDIO_FIXES_LOG.md#fix-3-browser-audio-not-reaching-backend)

### 10. Session Won't Start

**Symptoms:**
- Click "Start Session" → nothing happens
- Or error in console

**Diagnosis:**
```javascript
// Open browser console (F12)
// Look for errors starting with [WebRTC Bridge]
```

**Common Errors:**

**A) "Conversation not found"**
- Create a new conversation first
- Or check conversation_id in URL

**B) "OPENAI_API_KEY not configured"**
- Add key to `backend/.env`
- Restart backend

**C) "Failed to establish bridge"**
- Check backend logs for specific error
- Common: OpenAI API rate limit, invalid key, network issue

---

## Debugging Tools

### Backend Logs
```bash
# Watch all logs
tail -f /tmp/agentic-logs/backend.log

# Filter for WebRTC
tail -f /tmp/agentic-logs/backend.log | grep -E "WebRTC|aiortc"

# Filter for OpenAI events
tail -f /tmp/agentic-logs/backend.log | grep "OpenAI event"

# Filter for audio
tail -f /tmp/agentic-logs/backend.log | grep -E "audio|Audio|sample_rate"

# Filter for errors
tail -f /tmp/agentic-logs/backend.log | grep -i error
```

### Frontend Logs
```bash
# Watch console logs
tail -f /tmp/agentic-logs/frontend.log

# Browser console (F12)
# Look for [WebRTC Bridge] logs
```

### Export Conversations
```bash
# Export all conversations to JSON
python3 debug/export_voice_conversations.py

# Output: debug/db_exports/voice_conversations/*.json

# View latest conversation
ls -lt debug/db_exports/voice_conversations/ | head -2

# Check transcripts
cat debug/db_exports/voice_conversations/conv_*.json | jq '.events[] | select(.type | contains("transcript"))'
```

### WebRTC Stats (Browser Console)
```javascript
// Get peer connection stats
const stats = await window.peerConnection?.getStats();
stats.forEach(report => {
  if (report.type === 'inbound-rtp' && report.mediaType === 'audio') {
    console.log('Inbound Audio:', {
      packetsReceived: report.packetsReceived,
      packetsLost: report.packetsLost,
      jitter: report.jitter
    });
  }
});
```

### Network Capture
```bash
# Capture WebRTC traffic
sudo tcpdump -i any -w /tmp/webrtc.pcap port 8000 or port 19302

# Analyze with Wireshark
wireshark /tmp/webrtc.pcap
```

---

## Environment-Specific Issues

### Mobile (iOS/Android)

**Issue:** Microphone access blocked
**Solution:** Use HTTPS (`https://192.168.0.200/agentic/mobile-voice`)

**Issue:** Audio cutting out
**Solution:** Keep phone awake, close background apps

**Issue:** High latency
**Solution:** Use WiFi instead of cellular

### TV WebView

**Issue:** Poor audio quality
**Solution:** See [TV WebView Fix Summary](../troubleshooting/TV_WEBVIEW_FIX_SUMMARY.md)

### Jetson Nano Production

**Issue:** Service won't start
```bash
# Check service status
sudo systemctl status agentic-backend

# View logs
sudo journalctl -u agentic-backend -f

# Restart
sudo systemctl restart agentic-backend
```

---

## Performance Optimization

### Reduce Latency

**Backend:**
```python
# Reduce frame buffer size (trade stability for latency)
# Not recommended unless latency critical
```

**Network:**
- Use wired connection instead of WiFi
- Close bandwidth-heavy applications
- Test with: `ping localhost` (should be <1ms)

### Improve Audio Quality

**Increase Sample Rate:**
- Already at 48kHz (optimal for WebRTC)
- Don't change unless needed

**Adjust VAD:**
- Fine-tune for your environment
- See [Audio Fixes Log - Fix #5](technical/AUDIO_FIXES_LOG.md#fix-5-vad-configuration-improvements)

---

## Decision Tree

```
Issue?
  ↓
Can't start session?
  ├─ Yes → Check API key, backend status, conversation exists
  └─ No → Session starts but...
      ↓
Microphone not working?
  ├─ Yes → Check browser permissions, green bars, backend logs
  └─ No → Mic works but...
      ↓
No assistant audio?
  ├─ Yes → Check OpenAI connection, API key, blue bars
  └─ No → Assistant audio works but...
      ↓
Audio quality issues?
  ├─ Slow/fast → Sample rate mismatch
  ├─ Echo → Use headphones, mute speakers
  ├─ Cutoff early → Adjust VAD silence_duration_ms
  ├─ Low levels → Increase VOICE_INPUT_GAIN
  └─ Distorted → Check backend logs for errors
      ↓
Connection issues?
  ├─ ICE failed → Firewall, STUN server, network
  ├─ Timeout → Backend not responding
  └─ Drops → Network stability, close other apps
```

---

## Getting Help

### Information to Gather

When reporting issues, include:

1. **Browser console logs:**
   ```
   Right-click → Inspect → Console tab
   Copy all [WebRTC Bridge] logs
   ```

2. **Backend logs:**
   ```bash
   tail -100 /tmp/agentic-logs/backend.log
   ```

3. **Conversation export:**
   ```bash
   python3 debug/export_voice_conversations.py
   # Include the relevant JSON file
   ```

4. **Environment info:**
   ```bash
   # OS, browser version
   uname -a
   # Chrome: chrome://version
   # Firefox: about:support
   ```

5. **WebRTC stats:**
   ```javascript
   // In browser console
   const stats = await window.peerConnection?.getStats();
   console.log(Array.from(stats.values()));
   ```

---

## Related Documentation

- **[Voice System Overview](VOICE_SYSTEM_OVERVIEW.md)** - Architecture
- **[Voice Quick Start](VOICE_QUICK_START.md)** - Setup guide
- **[Voice Commands](VOICE_COMMANDS.md)** - Command reference
- **[Audio Fixes Log](technical/AUDIO_FIXES_LOG.md)** - Historical fixes

---

**Last Updated:** 2025-12-05
**Maintained by:** Agentic System Development Team
