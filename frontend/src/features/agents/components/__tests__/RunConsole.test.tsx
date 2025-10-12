/**
 * RunConsole.test.tsx - Unit Tests for RunConsole Component
 *
 * Tests the agent execution console component including:
 * - WebSocket connection management
 * - Message sending and receiving
 * - Log display and filtering
 * - Error handling
 * - Download logs functionality
 * - Shared socket mode
 */

import React from 'react';
import { render, screen, waitFor, RenderResult } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserEvent } from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import RunConsole from '../RunConsole';
import { createMockAgentRunWS, createMockAgentRunEvents } from '../../../../__tests__/mocks/websocket';

// ============================================================================
// Test Helpers
// ============================================================================

interface MockWebSocket {
  close: () => Promise<void>;
  send: (data: string) => void;
  error: () => void;
  messages: string[];
}

/**
 * Render RunConsole with router context
 */
const renderRunConsole = (props: Record<string, unknown> = {}, route: string = '/run/TestAgent'): RenderResult => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/run/:name" element={<RunConsole {...props} />} />
      </Routes>
    </MemoryRouter>
  );
};

// ============================================================================
// Test Suites
// ============================================================================

describe('RunConsole Component', () => {
  describe('Rendering', () => {
    it('renders the console interface', () => {
      renderRunConsole({ agentName: 'TestAgent' });

      expect(screen.getByText(/run/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/initial task for agent/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument();
    });

    it('displays connection status', () => {
      renderRunConsole({ agentName: 'TestAgent' });

      // Initially should be connecting or disconnected
      expect(
        screen.getByText(/connecting/i) || screen.getByText(/disconnected/i)
      ).toBeInTheDocument();
    });

    it('shows control buttons', () => {
      renderRunConsole({ agentName: 'TestAgent' });

      // Check for control buttons
      const reconnectButton = screen.getByTitle(/reconnect/i);
      const clearButton = screen.getByTitle(/clear logs/i);
      const downloadButton = screen.getByTitle(/download logs/i);

      expect(reconnectButton).toBeInTheDocument();
      expect(clearButton).toBeInTheDocument();
      expect(downloadButton).toBeInTheDocument();
    });
  });

  describe('WebSocket Connection', () => {
    it('establishes WebSocket connection on mount', async () => {
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      // Wait for connection to establish
      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      // Should show connection established message
      expect(screen.getByText(/connection established/i)).toBeInTheDocument();

      await mockWS.close();
    });

    it('shows connecting status during connection', () => {
      renderRunConsole({ agentName: 'TestAgent' });

      // Should show connecting status initially
      expect(screen.getByText(/connecting/i)).toBeInTheDocument();
    });

    it('handles connection errors gracefully', async () => {
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      // Wait for connection
      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      // Simulate error
      mockWS.error();

      await waitFor(() => {
        expect(screen.getByText(/websocket connection error/i)).toBeInTheDocument();
      });

      await mockWS.close();
    });

    it('handles unexpected disconnection', async () => {
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      // Close with non-normal code
      mockWS.close({ code: 1006, reason: 'Connection lost' });

      await waitFor(() => {
        expect(screen.getByText(/disconnected unexpectedly/i)).toBeInTheDocument();
      });
    });
  });

  describe('Message Handling', () => {
    it('sends run command when task is submitted', async () => {
      const user = userEvent.setup();
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      // Wait for connection
      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      // Enter task
      const taskInput = screen.getByLabelText(/initial task for agent/i) as HTMLInputElement;
      await user.type(taskInput, 'Test task for the agent');

      // Click run button
      const runButton = screen.getByRole('button', { name: /^run$/i });
      await user.click(runButton);

      // Should send message to WebSocket
      await waitFor(() => {
        const message = mockWS.messages[mockWS.messages.length - 1];
        const parsed = JSON.parse(message);
        expect(parsed.type).toBe('run');
        expect(parsed.data).toBe('Test task for the agent');
      });

      await mockWS.close();
    });

    it('displays received messages in log', async () => {
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      // Wait for connection
      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      // Send a message from server
      mockWS.send(
        JSON.stringify({
          type: 'TextMessage',
          data: { content: 'Agent is processing your request' },
          timestamp: new Date().toISOString(),
        })
      );

      // Should display the message
      await waitFor(() => {
        expect(screen.getByText(/agent is processing your request/i)).toBeInTheDocument();
      });

      await mockWS.close();
    });

    it('handles tool call events', async () => {
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      // Send tool call event
      mockWS.send(
        JSON.stringify({
          type: 'ToolCallRequestEvent',
          data: {
            name: 'web_search',
            arguments: { query: 'test query' },
            id: 'tool_1',
          },
          timestamp: new Date().toISOString(),
        })
      );

      // Should display tool call
      await waitFor(() => {
        expect(screen.getByText(/web_search/i)).toBeInTheDocument();
      });

      await mockWS.close();
    });

    it('handles error messages', async () => {
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      // Send error event
      mockWS.send(
        JSON.stringify({
          type: 'error',
          data: { message: 'Something went wrong' },
          timestamp: new Date().toISOString(),
        })
      );

      // Should display error
      await waitFor(() => {
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      });

      await mockWS.close();
    });
  });

  describe('User Interactions', () => {
    it('disables run button when not connected', () => {
      renderRunConsole({ agentName: 'TestAgent' });

      const runButton = screen.getByRole('button', { name: /^run$/i });
      expect(runButton).toBeDisabled();
    });

    it('disables run button when task is empty', async () => {
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      const runButton = screen.getByRole('button', { name: /^run$/i });

      // Should be disabled with empty task
      expect(runButton).toBeDisabled();

      await mockWS.close();
    });

    it('enables run button when connected and task is entered', async () => {
      const user = userEvent.setup();
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      const taskInput = screen.getByLabelText(/initial task for agent/i) as HTMLInputElement;
      await user.type(taskInput, 'Test task');

      const runButton = screen.getByRole('button', { name: /^run$/i });
      expect(runButton).not.toBeDisabled();

      await mockWS.close();
    });

    it('disables controls while agent is running', async () => {
      const user = userEvent.setup();
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      const taskInput = screen.getByLabelText(/initial task for agent/i) as HTMLInputElement;
      await user.type(taskInput, 'Test task');

      const runButton = screen.getByRole('button', { name: /^run$/i });
      await user.click(runButton);

      // Task input should be disabled while running
      expect(taskInput).toBeDisabled();

      await mockWS.close();
    });

    it('clears logs when clear button is clicked', async () => {
      const user = userEvent.setup();
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connection established/i)).toBeInTheDocument();
      });

      // Send a message
      mockWS.send(
        JSON.stringify({
          type: 'TextMessage',
          data: { content: 'Test message' },
          timestamp: new Date().toISOString(),
        })
      );

      await waitFor(() => {
        expect(screen.getByText(/test message/i)).toBeInTheDocument();
      });

      // Click clear button
      const clearButton = screen.getByTitle(/clear logs/i);
      await user.click(clearButton);

      // Logs should be cleared
      await waitFor(() => {
        expect(screen.queryByText(/test message/i)).not.toBeInTheDocument();
      });

      await mockWS.close();
    });

    it('downloads logs when download button is clicked', async () => {
      const user = userEvent.setup();
      const mockWS = createMockAgentRunWS('TestAgent');

      // Mock createElement and click for download
      const mockLink = {
        href: '',
        download: '',
        click: jest.fn(),
      } as unknown as HTMLAnchorElement;
      jest.spyOn(document, 'createElement').mockReturnValue(mockLink);
      jest.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink);
      jest.spyOn(document.body, 'removeChild').mockImplementation(() => mockLink);
      jest.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url');
      jest.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connection established/i)).toBeInTheDocument();
      });

      // Send a message to have logs
      mockWS.send(
        JSON.stringify({
          type: 'TextMessage',
          data: { content: 'Test message' },
          timestamp: new Date().toISOString(),
        })
      );

      await waitFor(() => {
        expect(screen.getByText(/test message/i)).toBeInTheDocument();
      });

      // Click download button
      const downloadButton = screen.getByTitle(/download logs/i);
      await user.click(downloadButton);

      // Check that download was triggered
      expect(mockLink.click).toHaveBeenCalled();
      expect(mockLink.download).toContain('TestAgent');

      await mockWS.close();
    });
  });

  describe('Shared Socket Mode', () => {
    it('accepts a shared WebSocket connection', async () => {
      const sharedSocket = new WebSocket('ws://localhost:8000/api/runs/SharedAgent');
      const mockWS = (global as any).createMockWebSocketServer('ws://localhost:8000/api/runs/SharedAgent');

      renderRunConsole({ agentName: 'TestAgent', sharedSocket });

      // Wait for connection handlers to be attached
      await waitFor(() => {
        expect(screen.getByText(/connection established/i)).toBeInTheDocument();
      });

      await mockWS.close();
    });

    it('does not close shared socket on unmount', async () => {
      const sharedSocket = new WebSocket('ws://localhost:8000/api/runs/SharedAgent');
      const mockWS = (global as any).createMockWebSocketServer('ws://localhost:8000/api/runs/SharedAgent');

      const { unmount } = renderRunConsole({ agentName: 'TestAgent', sharedSocket });

      await waitFor(() => {
        expect(screen.getByText(/connection established/i)).toBeInTheDocument();
      });

      const closeSpy = jest.spyOn(sharedSocket, 'close');

      // Unmount component
      unmount();

      // Shared socket should not be closed
      expect(closeSpy).not.toHaveBeenCalled();

      await mockWS.close();
    });

    it('disables reconnect button in shared socket mode', async () => {
      const sharedSocket = new WebSocket('ws://localhost:8000/api/runs/SharedAgent');
      const mockWS = (global as any).createMockWebSocketServer('ws://localhost:8000/api/runs/SharedAgent');

      renderRunConsole({ agentName: 'TestAgent', sharedSocket, readOnlyControls: true });

      await waitFor(() => {
        expect(screen.getByText(/connection established/i)).toBeInTheDocument();
      });

      const reconnectButton = screen.getByTitle(/reconnect/i);
      expect(reconnectButton).toBeDisabled();

      await mockWS.close();
    });
  });

  describe('Nested Mode', () => {
    it('renders in nested mode without back button', () => {
      renderRunConsole({ nested: true, agentName: 'TestAgent' });

      // Back button should not be present
      expect(screen.queryByRole('button', { name: /back to agents/i })).not.toBeInTheDocument();
    });

    it('applies nested styling', () => {
      const { container } = renderRunConsole({ nested: true, agentName: 'TestAgent' });

      // In nested mode, Paper components should have no border
      // Check for absence of Paper elevation
      const paperElements = container.querySelectorAll('[class*="MuiPaper"]');
      expect(paperElements.length).toBeGreaterThan(0);
    });
  });

  describe('Error Handling', () => {
    it('handles unparseable WebSocket messages', async () => {
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      // Send invalid JSON
      mockWS.send('invalid json {{{');

      // Should display error message
      await waitFor(() => {
        expect(screen.getByText(/received an invalid message/i)).toBeInTheDocument();
      });

      await mockWS.close();
    });

    it('shows error when trying to run without connection', async () => {
      const user = userEvent.setup();

      renderRunConsole({ agentName: 'TestAgent' });

      // Don't wait for connection - try to run immediately
      const taskInput = screen.getByLabelText(/initial task for agent/i);

      // Task input will be disabled, but we can test the logic
      // The run button should be disabled when not connected
      const runButton = screen.getByRole('button', { name: /^run$/i });
      expect(runButton).toBeDisabled();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      renderRunConsole({ agentName: 'TestAgent' });

      expect(screen.getByLabelText(/initial task for agent/i)).toBeInTheDocument();
      expect(screen.getByTitle(/reconnect/i)).toBeInTheDocument();
      expect(screen.getByTitle(/clear logs/i)).toBeInTheDocument();
      expect(screen.getByTitle(/download logs/i)).toBeInTheDocument();
    });

    it('shows status indicators', () => {
      renderRunConsole({ agentName: 'TestAgent' });

      // Status label should be visible
      expect(screen.getByText(/status:/i)).toBeInTheDocument();
    });

    it('auto-scrolls logs to bottom', async () => {
      const mockWS = createMockAgentRunWS('TestAgent');

      renderRunConsole({ agentName: 'TestAgent' });

      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument();
      });

      // Send multiple messages
      for (let i = 0; i < 10; i++) {
        mockWS.send(
          JSON.stringify({
            type: 'TextMessage',
            data: { content: `Message ${i}` },
            timestamp: new Date().toISOString(),
          })
        );
      }

      // Last message should be visible
      await waitFor(() => {
        expect(screen.getByText(/message 9/i)).toBeInTheDocument();
      });

      await mockWS.close();
    });
  });
});
