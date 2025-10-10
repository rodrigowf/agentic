#!/bin/bash

# Run Both Backend and Frontend for Agentic Voice Assistant
# This script starts both servers and manages them together

set -e

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Agentic Voice Assistant (Backend + Frontend)...${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate environment (venv or conda)
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo -e "${GREEN}Activating Python virtual environment...${NC}"
    source "$SCRIPT_DIR/venv/bin/activate"
elif command -v conda &> /dev/null; then
    if conda env list | grep -q "^agentic "; then
        echo -e "${GREEN}Activating conda environment 'agentic'...${NC}"
        eval "$(conda shell.bash hook)"
        conda activate agentic
    fi
fi

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${BLUE}Stopping backend (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID
    fi
    if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${BLUE}Stopping frontend (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}Starting backend on http://localhost:8000${NC}"
cd "$SCRIPT_DIR/backend"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "$SCRIPT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "${BLUE}Backend started (PID: $BACKEND_PID)${NC}"

# Wait for backend to start
sleep 3

# Start frontend
echo -e "${GREEN}Starting frontend on http://localhost:3000${NC}"
cd "$SCRIPT_DIR/frontend"
npm start > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo -e "${BLUE}Frontend started (PID: $FRONTEND_PID)${NC}"

echo -e "\n${GREEN}✓ All services started successfully!${NC}"
echo -e "${BLUE}Backend:${NC}  http://localhost:8000"
echo -e "${BLUE}Frontend:${NC} http://localhost:3000"
echo -e "\n${YELLOW}Logs:${NC}"
echo -e "  Backend:  $SCRIPT_DIR/logs/backend.log"
echo -e "  Frontend: $SCRIPT_DIR/logs/frontend.log"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for both processes
wait
