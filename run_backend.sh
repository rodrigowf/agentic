#!/bin/bash

# Run Backend for Agentic Voice Assistant
# This script starts the FastAPI backend server

set -e

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Agentic Backend...${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

# Activate Python environment (venv or conda)
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo -e "${GREEN}Activating Python virtual environment...${NC}"
    source "$SCRIPT_DIR/venv/bin/activate"
elif command -v conda &> /dev/null; then
    if conda env list | grep -q "^agentic "; then
        echo -e "${GREEN}Activating conda environment 'agentic'...${NC}"
        eval "$(conda shell.bash hook)"
        conda activate agentic
    else
        echo -e "${BLUE}No virtual environment found. Using system Python.${NC}"
    fi
else
    echo -e "${BLUE}No virtual environment found. Using system Python.${NC}"
fi

# Check for .env file
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${RED}Warning: .env file not found in backend/${NC}"
    echo -e "${BLUE}Please create backend/.env with your API keys:${NC}"
    echo "  OPENAI_API_KEY=your_key_here"
    echo "  ANTHROPIC_API_KEY=your_key_here"
    echo ""
fi

# Start backend
cd "$BACKEND_DIR"
echo -e "${GREEN}Starting uvicorn server on http://localhost:8000${NC}"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
