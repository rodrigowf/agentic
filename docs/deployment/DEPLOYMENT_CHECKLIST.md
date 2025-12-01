# Deployment Checklist

Use this checklist when deploying to a fresh environment.

## Pre-Installation

- [ ] Ubuntu 20.04+ / Debian 11+ / macOS
- [ ] Minimum 4GB RAM, 10GB disk space
- [ ] Internet connection
- [ ] sudo access
- [ ] API keys ready:
  - [ ] OpenAI API key
  - [ ] Anthropic API key (optional)

## System Dependencies

- [ ] Python 3.9+ installed
- [ ] Node.js 16+ installed
- [ ] Git installed
- [ ] Nginx installed (for HTTPS)
- [ ] Chromium/Chrome (for screenshots)

**Quick install:**
```bash
./deploy.sh
```

## Backend Setup

- [ ] Navigate to `backend/` directory
- [ ] Create virtual environment: `python3 -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Install packages: `pip install -r requirements.txt`
- [ ] Create `.env` file
- [ ] Add OpenAI API key to `.env`
- [ ] Add Anthropic API key to `.env`
- [ ] Verify: `python -c "import fastapi; print('OK')"`

## Frontend Setup

- [ ] Navigate to `frontend/` directory
- [ ] Install packages: `npm install`
- [ ] Verify: `npm list react`

## Directory Structure

- [ ] Create `backend/data/workspace/`
- [ ] Create `backend/data/memory/`
- [ ] Create `backend/data/api/`
- [ ] Create `backend/data/database/`
- [ ] Create `backend/voice/configs/`
- [ ] Create `backend/voice/prompts/`
- [ ] Create `logs/`
- [ ] Create `debug/screenshots/`
- [ ] Create `debug/db_exports/`
- [ ] Create `ssl/` (for HTTPS)

## Run Application (Development)

- [ ] Terminal 1: Start backend
  ```bash
  cd backend
  source venv/bin/activate
  uvicorn main:app --reload --host 0.0.0.0
  ```
- [ ] Terminal 2: Start frontend
  ```bash
  cd frontend
  npm start
  ```
- [ ] Browser: Open http://localhost:3000
- [ ] Test: Create an agent and run it

## HTTPS Setup (Mobile Access)

- [ ] Get computer IP: `hostname -I`
- [ ] Generate SSL certificate:
  ```bash
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/nginx-selfsigned.key \
    -out ssl/nginx-selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=Org/CN=YOUR_IP"
  ```
- [ ] Update `nginx.conf` with correct IP/paths
- [ ] Start nginx: `nginx -c ~/agentic/nginx.conf`
- [ ] Test HTTPS: `curl -k https://localhost/api/agents`

## Mobile Voice Access

- [ ] Desktop: Open `https://YOUR_IP/voice`
- [ ] Accept certificate warning
- [ ] Start voice session
- [ ] Mobile: Open `https://YOUR_IP/mobile-voice`
- [ ] Accept certificate warning
- [ ] Select conversation
- [ ] Start session
- [ ] Test: Speak into mobile, hear response

## Verification

- [ ] Backend running: `curl http://localhost:8000/api/agents`
- [ ] Frontend running: `curl http://localhost:3000`
- [ ] Nginx running: `ps aux | grep nginx`
- [ ] Database exists: `ls -la backend/voice_conversations.db`
- [ ] Logs directory exists: `ls -la logs/`

## Production Setup (Optional)

- [ ] Create systemd service for backend
- [ ] Build frontend: `npm run build`
- [ ] Setup PM2 for frontend: `pm2 serve build 3000`
- [ ] Configure firewall (ports 22, 443)
- [ ] Setup Let's Encrypt SSL certificate
- [ ] Configure log rotation
- [ ] Setup database backups
- [ ] Monitor services

## Troubleshooting

### Backend Issues
- [ ] Check Python version: `python3 --version`
- [ ] Check virtual environment activated
- [ ] Check .env file exists and has keys
- [ ] Check port 8000 not in use: `lsof -i :8000`
- [ ] Check backend logs: `tail /tmp/backend.log`

### Frontend Issues
- [ ] Check Node version: `node --version`
- [ ] Check npm packages installed: `ls node_modules`
- [ ] Check port 3000 not in use: `lsof -i :3000`
- [ ] Clear cache: `rm -rf node_modules && npm install`

### HTTPS Issues
- [ ] Check nginx running: `ps aux | grep nginx`
- [ ] Check nginx config: `nginx -t -c ~/agentic/nginx.conf`
- [ ] Check port 443 not in use: `sudo lsof -i :443`
- [ ] Check SSL certificates exist: `ls -la ssl/`
- [ ] Check nginx logs: `tail logs/nginx-error.log`

### Mobile Voice Issues
- [ ] Both desktop and mobile use HTTPS (same domain)
- [ ] Check WebRTC signaling: `tail -f logs/nginx-access.log | grep webrtc`
- [ ] Check peer registration: `grep "registered for signaling" /tmp/backend.log`
- [ ] Check no echo (latest code has fix)
- [ ] Check network connections: `ss -tn | grep :8000`

## Resources

- **Full Guide:** [docs/DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Dev Guide:** [../CLAUDE.md](../CLAUDE.md)
- **Quick Start:** [../DEPLOYMENT_README.md](../DEPLOYMENT_README.md)
- **Debug Guides:** `../debug/` directory

## Success Criteria

✅ Backend responding on port 8000
✅ Frontend responding on port 3000
✅ Can access dashboard at http://localhost:3000
✅ Can create and run agents
✅ Voice assistant works
✅ Mobile voice works via HTTPS
✅ No echo on mobile
✅ WebRTC peer connections established

**Status:** Ready for use! 🎉

**Last Updated:** 2025-12-01
