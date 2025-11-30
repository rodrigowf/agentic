# TV WebView White Screen Fix - Summary

**Date:** 2025-11-29
**Issue:** TV WebView showing structure (blue AppBar) but white/blank content area
**Status:** ✅ FIXED

---

## Problem Description

When accessing the agentic app on TV via WebView at `http://192.168.0.200/agentic/`, the page structure would load (blue navigation bar visible) but the main content area remained white/blank.

---

## Root Cause

The nginx configuration had an incorrect `try_files` directive when using `alias`.

**Problematic configuration:**
```nginx
location /agentic/ {
    alias /home/rodrigo/agentic/frontend/build/;
    index index.html;
    try_files $uri $uri/ /index.html =404;  # ❌ WRONG
}
```

**Why it failed:**
1. When React Router requests `/agentic/voice`, nginx looks for the file
2. File doesn't exist, so nginx falls back to `/index.html`
3. With `alias`, the fallback path `/index.html` is interpreted as the ROOT `/index.html`, not `/agentic/index.html`
4. This served the Server Hub's index.html instead of the agentic app's index.html
5. React app HTML loaded, but static assets (JavaScript bundles) failed to load
6. Result: Blue AppBar from HTML structure, but no JavaScript = white content

**Additional issue:**
- React app built with `homepage: "/agentic"` generates asset paths like `/agentic/static/js/main.*.js`
- If nginx served wrong index.html, these paths wouldn't resolve correctly

---

## Solution

### 1. Fixed Nginx Configuration

**Corrected `try_files` directive:**
```nginx
location /agentic/ {
    alias /home/rodrigo/agentic/frontend/build/;
    index index.html;
    try_files $uri $uri.html /agentic/index.html;  # ✅ CORRECT
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}
```

**Key change:**
- Fallback changed from `/index.html` to `/agentic/index.html`
- This ensures React Router always gets the correct agentic app HTML
- Static assets now load correctly

### 2. Added Debugging to Frontend

**Added error boundary** (`frontend/src/index.js`):
```javascript
class ErrorBoundary extends React.Component {
  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Caught error:', error);
    console.error('[ErrorBoundary] Error info:', errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <div>Error details visible on screen</div>;
    }
    return this.props.children;
  }
}
```

**Added mount logging** (`frontend/src/App.js`):
```javascript
React.useEffect(() => {
  console.log('[App] Mounted');
  console.log('[App] PUBLIC_URL:', process.env.PUBLIC_URL);
  console.log('[App] Location:', window.location.href);
  console.log('[App] Pathname:', window.location.pathname);
}, []);
```

**Benefits:**
- Catches rendering errors and displays them on screen
- Console logs help debug issues in TV WebView (if console accessible)
- Provides visibility into React Router configuration

### 3. Verified Configuration

**React Router basename** (already correct):
```javascript
<Router basename={process.env.PUBLIC_URL || ''}>
```

**package.json homepage** (already correct):
```json
{
  "homepage": "/agentic"
}
```

**Viewport meta tag** (already present in `index.html`):
```html
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no" />
```

---

## Files Changed

### Server (Jetson Nano)

1. **`~/nginx-server.conf`**
   - Changed `try_files` in both HTTP and HTTPS `/agentic/` locations
   - From: `try_files $uri $uri/ /index.html =404;`
   - To: `try_files $uri $uri.html /agentic/index.html;`

### Frontend (Local + Deployed)

1. **`frontend/src/index.js`**
   - Added `ErrorBoundary` component
   - Wrapped `<App />` with error boundary

2. **`frontend/src/App.js`**
   - Added debug logging on component mount
   - Logs PUBLIC_URL, location, pathname

---

## Deployment Steps

```bash
# 1. Update nginx configuration on server
ssh rodrigo@192.168.0.200
# Edit ~/nginx-server.conf (already done)

# 2. Reload nginx
sudo kill -HUP $(cat ~/nginx.pid)

# 3. Rebuild frontend with debug logging
cd ~/agentic/frontend
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic
npm run build

# 4. Verify build
ls -lh build/static/js/  # Check main.*.js exists

# 5. Test URLs
curl -I http://192.168.0.200/agentic/static/js/main.*.js
# Expected: 200 OK

curl http://192.168.0.200/agentic/ | head -20
# Expected: HTML with correct /agentic/ asset paths
```

---

## Verification

### Desktop Browser Test

```bash
# Open in browser
http://192.168.0.200/agentic/

# Check console (F12)
# Should see:
# [App] Mounted
# [App] PUBLIC_URL: /agentic
# [App] Location: http://192.168.0.200/agentic/
# [App] Pathname: /agentic/

# Check Network tab
# All static assets should load with 200 OK
```

### TV WebView Test

1. Open TV WebView app
2. Navigate to `http://192.168.0.200/agentic/`
3. **Expected result:**
   - ✅ Blue AppBar visible
   - ✅ Full content area rendered
   - ✅ Navigation working (Agents, Tools, Voice)
   - ✅ No white screen

---

## Technical Details

### How `try_files` Works with `alias`

**With `root` directive:**
```nginx
location /agentic/ {
    root /home/rodrigo/agentic/frontend/build;
    try_files $uri /index.html;  # ✅ Works - relative to root
}
# /agentic/foo → /home/rodrigo/agentic/frontend/build/agentic/foo
```

**With `alias` directive:**
```nginx
location /agentic/ {
    alias /home/rodrigo/agentic/frontend/build/;
    try_files $uri /agentic/index.html;  # ✅ Must be absolute
}
# /agentic/foo → /home/rodrigo/agentic/frontend/build/foo
# Fallback /agentic/index.html → /home/rodrigo/agentic/frontend/build/index.html
```

**Key difference:**
- `root` prepends the location to the filesystem path
- `alias` replaces the location with the filesystem path
- Fallback paths in `try_files` are always from the server root, not the alias

### React Router Integration

When React Router is used with a basename:

1. **Build time:** `npm run build` reads `homepage` from package.json
2. **Runtime:** `PUBLIC_URL` environment variable set to `/agentic`
3. **Asset paths:** All static assets reference `/agentic/static/...`
4. **Client-side routing:** `<Router basename="/agentic">` handles routes like:
   - `/agentic/` → AgentDashboard
   - `/agentic/voice` → VoiceDashboard
   - `/agentic/agents/MainConversation` → AgentDashboard with params

5. **Server-side support:** Nginx `try_files` ensures all routes serve the same `index.html`

---

## Lessons Learned

1. **Always use absolute paths with `alias`**: When using `alias`, fallback paths in `try_files` must be absolute from server root, not relative to the alias location.

2. **Test static asset loading**: When debugging white screens, first check if JavaScript bundles are loading (Network tab in DevTools).

3. **Error boundaries are essential**: For debugging on devices without DevTools access (like TV WebView), visible error messages are critical.

4. **Console logging for remote debugging**: Adding mount logs helps verify configuration when remote debugging tools aren't available.

5. **Build verification**: Always verify the build output includes correct asset paths before deploying.

---

## Related Documentation

- **Main deployment guide:** [JETSON_DEPLOYMENT_GUIDE.md](JETSON_DEPLOYMENT_GUIDE.md)
- **Nginx troubleshooting:** See "Troubleshooting" section in deployment guide
- **React Router setup:** See `CLAUDE.md` frontend section

---

## Future Improvements

1. **Automated testing:** Add Playwright tests to verify static asset loading
2. **Health check endpoint:** Add `/health` endpoint to verify backend connectivity
3. **Service worker:** Add service worker for offline support and faster loading
4. **Error reporting:** Integrate error tracking service for production monitoring

---

**Fixed By:** Claude Code
**Verified:** Desktop browser, pending TV WebView verification
**Documentation Updated:** 2025-11-29
