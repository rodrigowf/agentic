/**
 * E2E Tests for Voice Route Accessibility
 *
 * Tests all voice-related routes to ensure they're accessible and render correctly.
 */

const { chromium } = require('playwright');

const BASE_URL = 'http://localhost:3000';
const TIMEOUT = 10000;

async function runTests() {
  console.log('🚀 Starting Voice Routes E2E Tests...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  let passed = 0;
  let failed = 0;
  const results = [];

  // Helper: Test route accessibility
  async function testRoute(name, url, expectedTitle, checks = []) {
    console.log(`\n📝 Testing: ${name}`);
    console.log(`   URL: ${url}`);

    try {
      // Navigate to route
      const response = await page.goto(url, {
        waitUntil: 'networkidle',
        timeout: TIMEOUT
      });

      // Check HTTP status
      const status = response.status();
      console.log(`   ✓ HTTP Status: ${status}`);

      if (status !== 200) {
        throw new Error(`Expected 200, got ${status}`);
      }

      // Wait for page to load
      await page.waitForTimeout(2000);

      // Check final URL (detect redirects)
      const finalUrl = page.url();
      console.log(`   ✓ Final URL: ${finalUrl}`);

      if (finalUrl !== url) {
        throw new Error(`REDIRECT DETECTED: ${url} → ${finalUrl}`);
      }

      // Check page title
      const title = await page.title();
      console.log(`   ✓ Page Title: ${title}`);

      // Run custom checks
      for (const check of checks) {
        await check(page);
      }

      console.log(`   ✅ PASSED: ${name}`);
      passed++;
      results.push({ name, status: 'PASSED', url, finalUrl });

    } catch (error) {
      console.log(`   ❌ FAILED: ${name}`);
      console.log(`   Error: ${error.message}`);
      failed++;
      results.push({ name, status: 'FAILED', url, error: error.message });
    }
  }

  // ============================================
  // TEST 1: Voice WebRTC Test Page
  // ============================================
  await testRoute(
    'Voice WebRTC Test Page',
    `${BASE_URL}/agentic/voice-webrtc`,
    'AutoGen Dashboard',
    [
      async (page) => {
        const heading = await page.textContent('h4, h5, h6, [role="heading"]');
        if (!heading.includes('Voice Assistant') && !heading.includes('Backend WebRTC')) {
          throw new Error(`Expected heading with "Voice Assistant", got: ${heading}`);
        }
        console.log(`   ✓ Heading found: ${heading.substring(0, 50)}...`);
      },
      async (page) => {
        const hasButton = await page.isVisible('button:has-text("Start Session")');
        if (!hasButton) {
          throw new Error('Start Session button not found');
        }
        console.log(`   ✓ Start Session button visible`);
      }
    ]
  );

  // ============================================
  // TEST 2: Voice Original (without conversation ID)
  // ============================================
  await testRoute(
    'Voice Original (No ID)',
    `${BASE_URL}/agentic/voice-original`,
    'AutoGen Dashboard',
    [
      async (page) => {
        // Should show the interface, even if error is displayed
        const hasTeamInsights = await page.isVisible('text=TEAM INSIGHTS');
        const hasError = await page.isVisible('text=Missing conversation id');

        if (hasTeamInsights) {
          console.log(`   ✓ Voice interface rendered (Team Insights visible)`);
        } else if (hasError) {
          console.log(`   ✓ Voice interface rendered (Error message visible)`);
        } else {
          throw new Error('Voice interface not rendered');
        }
      }
    ]
  );

  // ============================================
  // TEST 3: Voice Original (with conversation ID)
  // ============================================
  await testRoute(
    'Voice Original (With ID: "test-conv")',
    `${BASE_URL}/agentic/voice-original/test-conv`,
    'AutoGen Dashboard',
    [
      async (page) => {
        // Should show voice interface
        const hasTeamInsights = await page.isVisible('text=TEAM INSIGHTS');
        if (!hasTeamInsights) {
          throw new Error('TEAM INSIGHTS tab not found');
        }
        console.log(`   ✓ Voice interface rendered with conversation ID`);
      },
      async (page) => {
        // Should have controls
        const hasConfigure = await page.isVisible('button:has-text("Configure")');
        if (!hasConfigure) {
          throw new Error('Configure button not found');
        }
        console.log(`   ✓ Configure button visible`);
      }
    ]
  );

  // ============================================
  // TEST 4: Voice Modular (without conversation ID)
  // ============================================
  await testRoute(
    'Voice Modular (No ID)',
    `${BASE_URL}/agentic/voice-modular`,
    'AutoGen Dashboard',
    [
      async (page) => {
        // Should show the interface
        const hasTeamInsights = await page.isVisible('text=TEAM INSIGHTS');
        const hasError = await page.isVisible('text=Missing conversation id');

        if (hasTeamInsights || hasError) {
          console.log(`   ✓ Voice interface rendered`);
        } else {
          throw new Error('Voice interface not rendered');
        }
      }
    ]
  );

  // ============================================
  // TEST 5: Voice Modular (with conversation ID)
  // ============================================
  await testRoute(
    'Voice Modular (With ID: "test-conv")',
    `${BASE_URL}/agentic/voice-modular/test-conv`,
    'AutoGen Dashboard',
    [
      async (page) => {
        // Should show voice interface
        const hasTeamInsights = await page.isVisible('text=TEAM INSIGHTS');
        if (!hasTeamInsights) {
          throw new Error('TEAM INSIGHTS tab not found');
        }
        console.log(`   ✓ Voice interface rendered with conversation ID`);
      }
    ]
  );

  // ============================================
  // TEST 6: Main Voice Route (existing production)
  // ============================================
  await testRoute(
    'Main Voice Route (Production)',
    `${BASE_URL}/agentic/voice`,
    'AutoGen Dashboard',
    [
      async (page) => {
        // Should show voice dashboard (list of conversations)
        const hasVoiceText = await page.isVisible('text=Voice');
        if (!hasVoiceText) {
          throw new Error('Voice page not rendered');
        }
        console.log(`   ✓ Voice dashboard rendered`);
      }
    ]
  );

  // ============================================
  // TEST 7: Check for Router Issues
  // ============================================
  console.log('\n🔍 Checking for Router Configuration Issues...');

  // Navigate to a test route and inspect React Router
  await page.goto(`${BASE_URL}/agentic/voice-original`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  const finalUrl = page.url();
  const isRedirected = !finalUrl.includes('/voice-original');

  if (isRedirected) {
    console.log(`   ⚠️  WARNING: Route is being redirected!`);
    console.log(`   Expected: ${BASE_URL}/agentic/voice-original`);
    console.log(`   Got: ${finalUrl}`);
    console.log(`   This indicates a React Router configuration issue.`);
  } else {
    console.log(`   ✓ No unexpected redirects detected`);
  }

  // ============================================
  // TEST 8: Screenshot All Routes
  // ============================================
  console.log('\n📸 Taking screenshots of all routes...');

  const routes = [
    { name: 'voice-webrtc', url: `${BASE_URL}/agentic/voice-webrtc` },
    { name: 'voice-original', url: `${BASE_URL}/agentic/voice-original` },
    { name: 'voice-original-with-id', url: `${BASE_URL}/agentic/voice-original/test-conv` },
    { name: 'voice-modular', url: `${BASE_URL}/agentic/voice-modular` },
    { name: 'voice-modular-with-id', url: `${BASE_URL}/agentic/voice-modular/test-conv` },
  ];

  for (const route of routes) {
    try {
      await page.goto(route.url, { waitUntil: 'networkidle', timeout: TIMEOUT });
      await page.waitForTimeout(2000);

      const screenshotPath = `/home/rodrigo/agentic/debug/screenshots/e2e-${route.name}.png`;
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`   ✓ Screenshot saved: e2e-${route.name}.png`);
    } catch (error) {
      console.log(`   ❌ Failed to screenshot ${route.name}: ${error.message}`);
    }
  }

  // ============================================
  // Summary
  // ============================================
  await browser.close();

  console.log('\n' + '='.repeat(60));
  console.log('📊 TEST RESULTS SUMMARY');
  console.log('='.repeat(60));
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`📝 Total: ${passed + failed}`);
  console.log('='.repeat(60));

  console.log('\n📋 Detailed Results:');
  results.forEach((result, i) => {
    console.log(`\n${i + 1}. ${result.name}`);
    console.log(`   Status: ${result.status}`);
    console.log(`   URL: ${result.url}`);
    if (result.finalUrl) {
      console.log(`   Final URL: ${result.finalUrl}`);
    }
    if (result.error) {
      console.log(`   Error: ${result.error}`);
    }
  });

  console.log('\n✨ Tests complete!');

  // Exit with error code if any tests failed
  process.exit(failed > 0 ? 1 : 0);
}

// Run tests
runTests().catch((error) => {
  console.error('\n❌ Test suite failed:', error);
  process.exit(1);
});
