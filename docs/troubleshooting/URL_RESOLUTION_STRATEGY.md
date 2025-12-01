# URL Resolution Strategy

## Problem Analysis

The application needs to work in three different scenarios:

1. **Local HTTP (Development)**: `http://localhost:3000` or `http://192.168.0.25:3000`
   - Frontend: React dev server on port 3000
   - Backend: FastAPI on port 8000
   - No nginx proxy

2. **Remote HTTP (Development)**: `http://192.168.0.25:3000` (from mobile)
   - Frontend: React dev server on port 3000
   - Backend: FastAPI on port 8000
   - No nginx proxy
   - Cross-device access

3. **HTTPS via nginx (Production-like)**: `https://192.168.0.25`
   - Frontend: Proxied through nginx on port 443
   - Backend: Proxied through nginx to port 8000
   - nginx handles SSL termination

## Current Issues

1. **Mixed content errors**: HTTPS page trying to load HTTP resources
2. **Hardcoded localhost**: Doesn't work from mobile devices
3. **Protocol detection bugs**: Wrong protocol selection logic
4. **Inconsistent URL building**: Different files use different logic

## Connection Types

### 1. REST API Calls (HTTP/HTTPS)
- **Files**: `api.js` (Axios instance)
- **Endpoints**: `/api/agents`, `/api/tools`, `/api/realtime/conversations`, etc.

### 2. Agent WebSocket (WS/WSS)
- **Files**: `api.js::runAgent()`, `RunConsole.js`
- **Endpoints**: `/api/runs/{agentName}`

### 3. Voice Conversation Stream WebSocket (WS/WSS)
- **Files**: `api.js::connectVoiceConversationStream()`
- **Endpoints**: `/api/realtime/conversations/{id}/stream`

### 4. Voice Assistant WebSockets (WS/WSS)
- **Files**: `VoiceAssistant.js`
- **Endpoints**:
  - `/api/runs/{agentName}` (nested team)
  - `/api/runs/ClaudeCode` (Claude Code)
  - `/api/realtime/audio-relay/{id}/desktop` (audio relay)

### 5. Mobile Voice WebSocket (WS/WSS)
- **Files**: `MobileVoice.js`
- **Endpoints**: `/api/realtime/audio-relay/{id}/mobile`

### 6. WebRTC Media Endpoints (HTTPS)
- **Files**: `VoiceAssistant.js`, `MobileVoice.js`
- **Endpoints**: `/api/realtime/token/openai`, `/api/realtime/sdp-offer`

## Solution: Centralized URL Builder

Create a single, reliable URL builder that:
1. Detects the environment correctly
2. Returns consistent URLs for all connection types
3. Works across all scenarios

### Detection Logic

```javascript
function detectEnvironment() {
  const protocol = window.location.protocol; // 'http:' or 'https:'
  const hostname = window.location.hostname; // 'localhost' or '192.168.0.25'
  const port = window.location.port; // '3000', '443', or ''

  // Scenario 1: HTTPS via nginx (production-like)
  if (protocol === 'https:') {
    return {
      type: 'nginx-https',
      httpBase: `https://${window.location.host}`,
      wsBase: `wss://${window.location.host}`,
      apiPath: '/api'
    };
  }

  // Scenario 2 & 3: HTTP direct (development)
  return {
    type: 'direct-http',
    httpBase: `http://${hostname}:8000`,
    wsBase: `ws://${hostname}:8000`,
    apiPath: '/api'
  };
}
```

### URL Building Functions

```javascript
// REST API URLs
function getApiUrl(path) {
  const env = detectEnvironment();
  return `${env.httpBase}${env.apiPath}${path}`;
}

// WebSocket URLs
function getWsUrl(path) {
  const env = detectEnvironment();
  return `${env.wsBase}${env.apiPath}${path}`;
}
```

## Implementation Plan

1. **Create centralized URL utility** (`frontend/src/utils/urlBuilder.js`)
   - Export `getApiUrl(path)`
   - Export `getWsUrl(path)`
   - Export `getHttpBase()` (for special cases)

2. **Update api.js**
   - Replace `getBackendURL()` with `getApiUrl()`
   - Replace WebSocket construction with `getWsUrl()`

3. **Update VoiceAssistant.js**
   - Replace `backendBase` logic with utility
   - Replace `wsBase` logic with utility

4. **Update MobileVoice.js**
   - Same as VoiceAssistant.js

5. **Update RunConsole.js**
   - Use `getWsUrl()` for agent connections

6. **Update DebugNetwork.js**
   - Use utility for consistency

## Testing Matrix

| Scenario | URL | REST API | Agent WS | Voice WS | Audio Relay | WebRTC |
|----------|-----|----------|----------|----------|-------------|--------|
| localhost:3000 | http | :8000/api | ws:8000 | ws:8000 | ws:8000 | http:8000 |
| 192.168.0.25:3000 | http | :8000/api | ws:8000 | ws:8000 | ws:8000 | http:8000 |
| https://192.168.0.25 | https | /api | wss:/api | wss:/api | wss:/api | https:/api |

## Expected Results

After implementation:
- ✅ No mixed content errors
- ✅ Works on localhost via HTTP
- ✅ Works on IP via HTTP (mobile development)
- ✅ Works via HTTPS through nginx (production)
- ✅ All WebSocket connections use correct protocol
- ✅ No hardcoded hosts or ports
- ✅ Single source of truth for URL resolution
