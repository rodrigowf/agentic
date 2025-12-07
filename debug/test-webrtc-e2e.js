/**
 * E2E Test for Backend WebRTC Voice Assistant
 *
 * Tests:
 * 1. Route accessibility (/voice-webrtc)
 * 2. Backend API endpoints
 * 3. UI rendering and controls
 * 4. Session creation and WebRTC setup
 */

const { chromium } = require('playwright');

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function testWebRTCRoute() {
  console.log('🚀 Starting Backend WebRTC E2E Test...\n');

  const browser = await chromium.launch({
    headless: true, // Run headless for faster execution
    slowMo: 0 // No delay
  });

  const context = await browser.newContext({
    permissions: ['microphone'], // Grant microphone permission
  });

  const page = await context.newPage();

  // Listen for console logs
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    if (type === 'error') {
      console.log(`❌ Browser Error: ${text}`);
    } else if (text.includes('Session') || text.includes('WebRTC') || text.includes('Data channel')) {
      console.log(`ℹ️  Browser Log: ${text}`);
    }
  });

  // Listen for page errors
  page.on('pageerror', error => {
    console.log(`❌ Page Error: ${error.message}`);
  });

  try {
    // TEST 1: Check if backend is running
    console.log('📡 Test 1: Checking backend health...');
    const backendUrl = 'http://localhost:8000';

    try {
      const healthResp = await fetch(`${backendUrl}/api/agents`);
      if (healthResp.ok) {
        console.log('✅ Backend is running\n');
      } else {
        console.log(`⚠️  Backend responded with status: ${healthResp.status}\n`);
      }
    } catch (err) {
      console.log('❌ Backend is NOT running!');
      console.log('   Please start: cd backend && uvicorn main:app --reload\n');
      throw new Error('Backend not running');
    }

    // TEST 2: Check if frontend is running
    console.log('📡 Test 2: Checking frontend...');
    const frontendUrl = 'http://localhost:3000';

    try {
      const frontendResp = await fetch(frontendUrl);
      if (frontendResp.ok) {
        console.log('✅ Frontend is running\n');
      } else {
        console.log(`⚠️  Frontend responded with status: ${frontendResp.status}\n`);
      }
    } catch (err) {
      console.log('❌ Frontend is NOT running!');
      console.log('   Please start: cd frontend && npm start\n');
      throw new Error('Frontend not running');
    }

    // TEST 3: Navigate to WebRTC route
    console.log('📡 Test 3: Navigating to /voice-webrtc...');
    const targetUrl = `${frontendUrl}/voice-webrtc`;

    const response = await page.goto(targetUrl, {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    if (!response) {
      console.log('❌ Failed to navigate to /voice-webrtc\n');
      throw new Error('Navigation failed');
    }

    console.log(`   Status: ${response.status()}`);
    console.log(`   URL: ${page.url()}`);

    if (response.status() !== 200) {
      console.log('❌ Route returned non-200 status\n');

      // Take screenshot for debugging
      await page.screenshot({ path: 'debug/screenshots/webrtc-error.png' });
      console.log('   Screenshot saved: debug/screenshots/webrtc-error.png\n');

      throw new Error(`Route returned ${response.status()}`);
    }

    console.log('✅ Route is accessible\n');

    // Wait for React to render
    await sleep(3000);

    // Take screenshot after load
    await page.screenshot({ path: 'debug/screenshots/webrtc-loaded.png' });
    console.log('   Screenshot saved: debug/screenshots/webrtc-loaded.png');

    // TEST 4: Check if UI elements are present
    console.log('📡 Test 4: Checking UI elements...');

    // Check for title with timeout
    const title = await page.textContent('h4', { timeout: 5000 }).catch(err => {
      console.log(`   Warning: Could not find h4 element: ${err.message}`);
      return null;
    });
    console.log(`   Title: "${title}"`);

    if (!title || !title.includes('Voice Assistant')) {
      console.log('❌ Title not found or incorrect\n');
      await page.screenshot({ path: 'debug/screenshots/webrtc-no-title.png' });
      throw new Error('UI not rendering correctly');
    }

    // Check for Start Session button
    const startButton = await page.$('button:has-text("Start Session")');
    if (!startButton) {
      console.log('❌ Start Session button not found\n');
      await page.screenshot({ path: 'debug/screenshots/webrtc-no-button.png' });
      throw new Error('Start button not found');
    }

    console.log('✅ UI elements present\n');

    // TEST 5: Check backend API endpoints
    console.log('📡 Test 5: Testing backend API endpoints...');

    // Test session creation endpoint
    try {
      const sessionResp = await fetch(`${backendUrl}/api/realtime/session`, {
        method: 'POST'
      });

      if (sessionResp.ok) {
        const sessionData = await sessionResp.json();
        console.log(`   ✅ Session creation: ${sessionData.status}`);
        console.log(`   Session ID: ${sessionData.session_id}\n`);

        // Clean up - delete session
        await fetch(`${backendUrl}/api/realtime/session/${sessionData.session_id}`, {
          method: 'DELETE'
        });
      } else {
        const errorText = await sessionResp.text();
        console.log(`   ⚠️  Session creation failed: ${sessionResp.status}`);
        console.log(`   Error: ${errorText}\n`);
      }
    } catch (err) {
      console.log(`   ❌ Session endpoint error: ${err.message}\n`);
    }

    // TEST 6: Click Start Session button
    console.log('📡 Test 6: Testing Start Session button...');

    await page.screenshot({ path: 'debug/screenshots/webrtc-before-start.png' });
    console.log('   Screenshot saved: debug/screenshots/webrtc-before-start.png');

    await startButton.click();
    console.log('   Clicked "Start Session" button');

    // Wait for status to change
    await sleep(3000);

    // Check status
    const statusText = await page.textContent('text=Status:');
    console.log(`   ${statusText}`);

    await page.screenshot({ path: 'debug/screenshots/webrtc-after-start.png' });
    console.log('   Screenshot saved: debug/screenshots/webrtc-after-start.png\n');

    // Check if error appeared
    const errorAlert = await page.$('.MuiAlert-standardError');
    if (errorAlert) {
      const errorText = await errorAlert.textContent();
      console.log(`   ⚠️  Error alert: ${errorText}\n`);
    }

    // Check if buttons changed
    const stopButton = await page.$('button:has-text("Stop Session")');
    const unmuteButton = await page.$('button:has-text("Unmute")');

    if (stopButton && unmuteButton) {
      console.log('   ✅ Session started - Stop and Unmute buttons appeared');
    } else {
      console.log('   ⚠️  Session may not have started correctly');
      console.log(`   Stop button: ${stopButton ? 'Found' : 'Not found'}`);
      console.log(`   Unmute button: ${unmuteButton ? 'Found' : 'Not found'}`);
    }

    console.log('\n✅ All tests completed!\n');

  } catch (error) {
    console.log(`\n❌ Test failed: ${error.message}\n`);

    // Take final screenshot
    await page.screenshot({ path: 'debug/screenshots/webrtc-final-error.png' });
    console.log('Final screenshot saved: debug/screenshots/webrtc-final-error.png\n');

    throw error;
  } finally {
    await browser.close();
    console.log('Browser closed.');
  }
}

// Run tests
testWebRTCRoute()
  .then(() => {
    console.log('\n🎉 E2E Test Suite Passed!\n');
    process.exit(0);
  })
  .catch((error) => {
    console.log('\n💥 E2E Test Suite Failed!\n');
    console.error(error);
    process.exit(1);
  });
