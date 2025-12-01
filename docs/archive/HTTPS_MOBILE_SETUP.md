# HTTPS Mobile Voice Setup Guide

## Problem

Mobile browsers (Chrome, Safari, Firefox) require HTTPS to access the microphone via WebRTC. This is a security requirement - HTTP only works on `localhost`, which mobile devices can't access.

## Solution

Use nginx as a reverse proxy with a self-signed SSL certificate to enable HTTPS access from mobile devices.

---

## Prerequisites

1. **nginx installed:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y nginx
   ```

2. **Backend and frontend running:**
   ```bash
   # Terminal 1: Backend
   cd /home/rodrigo/agentic/backend
   uvicorn main:app --reload

   # Terminal 2: Frontend
   cd /home/rodrigo/agentic/frontend
   npm start
   ```

---

## Quick Start

### 1. Start nginx reverse proxy

```bash
cd /home/rodrigo/agentic
./start-nginx.sh
```

This will:
- Start nginx with HTTPS on port 443
- Proxy frontend (React) from localhost:3000
- Proxy backend (FastAPI) from localhost:8000
- Enable HTTPS access for mobile devices

### 2. Get your computer's IP address

```bash
hostname -I | awk '{print $1}'
```

Example output: `192.168.1.100`

### 3. Access from mobile

**On your mobile browser (Chrome recommended):**

1. Open: `https://192.168.1.100/mobile-voice`
2. **Accept the security warning** (self-signed certificate)
   - Chrome: "Advanced" → "Proceed to 192.168.1.100 (unsafe)"
   - Safari: "Advanced" → "Visit this website"
   - Firefox: "Advanced" → "Accept the Risk and Continue"
3. Select conversation from dropdown
4. Tap green play button
5. Tap microphone to unmute
6. Start speaking!

### 4. Stop nginx when done

```bash
cd /home/rodrigo/agentic
./stop-nginx.sh
```

---

## Architecture

```
Mobile Browser (HTTPS)
    ↓
https://192.168.1.100:443
    ↓
Nginx Reverse Proxy
    ├─→ localhost:3000 (React frontend)
    └─→ localhost:8000 (FastAPI backend)
```

**Benefits:**
- ✅ Single certificate for both frontend and backend
- ✅ No CORS issues (same origin)
- ✅ Automatic HTTP → HTTPS redirect
- ✅ WebSocket support for voice streaming
- ✅ Works with self-signed certificates

---

## Files Created

| File | Purpose |
|------|---------|
| `ssl/nginx-selfsigned.crt` | SSL certificate (365 days) |
| `ssl/nginx-selfsigned.key` | SSL private key |
| `nginx.conf` | Nginx configuration |
| `start-nginx.sh` | Start nginx script |
| `stop-nginx.sh` | Stop nginx script |

---

## Troubleshooting

### "Connection refused" on mobile

**Check nginx is running:**
```bash
sudo nginx -t -c /home/rodrigo/agentic/nginx.conf
ps aux | grep nginx
```

**Check firewall:**
```bash
# Allow HTTPS port
sudo ufw allow 443/tcp

# Or disable firewall temporarily
sudo ufw disable
```

### "ERR_CERT_AUTHORITY_INVALID"

This is **expected** with self-signed certificates. You must:
1. Click "Advanced" in browser
2. Click "Proceed anyway" / "Accept risk"
3. Certificate will be saved for this device

### "Microphone access denied"

After accepting the certificate:
1. Check browser permissions (🔒 icon in address bar)
2. Allow microphone access for this site
3. Refresh the page
4. Try starting session again

### Backend not reachable

**Verify backend is running:**
```bash
curl http://localhost:8000/api/realtime/conversations
```

**Check nginx proxy:**
```bash
curl -k https://localhost/api/realtime/conversations
```

The `-k` flag skips certificate verification for testing.

### WebSocket connection fails

**Check nginx WebSocket config:**
```bash
# Should see "Upgrade" and "Connection" headers
curl -k -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  https://localhost/api/realtime-voice
```

**Restart nginx if needed:**
```bash
./stop-nginx.sh
./start-nginx.sh
```

---

## Network Requirements

- **Same WiFi network** - Mobile and desktop must be on the same network
- **Ports open:**
  - 443 (HTTPS - nginx)
  - 3000 (frontend - proxied by nginx)
  - 8000 (backend - proxied by nginx)

**Firewall rules:**
```bash
# Allow HTTPS
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

---

## Security Notes

### Self-Signed Certificate

The SSL certificate is **self-signed**, meaning:
- ✅ Encryption is still active (HTTPS)
- ⚠️ Browser will show security warning
- ⚠️ Not suitable for public internet
- ✅ Perfect for local network testing

### Production Deployment

For production or public access:
1. Get a real SSL certificate (Let's Encrypt, etc.)
2. Use a proper domain name
3. Update nginx config with real certificate paths
4. Enable firewall rules properly

---

## Advanced Configuration

### Custom Certificate Domain

If you want to avoid the browser warning, you can:

1. **Add local DNS entry** (requires router access)
   - Map `voice.local` → `192.168.1.100`

2. **Regenerate certificate with custom domain:**
   ```bash
   cd /home/rodrigo/agentic/ssl
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout nginx-selfsigned.key \
     -out nginx-selfsigned.crt \
     -subj "/CN=voice.local"
   ```

3. **Access via:** `https://voice.local/mobile-voice`

### Enable HTTP/2

Edit [nginx.conf](nginx.conf) line 21:
```nginx
listen 443 ssl http2;  # Add http2
```

Then restart nginx.

---

## Testing Checklist

- [ ] Nginx installed and running
- [ ] SSL certificate generated
- [ ] Backend running on localhost:8000
- [ ] Frontend running on localhost:3000
- [ ] Can access desktop: https://localhost
- [ ] Can access mobile: https://[IP]/mobile-voice
- [ ] Mobile accepts certificate warning
- [ ] Mobile can select conversation
- [ ] Mobile can start voice session
- [ ] Mobile can access microphone (HTTPS required!)
- [ ] Mobile receives audio from assistant
- [ ] Events appear in Recent Activity
- [ ] Desktop and mobile synchronized

---

## Quick Commands Reference

```bash
# Install nginx
sudo apt-get install -y nginx

# Start services
cd /home/rodrigo/agentic/backend && uvicorn main:app --reload &
cd /home/rodrigo/agentic/frontend && npm start &
cd /home/rodrigo/agentic && ./start-nginx.sh

# Stop nginx
cd /home/rodrigo/agentic && ./stop-nginx.sh

# Get IP address
hostname -I | awk '{print $1}'

# Test HTTPS locally
curl -k https://localhost
curl -k https://localhost/api/realtime/conversations

# View nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Check nginx status
sudo nginx -t -c /home/rodrigo/agentic/nginx.conf
ps aux | grep nginx
```

---

## Why This Approach?

**Alternative approaches considered:**

1. ❌ **HTTP only** - Mobile browsers block microphone access on HTTP
2. ❌ **Separate HTTPS for frontend and backend** - CORS issues, complex setup
3. ❌ **ngrok/tunneling service** - Requires external service, latency
4. ✅ **Nginx reverse proxy with single cert** - Clean, local, performant

**Benefits of nginx approach:**
- Single HTTPS endpoint for both frontend and backend
- No CORS configuration needed
- Works entirely on local network
- Standard industry practice
- Easy to upgrade to production

---

**Last Updated:** 2025-11-28

For questions or issues, see troubleshooting section above.
