#!/bin/bash
# Start nginx with custom configuration for voice assistant HTTPS access

# Don't exit on error during cleanup, only during actual start
set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF="$SCRIPT_DIR/nginx.conf"
NGINX_PID="$SCRIPT_DIR/nginx.pid"

echo "Starting nginx with HTTPS reverse proxy..."

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "ERROR: nginx is not installed!"
    echo "Please run: sudo apt-get install -y nginx"
    exit 1
fi

# Check if SSL certificates exist
if [ ! -f "$SCRIPT_DIR/ssl/nginx-selfsigned.crt" ] || [ ! -f "$SCRIPT_DIR/ssl/nginx-selfsigned.key" ]; then
    echo "ERROR: SSL certificates not found!"
    echo "Expected:"
    echo "  - $SCRIPT_DIR/ssl/nginx-selfsigned.crt"
    echo "  - $SCRIPT_DIR/ssl/nginx-selfsigned.key"
    exit 1
fi

# Stop system nginx service (prevents auto-restart)
echo "Stopping system nginx service..."
sudo systemctl stop nginx 2>/dev/null || true
sudo systemctl disable nginx 2>/dev/null || true

# Kill any remaining nginx processes
echo "Killing any remaining nginx processes..."
sudo pkill -9 nginx 2>/dev/null || true
sleep 1

# Stop existing nginx if running
if [ -f "$NGINX_PID" ]; then
    echo "Stopping existing nginx process..."
    sudo nginx -s stop -c "$NGINX_CONF" 2>/dev/null || true
    rm -f "$NGINX_PID"
fi

# Enable exit on error for the actual nginx start
set -e

# Test configuration
echo "Testing nginx configuration..."
sudo nginx -t -c "$NGINX_CONF"

# Start nginx
echo "Starting nginx..."
sudo nginx -c "$NGINX_CONF"

echo ""
echo "✅ Nginx started successfully!"
echo ""
echo "HTTPS access enabled on:"
echo "  - https://localhost (desktop)"
echo "  - https://$(hostname -I | awk '{print $1}') (mobile)"
echo ""
echo "To stop nginx, run:"
echo "  sudo nginx -s stop -c $NGINX_CONF"
echo ""
echo "⚠️  Mobile users: You'll need to accept the self-signed certificate warning"
echo "    in your browser when first accessing the HTTPS URL."
