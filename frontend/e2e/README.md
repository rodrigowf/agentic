# E2E Testing Guide

**Last Updated:** 2025-10-12

This directory contains end-to-end (E2E) tests for the agentic frontend application using Playwright.

---

## Table of Contents

1. [Overview](#overview)
2. [Setup](#setup)
3. [Running Tests](#running-tests)
4. [Writing Tests](#writing-tests)
5. [Test Structure](#test-structure)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [CI/CD Integration](#cicd-integration)

---

## Overview

E2E tests verify complete user workflows in real browsers. Unlike unit tests that test components in isolation, E2E tests:

- Use real browser automation (Chromium, Firefox, WebKit)
- Test actual user interactions (clicks, typing, navigation)
- Verify full application behavior end-to-end
- Catch integration issues between frontend and backend
- Take screenshots and videos on failure for debugging

**Test Coverage:**
- Agent management (create, edit, run, delete)
- Tool management (upload, edit, generate, save)
- Voice assistant (sessions, WebSocket streams, insights)

---

## Setup

### Prerequisites

- Node.js 16+ installed
- Frontend application dependencies installed (`npm install`)
- Backend server running (for full E2E tests)

### Installation

```bash
# Install Playwright and browsers
cd /home/rodrigo/agentic/frontend
npx playwright install

# Or install specific browsers
npx playwright install chromium
npx playwright install firefox
npx playwright install webkit
```

### Environment Configuration

Create `.env` file (optional):

```bash
# Frontend URL (default: http://localhost:3000)
PLAYWRIGHT_BASE_URL=http://localhost:3000

# Backend API URL (default: http://localhost:8000)
PLAYWRIGHT_API_URL=http://localhost:8000
```

---

## Running Tests

### Basic Commands

```bash
# Run all E2E tests
npm run test:e2e

# Run in headed mode (see browser)
npx playwright test --headed

# Run specific test file
npx playwright test e2e/tests/agent-workflow.spec.js

# Run specific test by name
npx playwright test -g "should create new looping agent"

# Run in specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit

# Run in debug mode
npx playwright test --debug

# Run with UI mode (interactive)
npm run test:e2e:ui
npx playwright test --ui
```

### Parallel Execution

```bash
# Run tests in parallel (default)
npx playwright test

# Run tests in specific number of workers
npx playwright test --workers=4

# Run tests serially
npx playwright test --workers=1
```

### Reporting

```bash
# View last test report
npx playwright show-report

# Generate HTML report
npx playwright test --reporter=html

# Generate JSON report
npx playwright test --reporter=json
```

---

## Writing Tests

### Test File Structure

```javascript
const { test, expect } = require('@playwright/test');
const { waitForAPIResponse } = require('../fixtures/test-helpers');

test.describe('Feature Name E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Setup before each test
    await page.goto('/feature');
  });

  test('should perform user action', async ({ page }) => {
    // Arrange
    await waitForAPIResponse(page, '/api/data');

    // Act
    await page.getByRole('button', { name: /click me/i }).click();

    // Assert
    await expect(page.locator('.result')).toContainText('Success');
  });
});
```

### Using Test Helpers

The project provides helper functions in `fixtures/test-helpers.js`:

```javascript
const {
  waitForAPIResponse,
  waitForWebSocket,
  fillForm,
  takeTimestampedScreenshot,
  waitForLoadingComplete,
  mockAPIEndpoint,
} = require('../fixtures/test-helpers');

test('example using helpers', async ({ page }) => {
  // Wait for API call
  await waitForAPIResponse(page, '/api/agents');

  // Fill form fields
  await fillForm(page, {
    'Agent Name': 'TestAgent',
    'Description': 'Test description',
  });

  // Wait for loading spinner to disappear
  await waitForLoadingComplete(page);

  // Take screenshot with timestamp
  await takeTimestampedScreenshot(page, 'test-result');

  // Mock API endpoint
  await mockAPIEndpoint(page, '**/api/tools', { tools: [] });
});
```

### Using Test Data

Reusable test data is in `fixtures/test-data.js`:

```javascript
const { testAgents, mockMessages, selectors, timeouts } = require('../fixtures/test-data');

test('example using test data', async ({ page }) => {
  // Use predefined agent config
  await fillForm(page, {
    'Agent Name': testAgents.looping.name,
    'Description': testAgents.looping.description,
  });

  // Use predefined selectors
  await page.click(selectors.agents.createButton);

  // Use predefined timeouts
  await expect(page.locator('.message')).toBeVisible({
    timeout: timeouts.medium,
  });

  // Mock WebSocket messages
  await mockWebSocket(page, '/api/runs/', [mockMessages.nested.textMessage]);
});
```

---

## Test Structure

### Directory Layout

```
e2e/
├── fixtures/                    # Test fixtures and helpers
│   ├── global-setup.js         # Global setup (runs once before all tests)
│   ├── global-teardown.js      # Global teardown (runs once after all tests)
│   ├── test-helpers.js         # Reusable helper functions
│   └── test-data.js            # Mock data and constants
│
├── tests/                       # Test files
│   ├── agent-workflow.spec.js  # Agent management tests
│   ├── tool-management.spec.js # Tool management tests
│   └── voice-workflow.spec.js  # Voice assistant tests
│
├── snapshots/                   # Visual regression snapshots (if using)
│
└── README.md                    # This file
```

### Configuration Files

- **`playwright.config.js`** - Main Playwright configuration
  - Test directory
  - Browsers to test
  - Timeouts and retries
  - Reporter settings
  - Web server configuration

---

## Best Practices

### 1. Use Descriptive Test Names

```javascript
// Good
test('should create looping agent and verify in list', async ({ page }) => {});

// Bad
test('test1', async ({ page }) => {});
```

### 2. Use Playwright Locators

```javascript
// Good - resilient to changes
await page.getByRole('button', { name: /submit/i }).click();
await page.getByLabel('Agent Name').fill('TestAgent');
await page.getByText('Success message').isVisible();

// Avoid - brittle CSS selectors
await page.click('.btn-submit-123');
```

### 3. Wait for State, Not Time

```javascript
// Good
await expect(page.locator('.result')).toBeVisible();
await page.waitForResponse((res) => res.url().includes('/api/agents'));

// Avoid
await page.waitForTimeout(5000);
```

### 4. Clean Up Test Data

```javascript
test.afterEach(async ({ page }) => {
  // Delete test agent if created
  const testAgent = page.locator('text=E2E_Test_Agent');
  if (await testAgent.isVisible()) {
    await page.getByRole('button', { name: /delete/i }).click();
    await page.getByRole('button', { name: /confirm/i }).click();
  }
});
```

### 5. Take Screenshots on Key Steps

```javascript
test('important workflow', async ({ page }) => {
  // Take screenshot at important steps
  await takeTimestampedScreenshot(page, 'step-1-form-filled');

  // ... perform action ...

  await takeTimestampedScreenshot(page, 'step-2-result');
});
```

### 6. Handle Flaky Tests

```javascript
// Retry flaky tests
test('potentially flaky test', async ({ page }) => {
  test.setTimeout(60000); // Increase timeout

  // Use retry logic
  await retryUntilSuccess(async () => {
    await page.getByRole('button', { name: /load/i }).click();
    await expect(page.locator('.data')).toBeVisible();
  }, 3, 1000);
});
```

### 7. Test User Workflows, Not Implementation

```javascript
// Good - tests user workflow
test('should create and run agent', async ({ page }) => {
  await page.goto('/agents');
  await page.getByRole('button', { name: /create/i }).click();
  await fillForm(page, { 'Agent Name': 'TestAgent' });
  await page.getByRole('button', { name: /save/i }).click();
  await page.getByRole('button', { name: /run/i }).click();
  await expect(page.locator('body')).toContainText(/running/i);
});

// Avoid - tests implementation details
test('should call createAgent API', async ({ page }) => {
  // Testing internal API calls instead of user workflow
});
```

---

## Troubleshooting

### Tests Failing to Connect

**Problem:** Tests can't reach frontend/backend

**Solution:**
```bash
# Ensure servers are running
cd /home/rodrigo/agentic/frontend && npm start
cd /home/rodrigo/agentic/backend && ./run.sh

# Check URLs in playwright.config.js
baseURL: 'http://localhost:3000',
apiURL: 'http://localhost:8000',
```

### Browser Not Installing

**Problem:** Playwright browsers not downloading

**Solution:**
```bash
# Reinstall browsers
npx playwright install --force

# Install system dependencies (Linux)
npx playwright install-deps

# Check disk space
df -h
```

### Tests Timing Out

**Problem:** Tests frequently timeout

**Solution:**
```javascript
// Increase timeout in playwright.config.js
module.exports = defineConfig({
  timeout: 60 * 1000, // 60 seconds
  expect: {
    timeout: 10000, // 10 seconds for assertions
  },
});

// Or increase per-test
test('slow test', async ({ page }) => {
  test.setTimeout(120000); // 2 minutes
});
```

### Screenshots Not Saving

**Problem:** Screenshots not being saved on failure

**Solution:**
```javascript
// Check playwright.config.js
use: {
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
}

// Create screenshots directory
mkdir -p test-results/screenshots
```

### WebSocket Tests Failing

**Problem:** WebSocket connection tests fail

**Solution:**
```javascript
// Use proper WebSocket mocking
await mockWebSocket(page, '/api/runs/', messages);

// Or listen for actual WebSocket
const wsPromise = page.waitForEvent('websocket', {
  predicate: (ws) => ws.url().includes('/api/runs/'),
  timeout: 10000,
});
```

### Flaky Tests

**Problem:** Tests pass sometimes, fail others

**Solution:**
```javascript
// 1. Use proper waiters
await waitForLoadingComplete(page);
await waitForAPIResponse(page, '/api/agents');

// 2. Increase specific timeouts
await expect(element).toBeVisible({ timeout: 10000 });

// 3. Disable animations (in playwright.config.js)
use: {
  hasTouch: false,
  // Disable animations
  actionTimeout: 5000,
}

// 4. Use retry logic
await retryUntilSuccess(async () => {
  await page.click('.button');
  await expect(page.locator('.result')).toBeVisible();
}, 3, 1000);
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Install Playwright browsers
        run: |
          cd frontend
          npx playwright install --with-deps

      - name: Start backend server
        run: |
          cd backend
          ./run.sh &
          sleep 10

      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 30

      - name: Upload screenshots
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-screenshots
          path: frontend/test-results/screenshots/
```

### Docker Example

```dockerfile
# Dockerfile for E2E tests
FROM mcr.microsoft.com/playwright:v1.40.0-focal

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

CMD ["npx", "playwright", "test"]
```

```bash
# Build and run
docker build -t agentic-e2e -f Dockerfile.e2e .
docker run -e PLAYWRIGHT_BASE_URL=http://host.docker.internal:3000 agentic-e2e
```

---

## Test Metrics

### Coverage Goals

- **Agent workflows:** 90%+ coverage of user flows
- **Tool management:** 85%+ coverage of CRUD operations
- **Voice assistant:** 80%+ coverage of session management

### Performance Benchmarks

- Test suite should complete in under 10 minutes
- Individual tests should complete in under 60 seconds
- Page load times should be under 3 seconds

---

## Additional Resources

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright API Reference](https://playwright.dev/docs/api/class-playwright)
- [Playwright Debugging Guide](https://playwright.dev/docs/debug)

---

## Support

For issues or questions about E2E tests:

1. Check existing test examples in `e2e/tests/`
2. Review helper functions in `e2e/fixtures/test-helpers.js`
3. Consult Playwright documentation
4. Check test output in `playwright-report/`
5. Review screenshots in `test-results/screenshots/`

---

**Last Updated:** 2025-10-12
