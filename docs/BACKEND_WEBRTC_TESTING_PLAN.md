# Backend WebRTC Testing & Debugging Plan

**Date:** 2025-12-02
**Status:** Audio not flowing from frontend → backend → OpenAI
**Goal:** Systematically debug and fix WebRTC audio pipeline

---

## Current Status

### What Works ✅

- Backend WebRTC session creation endpoint (`POST /api/realtime/session`)
- Frontend connects to backend and establishes WebRTC peer connection
- Backend connects to OpenAI Realtime API successfully
- Event persistence infrastructure in place (`on_event_callback`)
- Frontend modular voice page renders correctly

### What Doesn't Work ❌

- Audio not flowing from frontend microphone → backend → OpenAI
- OpenAI cannot "hear" the user speaking
- User speaks but gets no response
- Events recording had 422 error (fixed by disabling frontend recording)

---

## Root Cause Analysis

### Audio Flow Issue

**Problem:**
- Frontend sends audio via WebRTC **audio tracks** (`pc.addTrack(track, stream)`)
- Backend `FrontendAudioHandler` was listening for **data channel** messages
- These are incompatible communication methods

**Fix Applied:**
- Updated `FrontendAudioHandler.handle_sdp_offer()` to use `@pc.on("track")`
- Added `_receive_audio(track)` method to process audio frames
- Status: **Needs testing to verify**

### Audio Format Mismatch (Suspected)

**Potential Issue:**
- Frontend sends: Browser audio (typically 48kHz, possibly stereo)
- OpenAI expects: 24kHz, mono, PCM16
- May need audio resampling/conversion in backend

**Evidence Needed:**
- Check aiortc AudioFrame format in logs
- Verify sample rate and channels in received audio

---

## Testing Plan

### Phase 1: Backend → OpenAI Isolation Test

**Goal:** Verify backend can send audio to OpenAI without frontend

**Test Script:** `backend/tests/test_backend_openai_audio.py`

```python
"""
Test backend OpenAI WebRTC connection in isolation
No frontend required - sends simulated audio
"""
import asyncio
import numpy as np
import os
from api.openai_webrtc_client import OpenAIWebRTCClient

async def test_backend_to_openai():
    """Send simulated audio to OpenAI and verify events"""

    print("=== Phase 1: Backend → OpenAI Test ===")

    received_events = []
    received_audio = []

    # Callbacks to track what we receive
    def on_audio(audio_data):
        received_audio.append(len(audio_data))
        print(f"✓ Received {len(audio_data)} bytes from OpenAI")

    def on_event(event):
        event_type = event.get('type')
        received_events.append(event_type)
        print(f"✓ Event: {event_type}")

    # 1. Create OpenAI client
    print("\n1. Creating OpenAI client...")
    client = OpenAIWebRTCClient(
        api_key=os.getenv("OPENAI_API_KEY"),
        on_audio_callback=on_audio,
        on_event_callback=on_event
    )

    # 2. Connect to OpenAI
    print("2. Connecting to OpenAI...")
    await client.connect()
    print("✓ Connected")

    # 3. Send simulated audio (24kHz, mono, PCM16)
    print("3. Sending 5 seconds of simulated audio (1kHz tone)...")
    sample_rate = 24000
    duration_sec = 5
    frequency = 1000  # 1kHz test tone

    for i in range(50):  # 50 chunks of 100ms each = 5 seconds
        # Generate 100ms of 1kHz sine wave
        t = np.linspace(i * 0.1, (i + 1) * 0.1, 2400, endpoint=False)
        audio = (np.sin(2 * np.pi * frequency * t) * 10000).astype(np.int16)

        await client.send_audio(audio.tobytes())
        await asyncio.sleep(0.1)

        if i % 10 == 0:
            print(f"  {i * 100}ms sent...")

    print("✓ Audio sent")

    # 4. Wait for OpenAI response
    print("4. Waiting for OpenAI response...")
    await asyncio.sleep(5)

    # 5. Results
    print("\n=== RESULTS ===")
    print(f"Events received: {len(received_events)}")
    for evt in received_events[:10]:  # Show first 10
        print(f"  - {evt}")

    print(f"Audio chunks received: {len(received_audio)}")

    # Check critical events
    has_session_created = 'session.created' in received_events
    has_audio_buffer = any('audio_buffer' in e for e in received_events)
    has_response = any('response' in e for e in received_events)

    print(f"\n✓ Session created: {has_session_created}")
    print(f"✓ Audio buffer events: {has_audio_buffer}")
    print(f"✓ Response events: {has_response}")

    return has_session_created and has_audio_buffer

if __name__ == "__main__":
    asyncio.run(test_backend_to_openai())
```

**Expected Output:**
```
=== Phase 1: Backend → OpenAI Test ===
1. Creating OpenAI client...
2. Connecting to OpenAI...
✓ Connected
✓ Event: session.created
✓ Event: session.updated
3. Sending 5 seconds of simulated audio (1kHz tone)...
  0ms sent...
  1000ms sent...
  ...
✓ Audio sent
✓ Event: input_audio_buffer.speech_started
✓ Event: input_audio_buffer.committed
✓ Event: response.created
✓ Received 4800 bytes from OpenAI
...

=== RESULTS ===
Events received: 15
  - session.created
  - session.updated
  - input_audio_buffer.speech_started
  ...
✓ Session created: True
✓ Audio buffer events: True
✓ Response events: True
```

**Run Command:**
```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
python3 tests/test_backend_openai_audio.py
```

---

### Phase 2: Frontend → Backend Audio Reception Test

**Goal:** Test WebRTC audio reception from simulated frontend to backend

**Test Script:** `debug/test-frontend-webrtc.js` (Node.js with wrtc)

```javascript
/**
 * Simulates frontend WebRTC connection to backend
 * Uses node-webrtc library to create peer connection
 */
const wrtc = require('wrtc');
const fetch = require('node-fetch');

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function createFakeAudioTrack() {
  /**
   * Creates a fake audio track that sends 1kHz tone
   * This simulates the frontend microphone
   */
  const sampleRate = 48000;  // Browser default
  const frequency = 1000;

  const source = new wrtc.nonstandard.RTCAudioSource();
  const track = source.createTrack();

  let sampleIndex = 0;
  const samplesPerFrame = 480;  // 10ms at 48kHz

  // Send audio every 10ms
  setInterval(() => {
    const samples = new Int16Array(samplesPerFrame);
    for (let i = 0; i < samplesPerFrame; i++) {
      const t = (sampleIndex + i) / sampleRate;
      samples[i] = Math.sin(2 * Math.PI * frequency * t) * 10000;
    }

    source.onData({
      samples: samples,
      sampleRate: sampleRate,
      bitsPerSample: 16,
      channelCount: 1,
      numberOfFrames: samplesPerFrame
    });

    sampleIndex += samplesPerFrame;
  }, 10);

  return track;
}

async function testFrontendToBackend() {
  console.log('=== Phase 2: Frontend → Backend Audio Test ===\n');

  // 1. Create conversation
  console.log('1. Creating conversation...');
  const conv = await fetch('http://localhost:8000/api/realtime/conversations', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name: 'Frontend Audio Test'})
  }).then(r => r.json());

  console.log(`✓ Conversation: ${conv.id}\n`);

  // 2. Create backend session
  console.log('2. Creating backend session...');
  const session = await fetch('http://localhost:8000/api/realtime/session', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      conversation_id: conv.id,
      voice: 'alloy',
      agent_name: 'MainConversation',
      system_prompt: ''
    })
  }).then(r => r.json());

  console.log(`✓ Backend session: ${session.session_id}\n`);

  // 3. Create peer connection with fake audio
  console.log('3. Creating WebRTC peer connection...');
  const pc = new wrtc.RTCPeerConnection({
    iceServers: [{urls: 'stun:stun.l.google.com:19302'}]
  });

  // Generate and add fake audio track
  const audioTrack = createFakeAudioTrack();
  pc.addTrack(audioTrack);
  console.log('✓ Added audio track\n');

  // 4. Wait for ICE gathering
  const waitForIceGathering = () => new Promise(resolve => {
    if (pc.iceGatheringState === 'complete') return resolve();
    pc.addEventListener('icegatheringstatechange', () => {
      if (pc.iceGatheringState === 'complete') resolve();
    });
  });

  // 5. Create offer and set local description
  console.log('4. Creating SDP offer...');
  const offer = await pc.createOffer({offerToReceiveAudio: true});
  await pc.setLocalDescription(offer);
  await waitForIceGathering();
  console.log('✓ SDP offer created\n');

  // 6. Exchange SDP with backend
  console.log('5. Exchanging SDP with backend...');
  const answer = await fetch(`http://localhost:8000/api/realtime/sdp/${session.session_id}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/sdp'},
    body: pc.localDescription.sdp
  }).then(r => r.text());

  await pc.setRemoteDescription({type: 'answer', sdp: answer});
  console.log('✓ WebRTC connected\n');

  // 7. Wait and monitor
  console.log('6. Sending audio for 10 seconds...');
  console.log('   Watch backend logs for:');
  console.log('   - "Received audio track from frontend: audio"');
  console.log('   - Audio forwarding to OpenAI');
  console.log('');

  await sleep(10000);

  console.log('✓ Test complete');
  console.log('\n=== Check backend logs at /tmp/backend.log ===');

  process.exit(0);
}

testFrontendToBackend().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
```

**Setup:**
```bash
cd /home/rodrigo/agentic/debug
npm install wrtc node-fetch@2
```

**Run Command:**
```bash
cd /home/rodrigo/agentic/debug
node test-frontend-webrtc.js
```

**Expected Backend Logs:**
```
INFO: Connecting to OpenAI Realtime API (model: gpt-4o-realtime-preview-2024-12-17)
INFO: Successfully connected to OpenAI
INFO: Created session <id> for conversation <id>
INFO: Handling SDP offer for session <id>
INFO: Received audio track from frontend: audio  ← CRITICAL
INFO: SDP answer created
INFO: Frontend connected to session <id>
```

---

### Phase 3: Full Browser Integration Test

**Goal:** Test complete flow with real browser

**Test Script:** `debug/test-webrtc-e2e.js`

```javascript
/**
 * Full end-to-end test with real browser via Puppeteer
 * Tests: Browser → Backend → OpenAI → Backend → Browser
 */
const puppeteer = require('puppeteer');
const fs = require('fs');

async function testFullFlow() {
  console.log('=== Phase 3: Full Browser E2E Test ===\n');

  const browser = await puppeteer.launch({
    headless: false,  // Show browser
    args: [
      '--use-fake-ui-for-media-stream',  // Auto-grant mic permission
      '--use-fake-device-for-media-stream',  // Use fake audio
      '--no-sandbox'
    ]
  });

  const page = await browser.newPage();

  // Capture console logs
  const consoleLogs = [];
  page.on('console', msg => {
    const text = msg.text();
    consoleLogs.push(text);
    console.log(`[BROWSER] ${text}`);
  });

  // 1. Navigate to modular voice page
  console.log('1. Navigating to voice page...');
  await page.goto('http://localhost:3000/agentic/voice-modular/');
  await page.waitForTimeout(2000);

  // 2. Create a test conversation
  console.log('2. Creating test conversation...');
  const convResp = await page.evaluate(async () => {
    const resp = await fetch('/api/realtime/conversations', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name: 'E2E Test'})
    });
    return resp.json();
  });

  console.log(`✓ Conversation: ${convResp.id}`);

  // Navigate to conversation
  await page.goto(`http://localhost:3000/agentic/voice-modular/${convResp.id}`);
  await page.waitForTimeout(2000);

  // 3. Click play button
  console.log('3. Starting voice session...');
  await page.click('button[aria-label="Play"]');
  await page.waitForTimeout(3000);

  // 4. Check for success indicators
  console.log('4. Checking session status...');
  const hasBackendLog = consoleLogs.some(log => log.includes('[BackendWebRTC] Created backend session'));
  const hasWebRTCEstablished = consoleLogs.some(log => log.includes('[BackendWebRTC] WebRTC connection established'));
  const hasError = consoleLogs.some(log => log.toLowerCase().includes('error'));

  console.log(`\n=== RESULTS ===`);
  console.log(`✓ Backend session created: ${hasBackendLog}`);
  console.log(`✓ WebRTC established: ${hasWebRTCEstablished}`);
  console.log(`✓ No errors: ${!hasError}`);

  // 5. Take screenshot
  await page.screenshot({path: '/tmp/voice-e2e-test.png', fullPage: true});
  console.log('✓ Screenshot saved: /tmp/voice-e2e-test.png');

  // 6. Save console logs
  fs.writeFileSync('/tmp/voice-e2e-console.txt', consoleLogs.join('\n'));
  console.log('✓ Console logs saved: /tmp/voice-e2e-console.txt');

  // Keep browser open for manual inspection
  console.log('\n=== Browser kept open for inspection ===');
  console.log('Press Ctrl+C to close');

  // Don't close automatically
  await new Promise(() => {});
}

testFullFlow().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
```

**Setup:**
```bash
cd /home/rodrigo/agentic/debug
npm install puppeteer
```

**Run Command:**
```bash
cd /home/rodrigo/agentic/debug
node test-webrtc-e2e.js
```

---

## Debugging Checklist

### Backend Logs to Monitor

**Start backend with accessible logs:**
```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
uvicorn main:app --reload --log-level debug 2>&1 | tee /tmp/backend.log
```

**In another terminal, watch logs:**
```bash
tail -f /tmp/backend.log | grep -E "WebRTC|audio|track|OpenAI|session|Event:"
```

### Critical Log Messages

**Must See (✓ = Working):**
1. ✓ `"Created session <id> for conversation <conv_id>"`
2. ✓ `"Successfully connected to OpenAI"`
3. ✓ `"Frontend connected to session <id>"`
4. ⚠️ `"Received audio track from frontend: audio"` ← **CRITICAL - Not seeing this means audio not received**
5. ⚠️ `"Error receiving audio from frontend: <error>"` ← Shows what's wrong
6. ⚠️ `"Event: session.created"` ← Event callback working
7. ⚠️ `"Event: input_audio_buffer.speech_started"` ← OpenAI detected speech

### Frontend Console Messages

**Key indicators in browser console:**
1. ✅ `"[BackendWebRTC] Desktop microphone acquired"`
2. ✅ `"[BackendWebRTC] Created backend session: <id>"`
3. ✅ `"[BackendWebRTC] WebRTC connection established"`
4. ⚠️ `"[Event] controller:session_started"` ← Events flowing
5. ❌ Any errors or 422 responses

### Database Event Verification

**Check if events are being persisted:**
```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
python3 << 'EOF'
from utils.voice_conversation_store import store

# Replace with your conversation ID
conv_id = "your-conversation-id-here"

events = store.list_events(conv_id, limit=100)
print(f"Total events: {len(events)}")

for e in events[:20]:  # Show first 20
    print(f"{e['timestamp'][:19]} | {e['source']:10} | {e['type']}")
EOF
```

**Expected output if working:**
```
Total events: 45
2025-12-02T21:16:00 | voice      | session.created
2025-12-02T21:16:00 | voice      | session.updated
2025-12-02T21:16:03 | voice      | input_audio_buffer.speech_started
2025-12-02T21:16:04 | voice      | response.created
...
```

---

## Common Issues & Solutions

### Issue 1: Audio Track Not Received

**Symptoms:**
- Backend never logs `"Received audio track from frontend"`
- OpenAI doesn't respond to voice

**Debug:**
```python
# In frontend_audio_handler.py, add more logging
@self.pc.on("track")
def on_track(track):
    logger.info(f"!!! TRACK RECEIVED: {track.kind} !!!")  # Make it obvious
    logger.info(f"Track state: {track.readyState}")
    ...
```

**Possible causes:**
- SDP negotiation issue (offer/answer mismatch)
- ICE connection not established
- Track not added on frontend

**Fix:**
- Log full SDP offer/answer
- Check `pc.connectionState` and `pc.iceConnectionState`
- Verify `pc.addTrack()` is called on frontend

### Issue 2: Audio Format Mismatch

**Symptoms:**
- Track is received
- `_receive_audio()` is called
- But OpenAI doesn't respond or errors

**Debug:**
```python
async def _receive_audio(self, track):
    try:
        while True:
            frame = await track.recv()
            logger.info(f"Frame: {frame.sample_rate}Hz, {frame.samples.shape}, {frame.format}")
            # Check format details
    ...
```

**Possible causes:**
- Browser sends 48kHz, OpenAI expects 24kHz
- Stereo vs mono mismatch
- Wrong encoding (OpenAI needs PCM16)

**Fix:**
- Add resampling with `scipy.signal.resample`
- Convert stereo to mono: `audio_mono = audio_stereo.mean(axis=1)`
- Ensure int16 format

### Issue 3: Events Not Persisted

**Symptoms:**
- Session runs but database has no events
- `on_event_callback` not called

**Debug:**
```python
# In realtime_voice_webrtc.py, add logging to callback
def on_event_callback(event: dict):
    event_type = event.get("type", "unknown")
    logger.info(f"!!! EVENT CALLBACK: {event_type} !!!")
    try:
        conversation_store.append_event(...)
        logger.info(f"!!! EVENT SAVED !!!")
    except Exception as e:
        logger.error(f"!!! EVENT SAVE FAILED: {e} !!!")
```

**Possible causes:**
- OpenAI client not receiving events
- Data channel not established
- Callback not wired correctly

**Fix:**
- Verify data channel `onmessage` fires
- Check `_handle_openai_event()` is called
- Ensure callback is passed to `OpenAIWebRTCClient`

### Issue 4: No Audio Playback

**Symptoms:**
- Everything works but user can't hear OpenAI
- Events show responses but no audio

**Debug:**
- Check `pc.ontrack` fires on frontend
- Verify `audioRef.current.srcObject` is set
- Check browser audio isn't muted

**Fix:**
- Add audio element visibility (remove `display: none` temporarily)
- Check `audioRef.current.play()` is called
- Verify backend sends audio via track (not data channel)

---

## Quick Debug Commands

### Check Backend Status
```bash
# Is backend running?
ps aux | grep uvicorn

# What ports are open?
ss -tlnp | grep :8000

# Recent backend logs
tail -100 /tmp/backend.log

# Watch logs live
tail -f /tmp/backend.log | grep --line-buffered -E "ERROR|WARNING|audio|track"
```

### Test Backend Endpoints
```bash
# Health check
curl http://localhost:8000/

# List conversations
curl http://localhost:8000/api/realtime/conversations

# Create test conversation
curl -X POST http://localhost:8000/api/realtime/conversations \
  -H "Content-Type: application/json" \
  -d '{"name":"Debug Test"}'

# Create backend session
curl -X POST http://localhost:8000/api/realtime/session \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id":"test-123",
    "voice":"alloy",
    "agent_name":"MainConversation",
    "system_prompt":""
  }'
```

### Frontend Debug
```bash
# Take screenshot
node /home/rodrigo/agentic/debug/screenshot.js \
  "http://localhost:3000/agentic/voice-modular/<conversation_id>" \
  /tmp/voice-debug.png \
  3000
```

---

## Files Modified This Session

### Backend Files

**Event Persistence:**
- `backend/api/realtime_voice_webrtc.py` - Added conversation_store, on_event_callback
- `backend/api/openai_webrtc_client.py` - Added on_event_callback parameter and calling

**Audio Handling:**
- `backend/api/frontend_audio_handler.py` - Changed from data channel to audio tracks
  - Added `@pc.on("track")` handler
  - Added `_receive_audio(track)` method
  - Removed data channel message handling for audio

### Frontend Files

**Backend WebRTC Migration:**
- `frontend/src/features/voice/pages/VoiceAssistantModular.js`
  - Removed direct OpenAI connection code
  - Added backend WebRTC session creation
  - Disabled frontend event recording (backend handles it)
  - Added `backendSessionIdRef` for cleanup

**Event Filtering:**
- `frontend/src/features/voice/components/TeamInsightsPanel.js` - Filter `source === 'nested'`
- `frontend/src/features/voice/components/ClaudeCodePanel.js` - Filter `source === 'claude_code'`

**Unused (created but not integrated):**
- `frontend/src/features/voice/hooks/useBackendWebRTC.js` - Created but not used yet

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Browser)                        │
│                                                                  │
│  Microphone → AudioContext → mixedStream                        │
│                                   ↓                              │
│               RTCPeerConnection.addTrack(audioTrack)            │
│                                   ↓                              │
│                    WebRTC Audio Track →                         │
└──────────────────────────────────┼──────────────────────────────┘
                                   │
                                   │ WebRTC (Audio Track)
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND (Python)                         │
│                                                                  │
│  FrontendAudioHandler                                           │
│    ├─ RTCPeerConnection                                         │
│    ├─ @pc.on("track") → on_track(track)                        │
│    └─ _receive_audio(track)                                     │
│          ├─ frame = await track.recv()                          │
│          ├─ audio_bytes = frame.to_ndarray().tobytes()         │
│          └─ on_audio_callback(audio_bytes)                      │
│                    ↓                                             │
│         handle_frontend_audio(session_id, audio_data)          │
│                    ↓                                             │
│  OpenAIWebRTCClient                                             │
│    ├─ RTCPeerConnection → OpenAI                               │
│    ├─ AudioTrack.send(audio_data)                              │
│    ├─ DataChannel.onmessage → _handle_openai_event()          │
│    └─ on_event_callback(event)                                 │
│                    ↓                                             │
│         conversation_store.append_event()                       │
│                    ↓                                             │
│           SQLite: conversation_events                           │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   │ WebRTC
                                   ↓
┌─────────────────────────────────────────────────────────────────┐
│                   OpenAI Realtime API                           │
│                                                                  │
│  gpt-4o-realtime-preview-2024-12-17                            │
│  Voice: alloy                                                   │
│  Input: 24kHz PCM16 mono                                       │
│  Output: 24kHz PCM16 mono                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Next Steps for Follow-Up Conversation

1. **Start backend with accessible logs**
   ```bash
   cd /home/rodrigo/agentic/backend
   source venv/bin/activate
   uvicorn main:app --reload --log-level debug 2>&1 | tee /tmp/backend.log
   ```

2. **Run Phase 1 test** - Backend → OpenAI isolation
   ```bash
   python3 tests/test_backend_openai_audio.py
   ```

3. **Analyze Phase 1 results**
   - Did events arrive?
   - Did OpenAI respond to simulated audio?
   - Any errors in logs?

4. **If Phase 1 passes, run Phase 2** - Frontend → Backend
   ```bash
   cd /home/rodrigo/agentic/debug
   node test-frontend-webrtc.js
   ```

5. **Check critical log:** `"Received audio track from frontend"`
   - If YES: Audio track reception works, check format conversion
   - If NO: SDP negotiation or track handling broken

6. **If Phase 2 passes, run Phase 3** - Full browser E2E
   ```bash
   node test-webrtc-e2e.js
   ```

7. **Fix identified issues** based on test results

8. **Verify event persistence** in database

9. **Test with real voice** in browser

---

## Success Criteria

✅ **Phase 1 passes:** Backend can send/receive from OpenAI
✅ **Phase 2 passes:** Backend receives frontend audio track
✅ **Phase 3 passes:** Full browser flow works
✅ **Events persisted:** Database shows voice events
✅ **User can speak:** OpenAI responds to voice
✅ **User can hear:** OpenAI audio plays back

---

## Additional Resources

**WebRTC Debugging:**
- Chrome: `chrome://webrtc-internals`
- Check peer connection stats, ICE candidates, track stats

**aiortc Documentation:**
- https://aiortc.readthedocs.io/
- Check AudioFrame format, MediaStreamTrack usage

**OpenAI Realtime API:**
- https://platform.openai.com/docs/guides/realtime
- Audio requirements: 24kHz, PCM16, mono

**Useful Python Snippets:**
```python
# Check audio frame details
logger.info(f"Frame: rate={frame.sample_rate}, samples={frame.samples.shape}, format={frame.format}")

# Resample audio
from scipy import signal
audio_resampled = signal.resample(audio_48k, int(len(audio_48k) * 24000 / 48000))

# Convert stereo to mono
audio_mono = audio_stereo.mean(axis=1) if audio_stereo.ndim > 1 else audio_stereo
```

---

**Document saved:** 2025-12-02
**Ready for next debugging session!**
