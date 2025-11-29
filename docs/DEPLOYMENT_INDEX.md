# Deployment Documentation Index

**Complete guide to deploying the Agentic Voice Assistant system**

---

## Quick Start

**For impatient people:**
```bash
./deploy.sh
```

Then follow the instructions printed by the script.

---

## Documentation Structure

### 1. [DEPLOYMENT_README.md](../DEPLOYMENT_README.md) - **START HERE**
- One-command install
- Quick 3-step manual setup
- Common troubleshooting
- Quick commands reference

**Time:** 5 minutes to read, 15-30 minutes to deploy

### 2. [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - **COMPREHENSIVE**
- Complete installation guide
- System requirements
- Architecture overview
- Step-by-step installation
- HTTPS/nginx configuration
- Production deployment
- Security hardening
- Monitoring and backups

**Time:** 30 minutes to read, 1-2 hours to fully deploy

### 3. [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - **VERIFICATION**
- Pre-installation checklist
- Installation steps checklist
- Verification steps
- Troubleshooting guide
- Success criteria

**Time:** Use during deployment to track progress

### 4. [../CLAUDE.md](../CLAUDE.md) - **DEVELOPMENT**
- Development guide
- Architecture details
- Creating agents and tools
- Voice assistant system
- Mobile voice interface
- Debugging workflows

**Time:** Reference as needed during development

---

## Deployment Scenarios

### Scenario 1: Local Development (Single Machine)

**Goal:** Run on localhost for testing

**Steps:**
1. Run `./deploy.sh`
2. Edit `backend/.env` with API keys
3. Start backend: `cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0`
4. Start frontend: `cd frontend && npm start`
5. Access: http://localhost:3000

**Docs:** [DEPLOYMENT_README.md](../DEPLOYMENT_README.md)

**Time:** 15-30 minutes

---

### Scenario 2: Local + Mobile (HTTPS)

**Goal:** Use mobile phone as wireless microphone

**Steps:**
1. Complete Scenario 1
2. Generate SSL certificate (see DEPLOYMENT_README.md)
3. Start nginx: `nginx -c ~/agentic/nginx.conf`
4. Desktop: Open `https://YOUR_IP/voice`
5. Mobile: Open `https://YOUR_IP/mobile-voice`

**Docs:** 
- [DEPLOYMENT_README.md](../DEPLOYMENT_README.md) - Quick setup
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - HTTPS section

**Time:** +15 minutes on top of Scenario 1

---

### Scenario 3: Production Server

**Goal:** Deploy as always-running service

**Steps:**
1. Complete Scenario 1
2. Create systemd service for backend
3. Build frontend: `npm run build`
4. Setup PM2: `pm2 serve build 3000`
5. Configure Let's Encrypt SSL
6. Setup firewall
7. Configure monitoring

**Docs:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Production section

**Time:** 2-4 hours

---

## Common Tasks

### Installing on Fresh Ubuntu Server

```bash
# 1. Clone repository
git clone <repo-url> ~/agentic
cd ~/agentic

# 2. Run automated deployment
./deploy.sh

# 3. Configure API keys
nano backend/.env

# 4. Start services
# Terminal 1:
cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0

# Terminal 2:
cd frontend && npm start
```

### Setting Up HTTPS for Mobile

```bash
# 1. Get your IP
hostname -I | awk '{print $1}'

# 2. Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/nginx-selfsigned.key \
  -out ssl/nginx-selfsigned.crt \
  -subj "/C=US/ST=State/L=City/O=Org/CN=$(hostname -I | awk '{print $1}')"

# 3. Start nginx
nginx -c ~/agentic/nginx.conf

# 4. Access from mobile
# https://YOUR_IP/mobile-voice
```

### Updating Deployment

```bash
# 1. Pull latest changes
cd ~/agentic
git pull

# 2. Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 3. Update frontend
cd ../frontend
npm install

# 4. Restart services
# Kill and restart backend/frontend
# OR reload nginx: ./reload-nginx.sh
```

### Troubleshooting

**Quick diagnostic:**
```bash
# Check all services
curl http://localhost:8000/api/agents  # Backend
curl http://localhost:3000             # Frontend
ps aux | grep nginx                    # Nginx
ps aux | grep uvicorn                  # Backend process

# Check logs
tail -f logs/nginx-access.log
tail -f /tmp/backend.log
```

**Mobile not working:**
```bash
# 1. Verify HTTPS on both devices
# Desktop: https://IP/voice
# Mobile:  https://IP/mobile-voice

# 2. Check peer registration
grep "registered for signaling" /tmp/backend.log | tail -5

# 3. Monitor WebRTC
tail -f logs/nginx-access.log | grep webrtc-signal
```

---

## File Structure

```
agentic/
├── deploy.sh                       # Automated deployment script
├── DEPLOYMENT_README.md            # Quick start guide
├── reload-nginx.sh                 # Nginx reload helper
├── nginx.conf                      # Nginx configuration
│
├── docs/
│   ├── DEPLOYMENT_INDEX.md         # This file
│   ├── DEPLOYMENT_GUIDE.md         # Comprehensive guide
│   └── DEPLOYMENT_CHECKLIST.md     # Verification checklist
│
├── backend/
│   ├── .env.example                # Environment variables template
│   ├── requirements.txt            # Python dependencies
│   └── main.py                     # FastAPI application
│
├── frontend/
│   ├── package.json                # Node dependencies
│   └── src/                        # React application
│
├── debug/
│   ├── HTTPS_MOBILE_VOICE_FIX.md
│   ├── MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md
│   └── SESSION_SUMMARY_2025-11-29.md
│
└── CLAUDE.md                       # Development guide
```

---

## Support

### Documentation
- **Quick start:** [DEPLOYMENT_README.md](../DEPLOYMENT_README.md)
- **Full guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Checklist:** [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- **Dev guide:** [../CLAUDE.md](../CLAUDE.md)

### Debugging
- **HTTPS issues:** [../debug/HTTPS_MOBILE_VOICE_FIX.md](../debug/HTTPS_MOBILE_VOICE_FIX.md)
- **Mobile debugging:** [../debug/MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md](../debug/MOBILE_VOICE_HTTPS_DEBUGGING_GUIDE.md)
- **Session notes:** [../debug/SESSION_SUMMARY_2025-11-29.md](../debug/SESSION_SUMMARY_2025-11-29.md)

### Logs
- Backend: `/tmp/backend.log`
- Nginx access: `logs/nginx-access.log`
- Nginx error: `logs/nginx-error.log`

---

## Next Steps After Deployment

1. ✅ Verify installation (use checklist)
2. 📚 Read development guide (CLAUDE.md)
3. 🤖 Create your first agent
4. 🎤 Test voice assistant
5. 📱 Setup mobile voice (HTTPS)
6. 🔒 Harden security (production)
7. 📊 Setup monitoring (production)

**Last Updated:** 2025-11-29
