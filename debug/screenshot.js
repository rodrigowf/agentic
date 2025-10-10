#!/usr/bin/env node

/**
 * Screenshot Automation Script
 *
 * This script uses Puppeteer to take full-page screenshots of the running application.
 * It can be used for automated UI development and visual regression testing.
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Configuration
const DEFAULT_URL = 'http://localhost:3000';
const DEFAULT_OUTPUT = path.join(__dirname, 'screenshots', `screenshot-${Date.now()}.png`);
const VIEWPORT = {
  width: 1920,
  height: 1080,
  deviceScaleFactor: 1
};

// Parse command line arguments
const args = process.argv.slice(2);
const url = args[0] || DEFAULT_URL;
const outputPath = args[1] || DEFAULT_OUTPUT;
const waitTime = parseInt(args[2]) || 1000; // Wait time in ms for page to fully load

async function takeScreenshot() {
  let browser;

  try {
    console.log(`📸 Taking screenshot of: ${url}`);
    console.log(`⏳ Wait time: ${waitTime}ms`);

    // Ensure screenshots directory exists
    const screenshotsDir = path.join(__dirname, 'screenshots');
    if (!fs.existsSync(screenshotsDir)) {
      fs.mkdirSync(screenshotsDir, { recursive: true });
    }

    // Launch browser
    browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu'
      ]
    });

    const page = await browser.newPage();

    // Set viewport
    await page.setViewport(VIEWPORT);

    // Navigate to URL
    await page.goto(url, {
      waitUntil: 'networkidle2',
      timeout: 30000
    });

    // Wait additional time for dynamic content
    await page.waitForTimeout(waitTime);

    // Take full page screenshot
    await page.screenshot({
      path: outputPath,
      fullPage: true
    });

    console.log(`✅ Screenshot saved to: ${outputPath}`);
    console.log(`📏 Viewport: ${VIEWPORT.width}x${VIEWPORT.height}`);

    // Get page title for context
    const title = await page.title();
    console.log(`📄 Page title: ${title}`);

    // Return the output path for programmatic use
    return outputPath;

  } catch (error) {
    console.error('❌ Error taking screenshot:', error.message);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Run if called directly
if (require.main === module) {
  takeScreenshot().then(path => {
    console.log('\n📋 File path for reference:');
    console.log(path);
  });
}

module.exports = takeScreenshot;
