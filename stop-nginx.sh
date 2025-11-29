#!/bin/bash
# Stop nginx reverse proxy

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF="$SCRIPT_DIR/nginx.conf"
NGINX_PID="$SCRIPT_DIR/nginx.pid"

echo "Stopping nginx..."

# Stop nginx
sudo nginx -s stop -c "$NGINX_CONF" 2>/dev/null || {
    echo "Nginx not running or already stopped"
}

# Clean up PID file
rm -f "$NGINX_PID"

echo "✅ Nginx stopped"
