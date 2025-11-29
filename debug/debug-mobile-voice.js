/**
 * Debug script for MobileVoice page using Puppeteer
 * Simulates mobile device and captures console logs and errors
 */

const puppeteer = require('puppeteer');

(async () => {
  console.log('🚀 Starting MobileVoice debug session...\n');

  const browser = await puppeteer.launch({
    headless: false, // Show browser for debugging
    args: [
      '--use-fake-ui-for-media-stream', // Auto-grant microphone permission
      '--use-fake-device-for-media-stream', // Use fake microphone
      '--no-sandbox',
      '--disable-setuid-sandbox'
    ],
    devtools: true // Open DevTools automatically
  });

  const page = await browser.newPage();

  // Emulate mobile device (Android Chrome)
  await page.emulate({
    name: 'Pixel 5',
    userAgent: 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36',
    viewport: {
      width: 393,
      height: 851,
      deviceScaleFactor: 2.75,
      isMobile: true,
      hasTouch: true,
    }
  });

  // Capture all console messages
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();

    if (text.includes('[MobileVoice')) {
      if (type === 'error') {
        console.log(`❌ [ERROR] ${text}`);
      } else if (type === 'warning') {
        console.log(`⚠️  [WARN] ${text}`);
      } else {
        console.log(`ℹ️  [LOG] ${text}`);
      }
    }
  });

  // Capture page errors
  page.on('pageerror', error => {
    console.log(`💥 [PAGE ERROR] ${error.message}`);
    console.log(error.stack);
  });

  // Capture request failures
  page.on('requestfailed', request => {
    console.log(`🚫 [REQUEST FAILED] ${request.url()}`);
    console.log(`   Failure: ${request.failure().errorText}`);
  });

  // Navigate to mobile voice page
  console.log('📱 Loading mobile voice page...\n');
  await page.goto('http://localhost:3000/mobile-voice', {
    waitUntil: 'networkidle2',
    timeout: 30000
  });

  // Wait for page to render
  await page.waitForTimeout(2000);

  console.log('\n✅ Page loaded successfully');
  console.log('🎯 Checking for WebRTC v2.0 banner...\n');

  // Check if green banner is visible
  const bannerText = await page.evaluate(() => {
    const elements = Array.from(document.querySelectorAll('*'));
    const banner = elements.find(el => el.textContent.includes('WebRTC v2.0'));
    return banner ? banner.textContent : null;
  });

  if (bannerText) {
    console.log('✅ GREEN BANNER FOUND: ' + bannerText.trim());
  } else {
    console.log('❌ GREEN BANNER NOT FOUND - Old code may be loaded');
  }

  // Wait for conversations to load
  console.log('\n⏳ Waiting for conversations to load...\n');
  await page.waitForTimeout(3000);

  // Select first conversation
  console.log('📋 Selecting first conversation...\n');
  try {
    await page.click('div[role="button"]'); // Click dropdown
    await page.waitForTimeout(500);
    await page.keyboard.press('ArrowDown'); // Select first item
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1000);

    console.log('✅ Conversation selected\n');
  } catch (err) {
    console.log('⚠️  Could not select conversation:', err.message);
  }

  // Click start button
  console.log('🎬 Clicking START button...\n');
  try {
    // Find the green play button
    const startButton = await page.$('button[aria-label="Start session"], button svg[data-testid="PlayArrowIcon"]');

    if (startButton) {
      await startButton.click();
      console.log('✅ Start button clicked\n');
      console.log('📊 Monitoring console for 10 seconds...\n');

      // Wait and watch for errors
      await page.waitForTimeout(10000);

      console.log('\n✅ Debug session complete');
    } else {
      console.log('❌ Could not find start button');
    }
  } catch (err) {
    console.log('❌ Error clicking start:', err.message);
    console.log(err.stack);
  }

  console.log('\n👀 Browser will stay open for manual inspection...');
  console.log('Press Ctrl+C to close\n');

  // Keep browser open for inspection
  // await browser.close();
})();
