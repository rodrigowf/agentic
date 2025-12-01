# Voice Assistant Integration Plan

This document captures the full plan and current understanding for integrating an OpenAI Realtime Voice interface as a controller/wrapper around the existing AutoGen agents group conversation.

It serves as a guide for maintainers to navigate the codebase, understand the two live channels involved, the endpoints, and the incremental steps we are applying.


## High-level goals

- Provide a voice interface (browser microphone in, audio out) using OpenAI Realtime (WebRTC) while keeping it separate from the dashboard-managed agents.
- Treat the Voice Assistant as a controller/wrapper, not as a new dashboard agent.
- Maintain two distinct live connections:
  1) Client ↔ OpenAI Realtime (WebRTC): audio and event channel for synthesis and realtime function calling.
  2) Client ↔ Backend agent group run (WebSocket `/api/runs/{agent}`): stream of nested group chat events for UI display and controller logic.
- Forward nested team text responses to the Realtime model immediately so the model and the user stay in sync.


## Current repository structure (relevant parts)

Backend (FastAPI):
- `backend/main.py` – main FastAPI app, tools & agents endpoints, and `/api/runs/{agent_name}` WebSocket.
- `backend/runner.py` – connects WebSocket to AutoGen stream, serializes events, handles model clients.
- `backend/agent_factory.py` – builds agents by type (assistant, looping, code executor, nested team).
- `backend/nested_agent.py` – nested team agent; delegates to sub-agents and can include inner dialog.
- `backend/config_loader.py` – loads tools and agents from disk.
- `backend/realtime_voice.py` – router exposing:
  - `GET /token/openai` to mint short-lived OpenAI Realtime session credentials.
  - `POST /call` convenience proxy to Chat Completions (optional for text/tool calling).
- `backend/voice_controller.py` – optional wrapper class to orchestrate a nested team programmatically (pause/cancel). Not wired to endpoints; useful for future enhancements.

Frontend (React):
- `frontend/src/api.js` – REST base (`/api`) and WebSocket helper for `/api/runs/{agent}`.
- `frontend/src/pages/VoiceAssistant.js` – the Voice Assistant page; creates WebRTC session to OpenAI Realtime.
- `frontend/src/components/RunConsole.js` – reference UI for agent WebSocket streaming.


## Two live connections (clearly separated)

1) OpenAI Realtime (WebRTC)
   - The browser captures microphone audio and sends it to OpenAI.
   - The browser receives synthesized audio and event messages back.
   - Control/data channel is used to send events (e.g., `input_text`, `response.create`, function calls, etc.).

2) Backend Agent Stream (WebSocket `/api/runs/{agent}`)
   - Streams AutoGen nested conversation events (TextMessage, ToolCallRequest/Execution, etc.) to the UI.
   - The client (controller) can forward selected outputs (e.g., agent `TextMessage` content) to the Realtime model to narrate/align with the ongoing voice session.

These two channels do not talk directly to each other on the server; the client mediates.


## Endpoints

- Backend (dashboard):
  - `GET /api/tools` and related endpoints – manage tools.
  - `GET /api/agents` etc. – manage agents.
  - `WS /api/runs/{agent_name}` – run an agent (including nested team) and stream events.

- Backend (realtime voice):
  - `GET /api/realtime/token/openai` – returns `{ id, client_secret, expires_at, media_addr }` for the client to establish a Realtime WebRTC session.
  - `POST /api/realtime/call` – convenience proxy to OpenAI chat completions; optional.


## WebRTC (browser) flow with OpenAI Realtime

1) Client calls `GET /api/realtime/token/openai?model=gpt-4o-realtime-preview-2025-06-03&voice=onyx`.
2) Creates an `RTCPeerConnection`, adds microphone tracks.
3) Creates a data channel (label like `oai-events`) to send/receive JSON events.
4) Creates an SDP offer and sets it as the local description.
5) POSTs the SDP offer to OpenAI Realtime endpoint:
   - URL: `https://${media_addr}/v1/realtime?session_id=${id}`
   - Headers: `Authorization: Bearer ${client_secret}`, `Content-Type: application/sdp`
   - Body: `offer.sdp`
6) Sets the returned SDP answer as remote description.
7) On `pc.ontrack`, play the remote audio in an `<audio autoPlay>` element.

Sending text to be spoken by the model:
- Send on the data channel:
  - `{ "type": "input_text", "text": "..." }`
  - `{ "type": "response.create" }`


## Controller behavior: forwarding agent outputs to Realtime

- In parallel, open a WebSocket to `/api/runs/MainConversation` and send an initial `{ type: "run", data: "" }` message. If empty, the backend runner falls back to the agent config’s default `prompt.user`.
- For every streamed event:
  - Display all events for transparency.
  - When the event is a `TextMessage` (i.e., `type` equals `"textmessage"` in the WS payload), immediately forward `data.content` to the Realtime data channel as `input_text` plus `response.create` so the voice model narrates and stays aligned with agent outputs.
  - Optionally forward tool events as JSON over the data channel for awareness, but do not speak them by default.


## Implementation steps in this change set

1) Wire realtime router into main API
   - Import the router from `backend/realtime_voice.py` and mount it under `/api/realtime`.

2) Update `VoiceAssistant.js`
   - Fetch token from `/api/realtime/token/openai` (using the same base URL as the dashboard API).
   - Switch to the browser-supported WebRTC SDP exchange (no custom headers on WebSocket): POST offer SDP to OpenAI with `Authorization: Bearer ${client_secret}` and set the returned answer.
   - Create data channel (label `oai-events`) and add mic tracks.
   - Add `pc.ontrack` to play remote audio.
   - Open `/api/runs/MainConversation` WebSocket in parallel, send initial `run` message, and forward every `TextMessage` to the Realtime data channel.
   - Keep a simple input to send ad-hoc text to the Realtime model (`input_text` + `response.create`).

3) Leave `voice_controller.py` as a future server-side orchestrator (pause/cancel) if later needed to programmatically control nested runs.


## How to navigate the code

- Backend entry and routing:
  - `backend/main.py`: app setup, CORS, endpoints. Now also includes the realtime router under `/api/realtime`.
  - `backend/realtime_voice.py`: standalone router for Realtime token/call. Keep logic isolated.

- Agent execution path:
  - `backend/main.py` → `@app.websocket("/api/runs/{agent}")` → `backend/runner.py:run_agent_ws()`
  - `backend/runner.py` uses `agent_factory.create_agent_from_config()` to instantiate agents.
  - `backend/nested_agent.py` builds the nested team and streams events.

- Tools and agents persistence:
  - `backend/config_loader.py` loads `agents/*.json` and `tools/*.py`.
  - `backend/schemas.py` defines `AgentConfig`, `ToolInfo`, etc.

- Frontend:
  - `frontend/src/api.js` builds REST + WS base URLs and provides `runAgent(name)`.
  - `frontend/src/pages/VoiceAssistant.js` drives both connections (OpenAI Realtime and backend WS) and mediates between them.
  - `frontend/src/components/RunConsole.js` is a good reference for handling `/api/runs/*` messages.


## Environment and running locally

- Required env vars: `OPENAI_API_KEY` (and optionally `OPENAI_ORG`).
- Backend: `uvicorn backend.main:app --reload` (port 8000).
- Frontend: `npm start` (port 3000). The frontend uses `REACT_APP_API_URL` and `REACT_APP_WS_URL` fallbacks to `http://localhost:8000/api` and `ws://localhost:8000`.


## Future enhancements / TODOs

- Add client controls to pause/cancel the nested conversation (e.g., via a small control endpoint or extending the WS protocol).
- Fine-grained control over which inner dialog is spoken vs. only displayed.
- Tool result summarization before speaking.
- UI signals for Realtime connection state and TTS mute/unmute.
- Server-side `voice_controller.py` endpoints if we later need server-driven orchestration.


## Risks and notes

- Browsers cannot set custom headers on WebSocket constructors; the SDP POST flow is required for Realtime in browsers.
- The client secret returned by `/api/realtime/token/openai` is short-lived by design; the client must initiate the WebRTC connection promptly.
- Ensure your agent config `MainConversation.json` exists and contains either a suitable `prompt.user` or be prepared to send a task explicitly.
- Be mindful of quota/latency when speaking every `TextMessage` from the nested team.
