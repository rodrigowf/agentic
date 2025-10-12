/**
 * handlers.ts - Mock Service Worker (MSW) Request Handlers
 *
 * Defines mock API endpoints for testing.
 * These handlers intercept HTTP requests and return mock responses.
 */

import { rest } from 'msw';
import type { AgentConfig, ToolDefinition, VoiceConversation } from '../../types';

const API_URL = 'http://localhost:8000';

// ============================================================================
// Mock Data
// ============================================================================

import {
  mockAgents,
  mockTools,
  mockConversations,
  mockAgentConfig,
  mockModelsByProvider,
} from './data';

// ============================================================================
// Agent Endpoints
// ============================================================================

export const agentHandlers = [
  // List all agents
  rest.get(`${API_URL}/api/agents`, (req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ agents: mockAgents }));
  }),

  // Get specific agent
  rest.get(`${API_URL}/api/agents/:agentName`, (req, res, ctx) => {
    const { agentName } = req.params as { agentName: string };
    const agent = mockAgents.find((a) => a.name === agentName);

    if (!agent) {
      return res(ctx.status(404), ctx.json({ error: 'Agent not found' }));
    }

    return res(ctx.status(200), ctx.json(mockAgentConfig));
  }),

  // Create/Update agent
  rest.post<AgentConfig>(`${API_URL}/api/agents`, async (req, res, ctx) => {
    const body = await req.json();

    return res(
      ctx.status(200),
      ctx.json({
        message: 'Agent created successfully',
        agent: body,
      })
    );
  }),

  // Delete agent
  rest.delete(`${API_URL}/api/agents/:agentName`, (req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ message: 'Agent deleted successfully' }));
  }),
];

// ============================================================================
// Model Endpoints
// ============================================================================

export const modelHandlers = [
  // Get models for a provider
  rest.get(`${API_URL}/api/models/:provider`, (req, res, ctx) => {
    const { provider } = req.params as { provider: string };
    const models = mockModelsByProvider[provider] || [];

    return res(ctx.status(200), ctx.json({ models }));
  }),
];

// ============================================================================
// Tool Endpoints
// ============================================================================

export const toolHandlers = [
  // List all tools
  rest.get(`${API_URL}/api/tools`, (req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ tools: mockTools }));
  }),

  // Get specific tool
  rest.get(`${API_URL}/api/tools/:toolName`, (req, res, ctx) => {
    const { toolName } = req.params as { toolName: string };
    const tool = mockTools.find((t) => t.name === toolName);

    if (!tool) {
      return res(ctx.status(404), ctx.json({ error: 'Tool not found' }));
    }

    return res(ctx.status(200), ctx.json(tool));
  }),

  // Upload tool
  rest.post(`${API_URL}/api/tools`, (req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ message: 'Tool uploaded successfully' }));
  }),
];

// ============================================================================
// Voice Conversation Endpoints
// ============================================================================

export const voiceHandlers = [
  // List conversations
  rest.get(`${API_URL}/api/voice-conversations`, (req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ conversations: mockConversations }));
  }),

  // Get conversation
  rest.get(
    `${API_URL}/api/voice-conversations/:conversationId`,
    (req, res, ctx) => {
      const { conversationId } = req.params as { conversationId: string };
      const conversation = mockConversations.find((c) => c.id === conversationId);

      if (!conversation) {
        return res(ctx.status(404), ctx.json({ error: 'Conversation not found' }));
      }

      return res(ctx.status(200), ctx.json(conversation));
    }
  ),

  // Create conversation
  rest.post<{ name?: string }>(
    `${API_URL}/api/voice-conversations`,
    async (req, res, ctx) => {
      const body = await req.json();

      return res(
        ctx.status(201),
        ctx.json({
          id: 'new-conversation-id',
          name: body.name || 'New Conversation',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
      );
    }
  ),

  // Delete conversation
  rest.delete(
    `${API_URL}/api/voice-conversations/:conversationId`,
    (req, res, ctx) => {
      return res(
        ctx.status(200),
        ctx.json({ message: 'Conversation deleted successfully' })
      );
    }
  ),
];

// ============================================================================
// Error Simulation Handlers
// ============================================================================

export const errorHandlers = [
  // Simulate network error
  rest.get(`${API_URL}/api/error/network`, (req, res) => {
    return res.networkError('Network error');
  }),

  // Simulate server error
  rest.get(`${API_URL}/api/error/server`, (req, res, ctx) => {
    return res(ctx.status(500), ctx.json({ error: 'Internal server error' }));
  }),

  // Simulate timeout
  rest.get(`${API_URL}/api/error/timeout`, (req, res, ctx) => {
    return res(
      ctx.delay(30000), // 30 second delay
      ctx.status(408),
      ctx.json({ error: 'Request timeout' })
    );
  }),
];

// ============================================================================
// Combined Handlers
// ============================================================================

export const handlers = [
  ...agentHandlers,
  ...modelHandlers,
  ...toolHandlers,
  ...voiceHandlers,
  ...errorHandlers,
];
