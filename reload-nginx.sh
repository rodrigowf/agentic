#!/bin/bash
# Reload nginx configuration after changes

PID_FILE="/home/rodrigo/agentic/nginx.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "❌ Error: nginx PID file not found at $PID_FILE"
    echo "Is nginx running?"
    exit 1
fi

PID=$(cat "$PID_FILE")

echo "📋 Nginx PID: $PID"
echo "🔄 Reloading nginx configuration..."

# Send HUP signal to reload config (requires sudo if nginx runs as root)
sudo kill -HUP "$PID"

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration reloaded successfully!"
else
    echo "❌ Failed to reload nginx. You may need to run:"
    echo "   sudo kill -HUP $PID"
    exit 1
fi
