#!/bin/bash
# Interactive WebRTC Voice Session Setup
# Launches backend and frontend with full logging

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== WebRTC Voice Session Setup ===${NC}\n"

# Check OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY not set${NC}"
    echo "Please set it before starting:"
    echo "  export OPENAI_API_KEY=sk-proj-..."
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create logs directory
mkdir -p /tmp/agentic-logs

# Backend setup
echo -e "${BLUE}Backend:${NC} http://localhost:8000"
echo "  Logs: /tmp/agentic-logs/backend.log"
echo "  Terminal: Watch for WebRTC bridge logs, aiortc state, OpenAI events"
echo ""

# Frontend setup
echo -e "${BLUE}Frontend:${NC} http://localhost:3000/agentic/voice"
echo "  Logs: /tmp/agentic-logs/frontend.log"
echo "  Browser DevTools: [WebRTC Bridge] logs from VoiceAssistantModular"
echo ""

echo -e "${GREEN}Starting services...${NC}\n"

# Start backend in background
cd /home/rodrigo/agentic/backend
source venv/bin/activate
export LOG_LEVEL=DEBUG
echo -e "${BLUE}[Backend]${NC} Starting uvicorn on port 8000..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 2>&1 | tee /tmp/agentic-logs/backend.log &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/agents > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend ready${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠️  Backend startup timeout${NC}"
    fi
done

# Start frontend in background
cd /home/rodrigo/agentic/frontend
source ~/.nvm/nvm.sh
nvm use default > /dev/null 2>&1
echo -e "${BLUE}[Frontend]${NC} Starting React dev server on port 3000..."
npm start 2>&1 | tee /tmp/agentic-logs/frontend.log &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "Waiting for frontend to be ready..."
for i in {1..60}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend ready${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 60 ]; then
        echo -e "${YELLOW}⚠️  Frontend startup timeout${NC}"
    fi
done

echo ""
echo -e "${GREEN}=== Services Running ===${NC}"
echo -e "${BLUE}Backend PID:${NC}  $BACKEND_PID"
echo -e "${BLUE}Frontend PID:${NC} $FRONTEND_PID"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Open browser: http://localhost:3000/agentic/voice"
echo "2. Open browser DevTools console (F12)"
echo "3. Click 'Start Session' and speak"
echo "4. Monitor logs:"
echo "   - Backend:  tail -f /tmp/agentic-logs/backend.log"
echo "   - Frontend: tail -f /tmp/agentic-logs/frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both services${NC}"

# Trap Ctrl+C to kill both processes
trap "echo -e '\n${YELLOW}Stopping services...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for user interrupt
wait
