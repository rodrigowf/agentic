/**
 * setup.ts - Test Utilities and Helpers
 *
 * Provides custom render functions, test helpers, and utilities
 * for writing tests across the application.
 */

import React from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme, Theme } from '@mui/material/styles';
import userEvent from '@testing-library/user-event';
import type { AgentConfig, ToolDefinition, BaseMessage } from '../types';
import WS from 'jest-websocket-mock';

// ============================================================================
// Custom Render Function with Providers
// ============================================================================

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: string[];
  theme?: Theme;
}

/**
 * Custom render function that wraps components with necessary providers
 */
export function renderWithProviders(
  ui: React.ReactElement,
  {
    initialEntries = ['/'],
    theme = createTheme(),
    ...renderOptions
  }: CustomRenderOptions = {}
): RenderResult {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <BrowserRouter>
        <ThemeProvider theme={theme}>{children}</ThemeProvider>
      </BrowserRouter>
    );
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}

// ============================================================================
// WebSocket Test Helpers
// ============================================================================

/**
 * Create a mock WebSocket and wait for connection
 */
export async function createConnectedWebSocket(url: string): Promise<WS> {
  const server = (global as any).createMockWebSocketServer(url);
  await server.connected;
  return server;
}

/**
 * Send a message from mock WebSocket server to client
 */
export function sendWebSocketMessage(server: WS, message: Record<string, unknown>): void {
  server.send(JSON.stringify(message));
}

/**
 * Wait for WebSocket to receive a message
 */
export async function waitForWebSocketMessage(
  server: WS,
  timeout: number = 1000
): Promise<Record<string, unknown>> {
  const message = await server.nextMessage;
  return JSON.parse(message as string);
}

// ============================================================================
// API Test Helpers
// ============================================================================

/**
 * Wait for element to be removed from the document
 */
export async function waitForElementToBeRemoved(
  queryFn: () => HTMLElement | null,
  { timeout = 3000 }: { timeout?: number } = {}
): Promise<void> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (!queryFn()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }

  throw new Error('Element was not removed within timeout');
}

/**
 * Create mock fetch response
 */
export function createMockFetchResponse<T = unknown>(
  data: T,
  status: number = 200
): Promise<Response> {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
    headers: new Headers({
      'Content-Type': 'application/json',
    }),
  } as Response);
}

// ============================================================================
// Component Test Helpers
// ============================================================================

/**
 * Wait for async updates to complete
 */
export async function flushPromises(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

/**
 * Simulate user typing in an input field
 */
export async function typeInInput(
  element: HTMLElement,
  text: string,
  userEventInstance: ReturnType<typeof userEvent.setup>
): Promise<void> {
  await userEventInstance.clear(element);
  await userEventInstance.type(element, text);
}

/**
 * Wait for condition to be true
 */
export async function waitFor(
  condition: () => boolean,
  { timeout = 3000, interval = 50 }: { timeout?: number; interval?: number } = {}
): Promise<void> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (condition()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }

  throw new Error('Condition was not met within timeout');
}

// ============================================================================
// Mock Data Generators
// ============================================================================

/**
 * Create mock agent configuration
 */
export function createMockAgent(overrides: Partial<AgentConfig> = {}): AgentConfig {
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
    code_executor: null,
    model_client_stream: false,
    sources: null,
    system_message: null,
    max_consecutive_auto_reply: 20,
    reflect_on_tool_use: true,
    terminate_on_text: false,
    tool_call_loop: true,
    sub_agents: null,
    mode: null,
    orchestrator_prompt: null,
    include_inner_dialog: true,
    ...overrides,
  };
}

/**
 * Create mock tool configuration
 */
export function createMockTool(overrides: Partial<ToolDefinition> = {}): ToolDefinition {
  return {
    name: 'test_tool',
    file: 'test_tool.py',
    description: 'A test tool',
    ...overrides,
  };
}

/**
 * Create mock WebSocket event
 */
export function createMockWSEvent(
  type: string,
  data: Record<string, unknown> = {}
): BaseMessage {
  return {
    type,
    data,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Create mock conversation
 */
export function createMockConversation(
  overrides: Record<string, unknown> = {}
): Record<string, unknown> {
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
 */
export function hasClass(element: HTMLElement, className: string): boolean {
  return element.classList.contains(className);
}

/**
 * Get all elements with specific test ID
 */
export function getAllByTestId(container: HTMLElement, testId: string): Element[] {
  return Array.from(container.querySelectorAll(`[data-testid="${testId}"]`));
}

// ============================================================================
// Cleanup Helpers
// ============================================================================

/**
 * Clean up all timers and async operations
 */
export function cleanupTimers(): void {
  jest.clearAllTimers();
  jest.useRealTimers();
}

/**
 * Reset all mocks
 */
export function resetAllMocks(): void {
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
