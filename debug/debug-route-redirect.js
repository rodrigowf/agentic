/**
 * Debug script to trace route redirects
 */

const { chromium } = require('playwright');

async function debugRoute(url, description) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`🔍 Debugging: ${description}`);
  console.log(`📍 URL: ${url}`);
  console.log('='.repeat(70));

  const browser = await chromium.launch({ headless: false, slowMo: 500 });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Track all navigation events
  const navigationLog = [];

  page.on('framenavigated', (frame) => {
    if (frame === page.mainFrame()) {
      navigationLog.push({
        type: 'framenavigated',
        url: frame.url(),
        timestamp: Date.now()
      });
      console.log(`  [Navigation] → ${frame.url()}`);
    }
  });

  // Track redirects
  page.on('response', async (response) => {
    const status = response.status();
    if (status >= 300 && status < 400) {
      console.log(`  [Redirect] ${status} from ${response.url()}`);
      const location = response.headers()['location'];
      if (location) {
        console.log(`  [Redirect] → to ${location}`);
      }
    }
  });

  // Track console logs from the page
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    if (text.includes('RouteDebug') || text.includes('Navigate') || text.includes('redirect')) {
      console.log(`  [Console ${type}] ${text}`);
    }
  });

  // Navigate and wait
  console.log('\n📡 Navigating...');
  const response = await page.goto(url, {
    waitUntil: 'networkidle',
    timeout: 10000
  });

  console.log(`\n📊 Response Status: ${response.status()}`);
  console.log(`📍 Final URL: ${page.url()}`);

  // Wait for any React Router redirects
  await page.waitForTimeout(3000);

  const finalUrl = page.url();
  console.log(`\n🎯 Final URL after 3s: ${finalUrl}`);

  // Check if we were redirected
  if (finalUrl !== url) {
    console.log(`\n⚠️  REDIRECT DETECTED!`);
    console.log(`   Expected: ${url}`);
    console.log(`   Got:      ${finalUrl}`);

    // Try to find out why
    console.log('\n🔎 Checking for React Router issues...');

    // Check if Routes component exists
    const hasRoutes = await page.evaluate(() => {
      return !!document.querySelector('[data-testid="routes"]') ||
             document.body.innerHTML.includes('Routes') ||
             window.location.pathname;
    });

    console.log(`   React Router active: ${hasRoutes}`);

    // Get current location from React Router
    const reactLocation = await page.evaluate(() => {
      return {
        pathname: window.location.pathname,
        search: window.location.search,
        hash: window.location.hash
      };
    });

    console.log(`   React location:`, reactLocation);

    // Check for error boundaries
    const hasError = await page.evaluate(() => {
      return document.body.textContent.includes('error') ||
             document.body.textContent.includes('Error') ||
             document.body.textContent.includes('404');
    });

    console.log(`   Has error on page: ${hasError}`);

    // Get page title
    const title = await page.title();
    console.log(`   Page title: ${title}`);

    // Check what's actually rendered
    const bodyText = await page.evaluate(() => {
      return document.body.innerText.substring(0, 200);
    });
    console.log(`   Page content (first 200 chars):`);
    console.log(`   "${bodyText}"`);
  } else {
    console.log(`\n✅ No redirect - URL stayed the same`);
  }

  // Take screenshot
  const screenshotName = url.split('/').pop().replace(/[^a-zA-Z0-9]/g, '-');
  const screenshotPath = `/home/rodrigo/agentic/debug/screenshots/debug-${screenshotName}.png`;
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`\n📸 Screenshot saved: debug-${screenshotName}.png`);

  // Navigation history
  console.log(`\n📜 Navigation History (${navigationLog.length} events):`);
  navigationLog.forEach((entry, i) => {
    console.log(`   ${i + 1}. ${entry.url}`);
  });

  console.log(`\n⏸️  Keeping browser open for 10 seconds for manual inspection...`);
  await page.waitForTimeout(10000);

  await browser.close();
  console.log(`✅ Browser closed`);
}

async function runDebug() {
  const BASE_URL = 'http://localhost:3000';

  console.log('\n🚀 Starting Route Redirect Debugging\n');

  // Test 1: Debug route (should work)
  await debugRoute(
    `${BASE_URL}/agentic/debug-route-original`,
    'Debug Route Original'
  );

  // Test 2: Voice original route
  await debugRoute(
    `${BASE_URL}/agentic/voice-original`,
    'Voice Original Route'
  );

  // Test 3: Voice WebRTC (known working)
  await debugRoute(
    `${BASE_URL}/agentic/voice-webrtc`,
    'Voice WebRTC Route (Control)'
  );

  console.log('\n\n✨ Debugging complete!');
}

runDebug().catch(console.error);
