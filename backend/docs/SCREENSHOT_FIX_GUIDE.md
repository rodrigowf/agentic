# How to Fix Screenshot Capture on GNOME Wayland

## Quick Solutions (Choose One)

### Option 1: Use XWayland Backend (Recommended - Easiest)

Set an environment variable to force X11 compatibility mode:

```bash
# Test it temporarily
export GDK_BACKEND=x11
export QT_QPA_PLATFORM=xcb

# Then run your screenshot test
cd /home/rodrigo/agentic/backend
source venv/bin/activate
python3 test_screenshot.py
```

To make it permanent:
```bash
# Add to your ~/.bashrc or ~/.profile
echo 'export GDK_BACKEND=x11' >> ~/.bashrc
echo 'export QT_QPA_PLATFORM=xcb' >> ~/.bashrc
source ~/.bashrc
```

---

### Option 2: Switch to X11 Session (Most Compatible)

**Steps:**
1. Log out of your current session
2. At the login screen, click the gear icon (⚙️) in bottom-right corner
3. Select **"Ubuntu on Xorg"** or **"GNOME on X11"** (instead of Wayland)
4. Log back in

**Verify you're on X11:**
```bash
echo $XDG_SESSION_TYPE  # Should output "x11" not "wayland"
```

---

### Option 3: Fix gnome-screenshot (GNOME Native)

The gnome-screenshot tool has a library conflict. Fix it:

```bash
# Remove the broken snap version
sudo snap remove gnome-screenshot 2>/dev/null

# Reinstall from apt
sudo apt-get update
sudo apt-get install --reinstall gnome-screenshot

# Test it
gnome-screenshot --file=/tmp/test.png
```

---

### Option 4: Install Alternative Screenshot Tool

Install a tool that works better with Wayland:

```bash
# Install flameshot (works on both X11 and Wayland)
sudo apt-get install flameshot

# Test it
flameshot full --path /tmp/test.png
```

Then update the screenshot function to use flameshot (I can help with this).

---

### Option 5: Grant D-Bus Screenshot Permission

Allow programmatic screenshots via D-Bus:

```bash
# Create D-Bus policy file
sudo tee /etc/dbus-1/session.d/org.gnome.Shell.Screenshot.conf << 'EOF'
<!DOCTYPE busconfig PUBLIC
 "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <policy user="rodrigo">
    <allow send_destination="org.gnome.Shell.Screenshot"/>
    <allow send_interface="org.gnome.Shell.Screenshot"/>
  </policy>
</busconfig>
EOF

# Reload D-Bus configuration
dbus-send --session --type=method_call --dest=org.freedesktop.DBus \
  / org.freedesktop.DBus.ReloadConfig

# Log out and back in for changes to take effect
```

---

## Testing After Changes

After applying any fix, test with:

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
python3 test_screenshot.py
```

Or test directly:

```bash
source venv/bin/activate
python3 << 'EOF'
from tools.image_tools import take_screenshot
result = take_screenshot("Test after fix")
print(result)
EOF
```

---

## Which Option Should You Choose?

| Option | Difficulty | Effectiveness | Notes |
|--------|-----------|---------------|-------|
| **Option 1: XWayland** | ⭐ Easy | ✅ High | Temporary fix, works immediately |
| **Option 2: X11 Session** | ⭐⭐ Medium | ✅✅ Highest | Most compatible, requires logout |
| **Option 3: Fix gnome-screenshot** | ⭐ Easy | ✅ Medium | May still have Wayland issues |
| **Option 4: Install flameshot** | ⭐⭐ Medium | ✅✅ High | Requires code update |
| **Option 5: D-Bus policy** | ⭐⭐⭐ Hard | ✅ Medium | Advanced, may need more config |

**Recommendation:** Try **Option 1 (XWayland)** first - it's the easiest and usually works!

---

## Alternative: Use the Working Image Tools

If you don't need actual screenshots, the other image tools work perfectly:

```python
# Generate custom test images
generate_test_image("Your description", width=800, height=600)

# Generate sample charts/diagrams
get_sample_image("chart")
get_sample_image("diagram")
get_sample_image("photo")
```

These are often better for testing multimodal agents anyway since you control the content!

---

## Need Help?

Let me know which option you'd like to try, and I can help you implement it!
