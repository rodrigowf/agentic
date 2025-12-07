# Operational Context Guide

**CRITICAL: Claude instances operate in TWO distinct contexts with different behaviors.**

## Quick Context Detection

```bash
# Run this first to identify your environment
hostname && pwd
```

## Two Operational Contexts

### 1. Local Development (VS Code Claude Code Extension)
- **Hostname:** `rodrigo-laptop` or similar
- **Working directory:** `/home/rodrigo/agentic`
- **Access:** Direct file system, local Git, can run servers
- **URLs:**
  - Backend: `http://localhost:8000`
  - Frontend: `http://localhost:3000`

### 2. Jetson Production (Voice Assistant)
- **Hostname:** `jetson`
- **Working directory:** `/home/rodrigo/agentic`
- **Access:** Via SSH or voice assistant context
- **URLs:**
  - Backend: `https://192.168.0.200:8000`
  - Frontend: `https://192.168.0.200/agentic/`

## ⚠️ CRITICAL: Node.js Environment Differences

### Local Development (uses NVM)

**DO NOT use system node/npm commands!** Always use the full nvm path:

```bash
# Correct (always use these)
~/.nvm/versions/node/v22.21.1/bin/node script.js
~/.nvm/versions/node/v22.21.1/bin/npm start
~/.nvm/versions/node/v22.21.1/bin/npm install
~/.nvm/versions/node/v22.21.1/bin/npm run build

# Wrong (never use these)
node script.js
npm start
/usr/bin/node script.js
```

**Available nvm versions:** v16.20.2, v20.19.4, v22.19.0, v22.21.1

### Jetson Production (uses Conda)

**The Jetson uses Miniconda, NOT nvm!** Set the PATH to use the conda environment:

```bash
# Option 1: Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic
npm run build

# Option 2: Export PATH directly (for non-interactive SSH)
export PATH=/home/rodrigo/miniconda3/envs/agentic/bin:$PATH
npm run build

# Option 3: Use full path
~/miniconda3/envs/agentic/bin/npm run build
```

**Conda environment versions:**
- Python: 3.11.13
- Node.js: 20.17.0
- npm: 10.8.2

**Reason:** The systemd backend service uses the conda PATH. Frontend builds must use the same environment for consistency.

## Local Development Behavior

**You are:** A developer assistant with full system access

**Your role:**
- Direct code modification and refactoring
- Running tests and debugging
- Git operations (commit, push, branch management)
- Installing dependencies
- Starting/stopping development servers
- Taking screenshots of localhost
- Database migrations and schema changes
- Documentation updates

**Key Operations:**
```bash
# Start backend
cd /home/rodrigo/agentic/backend
source venv/bin/activate
uvicorn main:app --reload

# Start frontend
cd /home/rodrigo/agentic/frontend
~/.nvm/versions/node/v22.21.1/bin/npm start

# Run tests
cd /home/rodrigo/agentic/backend
pytest tests/ -v

# Take screenshots
~/.nvm/versions/node/v22.21.1/bin/node /home/rodrigo/agentic/debug/screenshot.js http://localhost:3000/voice

# Build frontend
cd /home/rodrigo/agentic/frontend
~/.nvm/versions/node/v22.21.1/bin/npm run build
```

**Don't:**
- SSH to Jetson (you're already local)
- Use production URLs (192.168.0.200)
- Restart systemd services (no services running locally)

## Jetson Production Behavior

**You are:** Part of the voice assistant system, operating through nested agents or SSH

**Your role:**
- Answering questions about the production system
- Monitoring production services
- Guiding remote deployments
- Analyzing production logs
- Responding to voice commands
- Coordinating with other agents (Memory, Database, Engineer, etc.)

**Key Operations:**
```bash
# SSH to Jetson (from laptop)
ssh rodrigo@192.168.0.200

# Check production services (on Jetson)
sudo systemctl status agentic-backend
sudo systemctl status mongodb

# Deploy frontend update (on Jetson via non-interactive SSH)
export PATH=/home/rodrigo/miniconda3/envs/agentic/bin:$PATH
cd ~/agentic/frontend
npm install  # if new dependencies added
npm run build
sudo kill -HUP $(cat ~/nginx.pid)

# Restart backend (on Jetson)
sudo systemctl restart agentic-backend

# View production logs (on Jetson)
sudo journalctl -u agentic-backend -f
tail -f ~/logs/nginx-error.log
```

**Special Voice Assistant Behavior:**
- **Narrate concisely** - Voice users can't see detailed logs
- **Use tools** - Delegate to send_to_nested, send_to_claude_code
- **Wait for completion** - Check for [RUN_FINISHED] events
- **Summarize results** - Provide high-level status updates

**Don't:**
- Start development servers (use systemd services)
- Use localhost URLs (use 192.168.0.200)
- Make direct code edits (delegate to Claude Code)
- Provide verbose output (voice context is limited)

## Context-Aware Decision Matrix

| Scenario | Local Dev (VS Code) | Production (Jetson) |
|----------|---------------------|---------------------|
| **Fix this bug** | Edit files directly, run tests, commit | Delegate to Claude Code via voice tool |
| **Deploy changes** | SSH to Jetson, build, restart | Build, restart services (if on Jetson) |
| **Show me logs** | Read local log files | SSH to Jetson, journalctl or tail logs |
| **Run the backend** | `uvicorn main:app --reload` | `sudo systemctl restart agentic-backend` |
| **Take screenshot** | Screenshot localhost:3000 | Screenshot 192.168.0.200 (via browser) |
| **What's in memory?** | Query ChromaDB directly | Use Memory agent tools |
| **Backend not running** | Start with uvicorn | Check systemd: `systemctl status agentic-backend` |
| **Frontend not loading** | Check npm start, React errors | Check nginx, build artifacts |
| **Database error** | Start MongoDB: `sudo systemctl start mongodb` | Same + check memory usage |
| **Permission denied** | Check file permissions, venv activated | Check systemd user, sudo if needed |

## Claude Code Integration

**When you ARE Claude Code (running in VS Code):**
- Full permission mode (user approval required unless bypassed)
- Direct file system access
- Can run any tools (Bash, Edit, Read, etc.)
- Should follow normal development workflow

**When you're CALLING Claude Code (via voice assistant):**
- Use `send_to_claude_code` tool with text instructions
- Claude Code runs with `bypassPermissions` mode
- Events streamed back via WebSocket
- Narrate significant milestones to user
- Wait for [CODE RESULT] events
