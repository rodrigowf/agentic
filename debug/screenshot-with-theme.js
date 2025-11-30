const puppeteer = require('puppeteer');

async function takeScreenshot(url, outputPath, waitTime = 1000, theme = 'dark') {
  let browser;
  try {
    console.log(`📸 Taking screenshot of: ${url}`);
    console.log(`🎨 Theme: ${theme}`);
    console.log(`⏳ Wait time: ${waitTime}ms`);

    browser = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const page = await browser.newPage();

    // Set viewport
    await page.setViewport({ width: 1920, height: 1080 });

    // Collect console messages
    const consoleMessages = [];
    page.on('console', msg => {
      consoleMessages.push(`[${msg.type()}] ${msg.text()}`);
    });

    // Collect errors
    const errors = [];
    page.on('pageerror', error => {
      errors.push(error.message);
    });

    // Navigate to page
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 });

    // Set theme in localStorage
    await page.evaluate((themeMode) => {
      localStorage.setItem('themeMode', themeMode);
    }, theme);

    // Reload to apply theme
    await page.reload({ waitUntil: 'networkidle0' });

    // Wait for specified time
    await page.waitForTimeout(waitTime);

    // Take screenshot
    await page.screenshot({ path: outputPath, fullPage: false });

    const title = await page.title();

    console.log(`✅ Screenshot saved to: ${outputPath}`);
    console.log(`📏 Viewport: 1920x1080`);
    console.log(`📄 Page title: ${title}`);

    // Log console messages
    if (consoleMessages.length > 0) {
      console.log('\n📝 Console messages:');
      consoleMessages.slice(0, 10).forEach(msg => console.log(`  ${msg}`));
      if (consoleMessages.length > 10) {
        console.log(`  ... and ${consoleMessages.length - 10} more`);
      }
    }

    // Log errors
    if (errors.length > 0) {
      console.log('\n❌ Page errors:');
      errors.forEach(err => console.log(`  ${err}`));
    }

    console.log(`\n📋 File path for reference:\n${outputPath}`);

  } catch (error) {
    console.error(`❌ Error taking screenshot: ${error.message}`);
    throw error;
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Parse command line arguments
const args = process.argv.slice(2);
const url = args[0] || 'http://localhost:3000';
const outputPath = args[1] || `/home/rodrigo/agentic/debug/screenshots/screenshot-${Date.now()}.png`;
const waitTime = parseInt(args[2]) || 1000;
const theme = args[3] || 'dark';

console.log(`\n📸 Taking screenshot of: ${url}`);
console.log(`⏳ Wait time: ${waitTime}ms`);

takeScreenshot(url, outputPath, waitTime, theme)
  .then(() => process.exit(0))
  .catch((error) => {
    console.error('Failed to take screenshot:', error);
    process.exit(1);
  });
