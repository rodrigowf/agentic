# Screenshot Tool - Real Implementation

## Overview

The `take_screenshot` tool has been updated to **actually capture real screenshots** using `pyautogui`. When used with the multimodal agent, the LLM can "see" and describe the actual screen content.

## Implementation Details

**File:** `backend/tools/image_tools.py`

### How It Works

1. **Captures Screenshot:** Uses `pyautogui.screenshot()` to capture the entire screen
2. **Saves to File:** Saves as PNG with timestamp in `workspace/screenshots/`
3. **Returns Path:** Returns file path which multimodal agent detects
4. **Agent Sees Image:** Multimodal agent converts to MultiModalMessage
5. **LLM Describes:** Vision-capable LLM describes the actual screen content

### Code

```python
def take_screenshot(description: str, output_path: Optional[str] = None) -> str:
    """Takes a real screenshot of the current screen."""
    import pyautogui

    # Determine output path
    if output_path:
        file_path = Path(output_path)
    else:
        workspace = Path(os.getcwd()) / "workspace" / "screenshots"
        workspace.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = workspace / f"screenshot_{timestamp}.png"

    # Take screenshot
    screenshot = pyautogui.screenshot()
    screenshot.save(str(file_path))

    return f"Screenshot captured and saved to: {file_path}"
```

## Requirements

### Dependencies

```bash
pip install pyautogui pillow
```

### System Requirements

**For GUI Environments:**
- Works on: Windows, macOS, Linux with X11 display
- Requires: Active display session

**For Headless/Server Environments:**
- ⚠️ **Will NOT work** without display (e.g., SSH sessions, Docker containers, CI/CD)
- Error: `Can't connect to display ":0"`
- Alternative: Use virtual display (Xvfb) or test image generation tools

## Testing

### In GUI Environment (Local Desktop)

```bash
cd backend
source venv/bin/activate
python3 test_real_screenshot.py
```

**Expected Output:**
```
✓ Screenshot was taken
✓ MultiModalMessage was created
✓ Agent provided description
✓ Description contains visual elements: window, screen, terminal, ...
✓ Screenshot file created: screenshot_20251011_055755.png (234.5 KB)

✓✓✓ REAL SCREENSHOT TEST PASSED ✓✓✓
```

### In Headless Environment

The tool will gracefully fail with an error message. Use `generate_test_image` or `get_sample_image` instead.

## Usage with Multimodal Agent

### Agent Configuration

```json
{
  "name": "ScreenshotAgent",
  "agent_type": "multimodal_tools_looping",
  "tools": ["take_screenshot"],
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.0
  },
  "prompt": {
    "system": "You can take screenshots and describe what you see. Use the take_screenshot tool and analyze the image."
  },
  "max_consecutive_auto_reply": 10,
  "reflect_on_tool_use": true
}
```

### Example Interaction

# Screenshot Tool – Enablement Guide

This guide explains how to get the `take_screenshot` tool working end-to-end so
the multimodal agent can capture and describe real screen images instead of
falling back to placeholder graphics.

---

## 1. How the Tool Captures Screenshots

- **Primary (Python) capture** – uses [`mss`](https://github.com/BoboTiG/python-mss)
  which works on Windows, macOS, and X11/Wayland Linux when a graphical session
  is available.
- **Secondary (Python) capture** – falls back to `pyautogui.screenshot()` if
  `mss` is missing or fails (commonly works on macOS, Windows, X11).
- **CLI fallback** – tries Wayland utilities (`grim`, `hyprshot`), X11 tools
  (`scrot`), or macOS `screencapture` depending on what’s installed.
- **Placeholder mode** – when every capture option fails or a black frame is
  produced (typical in headless environments), the tool generates an annotated
  placeholder image explaining the failure and how to fix it.

See implementation in `backend/tools/image_tools.py`.

---

## 2. Install Python Dependencies

These are already listed in `backend/requirements.txt`. Install them into the
backend virtualenv:

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

Key packages:

- `mss` – cross-platform screenshots from Python
- `pyautogui` – fallback screenshot API (requires Pillow)
- `Pillow` – image manipulation + placeholder rendering

If you prefer a one-off install without touching requirements:

```bash
backend/venv/bin/pip install mss pyautogui Pillow
```

---

## 3. Operating System Setup

### Linux (Wayland)

Wayland blocks legacy screenshot paths by default. Install at least one native
utility and allow applications to capture the screen.

```bash
# Debian/Ubuntu
sudo apt-get install grim slurp

# Fedora
sudo dnf install grim slurp

# Arch
sudo pacman -S grim slurp

# Allow screenshots in GNOME settings (Settings → Privacy → Screen Sharing)
```

Optional (Hyprland/Sway users):

```bash
sudo pacman -S hyprshot   # Arch example
```

Ensure the tool can access the display:

```bash
# For XWayland apps launched via terminal
export XDG_SESSION_TYPE=wayland
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}
```

### Linux (X11)

```bash
sudo apt-get install scrot   # or any equivalent screenshot CLI
xhost +local:                # grant local clients access if needed
```

If running over SSH: connect with X11 forwarding (`ssh -X user@host`) or use a
virtual display (see §4).

### macOS

- No extra CLI tools required; `mss` and `pyautogui` work out of the box once
  you grant screen recording permission (System Settings → Privacy & Security →
  Screen Recording → enable terminal app).

### Windows

- `mss`/`pyautogui` work on Windows 10+. No additional configuration required.

---

## 4. Headless / Remote Servers (CI, Docker, SSH without Desktop)

Headless servers have no live desktop buffer, so every capture attempt returns a
black frame. There are two options:

1. **Run a virtual display (Xvfb)**

   ```bash
   sudo apt-get install xvfb
   xvfb-run -a backend/venv/bin/python test_real_screenshot.py
   ```

   Inside the Xvfb session you’ll need to launch the UI you’re trying to
   capture (e.g., start your application before calling `take_screenshot`).

2. **Use mock image tools**

   When you only need deterministic images for testing, rely on
   `generate_test_image` or `get_sample_image` instead of real screenshots.

---

## 5. Verification Checklist

1. **Install Python deps**: `mss`, `pyautogui`, `Pillow`
2. **Ensure display access**: you’re in a real desktop session or Xvfb
3. **Install OS capture tool** (Wayland → `grim`, X11 → `scrot`) if Python
   capture cannot access the display
4. **Run the manual smoke test**:

   ```bash
   PYTHONPATH=backend backend/venv/bin/python - <<'PY'
   from tools.image_tools import take_screenshot
   print(take_screenshot('Manual verification'))
   PY
   ```

5. **Inspect the PNG** in `workspace/screenshots/` – it should show your actual
   desktop rather than the dark placeholder.

6. **Run the agent integration test** (requires OpenAI API key):

   ```bash
   backend/venv/bin/python backend/test_real_screenshot.py
   ```

---

## 6. Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| Placeholder image referencing “Captured image appears to be all black” | Running in headless session or missing permissions | Start a desktop session, enable screen capture permissions, or run under Xvfb |
| “mss not installed” | Dependency missing | `pip install mss` |
| “pyautogui capture failed: X connection failed” | Wayland blocked access | Enable screen capture in privacy settings or install Wayland-native tool |
| CLI fallback returns exit code 1 | `grim`/`scrot` not installed | Install relevant CLI utility |
| macOS: prompt to allow screen recording | Privacy permission not granted | Allow the terminal/IDE under System Settings |

View application logs (`logs/backend.log`) for additional details.

---

## 7. FAQ

**Q: Can I force the tool to use a specific backend?**

Set environment variables before launching the backend:

```bash
export SCREENSHOT_BACKEND=pyautogui   # or mss / grim / scrot
```

When set, the tool will attempt that backend first and report an error if it
fails.

**Q: How do I capture a specific monitor?**

`mss` supports monitor indices. Extend the tool (TODO) to honor
`SCREENSHOT_MONITOR=2` or adjust the code where noted in `image_tools.py`.

**Q: Why is the PNG completely transparent?**

Some tiling compositors block capture of application content. Enable
“Allow Applications to Capture” in compositor settings or run under X11/Xvfb.

---

## 8. Summary

- ✅ Python + CLI capture backends configured
- ✅ Placeholder mode prevents empty black images and gives actionable guidance
- ✅ Requirements and documentation updated
- � Real capture still requires a graphical session (Wayland/X11, macOS,
  Windows, or virtual display)

**Last updated:** 2025-10-11
