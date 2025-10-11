#!/bin/bash

# Fix X11 Display Authorization and Test Screenshot
# This script sets up proper X11 permissions for screenshots

echo "=================================================="
echo "Setting up X11 Display Authorization"
echo "=================================================="

# Set DISPLAY if not set
export DISPLAY=${DISPLAY:-:0}
echo "✓ DISPLAY set to: $DISPLAY"

# Get current user
CURRENT_USER=${USER:-$(whoami)}
echo "✓ Current user: $CURRENT_USER"

# Grant X11 access
echo ""
echo "Granting X11 access..."

# Method 1: xhost (if available)
if command -v xhost &> /dev/null; then
    xhost +local:$CURRENT_USER 2>/dev/null && echo "✓ xhost access granted" || echo "⚠ xhost failed (might not be needed)"
    xhost +local: 2>/dev/null && echo "✓ xhost local access granted" || true
else
    echo "⚠ xhost not available"
fi

# Check if XAUTHORITY exists
if [ -f "$HOME/.Xauthority" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
    echo "✓ XAUTHORITY: $XAUTHORITY"
else
    echo "⚠ No .Xauthority file found"
fi

# Test if display is accessible
echo ""
echo "Testing X11 display access..."
if command -v xdpyinfo &> /dev/null; then
    if xdpyinfo > /dev/null 2>&1; then
        echo "✓ X11 display is accessible"
    else
        echo "✗ X11 display is NOT accessible"
        echo ""
        echo "Troubleshooting steps:"
        echo "1. If running via SSH, reconnect with: ssh -X user@host"
        echo "2. If local, ensure you're in a graphical session"
        echo "3. Try: export DISPLAY=:0 && xhost +local:"
        echo ""
    fi
else
    echo "⚠ xdpyinfo not available (cannot verify display)"
fi

# Run the test
echo ""
echo "=================================================="
echo "Running Screenshot Test"
echo "=================================================="
echo ""

cd /home/rodrigo/agentic/backend
source venv/bin/activate
python3 tests/integration/test_real_screenshot.py

exit_code=$?

echo ""
echo "=================================================="
if [ $exit_code -eq 0 ]; then
    echo "✓✓✓ TEST PASSED ✓✓✓"
else
    echo "✗✗✗ TEST FAILED ✗✗✗"
    echo ""
    echo "If screenshots still fail, you're likely in a headless environment."
    echo "Use alternative tools instead:"
    echo "  - generate_test_image('description')"
    echo "  - get_sample_image('chart')"
fi
echo "=================================================="

exit $exit_code
