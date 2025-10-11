# Backend Scripts

This directory contains utility scripts for development, testing, and system configuration.

## Available Scripts

### fix_x11_and_test.sh
**Purpose:** Set up X11 display permissions and test screenshot functionality

**Usage:**
```bash
bash scripts/fix_x11_and_test.sh
```

**What it does:**
1. Sets up X11 display authorization using xhost
2. Checks for .Xauthority file
3. Verifies X11 display accessibility
4. Runs the real screenshot integration test
5. Reports success or failure with troubleshooting tips

**When to use:**
- When screenshot tests are failing due to X11 permission issues
- After switching from Wayland to X11 session
- When running in remote/SSH sessions

---

### fix_gnome_screenshot.sh
**Purpose:** Fix broken gnome-screenshot installation

**Usage:**
```bash
bash scripts/fix_gnome_screenshot.sh
```

**What it does:**
1. Removes snap version of gnome-screenshot (if exists)
2. Updates apt package list
3. Reinstalls gnome-screenshot from apt
4. Tests the installation
5. Provides troubleshooting guidance if issues persist

**When to use:**
- When gnome-screenshot has library conflicts
- After seeing "symbol lookup error" from gnome-screenshot
- When switching between snap and apt packages

---

## Adding New Scripts

When adding new scripts to this directory:

1. **Make them executable:**
   ```bash
   chmod +x scripts/your_script.sh
   ```

2. **Add shebang:** Start with `#!/bin/bash`

3. **Add documentation:**
   - Purpose comment at the top
   - Usage instructions
   - Example output

4. **Use absolute paths** when referencing backend directory:
   ```bash
   cd /home/rodrigo/agentic/backend
   source venv/bin/activate
   ```

5. **Provide clear output:**
   - Use echo statements to show progress
   - Add separators for readability
   - Show success/failure clearly

6. **Handle errors gracefully:**
   ```bash
   command || { echo "Error: command failed"; exit 1; }
   ```

7. **Update this README** with script documentation

## Script Best Practices

- **Idempotent:** Can be run multiple times safely
- **Informative:** Clear output about what's happening
- **Reversible:** Document how to undo changes (if applicable)
- **Tested:** Test on a clean environment before committing
- **Cross-platform aware:** Check for platform-specific commands

## Example Script Template

```bash
#!/bin/bash

# Script Name: do_something.sh
# Purpose: Brief description of what this script does
# Usage: bash scripts/do_something.sh [args]

set -e  # Exit on error

echo "=================================================="
echo "Script Name - Brief Description"
echo "=================================================="

# Check prerequisites
if ! command -v required_command &> /dev/null; then
    echo "Error: required_command not found"
    exit 1
fi

# Main logic
echo "Step 1: Doing something..."
# commands here

echo "Step 2: Doing something else..."
# more commands

echo ""
echo "=================================================="
echo "✓ Script completed successfully"
echo "=================================================="
```

---

**Last updated:** 2025-10-11
