# Jetson Nano Server - Operations Guide for Claude Code

**Last Updated:** 2025-11-30
**Purpose:** Practical guide for Claude Code to connect, update, and maintain the Jetson server
**Server:** Jetson Nano (192.168.0.200 / server.local)

---

## Quick Reference

### Essential Connection Info

```bash
# SSH Access
ssh rodrigo@192.168.0.200
# Password: rod454c544

# Using sshpass (for automation)
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 'COMMAND'

# Conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic
```

### URLs

- **Agentic App (HTTPS):** https://192.168.0.200/agentic/
- **Agentic App (HTTP):** http://192.168.0.200/agentic/
- **Server Hub:** https://192.168.0.200/ or http://192.168.0.200/
- **Copyparty:** http://192.168.0.200:3923/

---

## Table of Contents

1. [Connecting to the Server](#connecting-to-the-server)
2. [Deploying Code Updates](#deploying-code-updates)
3. [Frontend Updates](#frontend-updates)
4. [Backend Updates](#backend-updates)
5. [Nginx Configuration](#nginx-configuration)
6. [Common Operations](#common-operations)
7. [Troubleshooting](#troubleshooting)
8. [Lessons Learned](#lessons-learned)

---

## Connecting to the Server

### SSH Connection

**Method 1: Interactive SSH**
```bash
ssh rodrigo@192.168.0.200
# Enter password: rod454c544
```

**Method 2: Automated SSH (recommended for Claude Code)**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 'ls -la'
```

**Method 3: SSH with TTY (for sudo commands)**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 'echo "rod454c544" | sudo -S systemctl status nginx'
```

### Important Notes

- ✅ **Always use `-o StrictHostKeyChecking=no`** to avoid host key verification prompts
- ✅ **Use `-t` flag for commands requiring TTY** (like sudo with password)
- ✅ **Echo password to sudo with `-S` flag:** `echo "rod454c544" | sudo -S COMMAND`
- ⚠️ **Commands timeout if they expect interactive input** - use heredocs or echo for multi-line inputs

---

## Deploying Code Updates

### Complete Deployment Workflow

This is the **standard workflow** for deploying changes to the Jetson server:

```bash
# 1. Make changes locally (on desktop)
# Edit files as needed

# 2. Commit changes
git add .
git commit -m "Your commit message

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 3. Push to GitHub
git push origin main

# 4. Pull on Jetson server
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 'cd ~/agentic && git pull'

# 5a. If frontend changed: rebuild
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cd ~/agentic/frontend && source ~/miniconda3/etc/profile.d/conda.sh && conda activate agentic && npm run build'

# 5b. If backend changed: restart service
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S systemctl restart agentic-backend'

# 6. Reload nginx (always recommended after frontend rebuild)
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S kill -HUP $(cat ~/nginx.pid)'
```

### Git Operations on Server

**Handling uncommitted changes on server:**
```bash
# If git pull fails due to local changes, stash them
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cd ~/agentic && git stash && git pull && git stash pop'
```

**Check git status:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cd ~/agentic && git status'
```

---

## Frontend Updates

### Building the Frontend

The frontend build process can take **3-5 minutes** on the Jetson Nano (ARM64 processor).

**Standard build command:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cd ~/agentic/frontend && source ~/miniconda3/etc/profile.d/conda.sh && conda activate agentic && npm run build 2>&1 | tail -40'
```

**Important notes:**
- ⏱️ **Set timeout to at least 180000ms (3 minutes)** when using Bash tool
- 📦 **Build output goes to:** `~/agentic/frontend/build/`
- ✅ **Verify build succeeded:** Look for "Compiled successfully" in output
- 🔄 **Always reload nginx after build:** `sudo kill -HUP $(cat ~/nginx.pid)`

### Checking if Build Process is Running

Sometimes builds can hang or get stuck:

```bash
# Check if npm build is running
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'pgrep -f "npm run build" && echo "Build running" || echo "Build not running"'

# Kill stuck build process
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'pkill -f "npm run build"'
```

### Verifying Build Output

```bash
# Check build directory contents
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ls -lh ~/agentic/frontend/build/'

# Check main JS bundle
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ls -lh ~/agentic/frontend/build/static/js/'

# Verify specific file exists
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ls -la ~/agentic/frontend/build/favicon.ico'
```

### Direct File Copy (Alternative to Full Rebuild)

For **small changes** (like adding a single CSS file), you can copy directly instead of rebuilding:

```bash
# Copy single file using rsync
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  /home/rodrigo/agentic/frontend/public/webview-fix.css \
  rodrigo@192.168.0.200:~/agentic/frontend/build/
```

**When to use direct copy vs rebuild:**
- ✅ **Direct copy:** Static assets (CSS, images, favicon.ico) that don't require transpilation
- ❌ **Must rebuild:** JavaScript/JSX changes, package.json changes, React component changes

---

## Backend Updates

### Restarting the Backend Service

The backend runs as a systemd service called `agentic-backend`.

**Check status:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S systemctl status agentic-backend | head -20'
```

**Restart service:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S systemctl restart agentic-backend && echo "Backend restarted"'
```

**View logs:**
```bash
# Recent logs
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S journalctl -u agentic-backend --since "10 minutes ago" | tail -50'

# Follow logs in real-time (use with caution - will block)
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S journalctl -u agentic-backend -f'
```

### Deploying Backend Code Changes

```bash
# 1. Copy changed Python files
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  /home/rodrigo/agentic/backend/api/claude_code_controller.py \
  rodrigo@192.168.0.200:~/agentic/backend/api/

# 2. Restart backend service
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S systemctl restart agentic-backend'

# 3. Verify it restarted successfully
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S systemctl status agentic-backend | head -10'
```

### Backend Service Configuration

**Service file location:** `/etc/systemd/system/agentic-backend.service`

**Key details:**
- **Working directory:** `/home/rodrigo/agentic/backend`
- **Python:** `/home/rodrigo/miniconda3/envs/agentic/bin/python3.11`
- **Command:** `uvicorn main:app --host 127.0.0.1 --port 8000`
- **PATH includes:** `/home/rodrigo/miniconda3/envs/agentic/bin` (so `claude` CLI is accessible)

---

## Nginx Configuration

### Nginx Configuration File

**Location:** `/home/rodrigo/nginx-server.conf`

### Current Configuration (2025-11-30)

```nginx
# HTTPS Server (port 443)
server {
    listen 443 ssl;
    server_name 192.168.0.200 server.local;

    ssl_certificate /home/rodrigo/ssl/server.crt;
    ssl_certificate_key /home/rodrigo/ssl/server.key;

    # Redirect /agentic to /agentic/ (trailing slash required!)
    location = /agentic {
        return 301 $scheme://$host/agentic/;
    }

    # Agentic Frontend - ALL files under /agentic/
    location /agentic/ {
        alias /home/rodrigo/agentic/frontend/build/;
        index index.html;
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # Agentic Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # Server Hub (launcher page)
    location / {
        root /home/rodrigo/server-hub;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}

# HTTP Server (port 80) - identical configuration
```

### Critical Nginx Configuration Rules

**1. Trailing slash is CRITICAL:**
```nginx
# ✅ CORRECT: Redirect /agentic to /agentic/
location = /agentic {
    return 301 $scheme://$host/agentic/;
}

# ❌ WRONG: Without this, /agentic serves Server Hub instead of agentic app
```

**2. try_files with alias:**
```nginx
# ✅ CORRECT: Fallback to /index.html (relative to alias directory)
location /agentic/ {
    alias /home/rodrigo/agentic/frontend/build/;
    try_files $uri $uri/ /index.html;
}

# ❌ WRONG: Fallback to /agentic/index.html (would look for root /agentic/index.html)
# try_files $uri $uri/ /agentic/index.html;
```

**Why this works:**
- Request: `/agentic/voice` → tries `voice` file → doesn't exist → serves `/index.html` from alias dir
- Request: `/agentic/static/js/main.js` → tries `static/js/main.js` → exists → serves file
- Request: `/agentic/favicon.ico` → tries `favicon.ico` → exists → serves file

### Updating Nginx Configuration

**1. Edit configuration file:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 'cat > ~/nginx-server.conf << '\''EOF'\''
# Your nginx config here
EOF
'
```

**2. Test configuration:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S nginx -t -c /home/rodrigo/nginx-server.conf'
```

**3. Reload nginx:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S kill -HUP $(cat ~/nginx.pid) && echo "Nginx reloaded"'
```

**4. Check for errors:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'tail -20 ~/logs/nginx-error.log'
```

### Testing Routes After Nginx Changes

```bash
# Test main app
curl -s -o /dev/null -w "%{http_code}\n" https://192.168.0.200/agentic/ -k

# Test React Router route
curl -s -o /dev/null -w "%{http_code}\n" https://192.168.0.200/agentic/voice -k

# Test static asset
curl -s -o /dev/null -w "%{http_code}\n" https://192.168.0.200/agentic/static/js/main.*.js -k

# Test favicon
curl -s -o /dev/null -w "%{http_code}\n" https://192.168.0.200/agentic/favicon.ico -k
```

**Expected results:**
- `/agentic/` → 200 (HTML with React app)
- `/agentic/voice` → 200 (HTML - React Router handles it)
- `/agentic/static/js/main.*.js` → 200 (JS file)
- `/agentic/favicon.ico` → 200 (ICO file, or HTML if doesn't exist - browser ignores HTML)

### Nginx Logs

```bash
# Access log (requests)
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'tail -50 ~/logs/nginx-access.log'

# Error log (problems)
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'tail -50 ~/logs/nginx-error.log'

# Follow access log (real-time)
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'tail -f ~/logs/nginx-access.log'
```

---

## Common Operations

### Checking What's Running

```bash
# Check nginx process
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ps aux | grep nginx | grep -v grep'

# Check backend process
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ps aux | grep uvicorn | grep -v grep'

# Check copyparty process
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ps aux | grep copyparty | grep -v grep'

# Check ports in use
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ss -tlnp | grep -E "(80|443|8000|3923)"'
```

### Disk Space

```bash
# Check disk usage
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'df -h'

# Check agentic directory size
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'du -sh ~/agentic'

# Check build directory size
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'du -sh ~/agentic/frontend/build'
```

### System Information

```bash
# Check system load
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'uptime'

# Check memory usage
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'free -h'

# Check temperature (Jetson specific)
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cat /sys/devices/virtual/thermal/thermal_zone*/temp'
```

### Copyparty Configuration

Copyparty is a file server running on port 3923.

**Config file:** `/home/rodrigo/server.conf`

**Restart copyparty:**
```bash
# Kill existing process
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'pkill -f copyparty'

# Start new process
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  '/usr/bin/python3 -m copyparty -c /home/rodrigo/server.conf >> /home/rodrigo/copyparty.log 2>&1 &'
```

**Current mounts:**
- `/` → `/home/rodrigo/server` (rodrigo: rwmda)
- `/uploads` → `/home/rodrigo/server/uploads` (rodrigo: rwmda, familia: w, guest: g)
- `/agentic` → `/home/rodrigo/agentic` (rodrigo: rwmda)

---

## Troubleshooting

### Frontend Not Loading

**Symptoms:** White screen, blank page, or shows Server Hub instead of agentic app

**Diagnosis:**
```bash
# 1. Check if /agentic route redirects properly
curl -I https://192.168.0.200/agentic -k
# Should see: Location: https://192.168.0.200/agentic/

# 2. Check if /agentic/ serves HTML
curl -s https://192.168.0.200/agentic/ -k | head -5
# Should see: <!doctype html><html lang="en">... with /agentic/static/js/main.*.js

# 3. Check if static assets load
curl -I https://192.168.0.200/agentic/static/js/main.*.js -k
# Should see: HTTP/1.1 200 OK

# 4. Check nginx logs for errors
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'tail -50 ~/logs/nginx-error.log'
```

**Common fixes:**
1. **Missing trailing slash redirect** → Add `location = /agentic { return 301... }`
2. **Wrong try_files fallback** → Use `/index.html` not `/agentic/index.html`
3. **Build not deployed** → Run `npm run build` and reload nginx
4. **Nginx not reloaded** → Run `sudo kill -HUP $(cat ~/nginx.pid)`

### Backend Not Responding

**Symptoms:** API calls return 502/504, connection refused errors

**Diagnosis:**
```bash
# 1. Check if backend is running
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S systemctl status agentic-backend'

# 2. Check if port 8000 is listening
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ss -tlnp | grep 8000'

# 3. Test backend directly
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'curl -s http://127.0.0.1:8000/api/agents | head -20'

# 4. Check backend logs for errors
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S journalctl -u agentic-backend -n 100'
```

**Common fixes:**
1. **Service not running** → `sudo systemctl start agentic-backend`
2. **Service crashed** → Check logs, fix error, restart service
3. **Port already in use** → Kill old process, restart service
4. **Python environment wrong** → Service file has correct conda path

### Claude Code Integration Not Working

**Symptoms:** Voice system shows error "Claude Code session error: No such file or directory"

**Diagnosis:**
```bash
# 1. Check if claude CLI exists
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'source ~/miniconda3/etc/profile.d/conda.sh && conda activate agentic && which claude'

# Should return: /home/rodrigo/miniconda3/envs/agentic/bin/claude

# 2. Test claude CLI
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'source ~/miniconda3/etc/profile.d/conda.sh && conda activate agentic && claude --version'

# 3. Check backend service PATH includes conda bin
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cat /etc/systemd/system/agentic-backend.service | grep PATH'

# Should include: /home/rodrigo/miniconda3/envs/agentic/bin
```

**Fix:**
The backend now auto-detects Claude CLI using `shutil.which("claude")`, which works because:
1. Backend service has conda bin in PATH
2. `claude` is installed in conda environment
3. Code falls back to checking common paths if `which` fails

If still not working, update `backend/api/claude_code_controller.py` to add the correct path to the fallback list.

### TV WebView Shows White Screen

**Symptoms:** TV browser loads page structure (blue bar) but content area is white

**Diagnosis:**
```bash
# 1. Check if webview-fix.css exists
curl -s https://192.168.0.200/agentic/webview-fix.css -k
# Should return CSS content

# 2. Check if index.html includes webview-fix.css
curl -s https://192.168.0.200/agentic/ -k | grep "webview-fix"
# Should see: <link rel="stylesheet" href="/agentic/webview-fix.css"/>
```

**Fix:**
The `webview-fix.css` file sets explicit dimensions on `html`, `body`, and `#root` to prevent collapsed containers:

```css
html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

#root {
  width: 100%;
  height: 100%;
  min-height: 100vh;
  background: #ffffff;
}
```

If missing:
1. Ensure file exists in `frontend/public/webview-fix.css`
2. Ensure `index.html` includes the link
3. Rebuild frontend: `npm run build`
4. Reload nginx

---

## Lessons Learned

### Critical Insights from 2025-11-30 Session

#### 1. Nginx Configuration with Alias and Try Files

**Problem:** Using `try_files` with `alias` is tricky. Wrong configuration causes:
- Static assets to serve HTML instead of 404
- Routes to serve wrong content (Server Hub instead of agentic)

**Solution:**
```nginx
# Redirect /agentic to /agentic/ (CRITICAL!)
location = /agentic {
    return 301 $scheme://$host/agentic/;
}

# Serve files, fallback to /index.html (NOT /agentic/index.html)
location /agentic/ {
    alias /home/rodrigo/agentic/frontend/build/;
    try_files $uri $uri/ /index.html;
}
```

**Why:**
- With `alias`, the path is **replaced** not **prepended**
- `/agentic/voice` becomes `/home/rodrigo/.../build/voice`
- Fallback `/index.html` becomes `/home/rodrigo/.../build/index.html` ✅
- Fallback `/agentic/index.html` would become `/agentic/index.html` from root ❌

#### 2. Frontend Build Process on ARM64

**Problem:** Builds can take 3-5 minutes and may hang/timeout

**Solutions:**
- Always set timeout to at least 180000ms (3 minutes)
- Check if build is already running before starting new one
- Build may complete even if command times out - check build directory
- Kill stuck builds with `pkill -f "npm run build"`

**Verification:**
```bash
# Check if build succeeded
ls -lh ~/agentic/frontend/build/static/js/main.*.js
# Should show a ~1.4MB file
```

#### 3. TV WebView Requires Explicit Dimensions

**Problem:** React apps with no explicit height on `#root` collapse to zero height in WebView

**Solution:** Create `webview-fix.css` with:
```css
html, body, #root {
  width: 100%;
  height: 100%;
}
#root {
  min-height: 100vh;
}
```

**Key insight:** Desktop browsers infer container dimensions, TV WebViews don't.

#### 4. Claude Code CLI Path Detection

**Problem:** Hardcoded paths don't work across different environments (desktop vs Jetson)

**Solution:** Auto-detect using `shutil.which("claude")` first, then fall back to common paths:
```python
def _find_claude_cli():
    # Try which first (works in PATH)
    claude_path = shutil.which("claude")
    if claude_path:
        return claude_path

    # Fallback to known locations
    for path in [vscode_extension, conda_bin, system_bin]:
        if os.path.exists(path):
            return path
```

**Key insight:** Conda environments set PATH, so `which claude` works when service starts with conda in PATH.

#### 5. Git Operations on Server

**Problem:** `git pull` fails if server has uncommitted local changes

**Solution:**
```bash
git stash        # Save local changes
git pull         # Get remote changes
git stash pop    # Restore local changes
```

**Best practice:** Keep server in sync with repo, avoid manual edits on server.

#### 6. SSH with sshpass Best Practices

**For commands with output:**
```bash
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no user@host 'command'
```

**For commands needing TTY (sudo):**
```bash
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no -t user@host 'echo "PASSWORD" | sudo -S command'
```

**For multi-line commands (heredoc):**
```bash
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no user@host 'cat > file << '\''EOF'\''
content here
EOF
'
```

**Key insight:** The `'\''` sequence escapes single quotes inside a single-quoted string in bash.

#### 7. Systemd Service Management

**Always use sudo with password via stdin:**
```bash
echo "PASSWORD" | sudo -S systemctl restart service-name
```

**Check logs for debugging:**
```bash
sudo journalctl -u service-name --since "10 minutes ago"
```

**Key files:**
- Service definition: `/etc/systemd/system/service-name.service`
- After editing: `sudo systemctl daemon-reload`

---

## Complete Deployment Checklist

Use this checklist when deploying changes:

### Frontend Changes

- [ ] Make changes locally
- [ ] Test locally (`npm start`)
- [ ] Commit changes to git
- [ ] Push to GitHub
- [ ] SSH to server and pull changes
- [ ] Activate conda environment
- [ ] Run `npm run build` (wait 3-5 minutes)
- [ ] Verify build succeeded (check for "Compiled successfully")
- [ ] Reload nginx
- [ ] Test all routes (/, /voice, /agents, static assets)
- [ ] Test on desktop browser
- [ ] Test on TV WebView (if applicable)

### Backend Changes

- [ ] Make changes locally
- [ ] Test locally (if possible)
- [ ] Commit changes to git
- [ ] Push to GitHub
- [ ] SSH to server and pull changes (or rsync specific files)
- [ ] Restart backend service
- [ ] Check service status
- [ ] Check logs for errors
- [ ] Test API endpoints
- [ ] Test voice system (if using Claude Code)

### Nginx Configuration Changes

- [ ] Edit nginx config locally or on server
- [ ] Test configuration (`nginx -t`)
- [ ] Reload nginx (`kill -HUP`)
- [ ] Check error log for issues
- [ ] Test all affected routes
- [ ] Document changes in this guide

### Full System Update

- [ ] Frontend changes (see above)
- [ ] Backend changes (see above)
- [ ] Nginx changes (if needed)
- [ ] Update documentation
- [ ] Commit documentation updates
- [ ] Create git tag for milestone (if applicable)

---

## Quick Commands Reference

```bash
# Connect
ssh rodrigo@192.168.0.200

# Deploy complete update
cd ~/agentic && git pull
cd frontend && conda activate agentic && npm run build
sudo systemctl restart agentic-backend
sudo kill -HUP $(cat ~/nginx.pid)

# Check services
sudo systemctl status agentic-backend
ps aux | grep nginx
ss -tlnp | grep -E "(80|443|8000)"

# View logs
sudo journalctl -u agentic-backend -f
tail -f ~/logs/nginx-access.log
tail -f ~/logs/nginx-error.log

# Test routes
curl -I https://192.168.0.200/agentic/ -k
curl https://192.168.0.200/api/agents

# Emergency restart
sudo systemctl restart agentic-backend
sudo nginx -s reload
# OR
sudo kill -HUP $(cat ~/nginx.pid)
```

---

## Related Documentation

- **[JETSON_DEPLOYMENT_GUIDE.md](JETSON_DEPLOYMENT_GUIDE.md)** - Complete deployment setup guide
- **[TV_WEBVIEW_FIX_SUMMARY.md](TV_WEBVIEW_FIX_SUMMARY.md)** - TV WebView troubleshooting
- **[CLAUDE.md](../CLAUDE.md)** - Main project documentation

---

**Document Maintained By:** Claude Code
**Last Updated:** 2025-11-30
**Session:** Complete deployment operations and troubleshooting learned

