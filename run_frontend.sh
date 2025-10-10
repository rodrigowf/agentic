#!/bin/bash

# Run Frontend for Agentic Voice Assistant
# This script starts the React development server

set -e

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Agentic Frontend...${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Activate environment (venv or conda) - frontend needs Node.js
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo -e "${GREEN}Activating Python virtual environment...${NC}"
    source "$SCRIPT_DIR/venv/bin/activate"
    echo -e "${BLUE}Using system Node.js for frontend${NC}"
elif command -v conda &> /dev/null; then
    if conda env list | grep -q "^agentic "; then
        echo -e "${GREEN}Activating conda environment 'agentic'...${NC}"
        eval "$(conda shell.bash hook)"
        conda activate agentic
    else
        echo -e "${BLUE}No virtual environment found. Using system Node.js.${NC}"
    fi
else
    echo -e "${BLUE}No virtual environment found. Using system Node.js.${NC}"
fi

# Start frontend
cd "$FRONTEND_DIR"
echo -e "${GREEN}Starting React dev server on http://localhost:3000${NC}"
npm start
