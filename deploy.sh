#!/bin/bash
# Agentic Voice Assistant - Automated Deployment Script
# Last Updated: 2025-11-29

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}🚀 Agentic Voice Assistant Deployment${NC}"
echo "====================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo -e "${RED}❌ Please run as regular user (not root)${NC}"
  echo "   Usage: ./deploy.sh"
  exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo -e "${RED}❌ Cannot detect OS${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Detected OS: $OS $VER"
echo ""

# Check for required commands
echo -e "${BLUE}📋 Checking prerequisites...${NC}"

command -v python3 >/dev/null 2>&1 || { echo -e "${YELLOW}⚠  python3 not found - will install${NC}"; NEED_PYTHON=1; }
command -v node >/dev/null 2>&1 || { echo -e "${YELLOW}⚠  node not found - will install${NC}"; NEED_NODE=1; }
command -v git >/dev/null 2>&1 || { echo -e "${YELLOW}⚠  git not found - will install${NC}"; NEED_GIT=1; }
command -v nginx >/dev/null 2>&1 || { echo -e "${YELLOW}⚠  nginx not found - will install${NC}"; NEED_NGINX=1; }

# Install system dependencies if needed
if [ -n "$NEED_PYTHON" ] || [ -n "$NEED_NODE" ] || [ -n "$NEED_GIT" ] || [ -n "$NEED_NGINX" ]; then
    echo ""
    echo -e "${BLUE}📦 Installing system dependencies...${NC}"

    if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt update

        [ -n "$NEED_PYTHON" ] && sudo apt install -y python3 python3-pip python3-venv
        [ -n "$NEED_GIT" ] && sudo apt install -y git
        [ -n "$NEED_NGINX" ] && sudo apt install -y nginx

        if [ -n "$NEED_NODE" ]; then
            # Install Node.js 18.x via NodeSource
            curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
            sudo apt install -y nodejs
        fi

        # Optional: Chromium for screenshot tools
        sudo apt install -y chromium-browser 2>/dev/null || true

    else
        echo -e "${YELLOW}⚠  Unsupported OS. Please install manually:${NC}"
        echo "   - Python 3.9+"
        echo "   - Node.js 16+"
        echo "   - Git"
        echo "   - Nginx"
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} System dependencies ready"
echo ""

# Backend setup
echo -e "${BLUE}🐍 Setting up backend...${NC}"
cd "$SCRIPT_DIR/backend"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Created Python virtual environment"
else
    echo -e "${GREEN}✓${NC} Virtual environment already exists"
fi

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo -e "${GREEN}✓${NC} Backend dependencies installed"

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠  Creating .env template${NC}"
    cat > .env << 'EOF'
# API Keys (REQUIRED)
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Optional API Keys
GOOGLE_API_KEY=your-google-api-key-here

# Database
VOICE_CONVERSATION_DB_PATH=voice_conversations.db

# Logging
LOG_LEVEL=INFO

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chroma_db
EOF
    echo -e "${RED}❌ Please edit backend/.env and add your API keys${NC}"
    ENV_NEEDS_EDIT=1
else
    echo -e "${GREEN}✓${NC} .env file exists"
fi

deactivate
echo ""

# Frontend setup
echo -e "${BLUE}⚛️  Setting up frontend...${NC}"
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo "   Installing npm packages (this may take a few minutes)..."
    npm install --quiet
    echo -e "${GREEN}✓${NC} Frontend dependencies installed"
else
    echo -e "${GREEN}✓${NC} Frontend dependencies already installed"
fi

echo ""

# Create required directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p "$SCRIPT_DIR/backend/workspace"
mkdir -p "$SCRIPT_DIR/backend/chroma_db"
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/debug/screenshots"
mkdir -p "$SCRIPT_DIR/debug/db_exports"
mkdir -p "$SCRIPT_DIR/ssl"

echo -e "${GREEN}✓${NC} Directories created"
echo ""

# Get IP address for HTTPS setup
IP_ADDR=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Next Steps:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -n "$ENV_NEEDS_EDIT" ]; then
    echo -e "${YELLOW}1. Edit API keys:${NC}"
    echo "   nano $SCRIPT_DIR/backend/.env"
    echo ""
fi

echo -e "${GREEN}2. Start Backend:${NC}"
echo "   cd $SCRIPT_DIR/backend"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload --host 0.0.0.0"
echo ""

echo -e "${GREEN}3. Start Frontend (in new terminal):${NC}"
echo "   cd $SCRIPT_DIR/frontend"
echo "   npm start"
echo ""

echo -e "${GREEN}4. Access Application:${NC}"
echo "   Local:  http://localhost:3000"
echo "   Voice:  http://localhost:3000/voice"
echo ""

echo -e "${BLUE}For Mobile Access (HTTPS):${NC}"
echo ""
echo "   Your IP: $IP_ADDR"
echo ""
echo "   1. Generate SSL certificate:"
echo "      cd $SCRIPT_DIR"
echo "      openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\"
echo "        -keyout ssl/nginx-selfsigned.key \\"
echo "        -out ssl/nginx-selfsigned.crt \\"
echo "        -subj \"/C=US/ST=State/L=City/O=Org/CN=$IP_ADDR\""
echo ""
echo "   2. Start nginx:"
echo "      nginx -c $SCRIPT_DIR/nginx.conf"
echo ""
echo "   3. Access from mobile:"
echo "      https://$IP_ADDR/mobile-voice"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo "   Full guide: docs/DEPLOYMENT_GUIDE.md"
echo "   Dev guide:  CLAUDE.md"
echo ""

if [ -n "$ENV_NEEDS_EDIT" ]; then
    echo -e "${RED}⚠️  Don't forget to edit backend/.env with your API keys!${NC}"
fi
