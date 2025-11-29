# Quick Deployment Guide

## 🚀 One-Command Install

```bash
./deploy.sh
```

The script will:
- ✅ Install system dependencies (Python, Node.js, nginx)
- ✅ Setup Python virtual environment
- ✅ Install all Python packages
- ✅ Install all npm packages
- ✅ Create required directories
- ✅ Create .env template

## Manual Setup (3 Steps)

### 1. Configure API Keys

```bash
nano backend/.env
```

Add your API keys:
- `OPENAI_API_KEY` - Get from https://platform.openai.com/api-keys
- `ANTHROPIC_API_KEY` - Get from https://console.anthropic.com/settings/keys

### 2. Start Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0
```

Backend will run on: http://localhost:8000

### 3. Start Frontend (new terminal)

```bash
cd frontend
npm start
```

Frontend will run on: http://localhost:3000

## Access the Application

- **Main Dashboard:** http://localhost:3000
- **Agents:** http://localhost:3000/agents
- **Voice Assistant:** http://localhost:3000/voice
- **Mobile Voice:** http://localhost:3000/mobile-voice

## HTTPS Setup (For Mobile Access)

### Quick SSL Certificate

```bash
# Generate self-signed certificate
cd ~/agentic
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/nginx-selfsigned.key \
  -out ssl/nginx-selfsigned.crt \
  -subj "/C=US/ST=State/L=City/O=Org/CN=$(hostname -I | awk '{print $1}')"

# Start nginx
nginx -c ~/agentic/nginx.conf

# Or reload if already running
./reload-nginx.sh
```

### Access from Mobile

Get your computer's IP:
```bash
hostname -I | awk '{print $1}'
# Example: 192.168.0.25
```

On mobile browser:
```
https://192.168.0.25/mobile-voice
```

**Important:** Accept the self-signed certificate warning!

## Troubleshooting

### Backend won't start

```bash
# Check Python version (needs 3.9+)
python3 --version

# Reinstall dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend won't start

```bash
# Check Node version (needs 16+)
node --version

# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Mobile can't connect

```bash
# 1. Make sure nginx is running
ps aux | grep nginx

# 2. Check both desktop AND mobile use HTTPS
# Desktop: https://192.168.0.25/voice
# Mobile:  https://192.168.0.25/mobile-voice

# 3. Monitor connections
tail -f logs/nginx-access.log | grep webrtc-signal
```

## Full Documentation

See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for:
- Complete installation guide
- Production deployment
- Systemd services
- Security hardening
- Monitoring and backups

See [CLAUDE.md](CLAUDE.md) for:
- Development guide
- Creating agents and tools
- Architecture details
- Debugging workflows

## Quick Commands

```bash
# Backend
cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0

# Frontend
cd frontend && npm start

# Nginx (HTTPS)
nginx -c ~/agentic/nginx.conf

# Reload Nginx
./reload-nginx.sh

# Check logs
tail -f logs/nginx-access.log
tail -f /tmp/backend.log

# Monitor WebRTC
grep "registered for signaling" /tmp/backend.log | tail -5
```

## Requirements

**Minimum:**
- Ubuntu 20.04+ / Debian 11+ / macOS
- Python 3.9+
- Node.js 16+
- 4GB RAM
- 10GB disk space

**For mobile access:**
- WiFi network
- Same network for desktop and mobile
- HTTPS (nginx + SSL)

## Support

- 📖 Full docs: `docs/DEPLOYMENT_GUIDE.md`
- 🔧 Dev guide: `CLAUDE.md`
- 🐛 Debug guides: `debug/` directory
- 💬 Issues: Check logs in `logs/` directory

**Last Updated:** 2025-11-29
