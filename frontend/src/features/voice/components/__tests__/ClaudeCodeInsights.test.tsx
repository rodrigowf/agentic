/**
 * ClaudeCodeInsights.test.tsx - Unit Tests for ClaudeCodeInsights Component
 *
 * Tests the Claude Code event visualization component including:
 * - Event rendering and formatting
 * - Tool call display
 * - Tool result display
 * - Message extraction and parsing
 * - Accordion expansion
 * - Auto-scrolling
 */

import React from 'react';
import { render, screen, waitFor, within, RenderResult } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserEvent } from '@testing-library/user-event';
import ClaudeCodeInsights from '../ClaudeCodeInsights';
import { mockClaudeCodeMessages } from '../../../../__tests__/mocks/data';

// ============================================================================
// Test Helpers
// ============================================================================

interface ClaudeCodeMessage {
  id: number;
  timestamp: string;
  source: string;
  type: string;
  data: Record<string, any>;
}

/**
 * Format timestamp helper for tests
 */
const formatTimestamp = (timestamp: string): string => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString();
};

/**
 * Truncate text helper for tests
 */
const truncateText = (text: string, maxLength: number): string => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

/**
 * Safe stringify helper for tests
 */
const safeStringify = (obj: any): string => {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (e) {
    return String(obj);
  }
};

// ============================================================================
// Test Suites
// ============================================================================

describe('ClaudeCodeInsights Component', () => {
  describe('Rendering', () => {
    it('renders empty state when no messages', () => {
      render(
        <ClaudeCodeInsights
          messages={[]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/no claude code activity yet/i)).toBeInTheDocument();
    });

    it('renders messages when provided', () => {
      render(
        <ClaudeCodeInsights
          messages={mockClaudeCodeMessages}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Should show message cards
      expect(screen.getAllByRole('region')).toHaveLength(mockClaudeCodeMessages.length);
    });

    it('filters out non-claude_code messages', () => {
      const mixedMessages: ClaudeCodeMessage[] = [
        ...mockClaudeCodeMessages,
        {
          id: 99,
          timestamp: '2025-01-15T10:33:00Z',
          source: 'voice',
          type: 'TextMessage',
          data: { content: 'Voice message' },
        },
      ];

      render(
        <ClaudeCodeInsights
          messages={mixedMessages}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Should only show claude_code messages
      expect(screen.queryByText(/voice message/i)).not.toBeInTheDocument();
    });
  });

  describe('System Events', () => {
    it('displays system initialization event', () => {
      const systemEvent: ClaudeCodeMessage = {
        id: 1,
        timestamp: '2025-01-15T10:32:00Z',
        source: 'claude_code',
        type: 'SystemEvent',
        data: {
          type: 'SystemEvent',
          data: {
            message: 'init',
            details: {
              cwd: '/home/rodrigo/agentic',
              model: 'claude-sonnet-4-5-20250929',
            },
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[systemEvent]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/system event/i)).toBeInTheDocument();
      expect(screen.getByText(/init/i)).toBeInTheDocument();
    });

    it('displays system event metadata', async () => {
      const user = userEvent.setup();
      const systemEvent: ClaudeCodeMessage = {
        id: 1,
        timestamp: '2025-01-15T10:32:00Z',
        source: 'claude_code',
        type: 'SystemEvent',
        data: {
          type: 'SystemEvent',
          data: {
            message: 'init',
            details: {
              cwd: '/home/rodrigo/agentic',
              model: 'claude-sonnet-4-5-20250929',
            },
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[systemEvent]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Expand accordion to see metadata
      const expandButton = screen.getByRole('button', { name: /expand/i });
      await user.click(expandButton);

      await waitFor(() => {
        expect(screen.getByText(/model: claude-sonnet-4-5-20250929/i)).toBeInTheDocument();
      });
    });
  });

  describe('Text Messages', () => {
    it('displays assistant text messages', () => {
      const textMessage: ClaudeCodeMessage = {
        id: 2,
        timestamp: '2025-01-15T10:32:05Z',
        source: 'claude_code',
        type: 'TextMessage',
        data: {
          type: 'TextMessage',
          data: {
            content: 'I will help you modify the code...',
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[textMessage]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/assistant message/i)).toBeInTheDocument();
      expect(screen.getByText(/i will help you modify the code/i)).toBeInTheDocument();
    });

    it('truncates long text messages in preview', () => {
      const longContent = 'A'.repeat(500);
      const textMessage: ClaudeCodeMessage = {
        id: 2,
        timestamp: '2025-01-15T10:32:05Z',
        source: 'claude_code',
        type: 'TextMessage',
        data: {
          type: 'TextMessage',
          data: {
            content: longContent,
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[textMessage]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Should show truncated preview
      const preview = screen.getByText(/A+\.\.\.$/);
      expect(preview).toBeInTheDocument();
    });
  });

  describe('Tool Call Requests', () => {
    it('displays tool call request event', () => {
      const toolCallEvent: ClaudeCodeMessage = {
        id: 3,
        timestamp: '2025-01-15T10:32:10Z',
        source: 'claude_code',
        type: 'ToolCallRequestEvent',
        data: {
          type: 'ToolCallRequestEvent',
          data: {
            name: 'Read',
            arguments: {
              file_path: '/home/rodrigo/agentic/backend/main.py',
            },
            id: 'toolu_123',
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[toolCallEvent]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/tool request/i)).toBeInTheDocument();
      expect(screen.getByText(/Read/i)).toBeInTheDocument();
    });

    it('displays Bash command preview', () => {
      const bashEvent: ClaudeCodeMessage = {
        id: 3,
        timestamp: '2025-01-15T10:32:10Z',
        source: 'claude_code',
        type: 'ToolCallRequestEvent',
        data: {
          type: 'ToolCallRequestEvent',
          data: {
            name: 'Bash',
            arguments: {
              command: 'ls -la',
              description: 'List files',
            },
            id: 'toolu_123',
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[bashEvent]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/ls -la/i)).toBeInTheDocument();
    });

    it('displays Read file path preview', () => {
      const readEvent: ClaudeCodeMessage = {
        id: 3,
        timestamp: '2025-01-15T10:32:10Z',
        source: 'claude_code',
        type: 'ToolCallRequestEvent',
        data: {
          type: 'ToolCallRequestEvent',
          data: {
            name: 'Read',
            arguments: {
              file_path: '/path/to/file.py',
            },
            id: 'toolu_123',
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[readEvent]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/\/path\/to\/file\.py/i)).toBeInTheDocument();
    });

    it('displays Edit file path preview', () => {
      const editEvent: ClaudeCodeMessage = {
        id: 3,
        timestamp: '2025-01-15T10:32:10Z',
        source: 'claude_code',
        type: 'ToolCallRequestEvent',
        data: {
          type: 'ToolCallRequestEvent',
          data: {
            name: 'Edit',
            arguments: {
              file_path: '/path/to/file.py',
              old_string: 'old',
              new_string: 'new',
            },
            id: 'toolu_123',
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[editEvent]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/\/path\/to\/file\.py/i)).toBeInTheDocument();
    });
  });

  describe('Tool Call Execution', () => {
    it('displays successful tool execution', () => {
      const executionEvent: ClaudeCodeMessage = {
        id: 4,
        timestamp: '2025-01-15T10:32:15Z',
        source: 'claude_code',
        type: 'ToolCallExecutionEvent',
        data: {
          type: 'ToolCallExecutionEvent',
          data: {
            name: 'Read',
            result: 'import fastapi\nfrom fastapi import FastAPI',
            is_error: false,
            id: 'toolu_123',
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[executionEvent]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/tool result/i)).toBeInTheDocument();
      expect(screen.getByText(/success/i)).toBeInTheDocument();
    });

    it('displays error tool execution', () => {
      const errorEvent: ClaudeCodeMessage = {
        id: 4,
        timestamp: '2025-01-15T10:32:15Z',
        source: 'claude_code',
        type: 'ToolCallExecutionEvent',
        data: {
          type: 'ToolCallExecutionEvent',
          data: {
            name: 'Read',
            result: 'File not found',
            is_error: true,
            id: 'toolu_123',
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[errorEvent]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/tool result/i)).toBeInTheDocument();
      expect(screen.getByText(/error/i)).toBeInTheDocument();
      expect(screen.getByText(/file not found/i)).toBeInTheDocument();
    });

    it('shows line count for multi-line results', () => {
      const multilineResult = Array(20).fill('Line of code').join('\n');
      const executionEvent: ClaudeCodeMessage = {
        id: 4,
        timestamp: '2025-01-15T10:32:15Z',
        source: 'claude_code',
        type: 'ToolCallExecutionEvent',
        data: {
          type: 'ToolCallExecutionEvent',
          data: {
            name: 'Read',
            result: multilineResult,
            is_error: false,
            id: 'toolu_123',
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[executionEvent]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/20.*lines/i)).toBeInTheDocument();
    });
  });

  describe('Task Result', () => {
    it('displays successful task completion', () => {
      const taskResult: ClaudeCodeMessage = {
        id: 5,
        timestamp: '2025-01-15T10:32:20Z',
        source: 'claude_code',
        type: 'TaskResult',
        data: {
          type: 'TaskResult',
          data: {
            outcome: 'success',
            message: 'Code changes completed',
            duration_ms: 5420,
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[taskResult]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/task completed/i)).toBeInTheDocument();
      expect(screen.getByText(/success/i)).toBeInTheDocument();
      expect(screen.getByText(/5420 ms/i)).toBeInTheDocument();
    });

    it('displays task failure', () => {
      const taskResult: ClaudeCodeMessage = {
        id: 5,
        timestamp: '2025-01-15T10:32:20Z',
        source: 'claude_code',
        type: 'TaskResult',
        data: {
          type: 'TaskResult',
          data: {
            outcome: 'error',
            message: 'Task failed',
            duration_ms: 1000,
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[taskResult]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      expect(screen.getByText(/task completed/i)).toBeInTheDocument();
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });

    it('displays token usage if present', async () => {
      const user = userEvent.setup();
      const taskResult: ClaudeCodeMessage = {
        id: 5,
        timestamp: '2025-01-15T10:32:20Z',
        source: 'claude_code',
        type: 'TaskResult',
        data: {
          type: 'TaskResult',
          data: {
            outcome: 'success',
            message: 'Code changes completed',
            usage: {
              input_tokens: 1500,
              output_tokens: 500,
            },
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[taskResult]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Expand to see token usage
      const expandButton = screen.getByRole('button', { name: /expand/i });
      await user.click(expandButton);

      await waitFor(() => {
        expect(screen.getByText(/input tokens: 1500/i)).toBeInTheDocument();
        expect(screen.getByText(/output tokens: 500/i)).toBeInTheDocument();
      });
    });
  });

  describe('Accordion Interaction', () => {
    it('expands accordion on click', async () => {
      const user = userEvent.setup();

      render(
        <ClaudeCodeInsights
          messages={mockClaudeCodeMessages}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      const expandButtons = screen.getAllByRole('button', { name: /expand/i });
      await user.click(expandButtons[0]);

      // Should show raw event details
      await waitFor(() => {
        expect(screen.getByText(/"type":/i)).toBeInTheDocument();
      });
    });

    it('shows raw event data in expanded state', async () => {
      const user = userEvent.setup();

      render(
        <ClaudeCodeInsights
          messages={mockClaudeCodeMessages.slice(0, 1)}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      const expandButton = screen.getByRole('button', { name: /expand/i });
      await user.click(expandButton);

      // Should show JSON raw data
      await waitFor(() => {
        const rawDataElement = screen.getByText(/"message": "init"/i);
        expect(rawDataElement).toBeInTheDocument();
      });
    });
  });

  describe('Scrolling Behavior', () => {
    it('auto-scrolls to bottom when new messages arrive', async () => {
      const { rerender } = render(
        <ClaudeCodeInsights
          messages={mockClaudeCodeMessages.slice(0, 2)}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Add new message
      rerender(
        <ClaudeCodeInsights
          messages={mockClaudeCodeMessages}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Last message should be visible (auto-scroll)
      await waitFor(() => {
        expect(screen.getByText(/task completed/i)).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles messages with missing data fields', () => {
      const incompleteMessage: ClaudeCodeMessage = {
        id: 1,
        timestamp: '2025-01-15T10:32:00Z',
        source: 'claude_code',
        type: 'UnknownEvent',
        data: {},
      };

      render(
        <ClaudeCodeInsights
          messages={[incompleteMessage]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Should still render without crashing
      expect(screen.getByText(/UnknownEvent/i)).toBeInTheDocument();
    });

    it('handles messages with deeply nested data', () => {
      const nestedMessage: ClaudeCodeMessage = {
        id: 1,
        timestamp: '2025-01-15T10:32:00Z',
        source: 'claude_code',
        type: 'TextMessage',
        data: {
          type: 'TextMessage',
          data: {
            data: {
              content: 'Deeply nested content',
            },
          },
        },
      };

      render(
        <ClaudeCodeInsights
          messages={[nestedMessage]}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Should handle nested structure gracefully
      expect(screen.getByText(/assistant message/i)).toBeInTheDocument();
    });

    it('limits displayed messages to MAX_CODE_HIGHLIGHTS', () => {
      // Create 30 messages (more than MAX_CODE_HIGHLIGHTS = 25)
      const manyMessages: ClaudeCodeMessage[] = Array(30)
        .fill(null)
        .map((_, i) => ({
          id: i,
          timestamp: new Date().toISOString(),
          source: 'claude_code',
          type: 'TextMessage',
          data: {
            type: 'TextMessage',
            data: {
              content: `Message ${i}`,
            },
          },
        }));

      render(
        <ClaudeCodeInsights
          messages={manyMessages}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Should only show last 25 messages
      expect(screen.getAllByRole('region')).toHaveLength(25);

      // First messages should not be visible
      expect(screen.queryByText(/message 0/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/message 4/i)).not.toBeInTheDocument();

      // Last messages should be visible
      expect(screen.getByText(/message 29/i)).toBeInTheDocument();
      expect(screen.getByText(/message 25/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('uses proper ARIA roles', () => {
      render(
        <ClaudeCodeInsights
          messages={mockClaudeCodeMessages}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      // Accordions should have proper region role
      const regions = screen.getAllByRole('region');
      expect(regions.length).toBeGreaterThan(0);
    });

    it('provides expand/collapse buttons', () => {
      render(
        <ClaudeCodeInsights
          messages={mockClaudeCodeMessages}
          formatTimestamp={formatTimestamp}
          truncateText={truncateText}
          safeStringify={safeStringify}
        />
      );

      const expandButtons = screen.getAllByRole('button', { name: /expand/i });
      expect(expandButtons.length).toBe(mockClaudeCodeMessages.length);
    });
  });
});
