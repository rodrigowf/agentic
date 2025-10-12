/**
 * setupTests.ts - Jest Configuration and Global Test Setup
 *
 * This file is automatically loaded by Jest before running tests.
 * It sets up:
 * - @testing-library/jest-dom custom matchers
 * - Mock Service Worker (MSW) for API mocking
 * - WebSocket mocking
 * - Global test utilities
 */

import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

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

// Store WebSocket server instances for cleanup
declare global {
  var mockWebSocketServers: WS[];
  var createMockWebSocketServer: (url: string) => WS;
}

global.mockWebSocketServers = [];

// Helper to create mock WebSocket server
global.createMockWebSocketServer = (url: string): WS => {
  const server = new WS(url);
  global.mockWebSocketServers.push(server);
  return server;
};

// Clean up WebSocket mocks after each test
afterEach(async () => {
  // Close all mock WebSocket servers
  await Promise.all(
    global.mockWebSocketServers.map((server) => {
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

// Mock window.matchMedia (required for MUI components)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query: string) => ({
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
} as any;

// Mock ResizeObserver (required for Monaco Editor and some components)
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any;

// Mock localStorage
const localStorageMock: Storage = {
  length: 0,
  clear: jest.fn(),
  getItem: jest.fn(),
  key: jest.fn(),
  removeItem: jest.fn(),
  setItem: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock sessionStorage
const sessionStorageMock: Storage = {
  length: 0,
  clear: jest.fn(),
  getItem: jest.fn(),
  key: jest.fn(),
  removeItem: jest.fn(),
  setItem: jest.fn(),
};
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock });

// ============================================================================
// Custom Matchers
// ============================================================================

interface CustomMatchers<R = unknown> {
  toHaveReceivedWebSocketMessage(expected: Record<string, unknown>): R;
}

declare global {
  namespace jest {
    interface Expect extends CustomMatchers {}
    interface Matchers<R> extends CustomMatchers<R> {}
    interface InverseAsymmetricMatchers extends CustomMatchers {}
  }
}

// Add custom matcher for checking WebSocket messages
expect.extend({
  toHaveReceivedWebSocketMessage(
    received: { messages?: string[] },
    expected: Record<string, unknown>
  ) {
    const messages = received.messages || [];
    const hasMessage = messages.some((msg: string) => {
      try {
        const parsed = JSON.parse(msg);
        return JSON.stringify(parsed) === JSON.stringify(expected);
      } catch {
        return msg === JSON.stringify(expected);
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
