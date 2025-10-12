/**
 * api.integration.test.ts - API Client Integration Tests
 *
 * Tests the API client with mocked HTTP requests using MSW.
 * These tests verify the API client correctly formats requests and handles responses.
 */

import { rest } from 'msw';
import { server } from '../mocks/server';
import * as api from '../../api';
import type { AgentConfig } from '../../types';

const API_URL = 'http://localhost:8000';

describe('API Client Integration Tests', () => {
  // ============================================================================
  // Agent API Tests
  // ============================================================================

  describe('Agent API', () => {
    test('getAgents - should fetch list of agents', async () => {
      const response = await api.getAgents();

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('agents');
      expect(Array.isArray(response.data.agents)).toBe(true);
      expect(response.data.agents.length).toBeGreaterThan(0);
    });

    test('getAgents - should handle network errors', async () => {
      server.use(
        rest.get(`${API_URL}/api/agents`, (req, res) => {
          return res.networkError('Network connection failed');
        })
      );

      await expect(api.getAgents()).rejects.toThrow();
    });

    test('createAgent - should create a new agent', async () => {
      const newAgent: Partial<AgentConfig> = {
        name: 'TestAgent',
        agent_type: 'looping',
        tools: ['web_search'],
        llm: {
          provider: 'openai',
          model: 'gpt-4o-mini',
          temperature: 0.0,
          max_tokens: null,
        },
        prompt: {
          system: 'Test system prompt',
          user: 'Test user prompt',
        },
      };

      const response = await api.createAgent(newAgent);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('message');
      expect(response.data).toHaveProperty('agent');
    });

    test('createAgent - should handle validation errors', async () => {
      server.use(
        rest.post(`${API_URL}/api/agents`, (req, res, ctx) => {
          return res(
            ctx.status(400),
            ctx.json({ error: 'Invalid agent configuration' })
          );
        })
      );

      const invalidAgent = { name: 'Invalid' };

      await expect(api.createAgent(invalidAgent)).rejects.toThrow();
    });

    test('updateAgent - should update existing agent', async () => {
      server.use(
        rest.put(`${API_URL}/api/agents/:name`, (req, res, ctx) => {
          return res(
            ctx.status(200),
            ctx.json({ message: 'Agent updated successfully' })
          );
        })
      );

      const updatedAgent: Partial<AgentConfig> = {
        name: 'Researcher',
        agent_type: 'looping',
        tools: ['web_search', 'fetch_web_content'],
      };

      const response = await api.updateAgent('Researcher', updatedAgent);

      expect(response.status).toBe(200);
      expect(response.data.message).toBe('Agent updated successfully');
    });
  });
});
