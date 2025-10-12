/**
 * setupTests.js - Jest Configuration and Global Test Setup
 *
 * This file is automatically loaded by Jest before running tests.
 * It sets up:
 * - @testing-library/jest-dom custom matchers
 * - Mock Service Worker (MSW) for API mocking
 * - WebSocket mocking
 * - Global test utilities
 */

import '@testing-library/jest-dom';

// ============================================================================
// Mock Service Worker (MSW) Setup
// ============================================================================

import { server } from './__tests__/mocks/server';

// Enable API mocking before all tests
beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'warn', // Warn about unhandled requests
  });
});

// Reset request handlers after each test
afterEach(() => {
  server.resetHandlers();
});

// Clean up after all tests
afterAll(() => {
  server.close();
});

// ============================================================================
// WebSocket Mock Setup
// ============================================================================

import WS from 'jest-websocket-mock';

// Store WebSocket server instances for cleanup
global.mockWebSocketServers = [];

// Helper to create mock WebSocket server
global.createMockWebSocketServer = (url) => {
  const server = new WS(url);
  global.mockWebSocketServers.push(server);
  return server;
};

// Clean up WebSocket mocks after each test
afterEach(async () => {
  // Close all mock WebSocket servers
  await Promise.all(
    global.mockWebSocketServers.map(server => {
      try {
        return server.close();
      } catch (err) {
        // Server might already be closed
        return Promise.resolve();
      }
    })
  );
  global.mockWebSocketServers = [];
});

// ============================================================================
// Global Test Configuration
// ============================================================================

// Suppress console errors in tests (optional - uncomment if needed)
// const originalError = console.error;
// beforeAll(() => {
//   console.error = (...args) => {
//     if (
//       typeof args[0] === 'string' &&
//       args[0].includes('Warning: ReactDOM.render')
//     ) {
//       return;
//     }
//     originalError.call(console, ...args);
//   };
// });
//
// afterAll(() => {
//   console.error = originalError;
// });

// Mock window.matchMedia (required for MUI components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver (required for some MUI components)
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords() {
    return [];
  }
};

// Mock ResizeObserver (required for Monaco Editor and some components)
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.sessionStorage = sessionStorageMock;

// ============================================================================
// Custom Matchers
// ============================================================================

// Add custom matcher for checking WebSocket messages
expect.extend({
  toHaveReceivedWebSocketMessage(received, expected) {
    const messages = received.messages || [];
    const hasMessage = messages.some(msg => {
      try {
        const parsed = JSON.parse(msg);
        return JSON.stringify(parsed) === JSON.stringify(expected);
      } catch {
        return msg === expected;
      }
    });

    return {
      pass: hasMessage,
      message: () =>
        hasMessage
          ? `Expected WebSocket not to receive message ${JSON.stringify(expected)}`
          : `Expected WebSocket to receive message ${JSON.stringify(expected)}`,
    };
  },
});

// ============================================================================
// Environment Variables for Tests
// ============================================================================

process.env.REACT_APP_API_URL = 'http://localhost:8000';
process.env.REACT_APP_WS_URL = 'ws://localhost:8000';
