/**
 * E2E test for mobile voice bidirectional audio flow
 *
 * Tests:
 * 1. Desktop mic → OpenAI → Mobile speaker
 * 2. Mobile mic → Desktop → OpenAI → Both speakers
 * 3. Desktop mic muted → Mobile mic should still work
 */

const puppeteer = require('puppeteer');

// Test configuration
const DESKTOP_URL = 'http://localhost:3000/voice';
const MOBILE_URL = 'http://localhost:3000/mobile-voice';
const TEST_DURATION_MS = 30000; // 30 seconds
const CONVERSATION_NAME = 'E2E-Test-' + Date.now();

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function captureConsoleLogs(page, prefix) {
  const logs = [];

  page.on('console', msg => {
    const text = msg.text();
    const timestamp = new Date().toISOString();
    logs.push({ timestamp, text });
    console.log(`[${prefix}] ${timestamp} ${text}`);
  });

  page.on('pageerror', error => {
    console.error(`[${prefix}] PAGE ERROR:`, error.message);
  });

  return logs;
}

async function startDesktopSession(page, conversationName) {
  console.log('\n=== Starting Desktop Session ===');

  await page.goto(DESKTOP_URL, { waitUntil: 'networkidle2' });
  await sleep(2000);

  // Create new conversation
  const createButton = await page.$('button[aria-label="Create new conversation"]');
  if (createButton) {
    await createButton.click();
    await sleep(1000);

    // Enter conversation name
    await page.type('input[placeholder="Enter conversation name"]', conversationName);
    await sleep(500);

    // Click confirm
    const confirmButton = await page.$('button:has-text("Create")');
    if (confirmButton) {
      await confirmButton.click();
      await sleep(2000);
    }
  }

  // Start voice session
  console.log('[Desktop] Clicking play button...');
  const playButton = await page.$('button[aria-label="Start voice session"]');
  if (!playButton) {
    throw new Error('Desktop: Play button not found');
  }

  await playButton.click();
  console.log('[Desktop] Session started');
  await sleep(3000); // Wait for session to initialize

  return true;
}

async function startMobileSession(page, conversationId) {
  console.log('\n=== Starting Mobile Session ===');

  await page.goto(MOBILE_URL, { waitUntil: 'networkidle2' });
  await sleep(2000);

  // Select conversation from dropdown
  console.log('[Mobile] Selecting conversation...');
  const select = await page.$('select');
  if (!select) {
    throw new Error('Mobile: Conversation select not found');
  }

  // Select the conversation (first non-empty option)
  await page.select('select', conversationId);
  await sleep(1000);

  // Click start button
  console.log('[Mobile] Clicking start button...');
  const startButton = await page.$('button:has-text("Start")');
  if (!startButton) {
    throw new Error('Mobile: Start button not found');
  }

  await startButton.click();
  await sleep(2000);

  // Unmute mobile mic
  console.log('[Mobile] Clicking unmute button...');
  const muteButton = await page.$('button[aria-label="Unmute microphone"]');
  if (muteButton) {
    await muteButton.click();
    await sleep(1000);
  }

  console.log('[Mobile] Session started and unmuted');
  return true;
}

async function muteDesktopMic(desktopPage) {
  console.log('\n=== Muting Desktop Microphone ===');

  const muteButton = await desktopPage.$('button[aria-label="Mute microphone"]');
  if (!muteButton) {
    throw new Error('Desktop: Mute button not found');
  }

  await muteButton.click();
  console.log('[Desktop] Microphone muted');
  await sleep(1000);

  return true;
}

async function analyzeAudioFlow(desktopLogs, mobileLogs) {
  console.log('\n=== Analyzing Audio Flow ===');

  const analysis = {
    mobileMicSending: false,
    desktopReceivingMobileMic: false,
    desktopMicMuted: false,
    mobileGainCorrect: false,
    mixerActive: false,
    openAIRelaying: false,
    mobileReceivingResponse: false,
  };

  // Check mobile mic sending
  const mobileSending = mobileLogs.filter(log => log.text.includes('[MobileMic→Desktop]'));
  analysis.mobileMicSending = mobileSending.length > 0;

  const voiceDetected = mobileLogs.filter(log => log.text.includes('VOICE DETECTED'));
  console.log(`✓ Mobile mic sending: ${mobileSending.length} chunks, ${voiceDetected.length} voice detected`);

  // Check desktop receiving mobile mic
  const desktopReceiving = desktopLogs.filter(log => log.text.includes('[Desktop←MobileMic]'));
  analysis.desktopReceivingMobileMic = desktopReceiving.length > 0;

  const desktopVoice = desktopLogs.filter(log => log.text.includes('[Desktop←MobileMic] VOICE!'));
  console.log(`✓ Desktop receiving mobile mic: ${desktopReceiving.length} chunks, ${desktopVoice.length} voice detected`);

  // Check desktop mute state
  const muteLog = desktopLogs.find(log => log.text.includes('[DesktopMute]'));
  if (muteLog) {
    analysis.desktopMicMuted = muteLog.text.includes('gain set to: 0');
    analysis.mobileGainCorrect = muteLog.text.includes('Mobile gain still at: 1');
    analysis.mixerActive = muteLog.text.includes('Mixer still active');
    console.log(`✓ Desktop mic muted: ${analysis.desktopMicMuted}`);
    console.log(`✓ Mobile gain correct: ${analysis.mobileGainCorrect}`);
    console.log(`✓ Mixer active: ${analysis.mixerActive}`);
  }

  // Check OpenAI response relay
  const relayLogs = desktopLogs.filter(log => log.text.includes('[OpenAI→Mobile]'));
  analysis.openAIRelaying = relayLogs.length > 0;
  console.log(`✓ OpenAI relaying to mobile: ${relayLogs.length} chunks`);

  // Check mobile receiving response
  const mobileResponse = mobileLogs.filter(log => log.text.includes('Scheduled desktop audio chunk'));
  analysis.mobileReceivingResponse = mobileResponse.length > 0;
  console.log(`✓ Mobile receiving response: ${mobileResponse.length} chunks`);

  return analysis;
}

async function runTest() {
  console.log('='.repeat(60));
  console.log('Mobile Voice E2E Test - Bidirectional Audio Flow');
  console.log('='.repeat(60));

  const browser = await puppeteer.launch({
    headless: false, // Show browser for debugging
    args: [
      '--use-fake-ui-for-media-stream', // Auto-grant mic permission
      '--use-fake-device-for-media-stream',
      '--autoplay-policy=no-user-gesture-required',
    ],
    defaultViewport: null,
  });

  let desktopPage, mobilePage, desktopLogs = [], mobileLogs = [];

  try {
    // Create desktop page
    desktopPage = await browser.newPage();
    await desktopPage.setViewport({ width: 1280, height: 720 });
    desktopLogs = await captureConsoleLogs(desktopPage, 'DESKTOP');

    // Create mobile page (simulated as phone viewport)
    mobilePage = await browser.newPage();
    await mobilePage.setViewport({ width: 375, height: 667 }); // iPhone size
    mobileLogs = await captureConsoleLogs(mobilePage, 'MOBILE');

    // Test 1: Start desktop session
    console.log('\n📱 TEST 1: Desktop Session Start');
    await startDesktopSession(desktopPage, CONVERSATION_NAME);
    await sleep(5000);

    // Get conversation ID from URL or storage
    const conversationId = await desktopPage.evaluate(() => {
      // Try to get from URL or localStorage
      const match = window.location.href.match(/conversation[/=]([a-f0-9-]+)/);
      if (match) return match[1];

      // Fallback: get from conversations list
      return null; // Will need to query API
    });

    console.log('Conversation ID:', conversationId);

    // Test 2: Start mobile session
    console.log('\n📱 TEST 2: Mobile Session Start');
    if (conversationId) {
      await startMobileSession(mobilePage, conversationId);
    } else {
      // Fallback: Let mobile auto-select if only one conversation
      await mobilePage.goto(MOBILE_URL, { waitUntil: 'networkidle2' });
      await sleep(2000);
      const startButton = await mobilePage.$('button:has-text("Start")');
      if (startButton) {
        await startButton.click();
        await sleep(2000);
      }
    }

    // Test 3: Let it run with both mics active
    console.log('\n📱 TEST 3: Both Mics Active (10 seconds)');
    console.log('Speak into microphone to generate audio...');
    await sleep(10000);

    // Test 4: Mute desktop mic
    console.log('\n📱 TEST 4: Desktop Mic Muted');
    await muteDesktopMic(desktopPage);
    await sleep(2000);

    // Test 5: Continue with only mobile mic
    console.log('\n📱 TEST 5: Only Mobile Mic Active (10 seconds)');
    console.log('Speak into mobile to verify it still works...');
    await sleep(10000);

    // Analyze results
    const analysis = await analyzeAudioFlow(desktopLogs, mobileLogs);

    // Print summary
    console.log('\n' + '='.repeat(60));
    console.log('TEST RESULTS');
    console.log('='.repeat(60));

    const results = [
      { name: 'Mobile mic sending', pass: analysis.mobileMicSending },
      { name: 'Desktop receiving mobile mic', pass: analysis.desktopReceivingMobileMic },
      { name: 'Desktop mic muted correctly', pass: analysis.desktopMicMuted },
      { name: 'Mobile gain unchanged', pass: analysis.mobileGainCorrect },
      { name: 'Mixer still active', pass: analysis.mixerActive },
      { name: 'OpenAI relay to mobile', pass: analysis.openAIRelaying },
      { name: 'Mobile receiving response', pass: analysis.mobileReceivingResponse },
    ];

    results.forEach(r => {
      const icon = r.pass ? '✅' : '❌';
      console.log(`${icon} ${r.name}`);
    });

    const allPassed = results.every(r => r.pass);
    console.log('\n' + '='.repeat(60));
    if (allPassed) {
      console.log('🎉 ALL TESTS PASSED');
    } else {
      console.log('❌ SOME TESTS FAILED');
      console.log('\nFailed tests:');
      results.filter(r => !r.pass).forEach(r => {
        console.log(`  - ${r.name}`);
      });
    }
    console.log('='.repeat(60));

  } catch (error) {
    console.error('\n❌ TEST ERROR:', error.message);
    console.error(error.stack);
  } finally {
    console.log('\nClosing browser in 5 seconds...');
    await sleep(5000);
    await browser.close();
  }
}

// Run the test
runTest().catch(console.error);
