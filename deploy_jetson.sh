#!/bin/bash

# Deploy script for Jetson Nano server
# This script pulls latest changes from git and deploys to the Jetson Nano

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
JETSON_IP="192.168.0.200"
JETSON_USER="rodrigo"
JETSON_PASSWORD="rod454c544"
JETSON_PATH="~/agentic"
LOCAL_PATH="/home/rodrigo/agentic"

echo -e "${BLUE}=== Deploying to Jetson Nano (${JETSON_IP}) ===${NC}\n"

# Step 1: Pull latest changes on Jetson
echo -e "${BLUE}[1/5] Pulling latest changes from git on Jetson...${NC}"
sshpass -p "${JETSON_PASSWORD}" ssh -o StrictHostKeyChecking=no ${JETSON_USER}@${JETSON_IP} << 'EOF'
cd ~/agentic
git pull origin main
echo "Git pull completed"
EOF
echo -e "${GREEN}✓ Git pull completed${NC}\n"

# Step 2: Install/update dependencies on Jetson
echo -e "${BLUE}[2/5] Installing dependencies on Jetson...${NC}"
sshpass -p "${JETSON_PASSWORD}" ssh -o StrictHostKeyChecking=no ${JETSON_USER}@${JETSON_IP} << 'EOF'
cd ~/agentic/frontend
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic
npm install --quiet
echo "Dependencies installed"
EOF
echo -e "${GREEN}✓ Dependencies installed${NC}\n"

# Step 3: Build frontend on Jetson
echo -e "${BLUE}[3/5] Building frontend on Jetson...${NC}"
sshpass -p "${JETSON_PASSWORD}" ssh -o StrictHostKeyChecking=no ${JETSON_USER}@${JETSON_IP} << 'EOF'
cd ~/agentic/frontend
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic
npm run build
echo "Build completed"
EOF
echo -e "${GREEN}✓ Frontend build completed${NC}\n"

# Step 4: Reload nginx
echo -e "${BLUE}[4/5] Reloading nginx...${NC}"
sshpass -p "${JETSON_PASSWORD}" ssh -o StrictHostKeyChecking=no -t ${JETSON_USER}@${JETSON_IP} << 'EOF'
echo "rod454c544" | sudo -S kill -HUP $(cat ~/nginx.pid) 2>/dev/null
echo "Nginx reloaded"
EOF
echo -e "${GREEN}✓ Nginx reloaded${NC}\n"

# Step 5: Verify deployment
echo -e "${BLUE}[5/5] Verifying deployment...${NC}"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${JETSON_IP}/agentic/)
HTTPS_STATUS=$(curl -s -k -o /dev/null -w "%{http_code}" https://${JETSON_IP}/agentic/)

if [ "$HTTP_STATUS" = "200" ] && [ "$HTTPS_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Deployment verified${NC}"
    echo -e "  HTTP:  http://${JETSON_IP}/agentic/ - ${HTTP_STATUS}"
    echo -e "  HTTPS: https://${JETSON_IP}/agentic/ - ${HTTPS_STATUS}"
else
    echo -e "${RED}✗ Deployment verification failed${NC}"
    echo -e "  HTTP:  ${HTTP_STATUS}"
    echo -e "  HTTPS: ${HTTPS_STATUS}"
    exit 1
fi

echo -e "\n${GREEN}=== Deployment Complete! ===${NC}"
echo -e "Access your app at: ${BLUE}https://${JETSON_IP}/agentic/${NC}"
