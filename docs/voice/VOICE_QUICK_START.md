# Voice System - Quick Start

## Start Services (Two Terminals)

**Terminal 1 - Backend:**
```bash
cd /home/rodrigo/agentic
export OPENAI_API_KEY=sk-proj-...
./start-backend.sh
```

**Terminal 2 - Frontend:**
```bash
cd /home/rodrigo/agentic
./start-frontend.sh
```

## Use Voice Interface

1. Open: `http://localhost:3000/agentic/voice`
2. Open DevTools (F12)
3. Click "Start Session"
4. Speak!

## Monitor Logs

```bash
# Backend logs
tail -f /tmp/agentic-logs/backend.log | grep -E "WebRTC|aiortc|OpenAI"

# Frontend logs
tail -f /tmp/agentic-logs/frontend.log

# Browser console
# Look for: [WebRTC Bridge] logs
```

## Stop Services

```bash
# Ctrl+C in both terminals
# Or:
pkill -f uvicorn
pkill -f "npm start"
```

## Troubleshooting

**No microphone?**
- Check browser permissions
- Try different browser (Chrome works best)

**No audio response?**
- Verify `OPENAI_API_KEY` is set
- Check backend logs for errors
- Test: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`

**Connection fails?**
- Check ICE state in browser console
- Should go: `new → checking → connected`
- Check firewall allows port 8000

**Echo/feedback?**
- Use headphones
- Mute desktop speakers

## Full Documentation

See: [VOICE_INTERACTIVE_GUIDE.md](docs/WEBRTC_INTERACTIVE_TESTING.md)
