/**
 * agent-workflow.integration.test.ts - Agent Management Workflow Integration Tests
 *
 * Tests complete agent CRUD workflows including:
 * - Creating new agents
 * - Editing agent configurations
 * - Running agents with WebSocket
 * - Deleting agents
 */

import { render, screen, fireEvent, waitFor, RenderResult } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { rest, RestRequest, ResponseComposition, RestContext } from 'msw';
import { server } from '../mocks/server';
import AgentDashboard from '../../features/agents/pages/AgentDashboard';
import { mockAgents, mockAgentConfig } from '../mocks/data';

const API_URL = 'http://localhost:8000';

// Helper to render with router
const renderWithRouter = (component: React.ReactElement): RenderResult => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

interface MockWebSocketServer {
  connected: Promise<void>;
  send: (data: string) => void;
  close: () => Promise<void>;
  server: {
    clients: () => WebSocket[];
  };
}

describe('Agent Workflow Integration Tests', () => {
  // ============================================================================
  // Agent List Workflow
  // ============================================================================

  describe('Agent List Workflow', () => {
    test('should load and display agent list', async () => {
      renderWithRouter(<AgentDashboard />);

      // Wait for agents to load
      await waitFor(() => {
        expect(screen.getByText(/agents/i)).toBeInTheDocument();
      });

      // Verify mock agents are displayed
      await waitFor(() => {
        mockAgents.forEach((agent) => {
          const elements = screen.queryAllByText(new RegExp(agent.name, 'i'));
          expect(elements.length).toBeGreaterThan(0);
        });
      });
    });

    test('should display agent types correctly', async () => {
      renderWithRouter(<AgentDashboard />);

      await waitFor(() => {
        expect(screen.getAllByText(/nested_team/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/looping/i).length).toBeGreaterThan(0);
      });
    });

    // TODO: Implement empty state UI in AgentDashboard - see TEST_STATUS_REPORT.md
    test.skip('should handle empty agent list', async () => {
      server.use(
        rest.get(`${API_URL}/api/agents`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.json({ agents: [] }));
        })
      );

      renderWithRouter(<AgentDashboard />);

      await waitFor(() => {
        const noAgentsMessage = screen.queryByText(/no agents/i);
        expect(noAgentsMessage).toBeInTheDocument();
      });
    });

    test.skip('should handle agent list loading error', async () => {
      server.use(
        rest.get(`${API_URL}/api/agents`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(500), ctx.json({ error: 'Server error' }));
        })
      );

      renderWithRouter(<AgentDashboard />);

      await waitFor(() => {
        const errorMessage = screen.queryByText(/error.*loading.*agents/i);
        expect(errorMessage).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Agent Creation Workflow
  // ============================================================================

  describe('Agent Creation Workflow', () => {
    test.skip('should open create agent form', async () => {
      renderWithRouter(<AgentDashboard />);

      // Click create button
      const createButton = await screen.findByRole('button', {
        name: /create.*agent/i,
      });
      fireEvent.click(createButton);

      // Verify form is displayed
      await waitFor(() => {
        expect(screen.getByLabelText(/agent name/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/agent type/i)).toBeInTheDocument();
      });
    });

    test.skip('should create looping agent successfully', async () => {
      server.use(
        rest.post(`${API_URL}/api/agents`, async (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          const body = await req.json();
          expect(body.name).toBe('NewLoopingAgent');
          expect(body.agent_type).toBe('looping');

          return res(
            ctx.status(200),
            ctx.json({
              message: 'Agent created successfully',
              agent: body,
            })
          );
        })
      );

      renderWithRouter(<AgentDashboard />);

      // Open form
      const createButton = await screen.findByRole('button', {
        name: /create.*agent/i,
      });
      fireEvent.click(createButton);

      // Fill form
      await waitFor(() => {
        const nameInput = screen.getByLabelText(/agent name/i) as HTMLInputElement;
        fireEvent.change(nameInput, { target: { value: 'NewLoopingAgent' } });

        const typeSelect = screen.getByLabelText(/agent type/i) as HTMLSelectElement;
        fireEvent.change(typeSelect, { target: { value: 'looping' } });
      });

      // Submit
      const submitButton = screen.getByRole('button', { name: /create/i });
      fireEvent.click(submitButton);

      // Verify success message
      await waitFor(() => {
        expect(screen.getByText(/created successfully/i)).toBeInTheDocument();
      });
    });

    test.skip('should create nested team agent successfully', async () => {
      server.use(
        rest.post(`${API_URL}/api/agents`, async (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          const body = await req.json();
          expect(body.name).toBe('NewTeamAgent');
          expect(body.agent_type).toBe('nested_team');
          expect(body.sub_agents).toEqual(['Researcher', 'Developer']);

          return res(
            ctx.status(200),
            ctx.json({
              message: 'Agent created successfully',
              agent: body,
            })
          );
        })
      );

      renderWithRouter(<AgentDashboard />);

      // Open form and fill
      const createButton = await screen.findByRole('button', {
        name: /create.*agent/i,
      });
      fireEvent.click(createButton);

      await waitFor(() => {
        fireEvent.change(screen.getByLabelText(/agent name/i), {
          target: { value: 'NewTeamAgent' },
        });
        fireEvent.change(screen.getByLabelText(/agent type/i), {
          target: { value: 'nested_team' },
        });
      });

      // Add sub-agents
      const subAgentInput = screen.getByLabelText(/sub agents/i) as HTMLInputElement;
      fireEvent.change(subAgentInput, {
        target: { value: 'Researcher,Developer' },
      });

      // Submit
      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      await waitFor(() => {
        expect(screen.getByText(/created successfully/i)).toBeInTheDocument();
      });
    });

    test('should validate required fields', async () => {
      renderWithRouter(<AgentDashboard />);

      // Open form
      const createButton = await screen.findByRole('button', {
        name: /create.*agent/i,
      });
      fireEvent.click(createButton);

      // Try to submit without filling required fields
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /create/i });
        fireEvent.click(submitButton);
      });

      // Verify validation errors
      await waitFor(() => {
        expect(screen.getByText(/name.*required/i)).toBeInTheDocument();
      });
    });

    test.skip('should handle creation errors', async () => {
      server.use(
        rest.post(`${API_URL}/api/agents`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(400),
            ctx.json({ error: 'Invalid agent configuration' })
          );
        })
      );

      renderWithRouter(<AgentDashboard />);

      // Fill and submit form
      const createButton = await screen.findByRole('button', {
        name: /create.*agent/i,
      });
      fireEvent.click(createButton);

      await waitFor(() => {
        fireEvent.change(screen.getByLabelText(/agent name/i), {
          target: { value: 'TestAgent' },
        });
        fireEvent.change(screen.getByLabelText(/agent type/i), {
          target: { value: 'looping' },
        });
      });

      fireEvent.click(screen.getByRole('button', { name: /create/i }));

      // Verify error message
      await waitFor(() => {
        expect(screen.getByText(/invalid.*configuration/i)).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Agent Edit Workflow
  // ============================================================================

  describe('Agent Edit Workflow', () => {
    test.skip('should load agent for editing', async () => {
      server.use(
        rest.get(`${API_URL}/api/agents/:agentName`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.json(mockAgentConfig));
        })
      );

      renderWithRouter(<AgentDashboard />);

      // Click edit button
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      // Verify form is populated with agent data
      await waitFor(() => {
        const nameInput = screen.getByLabelText(/agent name/i) as HTMLInputElement;
        expect(nameInput).toHaveValue(mockAgentConfig.name);
      });
    });

    test.skip('should update agent successfully', async () => {
      server.use(
        rest.get(`${API_URL}/api/agents/:agentName`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.json(mockAgentConfig));
        }),
        rest.put(`${API_URL}/api/agents/:agentName`, async (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          const body = await req.json();
          expect(body.description).toBe('Updated description');

          return res(
            ctx.status(200),
            ctx.json({ message: 'Agent updated successfully' })
          );
        })
      );

      renderWithRouter(<AgentDashboard />);

      // Open edit form
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      // Update description
      await waitFor(() => {
        const descInput = screen.getByLabelText(/description/i) as HTMLInputElement;
        fireEvent.change(descInput, {
          target: { value: 'Updated description' },
        });
      });

      // Submit
      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      // Verify success
      await waitFor(() => {
        expect(screen.getByText(/updated successfully/i)).toBeInTheDocument();
      });
    });

    test.skip('should handle edit errors', async () => {
      server.use(
        rest.get(`${API_URL}/api/agents/:agentName`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.json(mockAgentConfig));
        }),
        rest.put(`${API_URL}/api/agents/:agentName`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(400),
            ctx.json({ error: 'Validation error' })
          );
        })
      );

      renderWithRouter(<AgentDashboard />);

      // Open edit and submit
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /save/i });
        fireEvent.click(saveButton);
      });

      // Verify error
      await waitFor(() => {
        expect(screen.getByText(/validation error/i)).toBeInTheDocument();
      });
    });

    test.skip('should cancel edit and discard changes', async () => {
      server.use(
        rest.get(`${API_URL}/api/agents/:agentName`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.json(mockAgentConfig));
        })
      );

      renderWithRouter(<AgentDashboard />);

      // Open edit
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      // Make changes
      await waitFor(() => {
        const nameInput = screen.getByLabelText(/agent name/i) as HTMLInputElement;
        fireEvent.change(nameInput, { target: { value: 'ChangedName' } });
      });

      // Cancel
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      fireEvent.click(cancelButton);

      // Verify form is closed
      await waitFor(() => {
        expect(screen.queryByLabelText(/agent name/i)).not.toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Agent Run Workflow
  // ============================================================================

  describe('Agent Run Workflow', () => {
    test.skip('should open run console for agent', async () => {
      renderWithRouter(<AgentDashboard />);

      // Click run button
      await waitFor(() => {
        const runButtons = screen.getAllByRole('button', { name: /run/i });
        fireEvent.click(runButtons[0]);
      });

      // Verify console is displayed
      await waitFor(() => {
        expect(screen.getByText(/console/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /start/i })).toBeInTheDocument();
      });
    });

    test.skip('should start agent execution', async () => {
      const mockWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/Researcher'
      ) as MockWebSocketServer;

      renderWithRouter(<AgentDashboard />);

      // Open console
      await waitFor(() => {
        const runButtons = screen.getAllByRole('button', { name: /run/i });
        fireEvent.click(runButtons[0]);
      });

      // Start execution
      await waitFor(() => {
        const startButton = screen.getByRole('button', { name: /start/i });
        fireEvent.click(startButton);
      });

      // Wait for WebSocket connection
      await mockWS.connected;

      // Send mock events
      mockWS.send(
        JSON.stringify({
          type: 'TextMessage',
          data: { content: 'Agent started' },
        })
      );

      // Verify message is displayed
      await waitFor(() => {
        expect(screen.getByText(/agent started/i)).toBeInTheDocument();
      });
    });

    test.skip('should stop agent execution', async () => {
      const mockWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/Researcher'
      ) as MockWebSocketServer;

      renderWithRouter(<AgentDashboard />);

      // Start execution
      await waitFor(() => {
        const runButtons = screen.getAllByRole('button', { name: /run/i });
        fireEvent.click(runButtons[0]);
      });

      await waitFor(() => {
        const startButton = screen.getByRole('button', { name: /start/i });
        fireEvent.click(startButton);
      });

      await mockWS.connected;

      // Stop execution
      await waitFor(() => {
        const stopButton = screen.getByRole('button', { name: /stop/i });
        fireEvent.click(stopButton);
      });

      // Verify WebSocket is closed
      await waitFor(() => {
        expect(mockWS.server.clients()[0].readyState).toBe(WebSocket.CLOSED);
      });
    });

    test.skip('should handle WebSocket connection errors', async () => {
      // Simulate connection failure by not creating mock server
      renderWithRouter(<AgentDashboard />);

      await waitFor(() => {
        const runButtons = screen.getAllByRole('button', { name: /run/i });
        fireEvent.click(runButtons[0]);
      });

      await waitFor(() => {
        const startButton = screen.getByRole('button', { name: /start/i });
        fireEvent.click(startButton);
      });

      // Verify error message
      await waitFor(
        () => {
          expect(screen.getByText(/connection.*failed/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  // ============================================================================
  // Agent Delete Workflow
  // ============================================================================

  describe('Agent Delete Workflow', () => {
    test.skip('should open delete confirmation dialog', async () => {
      renderWithRouter(<AgentDashboard />);

      // Click delete button
      await waitFor(() => {
        const deleteButtons = screen.getAllByRole('button', {
          name: /delete/i,
        });
        fireEvent.click(deleteButtons[0]);
      });

      // Verify confirmation dialog
      await waitFor(() => {
        expect(screen.getByText(/confirm.*delete/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
      });
    });

    test.skip('should delete agent successfully', async () => {
      server.use(
        rest.delete(`${API_URL}/api/agents/:agentName`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(200),
            ctx.json({ message: 'Agent deleted successfully' })
          );
        })
      );

      renderWithRouter(<AgentDashboard />);

      // Click delete
      await waitFor(() => {
        const deleteButtons = screen.getAllByRole('button', {
          name: /delete/i,
        });
        fireEvent.click(deleteButtons[0]);
      });

      // Confirm
      await waitFor(() => {
        const confirmButton = screen.getByRole('button', { name: /confirm/i });
        fireEvent.click(confirmButton);
      });

      // Verify success
      await waitFor(() => {
        expect(screen.getByText(/deleted successfully/i)).toBeInTheDocument();
      });
    });

    test.skip('should cancel delete operation', async () => {
      renderWithRouter(<AgentDashboard />);

      // Click delete
      await waitFor(() => {
        const deleteButtons = screen.getAllByRole('button', {
          name: /delete/i,
        });
        fireEvent.click(deleteButtons[0]);
      });

      // Cancel
      await waitFor(() => {
        const cancelButton = screen.getByRole('button', { name: /cancel/i });
        fireEvent.click(cancelButton);
      });

      // Verify dialog is closed
      await waitFor(() => {
        expect(
          screen.queryByText(/confirm.*delete/i)
        ).not.toBeInTheDocument();
      });
    });

    test.skip('should handle delete errors', async () => {
      server.use(
        rest.delete(`${API_URL}/api/agents/:agentName`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(500),
            ctx.json({ error: 'Failed to delete agent' })
          );
        })
      );

      renderWithRouter(<AgentDashboard />);

      // Delete and confirm
      await waitFor(() => {
        const deleteButtons = screen.getAllByRole('button', {
          name: /delete/i,
        });
        fireEvent.click(deleteButtons[0]);
      });

      await waitFor(() => {
        const confirmButton = screen.getByRole('button', { name: /confirm/i });
        fireEvent.click(confirmButton);
      });

      // Verify error
      await waitFor(() => {
        expect(screen.getByText(/failed to delete/i)).toBeInTheDocument();
      });
    });
  });
});
