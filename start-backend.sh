#!/bin/bash
# Start backend with full WebRTC logging

cd /home/rodrigo/agentic/backend
source venv/bin/activate

# Load .env file if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✓ Loaded environment from .env"
fi

# Check OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
    echo "Set it with: export OPENAI_API_KEY=sk-proj-..."
    echo "Or add to backend/.env file"
    echo ""
fi

# Export debug logging
export LOG_LEVEL=DEBUG

echo "=== Backend Starting ==="
echo "URL: http://localhost:8000"
echo "WebRTC endpoint: POST /api/realtime/webrtc/bridge"
echo "Watch for: [WebRTC] [aiortc] [OpenAI] logs"
echo ""

# Start uvicorn with logging to both console and file
mkdir -p /tmp/agentic-logs
uvicorn main:app --host 0.0.0.0 --port 8000 2>&1 | tee /tmp/agentic-logs/backend.log
