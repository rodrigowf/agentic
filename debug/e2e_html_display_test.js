#!/usr/bin/env node
/**
 * End-to-End Test for MainConversation -> HTMLDisplay Flow
 *
 * This test:
 * 1. Opens the MainConversation agent page
 * 2. Sends a task that requires research + HTML display
 * 3. Captures all console logs and WebSocket messages
 * 4. Verifies the flow works correctly
 *
 * Usage: node debug/e2e_html_display_test.js
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

// Configuration
const BASE_URL = 'http://localhost:3000/agentic';
const AGENT_NAME = 'MainConversation';
const TEST_TASK = 'Please research the weather forecast for Rio de Janeiro for tomorrow, then display it to me with a beautiful HTML visualization.';
const TIMEOUT_MS = 180000; // 3 minutes for the full flow

// Output directory
const OUTPUT_DIR = path.join(__dirname, 'e2e_outputs');
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Log file
const LOG_FILE = path.join(OUTPUT_DIR, `e2e_test_${Date.now()}.log`);
let logStream;

function log(message, data = null) {
  if (!logStream) return;
  const timestamp = new Date().toISOString();
  const logLine = data
    ? `[${timestamp}] ${message}: ${JSON.stringify(data, null, 2)}`
    : `[${timestamp}] ${message}`;
  console.log(logLine);
  try {
    logStream.write(logLine + '\n');
  } catch (e) {
    // Ignore write errors after stream is closed
  }
}

async function runTest() {
  logStream = fs.createWriteStream(LOG_FILE, { flags: 'a' });

  log('Starting E2E test for MainConversation -> HTMLDisplay flow');
  log('Test task', TEST_TASK);

  const browser = await puppeteer.launch({
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1920, height: 1080 }
  });

  const page = await browser.newPage();

  // Collect agent WebSocket messages only (filter by URL)
  const agentWsMessages = [];

  const cdp = await page.target().createCDPSession();
  await cdp.send('Network.enable');

  // Track WebSocket connections by requestId
  const wsConnections = {};

  cdp.on('Network.webSocketCreated', ({ requestId, url }) => {
    wsConnections[requestId] = { url, isAgentWs: url.includes('/api/runs/') };
    if (wsConnections[requestId].isAgentWs) {
      log('Agent WebSocket created', url);
    }
  });

  cdp.on('Network.webSocketFrameReceived', ({ requestId, timestamp, response }) => {
    if (wsConnections[requestId]?.isAgentWs) {
      try {
        const parsed = JSON.parse(response.payloadData);
        agentWsMessages.push(parsed);

        // Log important events
        if (parsed.type && !['hot', 'liveReload', 'reconnect', 'overlay', 'hash', 'ok'].includes(parsed.type)) {
          log(`AGENT WS [${parsed.type}]`, {
            source: parsed.data?.source,
            content: (parsed.data?.content || parsed.data?.message || '').substring(0, 200)
          });
        }
      } catch {
        // Non-JSON message, skip
      }
    }
  });

  cdp.on('Network.webSocketFrameSent', ({ requestId, timestamp, response }) => {
    if (wsConnections[requestId]?.isAgentWs) {
      try {
        const parsed = JSON.parse(response.payloadData);
        log('AGENT WS SENT', parsed);
      } catch {}
    }
  });

  try {
    // Navigate to agent page
    log(`Navigating to ${BASE_URL}/agents/${AGENT_NAME}`);
    await page.goto(`${BASE_URL}/agents/${AGENT_NAME}`, {
      waitUntil: 'networkidle2',
      timeout: 30000
    });

    // Take initial screenshot
    await page.screenshot({ path: path.join(OUTPUT_DIR, '01_initial_page.png'), fullPage: true });
    log('Took initial screenshot');

    // Wait for page to fully load (agent data to be populated)
    log('Waiting for page to fully load...');
    await page.waitForFunction(() => {
      // Check if agent name is displayed in the editor
      const nameInputs = document.querySelectorAll('input');
      for (const input of nameInputs) {
        if (input.value === 'MainConversation') return true;
      }
      return false;
    }, { timeout: 30000 });
    log('Agent data loaded');

    // Wait for WebSocket connection
    log('Waiting for WebSocket connection...');
    await page.waitForFunction(() => {
      const statusChip = document.querySelector('[class*="MuiChip"]');
      return statusChip && statusChip.textContent.includes('Connected');
    }, { timeout: 30000 });
    log('WebSocket connected');

    // Additional wait for stability
    await new Promise(r => setTimeout(r, 2000));

    // Enter the task
    log('Entering task...');
    await page.waitForSelector('textarea[placeholder="Enter the task description here..."]', { timeout: 10000 });
    const taskInput = await page.$('textarea[placeholder="Enter the task description here..."]');
    if (!taskInput) {
      throw new Error('Could not find task input textarea');
    }
    await taskInput.click({ clickCount: 3 }); // Select all existing text
    await taskInput.type(TEST_TASK, { delay: 5 });

    await page.screenshot({ path: path.join(OUTPUT_DIR, '02_task_entered.png'), fullPage: true });

    // Click Run button
    log('Clicking Run button...');
    const runButton = await page.$('button[aria-label="Run agent"]');
    if (!runButton) {
      throw new Error('Could not find Run button');
    }
    await runButton.click();

    log('Agent run started, waiting for completion...');

    // Track events and wait for completion
    let agentFinished = false;
    let terminateFromManager = false;
    let agentsInvolved = new Set();
    let htmlDisplayInvoked = false;

    // Poll for completion
    const startTime = Date.now();
    while (Date.now() - startTime < TIMEOUT_MS) {
      await new Promise(r => setTimeout(r, 2000));

      // Take periodic screenshots
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      if (elapsed % 30 === 0 && elapsed > 0) {
        await page.screenshot({
          path: path.join(OUTPUT_DIR, `03_progress_${elapsed}s.png`),
          fullPage: true
        });
        log(`Progress at ${elapsed}s - Messages: ${agentWsMessages.length}, Agents: ${Array.from(agentsInvolved).join(', ')}`);
      }

      // Analyze messages
      for (const msg of agentWsMessages) {
        // Track which agents are involved
        if (msg.data?.source) {
          agentsInvolved.add(msg.data.source);
        }

        // Check for HTMLDisplay involvement
        if (msg.data?.source === 'HTMLDisplay') {
          htmlDisplayInvoked = true;
        }

        // Check for system messages about completion
        if (msg.type === 'system' && msg.data?.message?.includes('Agent run finished')) {
          agentFinished = true;
          log('Agent run finished signal received');
        }

        // Check for Manager TERMINATE
        if (msg.data?.source === 'Manager' && msg.data?.content?.includes('TERMINATE')) {
          terminateFromManager = true;
        }
      }

      if (agentFinished) {
        log('Agent finished, breaking loop');
        break;
      }
    }

    // Take final screenshot
    await page.screenshot({ path: path.join(OUTPUT_DIR, '04_final_state.png'), fullPage: true });

    // Generate report
    const report = {
      success: agentFinished,
      durationMs: Date.now() - startTime,
      agentsInvolved: Array.from(agentsInvolved),
      htmlDisplayInvoked,
      terminateFromManager,
      totalMessages: agentWsMessages.length
    };

    log('\n=== TEST REPORT ===', report);

    // Save full agent messages log
    fs.writeFileSync(
      path.join(OUTPUT_DIR, 'agent_messages.json'),
      JSON.stringify(agentWsMessages, null, 2)
    );

    // Analyze the flow
    log('\n=== FLOW ANALYSIS ===');

    const agentSequence = agentWsMessages
      .filter(m => m.data?.source)
      .map(m => m.data.source);

    log('Agent sequence (first 30)', agentSequence.slice(0, 30));

    // Check if HTMLDisplay was invoked
    log('HTMLDisplay invoked', htmlDisplayInvoked);

    if (!htmlDisplayInvoked) {
      log('ISSUE: HTMLDisplay agent was NOT invoked!');
      log('This means Manager did not delegate to HTMLDisplay after Researcher finished');

      // Show Manager messages
      const managerMessages = agentWsMessages.filter(m => m.data?.source === 'Manager');
      log('Manager messages', managerMessages.map(m => m.data?.content?.substring(0, 200)));
    }

    // Check for HTML files in the output directory
    const htmlOutputDir = path.join(__dirname, '..', 'backend', 'data', 'workspace', 'html_outputs');
    if (fs.existsSync(htmlOutputDir)) {
      const htmlFiles = fs.readdirSync(htmlOutputDir).filter(f => f.endsWith('.html'));
      log('HTML files in output directory', htmlFiles);
    } else {
      log('HTML output directory does not exist');
    }

    log('\n=== TEST COMPLETE ===');
    log(`Results saved to: ${OUTPUT_DIR}`);

  } catch (error) {
    log('TEST ERROR', error.message);
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'error_screenshot.png'), fullPage: true });
    throw error;
  } finally {
    if (logStream) {
      logStream.end();
      logStream = null;
    }
    await browser.close();
  }
}

// Run the test
runTest().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
