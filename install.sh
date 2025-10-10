#!/bin/bash

# Agentic AI System - Installation Script
# This script checks for dependencies and sets up the environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get version number
get_version() {
    local cmd=$1
    local version_output=$($cmd 2>&1)
    echo "$version_output" | grep -oP '\d+\.\d+\.\d+' | head -1
}

# Function to compare versions
version_ge() {
    # Returns 0 if version $1 >= version $2
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]
}

print_header "Agentic AI System - Installation"

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "Project root: ${GREEN}${PROJECT_ROOT}${NC}"

# Step 1: Check for Node.js
print_header "Step 1: Checking Node.js"

NODE_REQUIRED_VERSION="20.0.0"
NODE_INSTALLED=false

if command_exists node; then
    NODE_VERSION=$(node --version | sed 's/v//')
    echo "Found Node.js version: $NODE_VERSION"

    if version_ge "$NODE_VERSION" "$NODE_REQUIRED_VERSION"; then
        print_success "Node.js version $NODE_VERSION is sufficient (>= $NODE_REQUIRED_VERSION)"
        NODE_INSTALLED=true
    else
        print_warning "Node.js version $NODE_VERSION is too old (need >= $NODE_REQUIRED_VERSION)"
    fi
else
    print_warning "Node.js not found"
fi

# Step 2: Check for Python3 and pip
print_header "Step 2: Checking Python3 and pip"

PYTHON_REQUIRED_VERSION="3.9.0"
PYTHON_INSTALLED=false
PIP_INSTALLED=false

if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "Found Python version: $PYTHON_VERSION"

    if version_ge "$PYTHON_VERSION" "$PYTHON_REQUIRED_VERSION"; then
        print_success "Python version $PYTHON_VERSION is sufficient (>= $PYTHON_REQUIRED_VERSION)"
        PYTHON_INSTALLED=true
    else
        print_warning "Python version $PYTHON_VERSION is too old (need >= $PYTHON_REQUIRED_VERSION)"
    fi
else
    print_warning "Python3 not found"
fi

if command_exists pip3 || command_exists pip; then
    print_success "pip is installed"
    PIP_INSTALLED=true
else
    print_warning "pip not found"
fi

# Check for venv module
VENV_AVAILABLE=false
if [ "$PYTHON_INSTALLED" = true ]; then
    if python3 -m venv --help >/dev/null 2>&1; then
        print_success "Python venv module is available"
        VENV_AVAILABLE=true
    else
        print_warning "Python venv module not available"
    fi
fi

# Step 3: Check if we need conda
print_header "Step 3: Determining installation strategy"

USE_CONDA=false
USE_VENV=false

# Decide between conda and venv
if [ "$NODE_INSTALLED" = false ] || [ "$PYTHON_INSTALLED" = false ] || [ "$PIP_INSTALLED" = false ]; then
    print_warning "Some dependencies are missing or outdated"
    print_info "Will use conda for complete environment setup (Python + Node.js)"

    if command_exists conda; then
        print_success "Conda is available, will use it for environment setup"
        USE_CONDA=true
    else
        print_warning "Conda not found, will install Miniconda"

        # Install Miniconda
        print_header "Installing Miniconda"

        MINICONDA_INSTALLER="/tmp/miniconda_installer.sh"

        # Detect architecture
        if [[ $(uname -m) == "x86_64" ]]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        elif [[ $(uname -m) == "aarch64" ]] || [[ $(uname -m) == "arm64" ]]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"
        else
            print_error "Unsupported architecture: $(uname -m)"
            exit 1
        fi

        print_info "Downloading Miniconda from: $MINICONDA_URL"
        curl -fsSL "$MINICONDA_URL" -o "$MINICONDA_INSTALLER"

        print_info "Installing Miniconda to $HOME/miniconda3"
        bash "$MINICONDA_INSTALLER" -b -p "$HOME/miniconda3"

        # Initialize conda
        "$HOME/miniconda3/bin/conda" init bash

        # Source conda
        source "$HOME/miniconda3/etc/profile.d/conda.sh"

        print_success "Miniconda installed successfully"
        rm -f "$MINICONDA_INSTALLER"

        USE_CONDA=true
    fi
elif [ "$VENV_AVAILABLE" = false ]; then
    print_warning "Python venv module not available"
    print_info "Will use conda for environment isolation"

    if command_exists conda; then
        print_success "Conda is available, will use it for environment setup"
        USE_CONDA=true
    else
        print_warning "Conda not found, will install Miniconda"

        # Install Miniconda
        print_header "Installing Miniconda"

        MINICONDA_INSTALLER="/tmp/miniconda_installer_venv.sh"

        # Detect architecture
        if [[ $(uname -m) == "x86_64" ]]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        elif [[ $(uname -m) == "aarch64" ]] || [[ $(uname -m) == "arm64" ]]; then
            MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"
        else
            print_error "Unsupported architecture: $(uname -m)"
            exit 1
        fi

        print_info "Downloading Miniconda from: $MINICONDA_URL"
        curl -fsSL "$MINICONDA_URL" -o "$MINICONDA_INSTALLER"

        print_info "Installing Miniconda to $HOME/miniconda3"
        bash "$MINICONDA_INSTALLER" -b -p "$HOME/miniconda3"

        # Initialize conda
        "$HOME/miniconda3/bin/conda" init bash

        # Source conda
        source "$HOME/miniconda3/etc/profile.d/conda.sh"

        print_success "Miniconda installed successfully"
        rm -f "$MINICONDA_INSTALLER"

        USE_CONDA=true
    fi
else
    print_success "All dependencies satisfied (Node.js >= 20, Python >= 3.9, venv available)"
    print_info "Will use Python venv for environment isolation"
    USE_VENV=true
fi

# Step 4: Setup environment
print_header "Step 4: Setting up environment"

if [ "$USE_CONDA" = true ]; then
    print_info "Creating conda environment 'agentic'"

    # Source conda if not already sourced
    if ! command_exists conda; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh" 2>/dev/null || true
    fi

    # Create conda environment with Python 3.11 and Node.js
    conda create -n agentic python=3.11 nodejs=20 -y

    print_success "Conda environment 'agentic' created"
    print_info "To activate: conda activate agentic"

    # Activate the environment for the rest of the script
    source activate agentic 2>/dev/null || conda activate agentic

    print_success "Environment activated"
elif [ "$USE_VENV" = true ]; then
    print_info "Creating Python virtual environment in venv/"

    # Create venv directory
    python3 -m venv "$PROJECT_ROOT/venv"

    print_success "Virtual environment created"

    # Activate the environment for the rest of the script
    source "$PROJECT_ROOT/venv/bin/activate"

    print_success "Virtual environment activated"
    print_info "Python packages will be installed in: $PROJECT_ROOT/venv"
    print_info "Node.js will use system installation (>= 20)"
else
    print_success "Using system Python and Node.js"
fi

# Step 5: Install Python dependencies
print_header "Step 5: Installing Python dependencies"

cd "$PROJECT_ROOT/backend"

if [ -f "requirements.txt" ]; then
    print_info "Installing from requirements.txt..."
    pip install -r requirements.txt
    print_success "Python dependencies installed"
else
    print_error "requirements.txt not found in backend/"
    exit 1
fi

# Step 6: Install Node.js dependencies
print_header "Step 6: Installing Node.js dependencies"

cd "$PROJECT_ROOT/frontend"

if [ -f "package.json" ]; then
    print_info "Installing npm packages..."
    npm install
    print_success "Node.js dependencies installed"
else
    print_error "package.json not found in frontend/"
    exit 1
fi

# Step 7: Install debug tools dependencies
print_header "Step 7: Installing debug tools"

cd "$PROJECT_ROOT/_debug"

if [ -f "package.json" ]; then
    print_info "Installing debug tools npm packages..."
    npm install
    print_success "Debug tools installed"
else
    print_warning "Debug tools package.json not found, skipping"
fi

# Step 8: Setup environment variables
print_header "Step 8: Checking environment variables"

cd "$PROJECT_ROOT/backend"

if [ ! -f ".env" ]; then
    print_warning ".env file not found in backend/"
    print_info "Creating .env template..."

    cat > .env << 'EOF'
# API Keys (required)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional API Keys
GOOGLE_API_KEY=your_google_api_key_here

# Database
DATABASE_PATH=voice_conversations.db

# Server Configuration
HOST=0.0.0.0
PORT=8000
EOF

    print_warning "Please edit backend/.env and add your API keys"
else
    print_success ".env file exists"
fi

# Step 9: Verify run scripts
print_header "Step 9: Verifying run scripts"

cd "$PROJECT_ROOT"

# Check if run scripts exist
if [ -f "run_backend.sh" ] && [ -f "run_frontend.sh" ] && [ -f "run_all.sh" ]; then
    # Make sure they're executable
    chmod +x run_backend.sh run_frontend.sh run_all.sh
    print_success "Run scripts are ready (run_backend.sh, run_frontend.sh, run_all.sh)"
else
    print_warning "Run scripts not found in project root"
    print_info "You may need to create them manually or they should be in the repository"
fi

# Final summary
print_header "Installation Complete!"

echo ""
print_success "All dependencies installed successfully!"
echo ""
print_info "Next steps:"
echo ""
echo "  1. Edit backend/.env and add your API keys:"
echo "     ${BLUE}nano backend/.env${NC}"
echo ""
echo "  2. Run the services:"
echo "     ${GREEN}./run_all.sh${NC}         (runs both backend and frontend)"
echo "     ${GREEN}./run_backend.sh${NC}     (runs only backend)"
echo "     ${GREEN}./run_frontend.sh${NC}    (runs only frontend)"
echo ""

if [ "$USE_CONDA" = true ]; then
    print_info "Conda environment created: 'agentic'"
    echo "  To activate manually: ${GREEN}conda activate agentic${NC}"
    echo ""
elif [ "$USE_VENV" = true ]; then
    print_info "Python virtual environment created: 'venv/'"
    echo "  To activate manually: ${GREEN}source venv/bin/activate${NC}"
    echo ""
fi

print_info "Access points:"
echo "  Backend API:  ${BLUE}http://localhost:8000${NC}"
echo "  Frontend UI:  ${BLUE}http://localhost:3000${NC}"
echo "  API Docs:     ${BLUE}http://localhost:8000/docs${NC}"
echo ""

print_success "Happy coding! 🚀"
echo ""
