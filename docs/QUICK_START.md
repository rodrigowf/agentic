# Quick Start Guide

Get up and running with the agentic system in 5 minutes.

## Prerequisites

- Python 3.9+
- Node.js 22.x (via nvm)
- MongoDB (for Database agent)
- Git

## 1. Check Your Context

```bash
hostname && pwd
# Expected: rodrigo-laptop or jetson, /home/rodrigo/agentic
```

See [OPERATIONAL_CONTEXT.md](guides/OPERATIONAL_CONTEXT.md) for context-specific instructions.

## 2. Start Backend (Local Development)

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
uvicorn main:app --reload
```

Backend runs on: `http://localhost:8000`

## 3. Start Frontend (Local Development)

```bash
cd /home/rodrigo/agentic/frontend
~/.nvm/versions/node/v22.21.1/bin/npm start
```

Frontend runs on: `http://localhost:3000`

## 4. Access the Application

- **Main UI:** http://localhost:3000/agentic/
- **Agent Dashboard:** http://localhost:3000/agentic/agents
- **Voice Assistant:** http://localhost:3000/agentic/voice
- **Mobile Voice:** http://192.168.x.x:3000/agentic/mobile-voice (from phone)

## 5. Test WebRTC Voice (Interactive)

### Option A: Two Terminal Workflow

**Terminal 1 - Backend:**
```bash
cd /home/rodrigo/agentic
./start-backend.sh
```

**Terminal 2 - Frontend:**
```bash
cd /home/rodrigo/agentic
./start-frontend.sh
```

**Browser:**
1. Open http://localhost:3000/agentic/voice
2. Press F12 (DevTools)
3. Click "Start Session"
4. Speak into microphone

### Option B: Automated Setup

```bash
cd /home/rodrigo/agentic
export OPENAI_API_KEY=sk-proj-...  # If not in .env
./start-webrtc-session.sh
```

See [WEBRTC_QUICK_START.md](../WEBRTC_QUICK_START.md) for complete WebRTC setup.

## Common Commands

```bash
# List available agents
curl http://localhost:8000/api/agents

# List available tools
curl http://localhost:8000/api/tools

# Take screenshot
~/.nvm/versions/node/v22.21.1/bin/node debug/screenshot.js http://localhost:3000/agentic/voice

# Run tests
cd backend && pytest tests/ -v

# Export voice conversations
python3 debug/export_voice_conversations.py
```

## Project Structure

```
/home/rodrigo/agentic/
├── backend/           # Python FastAPI + AutoGen
│   ├── agents/       # Agent JSON configurations
│   ├── tools/        # Custom tool implementations
│   ├── api/          # Voice & Claude Code controllers
│   └── tests/        # Test suite
├── frontend/         # React application
│   └── src/features/ # Voice, Agents, Tools features
├── debug/            # Screenshot & export tools
└── docs/             # Documentation
```

## Next Steps

- **Create an agent:** See [AGENT_DEVELOPMENT_GUIDE.md](guides/AGENT_DEVELOPMENT_GUIDE.md)
- **Create a tool:** See [TOOL_DEVELOPMENT_GUIDE.md](guides/TOOL_DEVELOPMENT_GUIDE.md)
- **Debug issues:** See [DEBUGGING_GUIDE.md](guides/DEBUGGING_GUIDE.md)
- **Deploy to production:** See [JETSON_DEPLOYMENT_GUIDE.md](JETSON_DEPLOYMENT_GUIDE.md)

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python3 --version  # Should be 3.9+

# Reinstall dependencies
cd backend
pip install -r requirements.txt
```

### Frontend won't start
```bash
# Always use nvm node path!
export NODE_PATH=~/.nvm/versions/node/v22.21.1/bin

# Reinstall dependencies
cd frontend
$NODE_PATH/npm install
```

### WebSocket not connecting
```bash
# Verify backend is running
curl http://localhost:8000/api/agents

# Check browser console for errors
# Expected WebSocket URL: ws://localhost:8000
```

## Getting Help

- **Full Documentation:** [CLAUDE.md](../CLAUDE.md)
- **Operational Context:** [OPERATIONAL_CONTEXT.md](guides/OPERATIONAL_CONTEXT.md)
- **WebRTC Testing:** [WEBRTC_INTERACTIVE_TESTING.md](WEBRTC_INTERACTIVE_TESTING.md)
- **Documentation Index:** [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
