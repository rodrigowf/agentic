# Voice System Commands Reference

## Start Services

```bash
# Terminal 1 - Backend
cd /home/rodrigo/agentic && ./start-backend.sh

# Terminal 2 - Frontend
cd /home/rodrigo/agentic && ./start-frontend.sh

# Browser
open http://localhost:3000/agentic/voice
```

## Monitor Logs

```bash
# Backend logs
tail -f /tmp/agentic-logs/backend.log

# Frontend logs
tail -f /tmp/agentic-logs/frontend.log

# Filter backend for WebRTC
tail -f /tmp/agentic-logs/backend.log | grep -E "WebRTC|aiortc"

# Filter for OpenAI events
tail -f /tmp/agentic-logs/backend.log | grep "OpenAI event"

# Filter for audio
tail -f /tmp/agentic-logs/backend.log | grep "audio frame"

# Filter for errors
tail -f /tmp/agentic-logs/backend.log | grep -i error
```

## Check Status

```bash
# Backend health
curl http://localhost:8000/api/agents

# Active conversations
curl http://localhost:8000/api/realtime/conversations

# Conversation events
curl http://localhost:8000/api/realtime/conversations/{id}

# Process status
ps aux | grep -E "(uvicorn|npm start)"

# Port check
lsof -i :8000
lsof -i :3000
```

## Stop Services

```bash
# Graceful stop (Ctrl+C in terminals)

# Force stop
pkill -f uvicorn
pkill -f "npm start"

# Verify stopped
ps aux | grep -E "(uvicorn|npm)" | grep -v grep
```

## Testing

```bash
# Unit tests
cd /home/rodrigo/agentic/backend
source venv/bin/activate
pytest tests/unit/test_openai_webrtc_client.py -v

# Integration tests
pytest tests/integration/test_backend_webrtc_integration.py -v

# All WebRTC tests
pytest tests/ -k "webrtc" -v
```

## Database

```bash
# Export conversations
python3 debug/export_voice_conversations.py

# Query SQLite
sqlite3 backend/voice_conversations.db

# List conversations
sqlite3 backend/voice_conversations.db "SELECT id, name, created_at FROM conversations;"

# Count events
sqlite3 backend/voice_conversations.db "SELECT COUNT(*) FROM events;"

# View JSON exports
ls -lh debug/db_exports/voice_conversations/
cat debug/db_exports/voice_conversations/*.json | jq '.events[] | select(.type == "response.audio_transcript.delta")'
```

## Debugging

```bash
# Check OPENAI_API_KEY
echo $OPENAI_API_KEY
grep OPENAI_API_KEY backend/.env

# Test OpenAI API
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"

# Check network connectivity
ping stun.l.google.com
curl -I http://localhost:8000

# Check firewall
sudo ufw status
sudo iptables -L

# System audio
pactl list sources  # Linux
system_profiler SPAudioDataType  # macOS

# Browser permissions
# Chrome: chrome://settings/content/microphone
# Firefox: about:preferences#privacy
```

## Performance

```bash
# Resource usage
top -p $(pgrep -f uvicorn)
top -p $(pgrep -f node)

# Memory
ps aux | grep -E "(uvicorn|node)" | awk '{print $6}'

# Network bandwidth
iftop -i any -f "port 8000"
nethogs

# Disk usage
du -sh /tmp/agentic-logs
```

## Browser Console

```javascript
// Get WebRTC stats
const stats = await window.peerConnection.getStats();
stats.forEach(report => console.log(report));

// Check ICE state
console.log('ICE:', window.peerConnection.iceConnectionState);
console.log('Connection:', window.peerConnection.connectionState);

// Check data channel
console.log('Data channel:', window.dataChannel?.readyState);

// Send test message
window.dataChannel?.send(JSON.stringify({text: "test"}));
```

## Environment

```bash
# Load environment
source backend/venv/bin/activate
source ~/.nvm/nvm.sh && nvm use default

# Check versions
python --version
node --version
npm --version

# Check dependencies
pip list | grep -E "aiortc|numpy|openai"
npm list react react-dom
```

## Cleanup

```bash
# Stop services
pkill -f uvicorn && pkill -f "npm start"

# Clear logs
rm /tmp/agentic-logs/*.log

# Clear cache
rm -rf frontend/node_modules/.cache
rm -rf backend/__pycache__

# Clear database (WARNING: deletes all conversations)
# rm backend/voice_conversations.db
```

## Documentation

```bash
# View guides
cat VOICE_QUICK_START.md
cat VOICE_INTERACTIVE_GUIDE.md
cat docs/WEBRTC_INTERACTIVE_TESTING.md
cat docs/webrtc-session-flow.txt

# Open in editor
code VOICE_SYSTEM_OVERVIEW.md
code docs/webrtc-bridge-notes.md
```

## Common Workflows

### Quick Test
```bash
# Start backend
./start-backend.sh &
sleep 5

# Start frontend
./start-frontend.sh &
sleep 10

# Open browser
xdg-open http://localhost:3000/agentic/voice
```

### Debug Session
```bash
# Terminal 1
./start-backend.sh | tee /tmp/backend-debug.log

# Terminal 2
./start-frontend.sh | tee /tmp/frontend-debug.log

# Terminal 3
tail -f /tmp/backend-debug.log | grep -i error

# Terminal 4
tail -f /tmp/backend-debug.log | grep "OpenAI event"
```

### Export and Analyze
```bash
# Export conversations
python3 debug/export_voice_conversations.py

# Find errors
jq '.events[] | select(.type == "error" or .type == "Error")' \
  debug/db_exports/voice_conversations/*.json

# Analyze transcript
jq '.events[] | select(.type == "response.audio_transcript.delta") | .data.delta' \
  debug/db_exports/voice_conversations/*.json
```

---

**See also:**
- [VOICE_QUICK_START.md](VOICE_QUICK_START.md) - Quick start guide
- [VOICE_INTERACTIVE_GUIDE.md](VOICE_INTERACTIVE_GUIDE.md) - Full walkthrough
- [docs/WEBRTC_INTERACTIVE_TESTING.md](docs/WEBRTC_INTERACTIVE_TESTING.md) - Testing guide
- [VOICE_SYSTEM_OVERVIEW.md](VOICE_SYSTEM_OVERVIEW.md) - Overview
