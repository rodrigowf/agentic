# WebRTC Bridge Migration Notes (handoff + full guide)

## What was requested
- Replace the existing voice transport (Pipecat WebSocket / backend WebSocket routing) with the working WebRTC bridge approach from `refs/webrtc-bridge/`.
- Preserve behavior: backend controls OpenAI Realtime connection; browser speaks WebRTC to backend; backend speaks WebRTC to OpenAI.

## Key sources studied
- `refs/webrtc-bridge/PROJECT_CONTEXT.md` and code in `refs/webrtc-bridge/src` (`server.ts`, `openai/openai.realtime.ts`, `webrtc/browser-bridge.ts`, `public/main.js`).
- Existing agentic code: `backend/api/openai_webrtc_client.py`, `backend/api/realtime_voice_webrtc.py`, `backend/utils/voice_conversation_store.py`, `frontend/src/features/voice/pages/VoiceAssistantModular.js`, `frontend/src/api.js`.

## Architecture overview (current)
- Browser ↔ Backend (FastAPI) over WebRTC:
  - Browser captures mic, creates SDP offer, posts to `/api/realtime/webrtc/bridge`.
  - Backend replies with SDP answer and keeps a `RTCPeerConnection` to the browser.
- Backend ↔ OpenAI Realtime over WebRTC:
  - Backend connects to OpenAI first (pre-warms sink/source to avoid initial jitter).
  - Forwards browser audio → OpenAI and OpenAI audio → browser.
- Event persistence:
  - Uses `voice_conversation_store` and `stream_manager` (when mounted) to record/broadcast events (session started/stopped, OpenAI events, function calls).

## Backend implementation
- File: `backend/api/realtime_voice_webrtc.py`
  - `POST /api/realtime/webrtc/bridge` → accepts `{conversation_id, offer, voice?, agent_name?, system_prompt?}`; returns `{session_id, answer}`.
  - `DELETE /api/realtime/webrtc/bridge/{conversation_id}` → stops active bridge for that conversation.
  - Single active bridge per conversation; old bridge closes before new one starts.
  - Connects to OpenAI first, then sets browser remote description, then answers.
  - Audio bridge via aiortc sinks/sources; assistant audio pushed to browser; browser audio pushed to OpenAI.
  - Events recorded via `_append_and_broadcast` (into SQLite + WebSocket stream if available).
- File: `backend/api/openai_webrtc_client.py`
  - Waits for ICE gathering to finish before sending offer.
  - Sends `session.update` (voice, modalities, optional system prompt, server VAD) and optional initial response once data channel opens.
  - Audio callbacks receive raw `AudioFrame`; AudioTrack normalizes PCM timing (Fraction time_base).
  - Helper `wait_for_ice_gathering_complete` exported.
- Tests: `backend/tests/integration/test_backend_webrtc_integration.py` (no network) cover AudioTrack, AudioFrameSourceTrack normalization, and event callback invocation.

## Frontend implementation
- File: `frontend/src/features/voice/pages/VoiceAssistantModular.js`
  - Builds browser `RTCPeerConnection`, posts offer SDP to `/api/realtime/webrtc/bridge`, applies answer.
  - Attaches remote audio to hidden `<audio>` (via `audioRef`); speaker mute toggles element mute.
  - Mic stream from getUserMedia; fallback silent oscillator if no mic (sets `noMicrophoneMode`).
  - Mute toggles mic track enabled; stop cleans up PC, tracks, fallback AudioContext.
  - `sendText` currently warns (no data channel path yet).
- API helpers: `frontend/src/api.js` adds `startVoiceWebRTCBridge` and `stopVoiceWebRTCBridge`.

## End-to-end flow (happy path)
1) Browser calls getUserMedia (or builds silent stream fallback).
2) Browser creates `RTCPeerConnection`, adds mic tracks, generates SDP offer.
3) `POST /api/realtime/webrtc/bridge` with `{conversation_id, offer, voice, agent_name, system_prompt?}`.
4) Backend:
   - Builds OpenAI session first (adds RTCAudioSource/RTCAudioSink, data channel).
   - Configures browser PC with outbound audio track (assistant → browser), sets remote offer, creates/sets local answer, waits for ICE gather complete, returns SDP answer.
   - Forwards browser audio frames to OpenAI; forwards assistant audio frames to browser.
5) Browser applies SDP answer, audio flows.
6) Events (session start/stop, OpenAI events) recorded/broadcast via conversation store/stream.

## Setup / prerequisites
- Backend Python deps must include aiortc + av.
- Env: `OPENAI_API_KEY` required.
- CORS already allows localhost/192.168.* for dev (see `backend/main.py`).

## Usage checklist
- Start backend and frontend.
- Create/select a voice conversation (UI uses conversation id in URL).
- Start session in VoiceAssistantModular:
  - Mic prompt appears; upon approval, offer is posted and bridge is created.
  - Remote audio arrives via hidden audio element.
- Stop session: tears down PC/tracks; optional backend stop via `DELETE /api/realtime/webrtc/bridge/{conversation_id}`.

## Extending / TODOs
- Text channel: ✅ backend now exposes `POST /api/realtime/webrtc/bridge/{conversation_id}/text` (sends `input_text` via Realtime data channel) and `sendText` in `VoiceAssistantModular` calls it. Next: surface pending/failed states in UI if needed.
- Status UI: add connection/ICE state indicators; surface backend errors in UI.
- Routing: ensure `/voice` (or desired path) points to VoiceAssistantModular and hides older WebSocket/Daily variants if deprecated.
- Tool/function calls: currently recorded; if you need to act on them, wire handlers in `BridgeSession.handle_function_call`.
- Mobile: current flow uses WebRTC only; verify permissions/HTTPS constraints for mobile WebRTC.

## Testing
- Unit/integration: `pytest backend/tests/integration/test_backend_webrtc_integration.py` (offline).
- Manual: start app, open VoiceAssistantModular page, start session, speak, verify audio round-trip and conversation stream events.

## Troubleshooting
- No audio from assistant: check browser PC state; ensure OpenAI connection succeeded; verify `OPENAI_API_KEY`.
- Mic denied: fallback silent oscillator engages; `noMicrophoneMode` shows; enable mic for real audio.
- ICE failures: ensure STUN reachable (`stun:stun.l.google.com:19302`); check firewall; inspect console logs.
- SDP errors: confirm backend route path `/api/realtime/webrtc/bridge` and that offer sdp string is passed.
- Missing deps: install aiortc/av; tests will fail without them.

## How to resume quickly
1) Install aiortc/av and run `pytest backend/tests/integration/test_backend_webrtc_integration.py`.
2) Launch backend/front, open VoiceAssistantModular (`/voice` or route using it), start session; confirm audio loop works.
3) Decide on text/tool channel story; implement data channel or REST helper, then wire `sendText`.
4) Add UI status indicators if needed and set `/voice` routing to this page as the primary transport.
