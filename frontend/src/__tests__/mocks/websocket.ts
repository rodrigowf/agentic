/**
 * websocket.ts - WebSocket Mocks
 *
 * Provides mock WebSocket implementations for testing.
 */

import WS from 'jest-websocket-mock';
import type { BaseMessage } from '../../types';

// ============================================================================
// WebSocket URLs
// ============================================================================

export const WS_URLS = {
  AGENT_RUN: 'ws://localhost:8000/api/runs',
  CLAUDE_CODE: 'ws://localhost:8000/api/runs/ClaudeCode',
  VOICE: 'ws://localhost:8000/api/realtime-voice',
} as const;

// ============================================================================
// Mock WebSocket Events
// ============================================================================

/**
 * Create mock agent run events
 */
export function createMockAgentRunEvents(): BaseMessage[] {
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
export function createMockClaudeCodeEvents(): BaseMessage[] {
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
export function createMockNestedAgentEvents(): BaseMessage[] {
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
export function createMockVoiceEvents(): Record<string, unknown>[] {
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
 */
export function createMockWSServer(
  url: string,
  events: BaseMessage[] | Record<string, unknown>[] = []
): WS {
  const server = new WS(url);

  // Send events when client connects
  server.on('connection', (socket) => {
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
 */
export function createMockAgentRunWS(agentName: string): WS {
  const url = `${WS_URLS.AGENT_RUN}/${agentName}`;
  return createMockWSServer(url, createMockAgentRunEvents());
}

/**
 * Create mock Claude Code WebSocket
 */
export function createMockClaudeCodeWS(): WS {
  return createMockWSServer(WS_URLS.CLAUDE_CODE, createMockClaudeCodeEvents());
}

/**
 * Create mock voice WebSocket
 */
export function createMockVoiceWS(): WS {
  return createMockWSServer(WS_URLS.VOICE, createMockVoiceEvents());
}

/**
 * Wait for WebSocket message matching condition
 */
export async function waitForWSMessage(
  server: WS,
  condition: (message: unknown) => boolean,
  timeout: number = 5000
): Promise<unknown> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    try {
      const message = await server.nextMessage;
      const parsed = JSON.parse(message as string);

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
 */
export function simulateWSError(server: WS, error: Error = new Error('WebSocket error')): void {
  server.error(error);
}

/**
 * Simulate WebSocket close
 */
export function simulateWSClose(
  server: WS,
  code: number = 1000,
  reason: string = 'Normal closure'
): void {
  server.close({ code, reason, wasClean: code === 1000 });
}
