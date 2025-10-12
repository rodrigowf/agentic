/**
 * voice-workflow.integration.test.ts - Voice Assistant Workflow Integration Tests
 *
 * Tests complete voice assistant workflows including:
 * - Starting and stopping voice sessions
 * - WebSocket connections (nested, claude_code, voice)
 * - Message handling and display
 * - Conversation management
 * - Event streaming and visualization
 */

import { render, screen, fireEvent, waitFor, act, RenderResult } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { rest, RestRequest, ResponseComposition, RestContext } from 'msw';
import { server } from '../mocks/server';
import VoiceAssistant from '../../features/voice/pages/VoiceAssistant';
import VoiceDashboard from '../../features/voice/pages/VoiceDashboard';
import {
  mockConversations,
  mockVoiceMessages,
  mockClaudeCodeMessages,
  mockNestedAgentMessages,
} from '../mocks/data';

const API_URL = 'http://localhost:8000';

// Helper to render with router
const renderWithRouter = (component: React.ReactElement): RenderResult => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

interface MockMediaStream {
  getTracks: () => Array<{ stop: jest.Mock }>;
  getAudioTracks: () => Array<{ enabled: boolean }>;
}

interface MockRTCPeerConnection {
  createDataChannel: jest.Mock;
  createOffer: jest.Mock;
  setLocalDescription: jest.Mock;
  setRemoteDescription: jest.Mock;
  addTrack: jest.Mock;
  close: jest.Mock;
  connectionState: string;
}

interface MockWebSocketServer {
  connected: Promise<void>;
  send: (data: string) => void;
  close: () => Promise<void>;
}

// Mock WebRTC and audio APIs
beforeEach(() => {
  (global as any).RTCPeerConnection = jest.fn().mockImplementation((): MockRTCPeerConnection => ({
    createDataChannel: jest.fn(),
    createOffer: jest.fn().mockResolvedValue({ type: 'offer', sdp: 'mock' }),
    setLocalDescription: jest.fn().mockResolvedValue(undefined),
    setRemoteDescription: jest.fn().mockResolvedValue(undefined),
    addTrack: jest.fn(),
    close: jest.fn(),
    connectionState: 'connected',
  }));

  (global.navigator as any).mediaDevices = {
    getUserMedia: jest.fn().mockResolvedValue({
      getTracks: () => [{ stop: jest.fn() }],
      getAudioTracks: () => [{ enabled: true }],
    } as MockMediaStream),
  };

  (global as any).AudioContext = jest.fn().mockImplementation(() => ({
    createAnalyser: jest.fn(() => ({
      fftSize: 256,
      frequencyBinCount: 128,
      getByteFrequencyData: jest.fn(),
    })),
    createMediaStreamSource: jest.fn(() => ({
      connect: jest.fn(),
    })),
  }));
});

describe('Voice Assistant Workflow Integration Tests', () => {
  // ============================================================================
  // Voice Session Workflow
  // ============================================================================

  describe('Voice Session Workflow', () => {
    test('should start voice session successfully', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;
      const mockClaudeWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/ClaudeCode'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Click start button
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      // Wait for connections
      await mockNestedWS.connected;
      await mockClaudeWS.connected;

      // Verify status
      await waitFor(() => {
        expect(screen.getByText(/session.*active/i)).toBeInTheDocument();
      });
    });

    test('should request microphone permission', async () => {
      renderWithRouter(<VoiceAssistant />);

      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      // Verify getUserMedia was called
      await waitFor(() => {
        expect((global.navigator as any).mediaDevices.getUserMedia).toHaveBeenCalledWith({
          audio: true,
        });
      });
    });

    test('should stop voice session', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;
      const mockClaudeWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/ClaudeCode'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;
      await mockClaudeWS.connected;

      // Stop session
      await waitFor(() => {
        const stopButton = screen.getByRole('button', { name: /stop/i });
        fireEvent.click(stopButton);
      });

      // Verify connections are closed
      await waitFor(() => {
        expect(screen.getByText(/session.*stopped/i)).toBeInTheDocument();
      });
    });

    test('should handle session start errors', async () => {
      // Simulate microphone permission denied
      (global.navigator as any).mediaDevices.getUserMedia = jest
        .fn()
        .mockRejectedValue(new Error('Permission denied'));

      renderWithRouter(<VoiceAssistant />);

      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      // Verify error message
      await waitFor(() => {
        expect(
          screen.getByText(/microphone.*permission.*denied/i)
        ).toBeInTheDocument();
      });
    });

    test('should mute/unmute audio', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;

      // Mute
      await waitFor(() => {
        const muteButton = screen.getByRole('button', { name: /mute/i });
        fireEvent.click(muteButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/muted/i)).toBeInTheDocument();
      });

      // Unmute
      const unmuteButton = screen.getByRole('button', { name: /unmute/i });
      fireEvent.click(unmuteButton);

      await waitFor(() => {
        expect(screen.queryByText(/muted/i)).not.toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Message Handling Workflow
  // ============================================================================

  describe('Message Handling Workflow', () => {
    test('should display voice messages', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;

      // Send voice message
      act(() => {
        mockNestedWS.send(
          JSON.stringify({
            type: 'TextMessage',
            source: 'voice',
            data: { content: 'Hello from voice assistant' },
          })
        );
      });

      // Verify message is displayed
      await waitFor(() => {
        expect(
          screen.getByText(/hello from voice assistant/i)
        ).toBeInTheDocument();
      });
    });

    test('should display Claude Code tool usage', async () => {
      const mockClaudeWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/ClaudeCode'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockClaudeWS.connected;

      // Send Claude Code tool usage
      act(() => {
        mockClaudeWS.send(
          JSON.stringify({
            type: 'ToolCallRequestEvent',
            source: 'claude_code',
            data: {
              type: 'ToolCallRequestEvent',
              data: {
                name: 'Bash',
                arguments: { command: 'ls -la' },
                id: 'tool_123',
              },
            },
          })
        );
      });

      // Verify tool usage is displayed
      await waitFor(() => {
        expect(screen.getByText(/bash/i)).toBeInTheDocument();
        expect(screen.getByText(/ls -la/i)).toBeInTheDocument();
      });
    });

    test('should display nested agent activities', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;

      // Send nested agent message
      act(() => {
        mockNestedWS.send(
          JSON.stringify({
            type: 'TextMessage',
            source: 'nested',
            data: {
              content: 'Researcher: Starting web search...',
              source: 'Researcher',
            },
          })
        );
      });

      // Verify in nested insights panel
      await waitFor(() => {
        expect(screen.getByText(/researcher/i)).toBeInTheDocument();
        expect(screen.getByText(/web search/i)).toBeInTheDocument();
      });
    });

    test('should handle multiple message sources simultaneously', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;
      const mockClaudeWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/ClaudeCode'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;
      await mockClaudeWS.connected;

      // Send messages from different sources
      act(() => {
        mockNestedWS.send(
          JSON.stringify({
            type: 'TextMessage',
            source: 'nested',
            data: { content: 'Nested message' },
          })
        );

        mockClaudeWS.send(
          JSON.stringify({
            type: 'TextMessage',
            source: 'claude_code',
            data: { type: 'TextMessage', data: { content: 'Claude message' } },
          })
        );
      });

      // Verify both messages are displayed
      await waitFor(() => {
        expect(screen.getByText(/nested message/i)).toBeInTheDocument();
        expect(screen.getByText(/claude message/i)).toBeInTheDocument();
      });
    });

    test('should scroll to latest message', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;

      // Send multiple messages
      act(() => {
        for (let i = 0; i < 20; i++) {
          mockNestedWS.send(
            JSON.stringify({
              type: 'TextMessage',
              source: 'nested',
              data: { content: `Message ${i}` },
            })
          );
        }
      });

      // Verify latest message is visible
      await waitFor(() => {
        expect(screen.getByText(/message 19/i)).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Conversation Management Workflow
  // ============================================================================

  describe('Conversation Management Workflow', () => {
    test('should list saved conversations', async () => {
      server.use(
        rest.get(`${API_URL}/api/realtime/conversations`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(200),
            ctx.json({ conversations: mockConversations })
          );
        })
      );

      renderWithRouter(<VoiceDashboard />);

      // Verify conversations are displayed
      await waitFor(() => {
        mockConversations.forEach((conv) => {
          expect(screen.getByText(conv.name)).toBeInTheDocument();
        });
      });
    });

    test('should create new conversation', async () => {
      server.use(
        rest.post(`${API_URL}/api/realtime/conversations`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(201),
            ctx.json({
              id: 'new-conv-id',
              name: 'New Session',
              created_at: new Date().toISOString(),
            })
          );
        })
      );

      renderWithRouter(<VoiceDashboard />);

      // Click create button
      const createButton = await screen.findByRole('button', {
        name: /new.*conversation/i,
      });
      fireEvent.click(createButton);

      // Enter name
      await waitFor(() => {
        const nameInput = screen.getByLabelText(/name/i) as HTMLInputElement;
        fireEvent.change(nameInput, { target: { value: 'New Session' } });
      });

      // Submit
      const submitButton = screen.getByRole('button', { name: /create/i });
      fireEvent.click(submitButton);

      // Verify success
      await waitFor(() => {
        expect(screen.getByText(/new session/i)).toBeInTheDocument();
      });
    });

    test('should view conversation details', async () => {
      server.use(
        rest.get(`${API_URL}/api/realtime/conversations`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(200),
            ctx.json({ conversations: mockConversations })
          );
        }),
        rest.get(
          `${API_URL}/api/realtime/conversations/:conversationId`,
          (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
            return res(
              ctx.status(200),
              ctx.json(mockConversations[0])
            );
          }
        ),
        rest.get(
          `${API_URL}/api/realtime/conversations/:conversationId/events`,
          (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
            return res(
              ctx.status(200),
              ctx.json({ events: mockVoiceMessages })
            );
          }
        )
      );

      renderWithRouter(<VoiceDashboard />);

      // Click on conversation
      await waitFor(() => {
        const convItems = screen.getAllByText(/session/i);
        fireEvent.click(convItems[0]);
      });

      // Verify details are displayed
      await waitFor(() => {
        expect(screen.getByText(/created/i)).toBeInTheDocument();
        expect(screen.getByText(/events/i)).toBeInTheDocument();
      });
    });

    test('should delete conversation', async () => {
      server.use(
        rest.get(`${API_URL}/api/realtime/conversations`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(200),
            ctx.json({ conversations: mockConversations })
          );
        }),
        rest.delete(
          `${API_URL}/api/realtime/conversations/:conversationId`,
          (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
            return res(
              ctx.status(200),
              ctx.json({ message: 'Conversation deleted' })
            );
          }
        )
      );

      renderWithRouter(<VoiceDashboard />);

      // Click delete button
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
        expect(screen.getByText(/deleted/i)).toBeInTheDocument();
      });
    });

    test('should filter conversations by source', async () => {
      server.use(
        rest.get(
          `${API_URL}/api/realtime/conversations/:conversationId/events`,
          (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
            const source = req.url.searchParams.get('source');
            const filteredEvents = mockVoiceMessages.filter(
              (msg) => !source || msg.source === source
            );

            return res(
              ctx.status(200),
              ctx.json({ events: filteredEvents })
            );
          }
        )
      );

      renderWithRouter(<VoiceDashboard />);

      // Select conversation
      await waitFor(() => {
        const convItems = screen.getAllByText(/session/i);
        fireEvent.click(convItems[0]);
      });

      // Apply filter
      await waitFor(() => {
        const filterSelect = screen.getByLabelText(/filter.*source/i) as HTMLSelectElement;
        fireEvent.change(filterSelect, { target: { value: 'claude_code' } });
      });

      // Verify filtered results
      await waitFor(() => {
        // Should only show claude_code events
        const events = screen.queryAllByText(/claude_code/i);
        expect(events.length).toBeGreaterThan(0);
      });
    });
  });

  // ============================================================================
  // Event Visualization Workflow
  // ============================================================================

  describe('Event Visualization Workflow', () => {
    test('should visualize Claude Code tool calls', async () => {
      const mockClaudeWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/ClaudeCode'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockClaudeWS.connected;

      // Send tool call and result
      act(() => {
        mockClaudeWS.send(
          JSON.stringify({
            type: 'ToolCallRequestEvent',
            source: 'claude_code',
            data: {
              type: 'ToolCallRequestEvent',
              data: {
                name: 'Read',
                arguments: { file_path: '/test/file.py' },
                id: 'tool_read_1',
              },
            },
          })
        );

        mockClaudeWS.send(
          JSON.stringify({
            type: 'ToolCallExecutionEvent',
            source: 'claude_code',
            data: {
              type: 'ToolCallExecutionEvent',
              data: {
                name: 'Read',
                result: 'File content here',
                is_error: false,
                id: 'tool_read_1',
              },
            },
          })
        );
      });

      // Verify visualization in ClaudeCodeInsights
      await waitFor(() => {
        expect(screen.getByText(/read/i)).toBeInTheDocument();
        expect(screen.getByText(/file content/i)).toBeInTheDocument();
      });
    });

    test('should show agent activity timeline', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;

      // Send agent activities
      act(() => {
        mockNestedAgentMessages.forEach((msg) => {
          mockNestedWS.send(JSON.stringify(msg));
        });
      });

      // Verify timeline in NestedAgentInsights
      await waitFor(() => {
        expect(screen.getByText(/manager/i)).toBeInTheDocument();
        expect(screen.getByText(/researcher/i)).toBeInTheDocument();
      });
    });

    test('should display tool execution statistics', async () => {
      const mockClaudeWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/ClaudeCode'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockClaudeWS.connected;

      // Send multiple tool calls
      act(() => {
        for (let i = 0; i < 5; i++) {
          mockClaudeWS.send(
            JSON.stringify({
              type: 'ToolCallRequestEvent',
              source: 'claude_code',
              data: {
                type: 'ToolCallRequestEvent',
                data: {
                  name: 'Bash',
                  arguments: { command: `command ${i}` },
                  id: `tool_${i}`,
                },
              },
            })
          );
        }
      });

      // Verify statistics
      await waitFor(() => {
        expect(screen.getByText(/5.*tool.*calls/i)).toBeInTheDocument();
      });
    });

    test('should toggle insights panel visibility', async () => {
      renderWithRouter(<VoiceAssistant />);

      // Find toggle button
      const toggleButton = await screen.findByRole('button', {
        name: /insights/i,
      });

      // Hide panel
      fireEvent.click(toggleButton);

      await waitFor(() => {
        expect(screen.queryByText(/claude code/i)).not.toBeVisible();
      });

      // Show panel
      fireEvent.click(toggleButton);

      await waitFor(() => {
        expect(screen.getByText(/claude code/i)).toBeVisible();
      });
    });
  });

  // ============================================================================
  // Error Handling Workflow
  // ============================================================================

  describe('Error Handling Workflow', () => {
    test('should handle WebSocket connection failures', async () => {
      // Don't create mock server to simulate connection failure
      renderWithRouter(<VoiceAssistant />);

      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      // Verify error message
      await waitFor(
        () => {
          expect(
            screen.getByText(/connection.*failed/i)
          ).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    test('should handle WebSocket disconnections gracefully', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;

      // Simulate disconnect
      act(() => {
        mockNestedWS.close();
      });

      // Verify reconnection attempt or error message
      await waitFor(() => {
        expect(
          screen.getByText(/disconnected|reconnecting/i)
        ).toBeInTheDocument();
      });
    });

    test('should display error messages from backend', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;

      // Send error message
      act(() => {
        mockNestedWS.send(
          JSON.stringify({
            type: 'Error',
            source: 'nested',
            data: { message: 'Agent execution failed' },
          })
        );
      });

      // Verify error is displayed
      await waitFor(() => {
        expect(screen.getByText(/execution failed/i)).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Audio Visualization Workflow
  // ============================================================================

  describe('Audio Visualization Workflow', () => {
    test('should display audio visualizer during session', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;

      // Verify visualizer is present
      await waitFor(() => {
        expect(screen.getByTestId('audio-visualizer')).toBeInTheDocument();
      });
    });

    test('should update visualizer with audio levels', async () => {
      const mockNestedWS = (global as any).createMockWebSocketServer(
        'ws://localhost:8000/api/runs/MainConversation'
      ) as MockWebSocketServer;

      renderWithRouter(<VoiceAssistant />);

      // Start session
      const startButton = await screen.findByRole('button', {
        name: /start.*session/i,
      });
      fireEvent.click(startButton);

      await mockNestedWS.connected;

      // Verify canvas element exists and is being updated
      await waitFor(() => {
        const canvas = screen.getByTestId('audio-visualizer-canvas');
        expect(canvas).toBeInTheDocument();
        expect(canvas.tagName).toBe('CANVAS');
      });
    });
  });
});
