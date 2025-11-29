/**
 * Playwright test for mobile-voice WebRTC signaling
 *
 * Captures console logs and network activity to debug the WebRTC connection
 */

const { chromium } = require('playwright');

async function testMobileVoiceWebRTC() {
  const browser = await chromium.launch({ headless: false }); // Non-headless to see what's happening
  const context = await browser.newContext({
    viewport: { width: 375, height: 812 }, // iPhone X size
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
  });
  const page = await context.newPage();

  // Collect console logs
  const logs = [];
  page.on('console', msg => {
    const text = msg.text();
    logs.push({ type: msg.type(), text });
    console.log(`[${msg.type().toUpperCase()}]`, text);
  });

  // Collect WebSocket messages
  const wsMessages = [];
  page.on('websocket', ws => {
    console.log(`[WebSocket] Created: ${ws.url()}`);
    wsMessages.push({ event: 'created', url: ws.url() });

    ws.on('framesent', event => {
      try {
        const payload = JSON.parse(event.payload);
        console.log(`[WS →] ${JSON.stringify(payload)}`);
        wsMessages.push({ event: 'sent', payload });
      } catch (e) {
        console.log(`[WS →] ${event.payload}`);
        wsMessages.push({ event: 'sent', payload: event.payload });
      }
    });

    ws.on('framereceived', event => {
      try {
        const payload = JSON.parse(event.payload);
        console.log(`[WS ←] ${JSON.stringify(payload)}`);
        wsMessages.push({ event: 'received', payload });
      } catch (e) {
        console.log(`[WS ←] ${event.payload}`);
        wsMessages.push({ event: 'received', payload: event.payload });
      }
    });

    ws.on('close', () => {
      console.log(`[WebSocket] Closed: ${ws.url()}`);
      wsMessages.push({ event: 'closed', url: ws.url() });
    });
  });

  try {
    console.log('\n=== TESTING MOBILE VOICE WEBRTC ===\n');

    // Navigate to mobile-voice page
    console.log('1. Navigating to mobile-voice page...');
    await page.goto('http://localhost:3000/mobile-voice/9fd231a8-0de7-4e46-b26c-a3cf28372cbb', {
      waitUntil: 'networkidle'
    });

    // Wait for conversations to load
    console.log('2. Waiting for conversations to load...');
    await page.waitForTimeout(2000);

    // Take screenshot before starting
    await page.screenshot({ path: '/home/rodrigo/agentic/debug/screenshots/mobile-voice-before-start.png' });
    console.log('   Screenshot saved: mobile-voice-before-start.png');

    // Check if conversation is selected
    const selectValue = await page.evaluate(() => {
      const select = document.querySelector('select');
      return select ? select.value : null;
    });
    console.log(`   Selected conversation: ${selectValue}`);

    // Click the start button
    console.log('3. Clicking start button...');
    const startButton = await page.locator('button[aria-label*="start"], button:has-text(""), svg[data-testid="PlayArrowIcon"]').first();

    // Find the play button by looking for the large circular button
    const playButton = await page.locator('button').filter({ has: page.locator('svg[data-testid="PlayArrowIcon"]') }).first();

    if (await playButton.isVisible()) {
      await playButton.click();
      console.log('   Play button clicked!');
    } else {
      console.log('   ❌ Play button not found!');
      await page.screenshot({ path: '/home/rodrigo/agentic/debug/screenshots/mobile-voice-no-play-button.png' });
      return;
    }

    // Wait for session to start
    console.log('4. Waiting for session to start...');
    await page.waitForTimeout(2000);

    // Take screenshot after starting
    await page.screenshot({ path: '/home/rodrigo/agentic/debug/screenshots/mobile-voice-after-start.png' });
    console.log('   Screenshot saved: mobile-voice-after-start.png');

    // Check for microphone mute button
    const muteButton = await page.locator('button').filter({ has: page.locator('svg[data-testid="MicOffIcon"], svg[data-testid="MicIcon"]') }).first();

    if (await muteButton.isVisible()) {
      console.log('5. Clicking unmute button...');
      await muteButton.click();
      console.log('   Microphone unmuted!');
      await page.waitForTimeout(1000);
    } else {
      console.log('5. ⚠ Mute button not visible');
    }

    // Wait a bit longer to observe WebSocket behavior
    console.log('6. Observing WebSocket behavior for 5 seconds...');
    await page.waitForTimeout(5000);

    // Take final screenshot
    await page.screenshot({ path: '/home/rodrigo/agentic/debug/screenshots/mobile-voice-final.png' });
    console.log('   Screenshot saved: mobile-voice-final.png');

    // Summary
    console.log('\n=== SUMMARY ===\n');
    console.log(`Console logs collected: ${logs.length}`);
    console.log(`WebSocket messages collected: ${wsMessages.length}`);

    console.log('\n=== WEBSOCKET ACTIVITY ===');
    wsMessages.forEach((msg, idx) => {
      console.log(`${idx + 1}. ${msg.event}${msg.url ? `: ${msg.url}` : ''}${msg.payload ? `: ${JSON.stringify(msg.payload)}` : ''}`);
    });

    console.log('\n=== CONSOLE LOGS (Mobile Voice specific) ===');
    logs.filter(log => log.text.includes('[MobileVoice]') || log.text.includes('[WS'))
        .forEach((log, idx) => {
          console.log(`${idx + 1}. [${log.type}] ${log.text}`);
        });

  } catch (error) {
    console.error('\n❌ ERROR:', error.message);
    await page.screenshot({ path: '/home/rodrigo/agentic/debug/screenshots/mobile-voice-error.png' });
  } finally {
    console.log('\n Keeping browser open for 10 seconds for inspection...');
    await page.waitForTimeout(10000);
    await browser.close();
  }
}

// Run the test
testMobileVoiceWebRTC().catch(console.error);
