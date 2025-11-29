#!/bin/bash
# Manual nginx startup - run this in your terminal with sudo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF="$SCRIPT_DIR/nginx.conf"

echo "════════════════════════════════════════════════════════"
echo "  NGINX HTTPS STARTUP FOR MOBILE VOICE"
echo "════════════════════════════════════════════════════════"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run with sudo"
    echo ""
    echo "   sudo $0"
    echo ""
    exit 1
fi

echo "📋 Step 1: Stopping system nginx service..."
systemctl stop nginx 2>/dev/null && echo "   ✅ Stopped" || echo "   ⚠️  Not running"
systemctl disable nginx 2>/dev/null && echo "   ✅ Disabled" || echo "   ⚠️  Already disabled"

echo ""
echo "📋 Step 2: Killing any remaining nginx processes..."
pkill nginx 2>/dev/null && echo "   ✅ Killed" || echo "   ⚠️  No processes found"
sleep 1

echo ""
echo "📋 Step 3: Testing nginx configuration..."
if nginx -t -c "$NGINX_CONF" 2>&1 | grep -q "test is successful"; then
    echo "   ✅ Configuration valid"
else
    echo "   ❌ Configuration test failed!"
    nginx -t -c "$NGINX_CONF"
    exit 1
fi

echo ""
echo "📋 Step 4: Starting nginx with HTTPS..."
if nginx -c "$NGINX_CONF"; then
    echo "   ✅ Started successfully!"
else
    echo "   ❌ Failed to start!"
    tail -20 /home/rodrigo/agentic/logs/nginx-error.log
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ NGINX RUNNING WITH HTTPS"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📱 Access URLs:"
echo "   Desktop: https://localhost/mobile-voice"
echo "   Mobile:  https://$(hostname -I | awk '{print $1}')/mobile-voice"
echo ""
echo "⚠️  Certificate Warning:"
echo "   Accept the self-signed certificate in your browser"
echo "   Chrome: Advanced → Proceed anyway"
echo "   Firefox: Advanced → Accept Risk"
echo ""
echo "📊 Logs:"
echo "   Access: tail -f /home/rodrigo/agentic/logs/nginx-access.log"
echo "   Errors: tail -f /home/rodrigo/agentic/logs/nginx-error.log"
echo ""
echo "🛑 To stop:"
echo "   sudo nginx -s stop"
echo ""
echo "════════════════════════════════════════════════════════"
