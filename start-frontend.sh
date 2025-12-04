#!/bin/bash
# Start frontend with logging

cd /home/rodrigo/agentic/frontend

# Load nvm
source ~/.nvm/nvm.sh
nvm use default

echo "=== Frontend Starting ==="
echo "URL: http://localhost:3000/agentic/voice"
echo "Browser DevTools: Check console for [WebRTC Bridge] logs"
echo ""

# Start React dev server with logging to both console and file
mkdir -p /tmp/agentic-logs
npm start 2>&1 | tee /tmp/agentic-logs/frontend.log
