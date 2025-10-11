#!/bin/bash

echo "========================================================================"
echo "Fix gnome-screenshot for Wayland"
echo "========================================================================"
echo ""

# Remove snap version if it exists
echo "[1/4] Checking for snap version..."
if snap list gnome-screenshot &>/dev/null; then
    echo "  → Removing snap version..."
    sudo snap remove gnome-screenshot
else
    echo "  ✓ No snap version found"
fi

# Update apt
echo ""
echo "[2/4] Updating apt package list..."
sudo apt-get update

# Reinstall gnome-screenshot from apt
echo ""
echo "[3/4] Reinstalling gnome-screenshot from apt..."
sudo apt-get install --reinstall gnome-screenshot -y

# Test it
echo ""
echo "[4/4] Testing gnome-screenshot..."
echo ""

if gnome-screenshot --version &>/dev/null; then
    echo "✓ gnome-screenshot version:"
    gnome-screenshot --version
    echo ""

    # Try to take a test screenshot
    echo "Testing screenshot capture..."
    TEST_FILE="/tmp/gnome_screenshot_test_$(date +%s).png"

    if gnome-screenshot --file="$TEST_FILE" 2>&1; then
        if [ -f "$TEST_FILE" ]; then
            SIZE=$(du -h "$TEST_FILE" | cut -f1)
            echo "✅ SUCCESS! Screenshot captured: $TEST_FILE ($SIZE)"
            echo ""
            echo "Now test the Python function:"
            echo "  cd /home/rodrigo/agentic/backend"
            echo "  source venv/bin/activate"
            echo "  python3 test_screenshot.py"
        else
            echo "⚠️  Command ran but no file created"
        fi
    else
        echo "❌ gnome-screenshot still has errors"
        echo ""
        echo "The library conflict persists. You may need to:"
        echo "  1. Switch to X11 session (logout → select 'Ubuntu on Xorg')"
        echo "  2. Or install alternative: sudo apt-get install flameshot"
    fi
else
    echo "❌ gnome-screenshot not working"
fi

echo ""
echo "========================================================================"
echo "Done!"
echo "========================================================================"
