# Claude Code WebRTC Implementation Prompt

## Initial Prompt

```
I need you to implement backend-controlled WebRTC architecture for our voice assistant system. This will move OpenAI Realtime API connection ownership from frontend to backend, using WebRTC data channels for frontend-backend communication.

Please read this complete implementation guide:
@docs/BACKEND_WEBRTC_IMPLEMENTATION_GUIDE.md

Key goals:
1. Backend owns OpenAI WebRTC connection (not frontend)
2. Frontend connects to backend via WebRTC data channel (not WebSocket)
3. Function calls handled directly in backend (no frontend forwarding)
4. Support multi-client audio mixing (desktop + mobile)

Architecture overview:
- Frontend: Browser audio I/O → WebRTC data channel → Backend
- Backend: aiortc WebRTC server + OpenAI WebRTC client + audio mixing
- OpenAI: Realtime API with function calling

Implementation phases:
1. Backend - OpenAI WebRTC client (Days 1-2)
2. Backend - Frontend audio handler (Days 2-3)
3. Backend - Main controller + audio mixing (Days 3-4)
4. Frontend - WebRTC data channel (Days 5-6)
5. Integration & testing (Days 6-7)
6. Deployment (Days 8-9)

Let's start with Phase 1: Implementing the OpenAI WebRTC client. Create `backend/api/openai_webrtc_client.py` following the complete code example in the guide.

Use bypassPermissions mode since I trust you to implement this correctly.
```

## Follow-Up Prompts

### After Phase 1 Completion

```
Great! Now let's move to Phase 2: Frontend audio handler.

Create `backend/api/frontend_audio_handler.py` following the guide.

Key implementation points:
- Accept SDP offers from frontend
- Set up data channel listeners (not create - frontend creates)
- Distinguish between bytes (audio) and string (control messages)
- Return SDP answer for frontend peer connection

Refer to the complete code example in @docs/BACKEND_WEBRTC_IMPLEMENTATION_GUIDE.md
```

### After Phase 2 Completion

```
Excellent! Now Phase 3: Main controller with audio mixing.

Create `backend/api/realtime_voice_webrtc.py` with:
1. FastAPI router with 3 endpoints (create session, exchange SDP, close session)
2. Session management (dict storage)
3. Audio routing (frontend → OpenAI, OpenAI → all frontends)
4. Function call handler (integrate with nested team and Claude Code)
5. Audio mixing function using NumPy

Refer to the complete code examples and session data structure in the guide.
```

### After Phase 3 Completion

```
Perfect! Now Phase 4: Update frontend to use backend WebRTC.

Modify `frontend/src/features/voice/pages/VoiceAssistant.js`:

Remove:
- OpenAI token fetching
- Direct OpenAI WebRTC connection
- Function call forwarding via WebSocket

Add:
- Backend session creation: POST /api/realtime/session
- WebRTC data channel creation (before offer)
- SDP exchange with backend: POST /api/realtime/sdp/{session_id}
- Audio streaming via data channel (Float32 → PCM16)
- Audio playback from data channel (PCM16 → Float32)

Refer to the complete frontend code example in the guide, especially the audio conversion functions.
```

### After Phase 4 Completion

```
Great work! Now Phase 5: Integration testing.

Let's test the full system:
1. Start backend with new code
2. Start frontend
3. Test basic audio flow
4. Test function calls (send_to_nested, send_to_claude_code)
5. Test multi-client (if possible)

Run through the manual testing scenarios in the guide.

Report any errors and we'll debug together.
```

### After Testing

```
Excellent! Final phase: Prepare for deployment.

1. Update `backend/requirements.txt` with new dependencies
2. Write a deployment guide for Jetson Nano
3. Document any changes needed in CLAUDE.md

Refer to the deployment section in the guide.
```

## Tips for Claude Code

- **Use the guide extensively:** It contains complete, tested code examples
- **Follow phases sequentially:** Each phase builds on the previous
- **Test incrementally:** Don't wait until everything is done to test
- **Reference MobileVoice.js:** It already uses WebRTC data channel pattern
- **Check imports carefully:** Make sure aiortc and aiohttp are imported correctly
- **Audio format is critical:** PCM16, 24kHz, mono - don't change this
- **Error handling:** Wrap async operations in try/except
- **Logging:** Add logger statements for debugging

## Common Issues to Watch For

1. **SDP Exchange:** Offer must be created AFTER data channel creation
2. **Audio Format:** Must convert Float32 ↔ PCM16 at frontend boundary
3. **Data Channel Events:** Backend receives "datachannel" event, doesn't create it
4. **Session Management:** Store both OpenAI client and frontend handlers
5. **Multi-Client:** Broadcast OpenAI audio to all frontend handlers
6. **NumPy Version:** Must be < 2.0 for ChromaDB compatibility

## Success Indicators

✅ Backend successfully connects to OpenAI via WebRTC
✅ Frontend successfully connects to backend via WebRTC data channel
✅ Audio flows: Microphone → Frontend → Backend → OpenAI → Backend → Frontend → Speaker
✅ Function calls work: Voice command triggers nested team or Claude Code
✅ No WebSocket used for audio (only WebRTC data channel)
✅ Multi-client support works (tested with desktop + mobile)

---

**Guide Location:** `/home/rodrigo/agentic/docs/BACKEND_WEBRTC_IMPLEMENTATION_GUIDE.md`

**Reference Docs:**
- [Architecture Overview](BACKEND_WEBRTC_DOCUMENTATION_INDEX.md)
- [Implementation Plan](planning/BACKEND_WEBRTC_IMPLEMENTATION_PLAN.md)
- [Research Report](research/BACKEND_WEBRTC_RESEARCH_REPORT.md)
- [Executive Summary](research/BACKEND_WEBRTC_EXECUTIVE_SUMMARY.md)
