# Jetson Nano Home Server Deployment Guide

**Last Updated:** 2025-11-29
**Server:** Jetson Nano (server.local / 192.168.0.200)

---

## Table of Contents

1. [Server Information](#server-information)
2. [Network Configuration](#network-configuration)
3. [SSL/TLS Setup](#ssltls-setup)
4. [Application Deployment](#application-deployment)
5. [Nginx Configuration](#nginx-configuration)
6. [Systemd Services](#systemd-services)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## Server Information

### Hardware & OS
- **Device:** NVIDIA Jetson Nano
- **Architecture:** ARM64 (aarch64)
- **OS:** Ubuntu 18.04.6 LTS
- **JetPack:** R32.7.6
- **Kernel:** Linux 4.9.337-tegra

### Network Details
- **Hostname:** server.local
- **Static IP:** 192.168.0.200 (configured via NetworkManager)
- **Gateway:** 192.168.0.1
- **DNS:** 8.8.8.8, 8.8.4.4

### User Credentials
- **User:** rodrigo
- **Password:** rod454c544
- **SSH Access:** `ssh rodrigo@192.168.0.200`

### Software Environment
- **Python:** 3.11.13 (via Miniconda3, conda environment: `agentic`)
- **Node.js:** 20.17.0 (via conda)
- **Nginx:** 1.14.0
- **Claude Code:** Installed and authenticated

---

## Network Configuration

### Static IP Assignment

The Jetson is configured with a static IP address to ensure consistent network access:

```bash
# View current network configuration
nmcli connection show "Wired connection 1"

# Configuration (already applied):
# IP: 192.168.0.200/24
# Gateway: 192.168.0.1
# DNS: 8.8.8.8, 8.8.4.4
```

**Why 192.168.0.200?**
- Outside typical DHCP range (usually .2-.100)
- Easy to remember
- Low collision risk with other devices

### Reconnect via SSH

```bash
# From desktop
ssh rodrigo@192.168.0.200
# OR
ssh rodrigo@server.local
```

---

## SSL/TLS Setup

### Certificate Authority (CA) Approach

To avoid certificate warnings on each device (TV, mobile, desktop), we created a local Certificate Authority.

#### CA Certificate Details

**Location:** `/home/rodrigo/ssl/`

**Files:**
- `ca.crt` - Certificate Authority certificate (install on devices once)
- `ca.key` - CA private key (keep secure!)
- `server.crt` - Server certificate (signed by CA)
- `server.key` - Server private key

**CA Certificate:**
```bash
# View CA certificate on server
cat ~/ssl/ca.crt

# Copy to desktop for device installation
scp rodrigo@192.168.0.200:~/ssl/ca.crt ~/Downloads/home-ca.crt
```

**Server Certificate Details:**
- **Subject:** /CN=192.168.0.200
- **SAN (Subject Alternative Names):**
  - IP: 192.168.0.200
  - DNS: server.local
- **Validity:** 365 days (expires 2026-11-29)

#### Installing CA Certificate on Devices

**Android TV / Mobile:**
1. Copy `ca.crt` to device
2. Settings → Security → Install from storage
3. Select "CA certificate"
4. Browse and select `home-ca.crt`
5. Reboot device

**Desktop (Linux):**
```bash
# Copy CA certificate to trusted store
sudo cp ~/ssl/ca.crt /usr/local/share/ca-certificates/home-ca.crt
sudo update-ca-certificates
```

**Desktop (macOS):**
1. Double-click `ca.crt`
2. Keychain Access → System
3. Double-click "Home CA"
4. Trust → When using this certificate: Always Trust

**Desktop (Windows):**
1. Double-click `ca.crt`
2. Install Certificate → Local Machine
3. Place in: Trusted Root Certification Authorities

---

## Application Deployment

### Conda Environment

The Jetson uses a conda environment for Python and Node.js:

```bash
# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic

# Verify versions
python --version  # Python 3.11.13
node --version    # v20.17.0
npm --version     # 10.8.2
```

### Directory Structure

```
/home/rodrigo/
├── agentic/                  # Main application
│   ├── backend/              # FastAPI backend
│   │   ├── main.py
│   │   ├── .env              # Environment variables (MongoDB, API keys)
│   │   ├── agents/
│   │   ├── tools/
│   │   ├── data/             # Database storage
│   │   │   └── memory/       # ChromaDB + memory banks
│   │   │       ├── chroma_db/
│   │   │       ├── memory_index.json
│   │   │       └── short_term_memory.txt
│   │   ├── database_metadata/  # MongoDB collection schemas
│   │   │   └── collections_schema.json
│   │   └── voice_conversations.db  # Voice conversation history
│   └── frontend/             # React frontend
│       ├── src/
│       ├── build/            # Production build (served by nginx)
│       └── package.json
│
├── server-hub/               # Server Hub launcher (root /)
│   └── index.html
│
├── ssl/                      # SSL certificates
│   ├── ca.crt
│   ├── ca.key
│   ├── server.crt
│   └── server.key
│
├── nginx-server.conf         # Nginx configuration
├── nginx.pid                 # Nginx process ID
└── logs/                     # Nginx logs
    ├── nginx-access.log
    └── nginx-error.log
```

### Database Services

The Jetson runs two database systems:

**MongoDB** (Document database for Database agent):
- Version: 3.6.3 (system install via apt)
- Port: 27017 (localhost)
- Database: `agentic_db`
- Auto-start: Enabled via systemd
- Status: `sudo systemctl status mongodb`

**ChromaDB** (Vector database for Memory agent):
- Version: 0.4.24 (Python package)
- Storage: `backend/data/memory/chroma_db/`
- Embeddings: OpenAI `text-embedding-3-small`
- Memory bank: `personal_info` (2 documents)

**Setup Guide:** See [docs/guides/DATABASE_AND_MEMORY_SETUP.md](../guides/DATABASE_AND_MEMORY_SETUP.md) for complete setup instructions.

### Deploying Updates

#### Update Frontend

```bash
# 1. SSH to server
ssh rodrigo@192.168.0.200

# 2. Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic

# 3. Pull latest changes
cd ~/agentic
git pull

# 4. Rebuild frontend
cd frontend
npm run build

# 5. Reload nginx
sudo kill -HUP $(cat ~/nginx.pid)
```

#### Update Backend

```bash
# 1. SSH to server
ssh rodrigo@192.168.0.200

# 2. Pull latest changes
cd ~/agentic
git pull

# 3. Restart backend service
sudo systemctl restart agentic-backend

# 4. Verify it's running
sudo systemctl status agentic-backend
```

---

## Nginx Configuration

### Overview

Nginx serves three applications:
1. **Server Hub** - Root path `/` (launcher page)
2. **Agentic Frontend** - Subpath `/agentic/` (React app)
3. **Agentic Backend API** - `/api/` (proxied to localhost:8000)

Both HTTP (port 80) and HTTPS (port 443) are supported with identical routing.

### Configuration File

**Location:** `/home/rodrigo/nginx-server.conf`

**Key sections:**

```nginx
# HTTPS Server (port 443)
location /agentic/ {
    alias /home/rodrigo/agentic/frontend/build/;
    index index.html;
    # Critical: fallback to /agentic/index.html for React Router
    try_files $uri $uri.html /agentic/index.html;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}

location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 86400;
}
```

### Important Notes

1. **`try_files` with `alias`:** When using `alias`, the fallback path must be absolute from the server root, not relative to the alias. That's why we use `/agentic/index.html` not `/index.html`.

2. **React Router support:** The `try_files` directive ensures React Router works correctly for client-side routes like `/agentic/voice` or `/agentic/agents/MainConversation`.

3. **WebSocket support:** The `proxy_set_header Upgrade` and `Connection` headers enable WebSocket connections for real-time features.

### Reloading Nginx

```bash
# After configuration changes
sudo kill -HUP $(cat ~/nginx.pid)

# Verify no errors
tail ~/logs/nginx-error.log

# Check if reload was successful (no new errors = success)
```

### Testing Nginx

```bash
# From desktop, test static files
curl -I http://192.168.0.200/agentic/static/js/main.*.js
# Expected: HTTP/1.1 200 OK

# Test index.html
curl http://192.168.0.200/agentic/
# Expected: HTML with <script src="/agentic/static/js/main.*.js">

# Test HTTPS
curl -k https://192.168.0.200/agentic/
# Expected: Same HTML

# Test backend API
curl http://192.168.0.200/api/agents
# Expected: JSON list of agents
```

---

## Systemd Services

### Backend Service

**Name:** `agentic-backend.service`
**Location:** `/etc/systemd/system/agentic-backend.service`

```ini
[Unit]
Description=Agentic Voice Assistant Backend
After=network.target

[Service]
Type=simple
User=rodrigo
Group=rodrigo
WorkingDirectory=/home/rodrigo/agentic/backend
Environment="PATH=/home/rodrigo/miniconda3/envs/agentic/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/rodrigo/miniconda3/envs/agentic/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Managing the service:**

```bash
# Check status
sudo systemctl status agentic-backend

# Start/Stop/Restart
sudo systemctl start agentic-backend
sudo systemctl stop agentic-backend
sudo systemctl restart agentic-backend

# View logs
sudo journalctl -u agentic-backend -f

# Enable/Disable autostart
sudo systemctl enable agentic-backend
sudo systemctl disable agentic-backend
```

### Nginx Process

Nginx is NOT running as a systemd service. It's manually started:

```bash
# Start nginx
sudo nginx -c /home/rodrigo/nginx-server.conf

# Check if running
ps aux | grep nginx

# Stop nginx
sudo kill $(cat ~/nginx.pid)

# Reload configuration
sudo kill -HUP $(cat ~/nginx.pid)
```

**To convert to systemd service (optional):**

```bash
# Create service file
sudo tee /etc/systemd/system/nginx-server.service > /dev/null << 'EOF'
[Unit]
Description=Nginx Server Hub
After=network.target

[Service]
Type=forking
PIDFile=/home/rodrigo/nginx.pid
ExecStartPre=/usr/sbin/nginx -t -c /home/rodrigo/nginx-server.conf
ExecStart=/usr/sbin/nginx -c /home/rodrigo/nginx-server.conf
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -QUIT $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable nginx-server
sudo systemctl start nginx-server
```

---

## Troubleshooting

### Common Issues

#### 1. **White screen on TV WebView**

**Symptoms:** Blue AppBar loads, but content area is white/blank.

**Possible causes:**
- Static assets not loading (check nginx `try_files`)
- JavaScript errors (check TV WebView console if accessible)
- React Router basename mismatch

**Debugging steps:**

```bash
# 1. Check if static files are accessible
curl -I http://192.168.0.200/agentic/static/js/main.*.js
# Should return: 200 OK

# 2. Check nginx configuration
cat ~/nginx-server.conf | grep -A 5 "location /agentic/"

# 3. Verify try_files is correct
# Should be: try_files $uri $uri.html /agentic/index.html;

# 4. Check build output includes correct PUBLIC_URL
cd ~/agentic/frontend
grep homepage package.json
# Should be: "homepage": "/agentic"

# 5. Check console logs (if accessible on TV)
# Look for errors in browser DevTools or WebView debug console

# 6. Test on desktop browser first
# Open: http://192.168.0.200/agentic/
# Check browser console (F12) for errors
```

**Solution checklist:**
- ✅ Nginx `try_files` includes `/agentic/index.html` fallback
- ✅ `package.json` has `"homepage": "/agentic"`
- ✅ React Router has `basename={process.env.PUBLIC_URL || ''}`
- ✅ Viewport meta tag in index.html for TV compatibility
- ✅ Error boundary added to catch rendering errors

#### 2. **Backend API not accessible**

**Symptoms:** Frontend loads, but API calls fail (404 or connection refused).

**Debugging:**

```bash
# 1. Check backend service
sudo systemctl status agentic-backend

# 2. Test backend directly
curl http://127.0.0.1:8000/api/agents
# Should return JSON

# 3. Test through nginx
curl http://192.168.0.200/api/agents
# Should also return JSON

# 4. Check nginx proxy configuration
cat ~/nginx-server.conf | grep -A 10 "location /api/"

# 5. Check nginx error log
tail -50 ~/logs/nginx-error.log | grep api
```

**Common fixes:**
- Restart backend: `sudo systemctl restart agentic-backend`
- Check PORT is 8000: `ss -tlnp | grep 8000`
- Verify proxy_pass ends with `/`: `proxy_pass http://127.0.0.1:8000/api/;`

#### 3. **SSL certificate warnings**

**Symptoms:** Browser shows "Not secure" or certificate error.

**Solution:** Install CA certificate on the device (see [SSL/TLS Setup](#ssltls-setup)).

**Verify certificate:**

```bash
# Check certificate details
openssl x509 -in ~/ssl/server.crt -text -noout | grep -A 2 "Subject Alternative Name"
# Should show: IP:192.168.0.200, DNS:server.local

# Check certificate chain
openssl verify -CAfile ~/ssl/ca.crt ~/ssl/server.crt
# Should say: OK
```

#### 4. **Research agent tools not loading**

**Symptoms:** Error message: "Agent 'Researcher' configured with tools that couldn't be loaded"

**Missing dependencies:**

```bash
# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic

# Install missing packages
pip install wikipedia arxiv "duckduckgo_search<6.0.0"

# Verify installation
python -c "import wikipedia, arxiv, duckduckgo_search; print('All tools available')"

# Restart backend
sudo systemctl restart agentic-backend
```

**Note:** duckduckgo_search version <6.0.0 required to avoid Rust dependency issues on Ubuntu 18.04.

---

## Maintenance

### Regular Tasks

#### Weekly
- Check disk space: `df -h`
- Review nginx logs: `tail -100 ~/logs/nginx-error.log`
- Review backend logs: `sudo journalctl -u agentic-backend --since "1 week ago"`

#### Monthly
- Update system packages: `sudo apt update && sudo apt upgrade`
- Update conda packages: `conda update --all`
- Rotate logs (if not using logrotate)

#### As Needed
- Renew SSL certificate (annually): See [SSL certificate renewal](#ssl-certificate-renewal)
- Update Node.js/Python versions
- Clean up old conversation data

### SSL Certificate Renewal

The server certificate expires after 1 year (2026-11-29). To renew:

```bash
# 1. SSH to server
ssh rodrigo@192.168.0.200

# 2. Generate new server certificate request
cd ~/ssl
openssl req -new -key server.key -out server.csr \
  -subj "/CN=192.168.0.200" \
  -addext "subjectAltName=IP:192.168.0.200,DNS:server.local"

# 3. Sign with CA
openssl x509 -req -in server.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256 \
  -extfile <(printf "subjectAltName=IP:192.168.0.200,DNS:server.local")

# 4. Reload nginx
sudo kill -HUP $(cat ~/nginx.pid)

# 5. Verify new certificate
openssl x509 -in server.crt -noout -dates
```

### Backup Strategy

**Critical files to backup:**

```bash
# Create backup directory
mkdir -p ~/backups/$(date +%Y%m%d)

# Backup configurations
cp ~/nginx-server.conf ~/backups/$(date +%Y%m%d)/
cp -r ~/ssl ~/backups/$(date +%Y%m%d)/

# Backup application data
cp ~/agentic/backend/voice_conversations.db ~/backups/$(date +%Y%m%d)/

# Backup agent configurations
cp -r ~/agentic/backend/agents ~/backups/$(date +%Y%m%d)/

# Create tarball
cd ~/backups
tar czf jetson-backup-$(date +%Y%m%d).tar.gz $(date +%Y%m%d)

# Copy to desktop
scp ~/backups/jetson-backup-$(date +%Y%m%d).tar.gz rodrigo@192.168.0.25:~/backups/
```

### Performance Monitoring

```bash
# Check CPU/Memory usage
htop

# Check nginx worker processes
ps aux | grep nginx

# Check backend process
ps aux | grep uvicorn

# Monitor connections
ss -tn | grep :8000  # Backend connections
ss -tn | grep :443   # HTTPS connections
ss -tn | grep :80    # HTTP connections

# Check disk I/O
iotop

# Monitor network traffic
iftop
```

---

## Access URLs

### Local Network Access

- **Server Hub (launcher):**
  - HTTP: `http://192.168.0.200/` or `http://server.local/`
  - HTTPS: `https://192.168.0.200/` or `https://server.local/`

- **Agentic App:**
  - HTTP: `http://192.168.0.200/agentic/`
  - HTTPS: `https://192.168.0.200/agentic/`

- **Backend API:**
  - HTTP: `http://192.168.0.200/api/`
  - HTTPS: `https://192.168.0.200/api/`

### Direct Backend Access (localhost only)

- `http://127.0.0.1:8000/api/` - Only accessible from server itself

---

## Quick Reference Commands

```bash
# === SSH ===
ssh rodrigo@192.168.0.200

# === Conda ===
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic

# === Backend Service ===
sudo systemctl status agentic-backend
sudo systemctl restart agentic-backend
sudo journalctl -u agentic-backend -f

# === Nginx ===
sudo kill -HUP $(cat ~/nginx.pid)          # Reload
tail -f ~/logs/nginx-access.log            # Access log
tail -f ~/logs/nginx-error.log             # Error log

# === Deploy Frontend ===
cd ~/agentic/frontend
npm run build
sudo kill -HUP $(cat ~/nginx.pid)

# === Check Services ===
ps aux | grep nginx
ps aux | grep uvicorn
ss -tlnp | grep -E '(80|443|8000)'

# === Logs ===
tail -50 ~/logs/nginx-error.log
sudo journalctl -u agentic-backend --since "1 hour ago"
```

---

## Support & Resources

- **Main Documentation:** `/home/rodrigo/agentic/CLAUDE.md`
- **Nginx Docs:** https://nginx.org/en/docs/
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **React Docs:** https://react.dev/

---

**Document Maintained By:** Claude Code
**Last Reviewed:** 2025-11-29
