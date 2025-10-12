/**
 * setup.js - Test Utilities and Helpers
 *
 * Provides custom render functions, test helpers, and utilities
 * for writing tests across the application.
 */

import React from 'react';
import { render } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

// ============================================================================
// Custom Render Function with Providers
// ============================================================================

/**
 * Custom render function that wraps components with necessary providers
 *
 * @param {React.Component} ui - Component to render
 * @param {Object} options - Render options
 * @param {Object} options.initialEntries - Initial router entries
 * @param {Object} options.theme - Custom theme override
 * @param {Object} options.renderOptions - Additional render options
 * @returns {Object} Render result with utilities
 */
export function renderWithProviders(
  ui,
  {
    initialEntries = ['/'],
    theme = createTheme(),
    ...renderOptions
  } = {}
) {
  function Wrapper({ children }) {
    return (
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          {children}
        </ThemeProvider>
      </BrowserRouter>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
}

// ============================================================================
// WebSocket Test Helpers
// ============================================================================

/**
 * Create a mock WebSocket and wait for connection
 *
 * @param {string} url - WebSocket URL
 * @returns {Promise<Object>} Mock WebSocket server
 */
export async function createConnectedWebSocket(url) {
  const server = global.createMockWebSocketServer(url);
  await server.connected;
  return server;
}

/**
 * Send a message from mock WebSocket server to client
 *
 * @param {Object} server - Mock WebSocket server
 * @param {Object} message - Message to send
 */
export function sendWebSocketMessage(server, message) {
  server.send(JSON.stringify(message));
}

/**
 * Wait for WebSocket to receive a message
 *
 * @param {Object} server - Mock WebSocket server
 * @param {number} timeout - Timeout in ms
 * @returns {Promise<Object>} Received message
 */
export async function waitForWebSocketMessage(server, timeout = 1000) {
  const message = await server.nextMessage;
  return JSON.parse(message);
}

// ============================================================================
// API Test Helpers
// ============================================================================

/**
 * Wait for element to be removed from the document
 *
 * @param {Function} queryFn - Query function
 * @param {number} timeout - Timeout in ms
 */
export async function waitForElementToBeRemoved(queryFn, { timeout = 3000 } = {}) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (!queryFn()) {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 50));
  }

  throw new Error('Element was not removed within timeout');
}

/**
 * Create mock fetch response
 *
 * @param {Object} data - Response data
 * @param {number} status - HTTP status code
 * @returns {Promise<Response>} Mock response
 */
export function createMockFetchResponse(data, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
    headers: new Headers({
      'Content-Type': 'application/json',
    }),
  });
}

// ============================================================================
// Component Test Helpers
// ============================================================================

/**
 * Wait for async updates to complete
 */
export async function flushPromises() {
  await new Promise(resolve => setTimeout(resolve, 0));
}

/**
 * Simulate user typing in an input field
 *
 * @param {HTMLElement} element - Input element
 * @param {string} text - Text to type
 * @param {Object} userEvent - User event instance from @testing-library/user-event
 */
export async function typeInInput(element, text, userEvent) {
  await userEvent.clear(element);
  await userEvent.type(element, text);
}

/**
 * Wait for condition to be true
 *
 * @param {Function} condition - Condition function
 * @param {number} timeout - Timeout in ms
 * @param {number} interval - Check interval in ms
 */
export async function waitFor(condition, { timeout = 3000, interval = 50 } = {}) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (condition()) {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  throw new Error('Condition was not met within timeout');
}

// ============================================================================
// Mock Data Generators
// ============================================================================

/**
 * Create mock agent configuration
 *
 * @param {Object} overrides - Override default values
 * @returns {Object} Mock agent config
 */
export function createMockAgent(overrides = {}) {
  return {
    name: 'TestAgent',
    agent_type: 'looping',
    tools: ['web_search'],
    llm: {
      provider: 'openai',
      model: 'gpt-4.1-mini',
      temperature: 0.0,
      max_tokens: null,
    },
    prompt: {
      system: 'You are a test agent',
      user: 'Perform test task',
    },
    description: 'A test agent',
    max_consecutive_auto_reply: 20,
    reflect_on_tool_use: true,
    terminate_on_text: false,
    tool_call_loop: true,
    ...overrides,
  };
}

/**
 * Create mock tool configuration
 *
 * @param {Object} overrides - Override default values
 * @returns {Object} Mock tool config
 */
export function createMockTool(overrides = {}) {
  return {
    name: 'test_tool',
    file: 'test_tool.py',
    description: 'A test tool',
    ...overrides,
  };
}

/**
 * Create mock WebSocket event
 *
 * @param {string} type - Event type
 * @param {Object} data - Event data
 * @returns {Object} Mock WebSocket event
 */
export function createMockWSEvent(type, data = {}) {
  return {
    type,
    data,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Create mock conversation
 *
 * @param {Object} overrides - Override default values
 * @returns {Object} Mock conversation
 */
export function createMockConversation(overrides = {}) {
  return {
    id: 'test-conversation-id',
    name: 'Test Conversation',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    voice_model: null,
    metadata: {},
    ...overrides,
  };
}

// ============================================================================
// Test Matchers
// ============================================================================

/**
 * Check if element has specific class
 *
 * @param {HTMLElement} element - Element to check
 * @param {string} className - Class name to check for
 * @returns {boolean} True if element has class
 */
export function hasClass(element, className) {
  return element.classList.contains(className);
}

/**
 * Get all elements with specific test ID
 *
 * @param {HTMLElement} container - Container element
 * @param {string} testId - Test ID to search for
 * @returns {Array<HTMLElement>} Array of elements
 */
export function getAllByTestId(container, testId) {
  return container.querySelectorAll(`[data-testid="${testId}"]`);
}

// ============================================================================
// Cleanup Helpers
// ============================================================================

/**
 * Clean up all timers and async operations
 */
export function cleanupTimers() {
  jest.clearAllTimers();
  jest.useRealTimers();
}

/**
 * Reset all mocks
 */
export function resetAllMocks() {
  jest.clearAllMocks();
  jest.resetAllMocks();
  localStorage.clear();
  sessionStorage.clear();
}

// ============================================================================
// Export All Utilities
// ============================================================================

export * from '@testing-library/react';
export { renderWithProviders as render };
