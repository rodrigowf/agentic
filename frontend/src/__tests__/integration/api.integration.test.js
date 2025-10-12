/**
 * api.integration.test.js - API Client Integration Tests
 *
 * Tests the API client with mocked HTTP requests using MSW.
 * These tests verify the API client correctly formats requests and handles responses.
 */

import { rest } from 'msw';
import { server } from '../mocks/server';
import * as api from '../../api';

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
      const newAgent = {
        name: 'TestAgent',
        agent_type: 'looping',
        tools: ['web_search'],
        llm: {
          provider: 'openai',
          model: 'gpt-4o-mini',
          temperature: 0.0,
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

      const updatedAgent = {
        name: 'Researcher',
        agent_type: 'looping',
        tools: ['web_search', 'fetch_web_content'],
      };

      const response = await api.updateAgent('Researcher', updatedAgent);

      expect(response.status).toBe(200);
      expect(response.data.message).toBe('Agent updated successfully');
    });
  });

  // ============================================================================
  // Tool API Tests
  // ============================================================================

  describe('Tool API', () => {
    test('getTools - should fetch list of tools', async () => {
      const response = await api.getTools();

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('tools');
      expect(Array.isArray(response.data.tools)).toBe(true);
    });

    test('getToolContent - should fetch tool code content', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools/content/:filename`, (req, res, ctx) => {
          return res(
            ctx.status(200),
            ctx.text('def my_tool():\n    return "Hello"')
          );
        })
      );

      const response = await api.getToolContent('my_tool.py');

      expect(response.status).toBe(200);
      expect(typeof response.data).toBe('string');
      expect(response.data).toContain('def my_tool()');
    });

    test('saveToolContent - should save tool code', async () => {
      server.use(
        rest.put(`${API_URL}/api/tools/content/:filename`, (req, res, ctx) => {
          return res(
            ctx.status(200),
            ctx.json({ message: 'Tool saved successfully' })
          );
        })
      );

      const toolCode = 'def new_tool():\n    pass';
      const response = await api.saveToolContent('new_tool.py', toolCode);

      expect(response.status).toBe(200);
      expect(response.data.message).toBe('Tool saved successfully');
    });

    test('uploadTool - should upload tool file', async () => {
      const file = new File(['print("hello")'], 'test_tool.py', {
        type: 'text/x-python',
      });

      const response = await api.uploadTool(file);

      expect(response.status).toBe(200);
      expect(response.data.message).toBe('Tool uploaded successfully');
    });

    test('generateToolCode - should generate tool code from prompt', async () => {
      server.use(
        rest.post(`${API_URL}/api/tools/generate`, (req, res, ctx) => {
          return res(
            ctx.status(200),
            ctx.text('def generated_tool():\n    """Generated by AI"""\n    pass')
          );
        })
      );

      const prompt = 'Create a tool that searches the web';
      const response = await api.generateToolCode(prompt);

      expect(response.status).toBe(200);
      expect(typeof response.data).toBe('string');
      expect(response.data).toContain('def generated_tool()');
    });
  });

  // ============================================================================
  // Voice Conversation API Tests
  // ============================================================================

  describe('Voice Conversation API', () => {
    test('createVoiceConversation - should create new conversation', async () => {
      const conversationData = {
        name: 'Test Session',
        voice_model: 'gpt-4o-realtime-preview',
      };

      const response = await api.createVoiceConversation(conversationData);

      expect(response.status).toBe(201);
      expect(response.data).toHaveProperty('id');
      expect(response.data).toHaveProperty('name');
    });

    test('listVoiceConversations - should fetch conversation list', async () => {
      server.use(
        rest.get(`${API_URL}/api/realtime/conversations`, (req, res, ctx) => {
          return res(
            ctx.status(200),
            ctx.json({
              conversations: [
                {
                  id: 'conv-1',
                  name: 'Session 1',
                  created_at: '2025-01-15T10:00:00Z',
                },
              ],
            })
          );
        })
      );

      const response = await api.listVoiceConversations();

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('conversations');
      expect(Array.isArray(response.data.conversations)).toBe(true);
    });

    test('getVoiceConversation - should fetch specific conversation', async () => {
      server.use(
        rest.get(
          `${API_URL}/api/realtime/conversations/:conversationId`,
          (req, res, ctx) => {
            const { conversationId } = req.params;
            return res(
              ctx.status(200),
              ctx.json({
                id: conversationId,
                name: 'Test Conversation',
                created_at: '2025-01-15T10:00:00Z',
              })
            );
          }
        )
      );

      const response = await api.getVoiceConversation('conv-123');

      expect(response.status).toBe(200);
      expect(response.data.id).toBe('conv-123');
    });

    test('updateVoiceConversation - should update conversation', async () => {
      server.use(
        rest.put(
          `${API_URL}/api/realtime/conversations/:conversationId`,
          (req, res, ctx) => {
            return res(
              ctx.status(200),
              ctx.json({ message: 'Conversation updated successfully' })
            );
          }
        )
      );

      const updateData = { name: 'Updated Session Name' };
      const response = await api.updateVoiceConversation('conv-123', updateData);

      expect(response.status).toBe(200);
      expect(response.data.message).toBe('Conversation updated successfully');
    });

    test('deleteVoiceConversation - should delete conversation', async () => {
      server.use(
        rest.delete(
          `${API_URL}/api/realtime/conversations/:conversationId`,
          (req, res, ctx) => {
            return res(
              ctx.status(200),
              ctx.json({ message: 'Conversation deleted successfully' })
            );
          }
        )
      );

      const response = await api.deleteVoiceConversation('conv-123');

      expect(response.status).toBe(200);
      expect(response.data.message).toBe('Conversation deleted successfully');
    });

    test('appendVoiceConversationEvent - should append event to conversation', async () => {
      server.use(
        rest.post(
          `${API_URL}/api/realtime/conversations/:conversationId/events`,
          (req, res, ctx) => {
            return res(
              ctx.status(201),
              ctx.json({ message: 'Event appended successfully' })
            );
          }
        )
      );

      const eventData = {
        source: 'voice',
        type: 'user_message',
        data: { content: 'Hello' },
      };

      const response = await api.appendVoiceConversationEvent('conv-123', eventData);

      expect(response.status).toBe(201);
    });

    test('getVoiceConversationEvents - should fetch conversation events', async () => {
      server.use(
        rest.get(
          `${API_URL}/api/realtime/conversations/:conversationId/events`,
          (req, res, ctx) => {
            return res(
              ctx.status(200),
              ctx.json({
                events: [
                  {
                    id: 1,
                    timestamp: '2025-01-15T10:00:00Z',
                    source: 'voice',
                    type: 'session.created',
                  },
                ],
              })
            );
          }
        )
      );

      const response = await api.getVoiceConversationEvents('conv-123');

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('events');
      expect(Array.isArray(response.data.events)).toBe(true);
    });

    test('getVoiceConversationEvents - should support query parameters', async () => {
      server.use(
        rest.get(
          `${API_URL}/api/realtime/conversations/:conversationId/events`,
          (req, res, ctx) => {
            const source = req.url.searchParams.get('source');
            expect(source).toBe('claude_code');

            return res(
              ctx.status(200),
              ctx.json({ events: [] })
            );
          }
        )
      );

      await api.getVoiceConversationEvents('conv-123', { source: 'claude_code' });
    });
  });

  // ============================================================================
  // Model Provider API Tests
  // ============================================================================

  describe('Model Provider API', () => {
    test('getModelsByProvider - should fetch OpenAI models', async () => {
      server.use(
        rest.get(`${API_URL}/api/models/:provider`, (req, res, ctx) => {
          const { provider } = req.params;
          const models = {
            openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
            anthropic: ['claude-sonnet-4-5-20250929', 'claude-3-5-sonnet-20240620'],
          };

          return res(
            ctx.status(200),
            ctx.json({ models: models[provider] || [] })
          );
        })
      );

      const response = await api.getModelsByProvider('openai');

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('models');
      expect(Array.isArray(response.data.models)).toBe(true);
      expect(response.data.models).toContain('gpt-4o');
    });

    test('getModelsByProvider - should handle unsupported provider', async () => {
      server.use(
        rest.get(`${API_URL}/api/models/:provider`, (req, res, ctx) => {
          return res(
            ctx.status(400),
            ctx.json({ error: 'Unsupported provider' })
          );
        })
      );

      await expect(api.getModelsByProvider('invalid_provider')).rejects.toThrow();
    });
  });

  // ============================================================================
  // WebSocket Connection Tests
  // ============================================================================

  describe('WebSocket Connections', () => {
    test('runAgent - should create WebSocket connection with correct URL', () => {
      const ws = api.runAgent('Researcher');

      expect(ws).toBeInstanceOf(WebSocket);
      expect(ws.url).toBe('ws://localhost:8000/api/runs/Researcher');
    });

    test('connectVoiceConversationStream - should create WebSocket with conversation ID', () => {
      const ws = api.connectVoiceConversationStream('conv-123');

      expect(ws).toBeInstanceOf(WebSocket);
      expect(ws.url).toContain('/api/realtime/conversations/conv-123/stream');
    });

    test('connectVoiceConversationStream - should include query parameters', () => {
      const ws = api.connectVoiceConversationStream('conv-123', {
        source: 'claude_code',
        limit: 100,
      });

      expect(ws).toBeInstanceOf(WebSocket);
      expect(ws.url).toContain('source=claude_code');
      expect(ws.url).toContain('limit=100');
    });
  });

  // ============================================================================
  // Error Handling Tests
  // ============================================================================

  describe('Error Handling', () => {
    test('should handle 404 errors', async () => {
      server.use(
        rest.get(`${API_URL}/api/agents/:agentName`, (req, res, ctx) => {
          return res(
            ctx.status(404),
            ctx.json({ error: 'Agent not found' })
          );
        })
      );

      try {
        await api.API.get('/agents/NonExistentAgent');
        fail('Should have thrown error');
      } catch (error) {
        expect(error.response.status).toBe(404);
        expect(error.response.data.error).toBe('Agent not found');
      }
    });

    test('should handle 500 server errors', async () => {
      server.use(
        rest.get(`${API_URL}/api/agents`, (req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({ error: 'Internal server error' })
          );
        })
      );

      try {
        await api.getAgents();
        fail('Should have thrown error');
      } catch (error) {
        expect(error.response.status).toBe(500);
      }
    });

    test('should handle network errors', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools`, (req, res) => {
          return res.networkError('Network connection failed');
        })
      );

      await expect(api.getTools()).rejects.toThrow();
    });
  });

  // ============================================================================
  // Request Headers and Configuration Tests
  // ============================================================================

  describe('Request Configuration', () => {
    test('should include withCredentials in axios instance', () => {
      expect(api.API.defaults.withCredentials).toBe(true);
    });

    test('should use correct base URL', () => {
      expect(api.API.defaults.baseURL).toBe('http://localhost:8000/api');
    });

    test('should send correct Content-Type for tool upload', async () => {
      server.use(
        rest.post(`${API_URL}/api/tools/upload`, async (req, res, ctx) => {
          const contentType = req.headers.get('content-type');
          expect(contentType).toContain('multipart/form-data');

          return res(
            ctx.status(200),
            ctx.json({ message: 'Tool uploaded successfully' })
          );
        })
      );

      const file = new File(['print("test")'], 'test.py', { type: 'text/x-python' });
      await api.uploadTool(file);
    });

    test('should send correct Content-Type for tool code save', async () => {
      server.use(
        rest.put(`${API_URL}/api/tools/content/:filename`, async (req, res, ctx) => {
          const contentType = req.headers.get('content-type');
          expect(contentType).toBe('text/plain');

          return res(
            ctx.status(200),
            ctx.json({ message: 'Tool saved' })
          );
        })
      );

      await api.saveToolContent('test.py', 'print("hello")');
    });
  });
});
