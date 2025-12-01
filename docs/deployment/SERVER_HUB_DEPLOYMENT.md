# Server Hub - Deployment Guide

**Last Updated:** 2025-12-01
**Purpose:** Deploy updates to Server Hub (launcher page at `/`)

---

## What is Server Hub?

A pure HTML/CSS/JS launcher page that serves as the entry point at `https://192.168.0.200/` (root path). It displays a grid of services with animated background.

**Technology:** Single-file static site (`index.html`) + JSON configuration

---

## Server Connection

```bash
# SSH access
ssh rodrigo@192.168.0.200
# Password: rod454c544

# Using sshpass (for automation)
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200
```

---

## Directory Structure

```
/home/rodrigo/server-hub/
├── index.html              # Main HTML file (all CSS/JS embedded)
├── public/
│   ├── tiles.json          # Service configuration
│   └── images/             # Service icons/images
│       ├── agentic.png
│       ├── copyparty.png
│       └── jellyfin.png
├── README.md               # Documentation
└── .git/                   # Git repository
```

---

## Nginx Configuration

**Location:** `/home/rodrigo/nginx-server.conf`

### Relevant Section (Both HTTP & HTTPS)

```nginx
# Server Hub (root path)
location / {
    root /home/rodrigo/server-hub;
    index index.html;
    try_files $uri $uri.html /index.html;
}
```

**Key Points:**
- Serves from `/home/rodrigo/server-hub` directory
- Falls back to `/index.html` for client-side routing
- Same configuration on both port 80 (HTTP) and 443 (HTTPS)

---

## Deployment Workflow

### 1. Update Content (Local Machine)

**Option A: Edit index.html**
```bash
# Edit the main HTML file
cd /home/rodrigo/agentic  # (or wherever your server-hub repo is)
# Make changes to index.html
```

**Option B: Update Service Tiles**
```bash
# Edit tiles.json to add/remove/update services
vim public/tiles.json
```

**Option C: Add New Service Icon**
```bash
# Add image to public/images/
cp my-service-icon.png public/images/
```

### 2. Commit Changes (if using git)

```bash
git add .
git commit -m "Update server hub content

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

### 3. Deploy to Server

**Pull changes:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cd ~/server-hub && git pull'
```

**OR copy files directly (for quick updates):**
```bash
# Copy single file
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  index.html \
  rodrigo@192.168.0.200:~/server-hub/

# Copy tiles.json
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  public/tiles.json \
  rodrigo@192.168.0.200:~/server-hub/public/

# Copy new image
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  public/images/my-service.png \
  rodrigo@192.168.0.200:~/server-hub/public/images/
```

### 4. Reload Nginx (Not always required)

**When to reload:**
- After nginx configuration changes (not for content updates)

**How to reload:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S kill -HUP $(cat ~/nginx.pid)'
```

**Note:** For static file changes (HTML/JSON/images), nginx reload is **NOT required**. Changes are visible immediately on next page load.

---

## Verification

### Test Routes

```bash
# Test HTTP
curl -I http://192.168.0.200/
# Expected: 200 OK

# Test HTTPS
curl -I -k https://192.168.0.200/
# Expected: 200 OK

# Test tiles.json
curl -s https://192.168.0.200/public/tiles.json -k
# Expected: JSON array

# Test image
curl -I -k https://192.168.0.200/public/images/agentic.png
# Expected: 200 OK
```

### View Deployed Content

```bash
# Check index.html on server
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'head -20 ~/server-hub/index.html'

# Check tiles.json
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cat ~/server-hub/public/tiles.json'

# List images
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ls -lh ~/server-hub/public/images/'
```

---

## Editing tiles.json

**Format:**
```json
[
  {
    "title": "Service Name",
    "subtitle": "Description",
    "image": "/images/service.png",
    "link": "https://192.168.0.200/path/",
    "ariaLabel": "Service Name",
    "center": true  // Optional: makes tile span 2 columns
  }
]
```

**Fields:**
- `title` (required): Display name
- `subtitle` (optional): Secondary text
- `image` (required): Path to icon (relative to `public/`)
- `link` (required): URL to open (auto-normalized to http:// if no protocol)
- `ariaLabel` (optional): Accessibility label
- `center` (optional): If true, tile spans 2 columns (use for featured service)

**Current Services:**
1. **Agentic** - `/agentic/` (center tile)
2. **CopyParty** - Port 3923 (file server)
3. **Jellyfin** - Port 8096 (media center)

---

## Common Tasks

### Add New Service

```bash
# 1. Add icon to images/
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  my-service.png \
  rodrigo@192.168.0.200:~/server-hub/public/images/

# 2. Edit tiles.json locally
# Add new entry to JSON array

# 3. Deploy updated tiles.json
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  public/tiles.json \
  rodrigo@192.168.0.200:~/server-hub/public/

# 4. Test
curl -s https://192.168.0.200/public/tiles.json -k | python3 -m json.tool
```

### Update Styling

```bash
# 1. Edit index.html locally (CSS is embedded in <style> tag)
# 2. Deploy
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  index.html \
  rodrigo@192.168.0.200:~/server-hub/

# 3. Hard refresh browser (Ctrl+Shift+R)
```

### Update Background Animation

```bash
# 1. Edit index.html (JavaScript in <script> tag at bottom)
# 2. Deploy same as above
```

---

## Troubleshooting

### Page Shows Blank/White Screen

**Check nginx is serving correct directory:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cat ~/nginx-server.conf | grep -A 3 "location / {"'

# Should show:
# location / {
#     root /home/rodrigo/server-hub;
#     index index.html;
#     try_files $uri $uri.html /index.html;
```

**Verify file exists:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ls -lh ~/server-hub/index.html'
```

### Tiles Not Loading (Shows "Loading services...")

**Check tiles.json:**
```bash
# Verify JSON is valid
curl -s https://192.168.0.200/public/tiles.json -k | python3 -m json.tool

# Check file on server
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cat ~/server-hub/public/tiles.json'
```

**Check browser console:**
- Open DevTools (F12)
- Look for fetch errors or JSON parse errors

### Images Not Loading

**Check image paths in tiles.json:**
- Should be `/images/filename.png` (leading slash)
- Files must exist in `~/server-hub/public/images/`

**Verify image exists:**
```bash
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'ls -lh ~/server-hub/public/images/agentic.png'
```

### Changes Not Visible

**Browser cache:**
- Hard refresh: `Ctrl+Shift+R` (Chrome/Firefox)
- Clear cache and reload
- Open incognito/private window

**Verify file was updated on server:**
```bash
# Check file modification time
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'stat ~/server-hub/index.html | grep Modify'
```

---

## Quick Reference

```bash
# === Connect ===
ssh rodrigo@192.168.0.200

# === Deploy via Git ===
cd ~/server-hub && git pull

# === Deploy Single File ===
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  index.html rodrigo@192.168.0.200:~/server-hub/

# === Deploy Config ===
sshpass -p 'rod454c544' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  public/tiles.json rodrigo@192.168.0.200:~/server-hub/public/

# === Test ===
curl -I https://192.168.0.200/ -k
curl -s https://192.168.0.200/public/tiles.json -k

# === View Nginx Config ===
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no rodrigo@192.168.0.200 \
  'cat ~/nginx-server.conf | grep -A 5 "location / {"'

# === Nginx Reload (if needed) ===
sshpass -p 'rod454c544' ssh -o StrictHostKeyChecking=no -t rodrigo@192.168.0.200 \
  'echo "rod454c544" | sudo -S kill -HUP $(cat ~/nginx.pid)'
```

---

## Related Documentation

- **[JETSON_DEPLOYMENT_GUIDE.md](JETSON_DEPLOYMENT_GUIDE.md)** - Complete server setup
- **[JETSON_OPERATIONS_GUIDE.md](JETSON_OPERATIONS_GUIDE.md)** - Operational procedures
- **Server Hub README:** `/home/rodrigo/server-hub/README.md`

---

**Document Created:** 2025-12-01
**Maintained By:** Claude Code
