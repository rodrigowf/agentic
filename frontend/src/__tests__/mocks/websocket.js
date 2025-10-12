/**
 * websocket.js - WebSocket Mocks
 *
 * Provides mock WebSocket implementations for testing.
 */

import WS from 'jest-websocket-mock';

// ============================================================================
// WebSocket URLs
// ============================================================================

export const WS_URLS = {
  AGENT_RUN: 'ws://localhost:8000/api/runs',
  CLAUDE_CODE: 'ws://localhost:8000/api/runs/ClaudeCode',
  VOICE: 'ws://localhost:8000/api/realtime-voice',
};

// ============================================================================
// Mock WebSocket Events
// ============================================================================

/**
 * Create mock agent run events
 */
export function createMockAgentRunEvents() {
  return [
    {
      type: 'AgentInitEvent',
      data: {
        agent_name: 'TestAgent',
        timestamp: new Date().toISOString(),
      },
    },
    {
      type: 'TextMessage',
      data: {
        content: 'Starting task...',
        source: 'assistant',
      },
    },
    {
      type: 'ToolCallRequestEvent',
      data: {
        name: 'web_search',
        arguments: { query: 'test query' },
        id: 'tool_call_1',
      },
    },
    {
      type: 'ToolCallExecutionEvent',
      data: {
        name: 'web_search',
        result: 'Search results...',
        is_error: false,
        id: 'tool_call_1',
      },
    },
    {
      type: 'TextMessage',
      data: {
        content: 'Task completed.',
        source: 'assistant',
      },
    },
    {
      type: 'TaskResult',
      data: {
        outcome: 'success',
        message: 'Task completed successfully',
      },
    },
  ];
}

/**
 * Create mock Claude Code events
 */
export function createMockClaudeCodeEvents() {
  return [
    {
      type: 'SystemEvent',
      data: {
        message: 'init',
        details: {
          cwd: '/home/rodrigo/agentic',
          model: 'claude-sonnet-4-5-20250929',
        },
      },
    },
    {
      type: 'TextMessage',
      data: {
        content: 'I will help with the code change...',
        source: 'ClaudeCode',
      },
    },
    {
      type: 'ToolCallRequestEvent',
      data: {
        name: 'Read',
        arguments: { file_path: '/test/file.js' },
        id: 'toolu_123',
      },
    },
    {
      type: 'ToolCallExecutionEvent',
      data: {
        name: 'Read',
        result: 'File contents...',
        is_error: false,
        id: 'toolu_123',
      },
    },
    {
      type: 'TaskResult',
      data: {
        outcome: 'success',
        message: 'Code changes completed',
        duration_ms: 5420,
      },
    },
  ];
}

/**
 * Create mock nested agent events
 */
export function createMockNestedAgentEvents() {
  return [
    {
      type: 'AgentInitEvent',
      data: {
        agent_name: 'MainConversation',
        sub_agents: ['Manager', 'Researcher', 'Developer'],
      },
    },
    {
      type: 'TextMessage',
      data: {
        content: 'Manager: Starting task coordination...',
        source: 'Manager',
      },
    },
    {
      type: 'TextMessage',
      data: {
        content: 'Researcher: Gathering information...',
        source: 'Researcher',
      },
    },
    {
      type: 'ToolCallRequestEvent',
      data: {
        name: 'web_search',
        arguments: { query: 'research query' },
        id: 'tool_call_nested_1',
        agent: 'Researcher',
      },
    },
  ];
}

/**
 * Create mock voice events
 */
export function createMockVoiceEvents() {
  return [
    {
      type: 'session.created',
      session: {
        id: 'session_123',
        model: 'gpt-4o-realtime-preview',
      },
    },
    {
      type: 'conversation.item.created',
      item: {
        id: 'item_123',
        type: 'message',
        role: 'user',
        content: [{ type: 'input_text', text: 'Hello' }],
      },
    },
    {
      type: 'response.audio_transcript.delta',
      delta: 'Hello! How can I help you today?',
    },
    {
      type: 'response.done',
      response: {
        id: 'response_123',
        status: 'completed',
      },
    },
  ];
}

// ============================================================================
// WebSocket Mock Helpers
// ============================================================================

/**
 * Create a mock WebSocket server with default behavior
 *
 * @param {string} url - WebSocket URL
 * @param {Array} events - Events to send
 * @returns {WS} Mock WebSocket server
 */
export function createMockWSServer(url, events = []) {
  const server = new WS(url);

  // Send events when client connects
  server.on('connection', socket => {
    events.forEach((event, index) => {
      setTimeout(() => {
        socket.send(JSON.stringify(event));
      }, index * 100); // Stagger events
    });
  });

  return server;
}

/**
 * Create mock agent run WebSocket
 *
 * @param {string} agentName - Agent name
 * @returns {WS} Mock WebSocket server
 */
export function createMockAgentRunWS(agentName) {
  const url = `${WS_URLS.AGENT_RUN}/${agentName}`;
  return createMockWSServer(url, createMockAgentRunEvents());
}

/**
 * Create mock Claude Code WebSocket
 *
 * @returns {WS} Mock WebSocket server
 */
export function createMockClaudeCodeWS() {
  return createMockWSServer(WS_URLS.CLAUDE_CODE, createMockClaudeCodeEvents());
}

/**
 * Create mock voice WebSocket
 *
 * @returns {WS} Mock WebSocket server
 */
export function createMockVoiceWS() {
  return createMockWSServer(WS_URLS.VOICE, createMockVoiceEvents());
}

/**
 * Wait for WebSocket message matching condition
 *
 * @param {WS} server - Mock WebSocket server
 * @param {Function} condition - Condition function
 * @param {number} timeout - Timeout in ms
 * @returns {Promise<Object>} Matching message
 */
export async function waitForWSMessage(server, condition, timeout = 5000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      const message = await server.nextMessage;
      const parsed = JSON.parse(message);

      if (condition(parsed)) {
        return parsed;
      }
    } catch (err) {
      // Continue waiting
    }
  }

  throw new Error('WebSocket message not received within timeout');
}

/**
 * Simulate WebSocket error
 *
 * @param {WS} server - Mock WebSocket server
 * @param {Error} error - Error to emit
 */
export function simulateWSError(server, error = new Error('WebSocket error')) {
  server.error(error);
}

/**
 * Simulate WebSocket close
 *
 * @param {WS} server - Mock WebSocket server
 * @param {number} code - Close code
 * @param {string} reason - Close reason
 */
export function simulateWSClose(server, code = 1000, reason = 'Normal closure') {
  server.close({ code, reason });
}
