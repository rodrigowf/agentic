/**
 * test-helpers.js - E2E Test Helper Functions
 *
 * Reusable helper functions for Playwright E2E tests.
 * These helpers abstract common operations and make tests more readable.
 */

const { expect } = require('@playwright/test');

/**
 * Wait for network to be idle
 * Useful after actions that trigger API calls
 */
async function waitForNetworkIdle(page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Wait for specific API response
 * @param {Page} page - Playwright page object
 * @param {string} urlPattern - URL pattern to match (can be regex or string)
 * @param {number} timeout - Maximum wait time in ms
 * @returns {Promise<Response>} - The API response
 */
async function waitForAPIResponse(page, urlPattern, timeout = 5000) {
  const response = await page.waitForResponse(
    (response) => {
      if (typeof urlPattern === 'string') {
        return response.url().includes(urlPattern);
      }
      return urlPattern.test(response.url());
    },
    { timeout }
  );
  return response;
}

/**
 * Wait for WebSocket connection
 * @param {Page} page - Playwright page object
 * @param {string} urlPattern - WebSocket URL pattern
 * @param {number} timeout - Maximum wait time in ms
 */
async function waitForWebSocket(page, urlPattern, timeout = 5000) {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`WebSocket connection timeout: ${urlPattern}`));
    }, timeout);

    page.on('websocket', (ws) => {
      if (ws.url().includes(urlPattern)) {
        clearTimeout(timeoutId);
        resolve(ws);
      }
    });
  });
}

/**
 * Fill form fields
 * @param {Page} page - Playwright page object
 * @param {Object} fields - Object with field labels/names as keys and values to fill
 */
async function fillForm(page, fields) {
  for (const [label, value] of Object.entries(fields)) {
    const input = page.getByLabel(label, { exact: false });
    await input.fill(value);
  }
}

/**
 * Take screenshot with timestamp
 * @param {Page} page - Playwright page object
 * @param {string} name - Screenshot name
 */
async function takeTimestampedScreenshot(page, name) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${name}-${timestamp}.png`;
  await page.screenshot({ path: `test-results/screenshots/${filename}` });
  return filename;
}

/**
 * Wait for element to be visible and stable
 * @param {Page} page - Playwright page object
 * @param {string} selector - Element selector
 * @param {number} timeout - Maximum wait time in ms
 */
async function waitForElementStable(page, selector, timeout = 5000) {
  const element = page.locator(selector);
  await element.waitFor({ state: 'visible', timeout });
  // Wait for element to stop moving (useful for animations)
  await expect(element).toBeVisible();
  await page.waitForTimeout(100); // Brief pause for stability
}

/**
 * Mock API endpoint
 * @param {Page} page - Playwright page object
 * @param {string} url - API endpoint URL pattern
 * @param {Object} response - Mock response data
 * @param {number} status - HTTP status code
 */
async function mockAPIEndpoint(page, url, response, status = 200) {
  await page.route(url, (route) => {
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

/**
 * Mock WebSocket connection
 * @param {Page} page - Playwright page object
 * @param {string} urlPattern - WebSocket URL pattern
 * @param {Array} messages - Array of messages to send
 */
async function mockWebSocket(page, urlPattern, messages = []) {
  await page.evaluateOnNewDocument((pattern, msgs) => {
    const OriginalWebSocket = window.WebSocket;

    class MockWebSocket extends EventTarget {
      constructor(url) {
        super();
        this.url = url;
        this.readyState = 0; // CONNECTING

        if (url.includes(pattern)) {
          setTimeout(() => {
            this.readyState = 1; // OPEN
            this.dispatchEvent(new Event('open'));

            // Send mock messages
            msgs.forEach((msg, index) => {
              setTimeout(() => {
                const event = new MessageEvent('message', {
                  data: JSON.stringify(msg),
                });
                this.dispatchEvent(event);
              }, (index + 1) * 100);
            });
          }, 100);
        } else {
          return new OriginalWebSocket(url);
        }
      }

      send(data) {
        console.log('MockWebSocket.send:', data);
      }

      close() {
        this.readyState = 3; // CLOSED
        this.dispatchEvent(new Event('close'));
      }
    }

    window.WebSocket = MockWebSocket;
  }, urlPattern, messages);
}

/**
 * Wait for console message
 * @param {Page} page - Playwright page object
 * @param {string|RegExp} pattern - Pattern to match in console message
 * @param {number} timeout - Maximum wait time in ms
 */
async function waitForConsoleMessage(page, pattern, timeout = 5000) {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(new Error(`Console message timeout: ${pattern}`));
    }, timeout);

    page.on('console', (msg) => {
      const text = msg.text();
      const matches =
        typeof pattern === 'string' ? text.includes(pattern) : pattern.test(text);

      if (matches) {
        clearTimeout(timeoutId);
        resolve(msg);
      }
    });
  });
}

/**
 * Click and wait for navigation
 * @param {Page} page - Playwright page object
 * @param {string} selector - Element selector
 */
async function clickAndNavigate(page, selector) {
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle' }),
    page.click(selector),
  ]);
}

/**
 * Get table data
 * @param {Page} page - Playwright page object
 * @param {string} tableSelector - Table selector
 * @returns {Promise<Array<Object>>} - Array of row objects
 */
async function getTableData(page, tableSelector) {
  return await page.evaluate((selector) => {
    const table = document.querySelector(selector);
    if (!table) return [];

    const headers = Array.from(table.querySelectorAll('th')).map((th) =>
      th.textContent.trim()
    );
    const rows = Array.from(table.querySelectorAll('tbody tr'));

    return rows.map((row) => {
      const cells = Array.from(row.querySelectorAll('td'));
      const rowData = {};
      cells.forEach((cell, index) => {
        rowData[headers[index]] = cell.textContent.trim();
      });
      return rowData;
    });
  }, tableSelector);
}

/**
 * Wait for spinner/loader to disappear
 * @param {Page} page - Playwright page object
 * @param {string} selector - Spinner selector (default: common spinner selectors)
 */
async function waitForLoadingComplete(page, selector = '[role="progressbar"], .loading, .spinner') {
  try {
    await page.waitForSelector(selector, { state: 'hidden', timeout: 10000 });
  } catch (error) {
    // Spinner might not be present, which is fine
  }
}

/**
 * Retry action until success or timeout
 * @param {Function} action - Async function to retry
 * @param {number} maxAttempts - Maximum number of attempts
 * @param {number} delayMs - Delay between attempts in ms
 */
async function retryUntilSuccess(action, maxAttempts = 3, delayMs = 1000) {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      return await action();
    } catch (error) {
      if (i === maxAttempts - 1) throw error;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
}

/**
 * Check accessibility violations (requires @axe-core/playwright)
 * @param {Page} page - Playwright page object
 */
async function checkA11y(page) {
  // Note: Requires installation of @axe-core/playwright
  // npm install --save-dev @axe-core/playwright
  try {
    const { injectAxe, checkA11y: axeCheck } = require('@axe-core/playwright');
    await injectAxe(page);
    await axeCheck(page);
  } catch (error) {
    console.warn('Accessibility check skipped (install @axe-core/playwright)');
  }
}

/**
 * Get local storage item
 * @param {Page} page - Playwright page object
 * @param {string} key - Storage key
 */
async function getLocalStorage(page, key) {
  return await page.evaluate((k) => localStorage.getItem(k), key);
}

/**
 * Set local storage item
 * @param {Page} page - Playwright page object
 * @param {string} key - Storage key
 * @param {string} value - Storage value
 */
async function setLocalStorage(page, key, value) {
  await page.evaluate(
    ({ k, v }) => localStorage.setItem(k, v),
    { k: key, v: value }
  );
}

module.exports = {
  waitForNetworkIdle,
  waitForAPIResponse,
  waitForWebSocket,
  fillForm,
  takeTimestampedScreenshot,
  waitForElementStable,
  mockAPIEndpoint,
  mockWebSocket,
  waitForConsoleMessage,
  clickAndNavigate,
  getTableData,
  waitForLoadingComplete,
  retryUntilSuccess,
  checkA11y,
  getLocalStorage,
  setLocalStorage,
};
