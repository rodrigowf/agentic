# CLAUDE.md - Agentic System Guide

**Last Updated:** 2025-12-07
**For:** Future Claude instances working on this codebase

---

## 🚀 Quick Start

New to this project? Start here:

1. **[Quick Start Guide](docs/QUICK_START.md)** - Get running in 5 minutes
2. **[Operational Context](docs/guides/OPERATIONAL_CONTEXT.md)** - Understand your environment (Local Dev vs Production)
3. **[Documentation Index](docs/DOCUMENTATION_INDEX.md)** - Complete documentation map

---

## Table of Contents

0. [Essential Context](#essential-context)
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Development Guides](#development-guides)
4. [System Components](#system-components)
5. [Deployment](#deployment)
6. [Quick Reference](#quick-reference)

---

## Essential Context

### Detect Your Environment First

```bash
hostname && pwd
```

**Two operational contexts exist:**

1. **Local Development (VS Code)** - Direct code editing, localhost URLs
2. **Jetson Production** - Voice assistant, systemd services, HTTPS URLs

**📖 See:** [OPERATIONAL_CONTEXT.md](docs/guides/OPERATIONAL_CONTEXT.md) for complete context guide.

### ⚠️ CRITICAL: Node.js Environment Differences

**Local Development (uses NVM):**
```bash
~/.nvm/versions/node/v22.21.1/bin/npm start
```

**Jetson Production (uses Conda):**
```bash
export PATH=/home/rodrigo/miniconda3/envs/agentic/bin:$PATH
npm run build
```

**Note:** Never use bare `npm` or `node` commands - always use full paths or set PATH first.

---

## Project Overview

An **agentic AI system** with Python backend (FastAPI + AutoGen) and React frontend.

### Key Features

- **Multi-agent coordination** - Nested team agents with orchestration
- **Multimodal vision agents** - Interpret images from tool responses
- **Voice assistant** - OpenAI Realtime API with WebRTC bridge
- **Mobile voice interface** - Smartphone as wireless microphone
- **Claude Code integration** - Live code self-editing
- **Memory management** - ChromaDB + MongoDB storage
- **Screenshot workflows** - Automated UI development

### Tech Stack

**Backend:**
- Python 3.x, FastAPI, AutoGen
- ChromaDB 0.4.24, MongoDB 3.6+, SQLite
- OpenAI API, Anthropic API

**Frontend:**
- React 18, Material-UI
- WebSocket + WebRTC
- Feature-based architecture

---

## Architecture

### Directory Structure

```
/home/rodrigo/agentic/
├── backend/                    # Python FastAPI server
│   ├── main.py                 # FastAPI entry point
│   ├── agents/                 # Agent JSON configurations
│   ├── tools/                  # Custom tool implementations
│   ├── core/                   # Agent execution engine
│   ├── api/                    # Voice & Claude Code controllers
│   ├── config/                 # Configuration & schemas
│   ├── utils/                  # Utility modules
│   └── tests/                  # Test suite
│
├── frontend/                   # React application
│   └── src/features/           # Feature-based organization
│       ├── agents/             # Agent management
│       ├── tools/              # Tool management
│       └── voice/              # Voice assistant
│
├── debug/                      # Screenshot & export tools
├── docs/                       # Documentation
└── CLAUDE.md                   # This file
```

### Data Flow

```
User Input → WebSocket → FastAPI → Agent Factory → Agent Execution
    → Tool Execution → WebSocket Stream → Frontend → UI Display
```

### Important URLs

**Local Development:**
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000/agentic/`

**Production (Jetson):**
- Backend: `https://192.168.0.200/api/`
- Frontend: `https://192.168.0.200/agentic/`

---

## Development Guides

### Agent Development

**Agent Types:**
- `looping` - Single agent with tool loop
- `nested_team` - Multi-agent coordination
- `multimodal_tools_looping` - Vision-capable agent
- `dynamic_init_looping` - Custom initialization logic

**Create New Agent:**
1. Create JSON in `backend/agents/YourAgent.json`
2. Configure tools, LLM, prompts
3. Test via frontend

**📖 Complete Guide:** [Creating New Agents](#creating-new-agents) (see full CLAUDE.md)

### Tool Development

**Tool Structure:**
```python
# tools/my_tool.py
from autogen_core.tools import FunctionTool

def my_tool(param: str) -> str:
    """Tool description for LLM"""
    return f"Result: {param}"

my_tool_func = FunctionTool(
    func=my_tool,
    name="my_tool",
    description="Brief description"
)

tools = [my_tool_func]
```

**📖 Complete Guide:** [Creating New Tools](#creating-new-tools) (see full CLAUDE.md)

### Voice System

**WebRTC Bridge Architecture:**
```
Browser (WebRTC) ↔ Backend (aiortc) ↔ OpenAI Realtime API (WebRTC)
```

**Start Interactive Session:**
```bash
# Terminal 1
./start-backend.sh

# Terminal 2
./start-frontend.sh

# Browser: http://localhost:3000/agentic/voice
```

**📖 Complete Guides:**
- [Voice Quick Start](docs/voice/VOICE_QUICK_START.md) - 1-minute setup
- [Voice Interactive Guide](docs/voice/VOICE_INTERACTIVE_GUIDE.md) - Full walkthrough
- [Voice System Overview](docs/voice/VOICE_SYSTEM_OVERVIEW.md) - Testing guide

### Mobile Voice Interface

**Purpose:** Use smartphone as wireless microphone

**Access:** `http://[YOUR_IP]:3000/agentic/mobile-voice`

**📖 Complete Guide:** [docs/guides/MOBILE_VOICE_GUIDE.md](docs/guides/MOBILE_VOICE_GUIDE.md)

---

## System Components

### Database & Memory

**Two Systems:**
1. **MongoDB** - Structured data (Database agent, 10 tools)
2. **ChromaDB** - Vector memory (Memory agent, 8 tools)

**📖 Complete Setup:** [docs/guides/DATABASE_AND_MEMORY_SETUP.md](docs/guides/DATABASE_AND_MEMORY_SETUP.md)

### Debugging Tools

**Screenshot Automation:**
```bash
~/.nvm/versions/node/v22.21.1/bin/node debug/screenshot.js http://localhost:3000/agentic/voice
```

**Voice Conversation Export:**
```bash
python3 debug/export_voice_conversations.py
```

**📖 Complete Guide:** [Debugging Tools & Workflows](#debugging-tools--workflows) (see full CLAUDE.md)

### Claude Code Integration

**Self-editing capabilities via voice:**
- Voice model calls: `send_to_claude_code({text: "Add feature"})`
- Claude Code executes with `bypassPermissions` mode
- Events stream back via WebSocket

**📖 Complete Guide:** [Claude Code Self-Editor](#claude-code-self-editor) (see full CLAUDE.md)

---

## Deployment

### Jetson Nano Production

**Server:** 192.168.0.200 (ARM64, Ubuntu 18.04.6 LTS)

**Quick Access:**
```bash
# SSH
ssh rodrigo@192.168.0.200

# HTTPS
https://192.168.0.200/agentic/
```

**Environment:** Miniconda3 with `agentic` conda environment (Python 3.11, Node 20.17)

**Common Tasks:**
```bash
# Set PATH for conda environment (required for non-interactive SSH)
export PATH=/home/rodrigo/miniconda3/envs/agentic/bin:$PATH

# Deploy frontend update
cd ~/agentic/frontend
npm install  # if new dependencies
npm run build
sudo kill -HUP $(cat ~/nginx.pid)

# Restart backend
sudo systemctl restart agentic-backend

# View logs
sudo journalctl -u agentic-backend -f
```

**📖 Complete Guide:** [docs/deployment/JETSON_DEPLOYMENT_GUIDE.md](docs/deployment/JETSON_DEPLOYMENT_GUIDE.md)

---

## Quick Reference

### Common Commands

```bash
# Start services (local dev)
cd backend && source venv/bin/activate && uvicorn main:app --reload
cd frontend && ~/.nvm/versions/node/v22.21.1/bin/npm start

# Run tests
cd backend && pytest tests/ -v

# Take screenshot
~/.nvm/versions/node/v22.21.1/bin/node debug/screenshot.js http://localhost:3000/agentic/voice

# Export voice data
python3 debug/export_voice_conversations.py

# List agents/tools
curl http://localhost:8000/api/agents
curl http://localhost:8000/api/tools
```

### WebRTC Voice Commands

```bash
# Test WebRTC (no network)
pytest tests/integration/test_backend_webrtc_integration.py -v

# Check active sessions
curl http://localhost:8000/api/realtime/conversations

# Stop voice bridge
curl -X DELETE http://localhost:8000/api/realtime/webrtc/bridge/{conversation_id}

# Monitor logs
tail -f logs/backend.log | grep -E "(webrtc|openai)"
```

### File Locations

| Purpose | Location |
|---------|----------|
| **Agent configs** | `backend/agents/*.json` |
| **Tool implementations** | `backend/tools/*.py` |
| **Voice controller** | `backend/api/realtime_voice_webrtc.py` |
| **OpenAI WebRTC client** | `backend/api/openai_webrtc_client.py` |
| **Frontend voice** | `frontend/src/features/voice/pages/` |
| **Screenshot tool** | `debug/screenshot.js` |
| **Voice DB exports** | `debug/db_exports/voice_conversations/` |
| **Documentation** | `docs/` |

---

## Best Practices

### Development Workflow

1. **Always Use TodoWrite** - Track multi-step tasks
2. **Read Before Write** - Understand context before changes
3. **Test Changes** - Screenshots for UI, exports for backend
4. **Screenshot Before/After** - Visual verification for UI changes

### UI Development

```bash
# 1. Screenshot before
node debug/screenshot.js http://localhost:3000/agentic/voice before.png

# 2. Make changes

# 3. Wait for hot reload
sleep 3

# 4. Screenshot after
node debug/screenshot.js http://localhost:3000/agentic/voice after.png

# 5. Read and verify
```

### Agent Development

1. Design agent purpose - What specific task?
2. Choose agent type - Looping or nested team?
3. Select tools - What capabilities needed?
4. Write system prompt - Clear instructions + examples
5. Test iteratively - Start simple, add complexity

---

## Troubleshooting

### Backend Issues

```bash
# Port conflict
lsof -i :8000

# Dependencies
cd backend && pip install -r requirements.txt

# MongoDB not running
sudo systemctl start mongodb
```

### Frontend Issues

```bash
# Always use nvm path!
export NODE_PATH=~/.nvm/versions/node/v22.21.1/bin

# Port conflict
lsof -i :3000

# Reinstall dependencies
cd frontend && $NODE_PATH/npm install
```

### WebRTC Issues

```bash
# Check browser console for ICE state
# Expected: new → checking → connected → completed

# Backend logs
tail -f logs/backend.log | grep -i webrtc

# Verify OPENAI_API_KEY
grep OPENAI_API_KEY backend/.env
```

---

## Documentation Index

### Core Documentation
- **[QUICK_START.md](docs/QUICK_START.md)** - Get started in 5 minutes
- **[OPERATIONAL_CONTEXT.md](docs/guides/OPERATIONAL_CONTEXT.md)** - Context-specific behavior
- **[DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md)** - Complete doc map

### Feature Guides
- **[DATABASE_AND_MEMORY_SETUP.md](docs/guides/DATABASE_AND_MEMORY_SETUP.md)** - MongoDB & ChromaDB
- **[MULTIMODAL_AGENT_GUIDE.md](docs/guides/MULTIMODAL_AGENT_GUIDE.md)** - Vision agents
- **[MOBILE_VOICE_GUIDE.md](docs/guides/MOBILE_VOICE_GUIDE.md)** - Smartphone microphone

### Voice System
- **[Voice System Overview](docs/voice/VOICE_SYSTEM_OVERVIEW.md)** - Architecture & integration
- **[Voice Quick Start](docs/voice/VOICE_QUICK_START.md)** - 5-minute setup
- **[Voice Interactive Guide](docs/voice/VOICE_INTERACTIVE_GUIDE.md)** - Complete walkthrough
- **[Voice Commands](docs/voice/VOICE_COMMANDS.md)** - Command reference
- **[Voice Troubleshooting](docs/voice/VOICE_TROUBLESHOOTING.md)** - Debug guide

### Voice Technical Details
- **[Backend Implementation](docs/voice/technical/BACKEND_IMPLEMENTATION.md)** - WebRTC bridge (coming soon)
- **[Frontend Implementation](docs/voice/technical/FRONTEND_IMPLEMENTATION.md)** - React components (coming soon)
- **[Nested Agents Integration](docs/voice/technical/NESTED_AGENTS_INTEGRATION.md)** - Agent orchestration
- **[Audio Fixes Log](docs/voice/technical/AUDIO_FIXES_LOG.md)** - Historical audio issues & fixes

### Deployment
- **[JETSON_DEPLOYMENT_GUIDE.md](docs/JETSON_DEPLOYMENT_GUIDE.md)** - Production server
- **[TV_WEBVIEW_FIX_SUMMARY.md](docs/TV_WEBVIEW_FIX_SUMMARY.md)** - TV compatibility

### Architecture
- **[REFACTORING_SUMMARY.md](docs/architecture/REFACTORING_SUMMARY.md)** - Backend structure
- **[FRONTEND_REFACTORING.md](docs/architecture/FRONTEND_REFACTORING.md)** - Frontend structure

---

## Recent Changes

### Interactive Session Setup (2025-12-04)
- Created helper scripts: `start-backend.sh`, `start-frontend.sh`, `start-webrtc-session.sh`
- Added comprehensive WebRTC testing guides
- Dual logging (console + `/tmp/agentic-logs/`)

### WebRTC Bridge Migration (2025-12-04)
- Migrated from Pipecat to pure WebRTC bridge
- Direct OpenAI Realtime API connection
- Comprehensive unit and integration tests

### Documentation Reorganization (2025-12-04)
- Extracted detailed content to focused guides
- Created QUICK_START.md for immediate setup
- Streamlined CLAUDE.md with references

### NVM Node Path Enforcement (2025-12-04)
- Critical instructions for using full nvm paths
- System node may be outdated/incompatible

### Database & Memory System (2025-12-02)
- MongoDB + ChromaDB fully operational
- Memory banks migrated from git history
- Comprehensive setup documentation

---

**End of CLAUDE.md**

For detailed information on any topic, see the documentation links above.

**Last updated:** 2025-12-04
