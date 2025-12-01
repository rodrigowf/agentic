const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Test different viewport sizes
const viewports = [
  { name: 'desktop-large', width: 1920, height: 1080, isMobile: false },
  { name: 'desktop-medium', width: 1280, height: 800, isMobile: false },
  { name: 'tablet-landscape', width: 1024, height: 768, isMobile: false },
  { name: 'tablet-portrait', width: 768, height: 1024, isMobile: true },
  { name: 'mobile-large', width: 414, height: 896, isMobile: true },
  { name: 'mobile-medium', width: 375, height: 667, isMobile: true },
  { name: 'mobile-small', width: 320, height: 568, isMobile: true },
];

(async () => {
  const url = 'http://localhost:3000/agentic/voice';
  const outputDir = '/home/rodrigo/agentic/debug/screenshots/responsive-test';

  // Create output directory
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log('🧪 Starting Responsive Layout E2E Test\n');
  console.log('URL:', url);
  console.log('Output:', outputDir);
  console.log('─'.repeat(60));

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const results = [];

  for (const viewport of viewports) {
    console.log(`\n📱 Testing: ${viewport.name} (${viewport.width}x${viewport.height})`);

    const page = await browser.newPage();
    await page.setViewport({
      width: viewport.width,
      height: viewport.height,
      isMobile: viewport.isMobile,
      deviceScaleFactor: 2
    });

    try {
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
      await page.waitForTimeout(2000);

      // Check if elements exist and their visibility
      const layoutInfo = await page.evaluate(() => {
        // Check for drawer (mobile)
        const drawer = document.querySelector('.MuiDrawer-root');
        const drawerPaper = document.querySelector('.MuiDrawer-paper');

        // Check for hamburger button
        const hamburger = document.querySelector('[aria-label*="menu"], button svg[data-testid="MenuIcon"]')?.closest('button');

        // Check for left panel (desktop)
        const leftPanel = Array.from(document.querySelectorAll('div')).find(div => {
          const style = window.getComputedStyle(div);
          return style.borderRight && style.borderRight !== 'none' && div.textContent.includes('Team Insights');
        });

        // Check main container flex direction
        const mainContainer = document.querySelector('div[tabindex="-1"]');
        const flexDirection = mainContainer ? window.getComputedStyle(mainContainer).flexDirection : null;

        // Check for tabs
        const tabs = document.querySelector('.MuiTabs-root');
        const tabLabels = Array.from(document.querySelectorAll('.MuiTab-root')).map(t => t.textContent);

        return {
          hasDrawer: !!drawer,
          drawerVisible: drawerPaper ? window.getComputedStyle(drawerPaper).visibility !== 'hidden' : false,
          hasHamburger: !!hamburger,
          hamburgerVisible: hamburger ? window.getComputedStyle(hamburger).display !== 'none' : false,
          hasLeftPanel: !!leftPanel,
          leftPanelVisible: leftPanel ? window.getComputedStyle(leftPanel).display !== 'none' : false,
          flexDirection,
          hasTabs: !!tabs,
          tabLabels,
          windowWidth: window.innerWidth,
          windowHeight: window.innerHeight,
        };
      });

      const screenshotPath = path.join(outputDir, `${viewport.name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: false });

      results.push({
        viewport: viewport.name,
        width: viewport.width,
        expected: viewport.isMobile ? 'mobile' : 'desktop',
        ...layoutInfo,
        screenshot: screenshotPath
      });

      console.log('  ✓ Screenshot saved');
      console.log('  Layout info:');
      console.log('    - Flex direction:', layoutInfo.flexDirection);
      console.log('    - Hamburger visible:', layoutInfo.hamburgerVisible);
      console.log('    - Left panel visible:', layoutInfo.leftPanelVisible);
      console.log('    - Has drawer:', layoutInfo.hasDrawer);

    } catch (error) {
      console.error('  ✗ Error:', error.message);
      results.push({
        viewport: viewport.name,
        width: viewport.width,
        error: error.message
      });
    }

    await page.close();
  }

  await browser.close();

  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('📊 Test Summary\n');

  results.forEach(result => {
    if (result.error) {
      console.log(`❌ ${result.viewport}: ERROR - ${result.error}`);
    } else {
      const isMobileLayout = result.flexDirection === 'column' || result.hamburgerVisible;
      const shouldBeMobile = result.width < 960;
      const correct = isMobileLayout === shouldBeMobile;

      console.log(`${correct ? '✅' : '⚠️ '} ${result.viewport} (${result.width}px)`);
      console.log(`   Expected: ${shouldBeMobile ? 'mobile' : 'desktop'}, Got: ${isMobileLayout ? 'mobile' : 'desktop'}`);
      console.log(`   FlexDir: ${result.flexDirection}, Hamburger: ${result.hamburgerVisible}, LeftPanel: ${result.leftPanelVisible}`);
    }
  });

  console.log('\n📁 Screenshots saved to:', outputDir);
  console.log('─'.repeat(60));
})();
