/**
 * playwright.config.js - Playwright E2E Test Configuration
 *
 * Configuration for end-to-end tests using Playwright.
 * Tests real user workflows in actual browsers.
 */

const { defineConfig, devices } = require('@playwright/test');

/**
 * See https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  // Test directory
  testDir: './e2e/tests',

  // Maximum time one test can run for
  timeout: 30 * 1000,

  // Expect timeout for assertions
  expect: {
    timeout: 5000,
  },

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list'], // Console output
  ],

  // Shared settings for all the projects below
  use: {
    // Base URL to use in actions like `await page.goto('/')`
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',

    // API endpoint for backend
    apiURL: process.env.PLAYWRIGHT_API_URL || 'http://localhost:8000',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Ignore HTTPS errors
    ignoreHTTPSErrors: true,

    // Browser options
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,

    // Navigation timeout
    navigationTimeout: 10000,

    // Action timeout
    actionTimeout: 5000,
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Test against mobile viewports
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
    // {
    //   name: 'Mobile Safari',
    //   use: { ...devices['iPhone 12'] },
    // },

    // Test against branded browsers
    // {
    //   name: 'Microsoft Edge',
    //   use: { ...devices['Desktop Edge'], channel: 'msedge' },
    // },
    // {
    //   name: 'Google Chrome',
    //   use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    // },
  ],

  // Run your local dev server before starting the tests
  webServer: [
    {
      command: 'cd .. && npm start',
      url: 'http://localhost:3000',
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    // Uncomment to also start backend server
    // {
    //   command: 'cd ../../backend && ./run.sh',
    //   url: 'http://localhost:8000',
    //   timeout: 120 * 1000,
    //   reuseExistingServer: !process.env.CI,
    //   stdout: 'pipe',
    //   stderr: 'pipe',
    // },
  ],

  // Global setup and teardown
  globalSetup: require.resolve('./e2e/fixtures/global-setup.js'),
  globalTeardown: require.resolve('./e2e/fixtures/global-teardown.js'),

  // Output folder for test artifacts
  outputDir: 'test-results/',

  // Folder for test artifacts such as screenshots, videos, traces, etc.
  snapshotDir: 'e2e/snapshots',
});
