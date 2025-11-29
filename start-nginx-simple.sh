#!/bin/bash
# Simple nginx HTTPS startup script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF="$SCRIPT_DIR/nginx.conf"

echo "🔄 Stopping system nginx..."
sudo systemctl stop nginx 2>/dev/null
sudo systemctl disable nginx 2>/dev/null

echo "🔄 Killing any nginx processes..."
sudo pkill nginx 2>/dev/null
sleep 2

echo "✅ Testing nginx configuration..."
if ! sudo nginx -t -c "$NGINX_CONF"; then
    echo "❌ Configuration test failed!"
    exit 1
fi

echo "🚀 Starting nginx with HTTPS..."
if sudo nginx -c "$NGINX_CONF"; then
    echo ""
    echo "✅ Nginx started successfully!"
    echo ""
    echo "📱 Access from:"
    echo "   Desktop: https://localhost/mobile-voice"
    echo "   Mobile:  https://$(hostname -I | awk '{print $1}')/mobile-voice"
    echo ""
    echo "⚠️  Accept the certificate warning in your browser"
    echo ""
    echo "🛑 To stop: sudo nginx -s stop"
else
    echo "❌ Failed to start nginx!"
    exit 1
fi
