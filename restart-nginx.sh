#!/bin/bash
# Restart nginx with fresh configuration

echo "🔄 Stopping nginx..."
sudo pkill nginx 2>/dev/null || true
sleep 2

echo "✅ Starting nginx with updated config..."
sudo nginx -c /home/rodrigo/agentic/nginx.conf

echo ""
echo "📋 Nginx processes:"
ps aux | grep nginx | grep -v grep

echo ""
echo "✅ Done! Nginx restarted with fresh configuration."
