/**
 * global-setup.js - Playwright Global Setup
 *
 * Runs once before all tests.
 * Use this for:
 * - Starting external services
 * - Creating test databases
 * - Global authentication setup
 */

const { chromium } = require('@playwright/test');

module.exports = async (config) => {
  console.log('🚀 Starting global E2E test setup...');

  // Example: Global authentication (if needed)
  // const browser = await chromium.launch();
  // const page = await browser.newPage();
  // await page.goto(config.use.baseURL);
  // // Perform authentication
  // await page.context().storageState({ path: 'playwright/.auth/user.json' });
  // await browser.close();

  console.log('✅ Global E2E test setup complete');
};
