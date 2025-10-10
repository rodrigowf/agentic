# Automated UI Development Workflow

This document contains precise instructions for Claude on how to use the screenshot automation tool for fully automated frontend UI development.

## Setup (One-time)

1. **Install dependencies:**
   ```bash
   cd /home/rodrigo/agentic/_debug
   npm install
   ```

2. **Make screenshot script executable:**
   ```bash
   chmod +x /home/rodrigo/agentic/_debug/screenshot.js
   ```

## Core Workflow for UI Development

### Phase 1: Initial Screenshot (Understanding Current State)

Before making ANY changes to the UI, ALWAYS take a screenshot first to understand the current state:

```bash
node /home/rodrigo/agentic/_debug/screenshot.js http://localhost:3000/agents/MainConversation
```

**Then READ the screenshot** using the Read tool to analyze the current UI state.

### Phase 2: Make Code Changes

After understanding the current state:
1. Use Edit tool to make changes to React components
2. The dev server (running on localhost:3000) will auto-reload
3. Wait 2-3 seconds for the changes to take effect

### Phase 3: Verify Changes (Screenshot After)

After making changes, ALWAYS take a new screenshot to verify:

```bash
node /home/rodrigo/agentic/_debug/screenshot.js http://localhost:3000/agents/MainConversation /home/rodrigo/agentic/_debug/screenshots/after-change-$(date +%s).png 3000
```

**Then READ the new screenshot** to verify your changes worked as expected.

### Phase 4: Iterate

Compare the before/after screenshots:
- If changes look correct: proceed to next task
- If issues found: make corrections and repeat Phase 2-3

## Screenshot Script Usage

### Basic Usage
```bash
node screenshot.js [URL] [OUTPUT_PATH] [WAIT_TIME_MS]
```

### Parameters
- `URL`: Target URL (default: http://localhost:3000)
- `OUTPUT_PATH`: Where to save screenshot (default: screenshots/screenshot-{timestamp}.png)
- `WAIT_TIME_MS`: Wait time in milliseconds for dynamic content (default: 1000)

### Examples

**Screenshot main page:**
```bash
node /home/rodrigo/agentic/_debug/screenshot.js http://localhost:3000
```

**Screenshot specific route with custom wait:**
```bash
node /home/rodrigo/agentic/_debug/screenshot.js http://localhost:3000/agents/MainConversation /home/rodrigo/agentic/_debug/screenshots/main-conversation.png 2000
```

**Screenshot after making changes (longer wait for re-render):**
```bash
node /home/rodrigo/agentic/_debug/screenshot.js http://localhost:3000/agents/MainConversation /home/rodrigo/agentic/_debug/screenshots/after-refactor.png 3000
```

## Key Principles for Automated Development

### 1. ALWAYS Screenshot Before and After
Never make UI changes without visual verification. This prevents:
- Breaking existing layouts
- Introducing visual regressions
- Missing CSS/styling issues

### 2. Use Descriptive Screenshot Names
```bash
# Good
/home/rodrigo/agentic/_debug/screenshots/before-refactor-agent-dashboard.png
/home/rodrigo/agentic/_debug/screenshots/after-refactor-agent-dashboard.png

# Bad
/home/rodrigo/agentic/_debug/screenshots/screenshot1.png
```

### 3. Wait Appropriately
- Initial page load: 1000-2000ms
- After code changes (hot reload): 2000-3000ms
- Complex animations/transitions: 3000-5000ms

### 4. Read Screenshots Immediately
After taking a screenshot, ALWAYS use the Read tool to analyze it before proceeding.

## Complete Example Workflow

**Task: Refactor the AgentDashboard component**

```bash
# Step 1: Take "before" screenshot
node /home/rodrigo/agentic/_debug/screenshot.js http://localhost:3000/agents/MainConversation /home/rodrigo/agentic/_debug/screenshots/before-dashboard-refactor.png 2000
```

**Step 2: Read the screenshot**
```
Read tool: /home/rodrigo/agentic/_debug/screenshots/before-dashboard-refactor.png
```

**Step 3: Make code changes**
```
Edit tool: /home/rodrigo/agentic/frontend/src/components/AgentDashboard.js
(make refactoring changes)
```

**Step 4: Wait for hot reload (3 seconds for safety)**
```bash
sleep 3
```

**Step 5: Take "after" screenshot**
```bash
node /home/rodrigo/agentic/_debug/screenshot.js http://localhost:3000/agents/MainConversation /home/rodrigo/agentic/_debug/screenshots/after-dashboard-refactor.png 3000
```

**Step 6: Read and compare**
```
Read tool: /home/rodrigo/agentic/_debug/screenshots/after-dashboard-refactor.png
```

**Step 7: Verify changes**
- Compare before/after screenshots
- Check that layout is preserved
- Verify no visual regressions
- Confirm refactoring goals achieved

## Troubleshooting

### Screenshot is blank or shows error page
- Increase wait time (try 5000ms)
- Check that the dev server is running on the correct port
- Verify the URL is correct

### Changes not reflected in screenshot
- Increase wait time to allow hot reload to complete
- Check for console errors in the frontend
- Verify the file was actually saved

### Browser launch fails
- Install required dependencies: `sudo apt-get install -y chromium-browser`
- Or use bundled Chromium that comes with Puppeteer

## Integration with Todo Workflow

When working on UI tasks, structure todos like this:

1. "Take before screenshot of current UI" (status: pending)
2. "Refactor AgentDashboard component" (status: pending)
3. "Take after screenshot to verify changes" (status: pending)
4. "Compare screenshots and verify no regressions" (status: pending)

Mark each as in_progress → completed as you go through the workflow.

## File Locations

- **Screenshot script:** `/home/rodrigo/agentic/_debug/screenshot.js`
- **Screenshots directory:** `/home/rodrigo/agentic/_debug/screenshots/`
- **This guide:** `/home/rodrigo/agentic/_debug/AUTOMATED_UI_DEVELOPMENT.md`

## Best Practices

1. **Always use absolute paths** in commands
2. **Name screenshots descriptively** with context about what changed
3. **Keep screenshots** for the duration of the refactoring session
4. **Clean up old screenshots** periodically to save space
5. **Take screenshots at key stages** not just before/after
6. **Use consistent wait times** for the same page (predictable results)
7. **Read screenshots immediately** after taking them to provide context

## Notes for Claude

- You have the Read tool that can analyze images/screenshots
- After taking a screenshot with Bash, immediately Read it
- Use the visual information to guide your next edits
- If something looks wrong in the screenshot, fix it before proceeding
- Keep the user informed about what you see in each screenshot
- This enables truly autonomous frontend development without user intervention
