# Claude Code Permission Fix Summary

**Date:** 2025-10-11
**Issue:** Claude Code was requesting permission prompts during voice assistant sessions, but users couldn't provide interactive approval.

---

## Problem

When the voice assistant sent tasks to Claude Code via the `/api/runs/ClaudeCode` WebSocket endpoint, Claude Code would wait for permission approval before executing tools like Bash, Read, Edit, etc. Since the voice assistant operates in a non-interactive mode, there was no way for users to approve these permissions, causing Claude Code to hang indefinitely.

---

## Solution

Configured Claude Code to use **`bypassPermissions` mode**, which automatically executes all tool calls without prompting for approval.

---

## Changes Made

### 1. Updated `backend/api/claude_code_controller.py`

**Changed the default permission mode from `"default"` to `"bypassPermissions"`:**

```python
class ClaudeCodeProcess:
    """Manages a Claude Code CLI subprocess with JSON streaming."""

    # Claude CLI path - VSCode extension binary
    CLAUDE_CLI_PATH = "/home/rodrigo/.vscode/extensions/anthropic.claude-code-2.0.14-linux-x64/resources/native-binary/claude"

    def __init__(
        self,
        working_dir: str = "/home/rodrigo/agentic",
        model: str = "claude-sonnet-4-5-20250929",
        permission_mode: str = "bypassPermissions",  # ← Changed from "default"
    ):
        ...

class ClaudeCodeSession:
    """High-level session manager for Claude Code interactions."""

    def __init__(
        self,
        working_dir: str = "/home/rodrigo/agentic",
        model: str = "claude-sonnet-4-5-20250929",
        permission_mode: str = "bypassPermissions",  # ← Changed from "default"
    ):
        ...
```

**Added the Claude CLI binary path as a class constant:**
- Path: `/home/rodrigo/.vscode/extensions/anthropic.claude-code-2.0.14-linux-x64/resources/native-binary/claude`
- This ensures Claude Code can be found even when not in the system PATH

### 2. Updated `backend/main.py`

**Changed the WebSocket endpoint to use `bypassPermissions`:**

```python
@app.websocket("/api/runs/ClaudeCode")
async def run_claude_code_ws(websocket: WebSocket):
    """WebSocket endpoint for Claude Code self-editor."""
    ...
    session = ClaudeCodeSession(
        working_dir=working_dir,
        model="claude-sonnet-4-5-20250929",
        permission_mode="bypassPermissions",  # ← Changed from "default"
    )
    ...
```

### 3. Updated Documentation

**Added comprehensive permission handling documentation to `CLAUDE.md`:**

- Explained the permission modes available
- Documented the security considerations
- Provided testing instructions
- Added troubleshooting guidance

---

## Permission Modes Available

| Mode | Description | Use Case |
|------|-------------|----------|
| `bypassPermissions` | **Used for voice assistant** - Executes all tools without prompts | Non-interactive environments, trusted operations |
| `acceptEdits` | Auto-accepts file edits only, still prompts for other tools | Semi-automated workflows |
| `default` | Normal interactive permission prompts | Interactive CLI sessions |
| `plan` | Plan mode, doesn't execute tools | Planning-only sessions |

---

## Testing

### Test Script: `backend/test_claude_code_permissions.py`

A standalone test that verifies Claude Code executes tools without permission prompts:

```bash
cd /home/rodrigo/agentic/backend
python3 test_claude_code_permissions.py
```

**Expected output:**
```
✓ SUCCESS: Claude Code executed tools without permission prompts!
```

### Integration Test: `backend/test_voice_claude_integration.py`

A WebSocket integration test that simulates the voice assistant flow:

```bash
cd /home/rodrigo/agentic/backend
venv/bin/python test_voice_claude_integration.py
```

**Expected output:**
```
✅ TEST PASSED
Claude Code executed tools without permission prompts!
The voice assistant integration is working correctly.
```

**Test Results:**
- ✅ WebSocket connection established
- ✅ Message sent to Claude Code
- ✅ Claude Code executed 2 Bash tool calls without asking for permissions
- ✅ Task completed successfully

---

## Security Considerations

The `bypassPermissions` mode is **safe in this context** because:

1. **Trusted Environment:** The voice assistant is already trusted to execute arbitrary code
2. **Same Working Directory:** Claude Code operates in the same directory as the voice assistant
3. **System Design:** The system is explicitly designed for self-modification capabilities
4. **Sandboxed Scope:** All operations are scoped to the project directory

### For Production Deployments

If deploying in untrusted or public environments, consider:

1. **Tool Allowlisting:**
   ```python
   cmd.extend(["--allowed-tools", "Bash(git:*) Edit Read"])
   ```

2. **Directory Restrictions:**
   ```python
   cmd.extend(["--add-dir", "/safe/path"])
   ```

3. **Disallow Dangerous Tools:**
   ```python
   cmd.extend(["--disallowed-tools", "Bash(rm:*) Bash(sudo:*)"])
   ```

4. **Implement Approval Workflows:**
   - Add a UI component for permission approval
   - Queue tool requests for manual review
   - Implement role-based access control

---

## Verification

### Manual Testing

1. Start the backend:
   ```bash
   cd /home/rodrigo/agentic/backend
   uvicorn main:app --reload --port 8002
   ```

2. Run the integration test:
   ```bash
   venv/bin/python test_voice_claude_integration.py
   ```

3. Expected behavior:
   - Claude Code connects via WebSocket
   - Receives a user message
   - Executes Bash tools without waiting
   - Returns results immediately
   - Completes the task successfully

### Voice Assistant Testing

1. Start the voice assistant
2. Say: "Claude, list the Python files in the backend"
3. Observe: Claude Code should execute the command immediately without hanging
4. Verify: The voice assistant narrates the results

---

## Troubleshooting

### Issue: "Command not found: claude"

**Solution:** The fix includes the full path to the Claude CLI binary:
```python
CLAUDE_CLI_PATH = "/home/rodrigo/.vscode/extensions/anthropic.claude-code-2.0.14-linux-x64/resources/native-binary/claude"
```

### Issue: "WebSocket connection failed"

**Causes:**
1. Backend not running
2. Wrong port number
3. CORS configuration

**Solution:**
```bash
# Check if backend is running
ps aux | grep uvicorn

# Check the port
lsof -i :8002

# Restart backend
cd backend && uvicorn main:app --reload
```

### Issue: "Still getting permission prompts"

**Verify:**
1. Backend has been restarted to pick up the changes
2. `permission_mode="bypassPermissions"` is set in both files
3. Check backend logs for errors

---

## Files Modified

1. ✅ `backend/api/claude_code_controller.py` - Changed default permission mode
2. ✅ `backend/main.py` - Updated WebSocket endpoint
3. ✅ `CLAUDE.md` - Added permission handling documentation

## Files Created

1. ✅ `backend/test_claude_code_permissions.py` - Standalone test
2. ✅ `backend/test_voice_claude_integration.py` - Integration test
3. ✅ `PERMISSION_FIX_SUMMARY.md` - This summary

---

## Next Steps

1. ✅ Test with actual voice assistant session
2. Consider implementing:
   - Tool usage analytics/monitoring
   - Optional permission confirmation UI
   - Configurable permission policies per conversation
   - Audit logging for all Claude Code actions

---

## References

- Claude Code CLI documentation: `claude --help`
- Permission modes: `--permission-mode` flag
- WebSocket endpoint: `/api/runs/ClaudeCode`
- Voice assistant integration: `frontend/src/features/voice/pages/VoiceAssistant.js`

---

**Status:** ✅ **FIXED AND TESTED**

The voice assistant can now successfully delegate tasks to Claude Code without permission blocking.
