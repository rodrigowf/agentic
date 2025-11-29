# Agentic Voice Assistant - Deployment Guide

**Complete installation guide for deploying to a fresh environment**

**Last Updated:** 2025-11-29

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Architecture Overview](#architecture-overview)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [HTTPS Setup (Mobile Access)](#https-setup-mobile-access)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)
9. [Production Considerations](#production-considerations)

---

## System Requirements

### Hardware

**Minimum:**
- CPU: 2 cores
- RAM: 4GB
- Disk: 10GB free space
- Network: WiFi or Ethernet

**Recommended:**
- CPU: 4+ cores
- RAM: 8GB+
- Disk: 20GB+ SSD
- Network: Stable WiFi (for mobile voice)

### Software

**Operating System:**
- Ubuntu 20.04+ (tested)
- Debian 11+
- Other Linux distributions (may require adjustments)
- macOS (with modifications)

**Required:**
- Python 3.9+
- Node.js 16+ and npm
- Git
- nginx (for HTTPS/mobile access)
- Chrome/Chromium (for screenshot tools)

**Optional:**
- Android Debug Bridge (adb) - for mobile debugging
- Docker (alternative deployment method)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  User Devices                        │
│  Desktop Browser        Mobile Browser               │
│  (localhost:3000)      (192.168.x.x:3000)           │
└──────────┬──────────────────┬────────────────────────┘
           │                  │
     ┌─────▼──────────────────▼─────┐
     │   Nginx Reverse Proxy         │  (HTTPS - port 443)
     │   - Frontend proxy            │
     │   - Backend API proxy         │
     │   - WebSocket proxy           │
     └─────┬──────────────────┬──────┘
           │                  │
     ┌─────▼──────┐    ┌─────▼──────────┐
     │  React      │    │  FastAPI       │
     │  Frontend   │    │  Backend       │
     │  (port 3000)│    │  (port 8000)   │
     └─────────────┘    └─────┬──────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
         ┌───────▼────────┐    ┌──────────▼─────────┐
         │  OpenAI API    │    │  SQLite Database   │
         │  - GPT models  │    │  - Conversations   │
         │  - Realtime    │    │  - Events          │
         └────────────────┘    └────────────────────┘
```

---

## Installation Steps

### Step 1: Install System Dependencies

```bash
# Update package lists
sudo apt update

# Install Python and development tools
sudo apt install -y python3 python3-pip python3-venv

# Install Node.js and npm (via NodeSource)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install nginx
sudo apt install -y nginx

# Install Git
sudo apt install -y git

# Install Chromium (for screenshot tools)
sudo apt install -y chromium-browser

# Verify installations
python3 --version  # Should be 3.9+
node --version     # Should be 16+
npm --version
nginx -v
git --version
```

### Step 2: Clone Repository

```bash
# Clone the repository
cd ~
git clone <repository-url> agentic
cd agentic

# Or if you already have the code, skip to next step
```

### Step 3: Backend Setup

```bash
cd ~/agentic/backend

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; import autogen_core; print('Backend dependencies OK')"
```

### Step 4: Configure Environment Variables

```bash
cd ~/agentic/backend

# Create .env file
cat > .env << 'EOF'
# API Keys (REQUIRED)
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional API Keys
GOOGLE_API_KEY=your-google-api-key-here

# Database (optional - defaults to backend/voice_conversations.db)
VOICE_CONVERSATION_DB_PATH=voice_conversations.db

# Logging
LOG_LEVEL=INFO

# ChromaDB (for memory)
CHROMA_PERSIST_DIRECTORY=./chroma_db
EOF

# Edit the file and add your actual API keys
nano .env
# Or use your preferred editor: vim, code, etc.
```

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys
- Google AI: https://makersuite.google.com/app/apikey

### Step 5: Frontend Setup

```bash
cd ~/agentic/frontend

# Install Node dependencies
npm install

# Verify installation
npm list react react-dom @mui/material
```

### Step 6: Initialize Database

```bash
cd ~/agentic/backend

# The database will be created automatically on first run
# But you can test the connection:
python3 -c "from utils.voice_conversation_store import ConversationStore; store = ConversationStore(); print('Database OK')"
```

### Step 7: Setup Workspace Directories

```bash
cd ~/agentic

# Create required directories
mkdir -p backend/workspace
mkdir -p backend/chroma_db
mkdir -p logs
mkdir -p debug/screenshots
mkdir -p debug/db_exports
mkdir -p ssl  # For HTTPS certificates

# Set permissions
chmod 755 backend/workspace
chmod 755 logs
chmod 755 debug/screenshots
```

---

## Configuration

### Backend Configuration

**Agent Configuration:**

Agents are defined in `backend/agents/*.json`. Default agents are already configured.

To create a new agent:
```bash
cd ~/agentic/backend/agents

# Copy an existing agent as template
cp MainConversation.json MyAgent.json

# Edit the configuration
nano MyAgent.json
```

See `CLAUDE.md` for agent configuration details.

### Frontend Configuration

**API URL Configuration:**

The frontend uses automatic URL detection (`frontend/src/utils/urlBuilder.js`).

No configuration needed for development. For production, optionally set:
```bash
# frontend/.env (optional)
REACT_APP_BACKEND_URL=https://your-domain.com
```

---

## Running the Application

### Development Mode (Local)

**Terminal 1 - Backend:**
```bash
cd ~/agentic/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Backend running at: http://localhost:8000
# API docs at: http://localhost:8000/docs
```

**Terminal 2 - Frontend:**
```bash
cd ~/agentic/frontend
npm start

# Frontend running at: http://localhost:3000
# Automatically opens in browser
```

**Access the Application:**
- Main dashboard: http://localhost:3000
- Agents: http://localhost:3000/agents
- Voice assistant: http://localhost:3000/voice
- Mobile voice: http://localhost:3000/mobile-voice

### Production Mode (Background Services)

**Backend as systemd service:**

```bash
# Create service file
sudo nano /etc/systemd/system/agentic-backend.service
```

```ini
[Unit]
Description=Agentic Voice Assistant Backend
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/agentic/backend
Environment="PATH=/home/your-username/agentic/backend/venv/bin"
ExecStart=/home/your-username/agentic/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable agentic-backend
sudo systemctl start agentic-backend

# Check status
sudo systemctl status agentic-backend

# View logs
sudo journalctl -u agentic-backend -f
```

**Frontend with PM2:**

```bash
# Install PM2 globally
sudo npm install -g pm2

# Build frontend for production
cd ~/agentic/frontend
npm run build

# Serve with PM2
pm2 serve build 3000 --name agentic-frontend --spa

# Save PM2 configuration
pm2 save
pm2 startup  # Follow instructions to enable on boot
```

---

## HTTPS Setup (Mobile Access)

For accessing from mobile devices over HTTPS, you need nginx with SSL certificates.

### Option 1: Self-Signed Certificate (Development)

```bash
cd ~/agentic

# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/nginx-selfsigned.key \
  -out ssl/nginx-selfsigned.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=192.168.0.25"

# Replace 192.168.0.25 with your actual IP address
```

### Option 2: Let's Encrypt (Production)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (requires domain name)
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

### Configure Nginx

```bash
# Stop any existing nginx
sudo systemctl stop nginx
sudo pkill nginx

# Use the custom nginx configuration
cd ~/agentic

# The nginx.conf is already configured
# Just update your IP address if needed
nano nginx.conf
# Update ssl_certificate paths if using different location

# Start nginx with custom config
nginx -c ~/agentic/nginx.conf

# Or create PID file first:
touch ~/agentic/nginx.pid
nginx -c ~/agentic/nginx.conf
```

**Nginx Configuration Checklist:**

The included `nginx.conf` already has:
- ✅ HTTPS on port 443
- ✅ Frontend proxy (React app)
- ✅ Backend API proxy
- ✅ WebSocket support
- ✅ WebRTC signaling endpoint (`/api/realtime/webrtc-signal/`)
- ✅ Cache disabled for development

**Reload Nginx After Changes:**
```bash
./reload-nginx.sh
# Or manually:
sudo kill -HUP $(cat ~/agentic/nginx.pid)
```

### Access via HTTPS

**Get your IP address:**
```bash
hostname -I | awk '{print $1}'
# Example output: 192.168.0.25
```

**Access from desktop:**
```
https://192.168.0.25/voice
```

**Access from mobile:**
```
https://192.168.0.25/mobile-voice
```

**Important:** Accept the self-signed certificate warning on both devices.

---

## Verification

### Backend Verification

```bash
# Check backend is running
curl http://localhost:8000/api/agents
# Should return JSON list of agents

# Check API documentation
curl http://localhost:8000/docs
# Should return HTML (Swagger UI)

# Check health
ps aux | grep uvicorn
```

### Frontend Verification

```bash
# Check frontend is running
curl http://localhost:3000
# Should return HTML

# Check build (if production)
ls -la ~/agentic/frontend/build/
```

### Nginx Verification

```bash
# Check nginx is running
ps aux | grep nginx

# Test configuration
nginx -t -c ~/agentic/nginx.conf

# Check HTTPS access
curl -k https://192.168.0.25/api/agents
# -k flag ignores self-signed cert warning
```

### Complete System Check

```bash
# Run all checks
cd ~/agentic

# Backend
curl http://localhost:8000/api/agents && echo "✅ Backend OK" || echo "❌ Backend FAIL"

# Frontend
curl http://localhost:3000 > /dev/null 2>&1 && echo "✅ Frontend OK" || echo "❌ Frontend FAIL"

# Nginx HTTPS
curl -k https://localhost/api/agents > /dev/null 2>&1 && echo "✅ Nginx OK" || echo "❌ Nginx FAIL"

# Database
test -f backend/voice_conversations.db && echo "✅ Database exists" || echo "❌ Database missing"
```

---

## Troubleshooting

### Backend Won't Start

**Error: "ModuleNotFoundError"**
```bash
cd ~/agentic/backend
source venv/bin/activate
pip install -r requirements.txt
```

**Error: "Port 8000 already in use"**
```bash
# Find and kill process
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

**Error: "OpenAI API key not found"**
```bash
# Check .env file
cat backend/.env | grep OPENAI_API_KEY

# Make sure it's set
nano backend/.env
```

### Frontend Won't Start

**Error: "npm ERR! code ENOENT"**
```bash
cd ~/agentic/frontend
rm -rf node_modules package-lock.json
npm install
```

**Error: "Port 3000 already in use"**
```bash
# Kill process on port 3000
lsof -i :3000
kill -9 <PID>

# Or set different port
PORT=3001 npm start
```

### Nginx Issues

**Error: "nginx: [emerg] bind() to 0.0.0.0:443 failed"**
```bash
# Check what's using port 443
sudo lsof -i :443

# Stop conflicting service
sudo systemctl stop apache2  # If Apache is running
```

**Error: "Permission denied" on nginx.pid**
```bash
# Make sure nginx runs as root or fix permissions
sudo nginx -c ~/agentic/nginx.conf

# Or change PID file location in nginx.conf
```

### Mobile Voice Not Working

**Problem: Mobile can't connect**
```bash
# 1. Check both desktop and mobile use HTTPS
# Desktop: https://192.168.0.25/voice
# Mobile: https://192.168.0.25/mobile-voice

# 2. Check WebRTC signaling
tail -f ~/agentic/logs/nginx-access.log | grep webrtc-signal

# 3. Check peer registration
grep "registered for signaling" /tmp/backend.log | tail -5
```

**Problem: Echo on mobile**
```bash
# Make sure you have latest code (echo fix applied)
cd ~/agentic
git pull

# Check VoiceAssistant.js line 1319 - should NOT send desktop mic
grep -n "ONLY send OpenAI response" frontend/src/features/voice/pages/VoiceAssistant.js
```

---

## Production Considerations

### Security

**1. Use Strong SSL Certificates:**
- Replace self-signed certificates with Let's Encrypt or commercial certificates
- Update nginx.conf with proper certificate paths

**2. Firewall Configuration:**
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

**3. API Key Protection:**
```bash
# Secure .env file
chmod 600 ~/agentic/backend/.env

# Never commit .env to git
echo ".env" >> ~/agentic/backend/.gitignore
```

**4. Restrict Backend Access:**
```bash
# Edit nginx.conf to only expose through nginx
# Backend should only listen on localhost
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Performance

**1. Enable Nginx Caching (Production):**

Edit `nginx.conf` and remove cache-disabling directives in production.

**2. Use Production Build:**
```bash
cd ~/agentic/frontend
npm run build
# Serve build/ directory with nginx or PM2
```

**3. Database Optimization:**
```bash
# Regular cleanup of old conversations
cd ~/agentic
python3 debug/export_voice_conversations.py
# Archive and delete old data
```

### Monitoring

**1. Setup Log Rotation:**
```bash
sudo nano /etc/logrotate.d/agentic
```

```
/home/your-username/agentic/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

**2. Monitor Services:**
```bash
# Backend
sudo systemctl status agentic-backend

# Nginx
sudo systemctl status nginx

# PM2 (if using)
pm2 status
pm2 logs agentic-frontend
```

### Backup

**1. Database Backup:**
```bash
# Daily backup script
cat > ~/agentic/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
cp ~/agentic/backend/voice_conversations.db ~/agentic/backups/db_$DATE.db
find ~/agentic/backups -name "db_*.db" -mtime +30 -delete
EOF

chmod +x ~/agentic/backup.sh

# Add to crontab
crontab -e
# Add line:
# 0 2 * * * /home/your-username/agentic/backup.sh
```

**2. Configuration Backup:**
```bash
# Backup .env and nginx.conf
tar -czf agentic-config-backup.tar.gz \
  ~/agentic/backend/.env \
  ~/agentic/nginx.conf \
  ~/agentic/ssl/
```

---

## Quick Start Script

Create an automated installation script:

```bash
cat > ~/agentic/deploy.sh << 'ENDSCRIPT'
#!/bin/bash
set -e

echo "🚀 Agentic Voice Assistant Deployment"
echo "====================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo "❌ Please run as regular user (not root)"
  exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm nginx git chromium-browser

# Backend setup
echo "🐍 Setting up backend..."
cd ~/agentic/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Frontend setup
echo "⚛️  Setting up frontend..."
cd ~/agentic/frontend
npm install

# Create directories
echo "📁 Creating directories..."
mkdir -p ~/agentic/backend/workspace
mkdir -p ~/agentic/logs
mkdir -p ~/agentic/debug/screenshots
mkdir -p ~/agentic/ssl

# Check for API keys
if [ ! -f ~/agentic/backend/.env ]; then
  echo "⚠️  .env file not found. Creating template..."
  cat > ~/agentic/backend/.env << 'EOF'
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
EOF
  echo "⚠️  Please edit backend/.env and add your API keys"
fi

echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env and add your API keys"
echo "2. Start backend: cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0"
echo "3. Start frontend: cd frontend && npm start"
echo "4. Access at: http://localhost:3000"
ENDSCRIPT

chmod +x ~/agentic/deploy.sh
```

**Run automated deployment:**
```bash
./deploy.sh
```

---

## Summary

**Complete installation takes approximately 15-30 minutes.**

**Minimal setup (development):**
1. Install dependencies (Python, Node.js, nginx)
2. Clone repository
3. Setup backend (venv, pip install)
4. Setup frontend (npm install)
5. Configure .env with API keys
6. Run backend and frontend

**Production setup adds:**
7. SSL certificates (Let's Encrypt or self-signed)
8. Nginx configuration
9. Systemd services
10. Firewall rules
11. Monitoring and backups

**For mobile voice access:**
- Must use HTTPS (nginx + SSL)
- Both desktop and mobile use same domain
- Accept certificate warnings on both devices

**Support:**
- See `CLAUDE.md` for development guide
- See `debug/` for troubleshooting guides
- Check logs: `logs/nginx-*.log`, `/tmp/backend.log`

**Last Updated:** 2025-11-29
