/**
 * ClaudeCodeInsights - Claude Code activity display with vcode-inspired styling
 *
 * Features:
 * - Color-coded left borders for different event types
 * - Collapsible sections for tool outputs
 * - Diff visualization for file edits
 * - Animated states for streaming/in-progress
 * - Todo item tracking with state-based styling
 */

import React, { useMemo, useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { Virtuoso } from 'react-virtuoso';
import { Box, Typography, Collapse, alpha, keyframes } from '@mui/material';
import TerminalIcon from '@mui/icons-material/Terminal';
import EditIcon from '@mui/icons-material/Edit';
import DescriptionIcon from '@mui/icons-material/Description';
import SearchIcon from '@mui/icons-material/Search';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import CodeIcon from '@mui/icons-material/Code';
import TaskAltIcon from '@mui/icons-material/TaskAlt';
import PublicIcon from '@mui/icons-material/Public';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';

const MAX_CODE_HIGHLIGHTS = 50;

// Pulse animation for streaming states
const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
`;

// Spin animation for in-progress todo items
const spin = keyframes`
  to { transform: rotate(360deg); }
`;

// Color scheme matching vcode's design (adapted for MUI theming)
const eventColors = {
  info: { border: '#5ea3ff', bg: 'rgba(94, 163, 255, 0.08)' },
  function: { border: '#a78bfa', bg: 'rgba(167, 139, 250, 0.08)' },
  success: { border: '#6cf0c2', bg: 'rgba(108, 240, 194, 0.08)' },
  warning: { border: '#fbbf24', bg: 'rgba(251, 191, 36, 0.08)' },
  error: { border: '#ff6b6b', bg: 'rgba(255, 107, 107, 0.08)' },
  output: { border: '#9aa1b5', bg: 'rgba(154, 161, 181, 0.08)' },
  task: { border: '#f472b6', bg: 'rgba(244, 114, 182, 0.08)' },
  web: { border: '#60a5fa', bg: 'rgba(96, 165, 250, 0.08)' },
};

// Section component for collapsible tool outputs
const OutputSection = ({ type, title, detail, children, defaultCollapsed = false }) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const colors = eventColors[type] || eventColors.output;

  return (
    <Box
      sx={{
        my: 0.5,
        borderRadius: 1,
        overflow: 'hidden',
        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.03)',
        border: '1px solid',
        borderColor: 'divider',
        borderLeft: '3px solid',
        borderLeftColor: colors.border,
      }}
    >
      <Box
        onClick={() => setCollapsed(!collapsed)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 1.5,
          py: 1,
          bgcolor: colors.bg,
          cursor: 'pointer',
          userSelect: 'none',
          '&:hover': {
            bgcolor: (theme) => alpha(colors.border, 0.12),
          },
        }}
      >
        {collapsed ? (
          <KeyboardArrowRightIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
        ) : (
          <KeyboardArrowDownIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
        )}
        <Typography
          variant="caption"
          sx={{
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'text.secondary',
          }}
        >
          {title}
        </Typography>
        {detail && (
          <Typography
            variant="caption"
            sx={{
              color: 'text.secondary',
              opacity: 0.7,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
            }}
          >
            {detail}
          </Typography>
        )}
      </Box>
      <Collapse in={!collapsed}>
        <Box sx={{ p: 1.5 }}>{children}</Box>
      </Collapse>
    </Box>
  );
};

// Bash command display
const BashSection = ({ command, output, description, isRunning }) => (
  <OutputSection type="info" title="Bash" detail={description || command?.slice(0, 50)} defaultCollapsed={!isRunning}>
    <Box
      sx={{
        mb: 1,
        p: 1,
        borderRadius: 1,
        bgcolor: eventColors.info.bg,
        border: '1px solid',
        borderColor: (theme) => alpha(eventColors.info.border, 0.2),
      }}
    >
      <Typography
        variant="caption"
        sx={{
          display: 'inline-block',
          px: 0.75,
          py: 0.25,
          mb: 0.5,
          borderRadius: 0.5,
          bgcolor: (theme) => alpha(eventColors.info.border, 0.3),
          color: eventColors.info.border,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          fontSize: '0.65rem',
        }}
      >
        IN
      </Typography>
      <Typography
        component="pre"
        sx={{
          fontFamily: '"JetBrains Mono", "Fira Code", monospace',
          fontSize: '0.8rem',
          m: 0,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        $ {command}
      </Typography>
    </Box>
    {(output || isRunning) && (
      <Box
        sx={{
          p: 1,
          borderRadius: 1,
          bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(0, 0, 0, 0.3)' : 'rgba(0, 0, 0, 0.05)',
          border: '1px solid',
          borderColor: 'divider',
          maxHeight: 200,
          overflow: 'auto',
          ...(isRunning && {
            animation: `${pulse} 1.5s ease-in-out infinite`,
          }),
        }}
      >
        <Typography
          variant="caption"
          sx={{
            display: 'inline-block',
            px: 0.75,
            py: 0.25,
            mb: 0.5,
            borderRadius: 0.5,
            bgcolor: 'rgba(154, 161, 181, 0.2)',
            color: 'text.secondary',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            fontSize: '0.65rem',
          }}
        >
          OUT
        </Typography>
        <Typography
          component="pre"
          sx={{
            fontFamily: '"JetBrains Mono", "Fira Code", monospace',
            fontSize: '0.75rem',
            m: 0,
            color: 'text.secondary',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {output || 'Running...'}
        </Typography>
      </Box>
    )}
  </OutputSection>
);

// File edit with diff visualization
const EditSection = ({ filePath, oldString, newString }) => {
  const oldLines = (oldString || '').split('\n');
  const newLines = (newString || '').split('\n');
  const fileName = filePath?.split('/').pop() || 'file';

  return (
    <OutputSection type="success" title="Edit" detail={fileName}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          mb: 1,
          p: 0.75,
          borderRadius: 0.5,
          bgcolor: eventColors.info.bg,
        }}
      >
        <DescriptionIcon sx={{ fontSize: 14, color: eventColors.info.border }} />
        <Typography
          variant="caption"
          sx={{
            fontFamily: 'monospace',
            color: eventColors.info.border,
            fontWeight: 500,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {filePath}
        </Typography>
      </Box>
      <Box
        sx={{
          fontFamily: '"JetBrains Mono", "Fira Code", monospace',
          fontSize: '0.75rem',
          lineHeight: 1.6,
          bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.03)',
          borderRadius: 1,
          p: 1,
          overflow: 'auto',
          maxHeight: 300,
        }}
      >
        {oldLines.map((line, i) => (
          line.trim() && !newLines.includes(line) && (
            <Box
              key={`old-${i}`}
              sx={{
                color: eventColors.error.border,
                bgcolor: 'rgba(255, 107, 107, 0.1)',
                px: 0.5,
                whiteSpace: 'pre',
              }}
            >
              - {line}
            </Box>
          )
        ))}
        {newLines.map((line, i) => (
          line.trim() && (
            !oldLines.includes(line) ? (
              <Box
                key={`new-${i}`}
                sx={{
                  color: eventColors.success.border,
                  bgcolor: 'rgba(108, 240, 194, 0.1)',
                  px: 0.5,
                  whiteSpace: 'pre',
                }}
              >
                + {line}
              </Box>
            ) : (
              <Box
                key={`ctx-${i}`}
                sx={{
                  color: 'text.secondary',
                  px: 0.5,
                  whiteSpace: 'pre',
                }}
              >
                {'  '}{line}
              </Box>
            )
          )
        ))}
      </Box>
    </OutputSection>
  );
};

// Todo list with animated states
const TodoSection = ({ todos }) => (
  <OutputSection type="function" title="Todos" detail={`${todos.filter(t => t.status === 'completed').length}/${todos.length} done`}>
    <Box component="ul" sx={{ m: 0, p: 0, listStyle: 'none' }}>
      {todos.map((todo, i) => (
        <Box
          key={i}
          component="li"
          sx={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 1.25,
            py: 0.75,
            borderBottom: '1px solid',
            borderColor: 'divider',
            '&:last-child': { borderBottom: 'none' },
          }}
        >
          {/* Checkbox with state-based styling */}
          <Box
            sx={{
              width: 16,
              height: 16,
              borderRadius: 0.5,
              border: '2px solid',
              borderColor: todo.status === 'completed'
                ? eventColors.success.border
                : todo.status === 'in_progress'
                  ? eventColors.info.border
                  : 'text.secondary',
              bgcolor: todo.status === 'completed'
                ? eventColors.success.border
                : todo.status === 'in_progress'
                  ? eventColors.info.bg
                  : 'transparent',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              mt: 0.25,
              ...(todo.status === 'in_progress' && {
                animation: `${pulse} 1.5s ease-in-out infinite`,
              }),
            }}
          >
            {todo.status === 'completed' && (
              <Typography
                sx={{
                  fontSize: 10,
                  fontWeight: 'bold',
                  color: (theme) => theme.palette.mode === 'dark' ? '#0a0b10' : '#fff',
                }}
              >
                ✓
              </Typography>
            )}
            {todo.status === 'in_progress' && (
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  border: '2px solid',
                  borderColor: eventColors.info.border,
                  borderTopColor: 'transparent',
                  borderRadius: '50%',
                  animation: `${spin} 0.8s linear infinite`,
                }}
              />
            )}
          </Box>
          <Typography
            variant="body2"
            sx={{
              color: todo.status === 'completed' ? 'text.secondary' : 'text.primary',
              textDecoration: todo.status === 'completed' ? 'line-through' : 'none',
            }}
          >
            {todo.content || todo.activeForm}
          </Typography>
        </Box>
      ))}
    </Box>
  </OutputSection>
);

// Simple message line with type-based styling
const CodexLine = ({ type, children, streaming = false, expandable = false, fullText = null }) => {
  const [expanded, setExpanded] = useState(false);
  const colors = eventColors[type] || eventColors.output;

  return (
    <Box
      onClick={expandable ? () => setExpanded(!expanded) : undefined}
      sx={{
        p: 1,
        borderRadius: 1,
        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.02)',
        border: '1px solid',
        borderColor: 'divider',
        borderLeft: '3px solid',
        borderLeftColor: colors.border,
        fontFamily: '"JetBrains Mono", "Fira Code", monospace',
        fontSize: '0.8rem',
        lineHeight: 1.5,
        wordBreak: 'break-word',
        whiteSpace: 'pre-wrap',
        cursor: expandable ? 'pointer' : 'default',
        ...(streaming && {
          borderStyle: 'dashed',
          animation: `${pulse} 1.5s ease-in-out infinite`,
        }),
        ...(expandable && {
          '&:hover': {
            bgcolor: (theme) => theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.04)',
          },
        }),
      }}
    >
      {expandable && fullText ? (expanded ? fullText : children) : children}
      {expandable && (
        <Typography
          component="span"
          sx={{ fontSize: 10, opacity: 0.5, ml: 0.5 }}
        >
          {expanded ? ' ▼' : ' ▶'}
        </Typography>
      )}
    </Box>
  );
};

// Get icon for event type
const getEventIcon = (iconType) => {
  const iconSx = { fontSize: 16, mr: 0.5 };
  switch (iconType) {
    case 'terminal': return <TerminalIcon sx={{ ...iconSx, color: eventColors.info.border }} />;
    case 'edit': return <EditIcon sx={{ ...iconSx, color: eventColors.success.border }} />;
    case 'file': return <DescriptionIcon sx={{ ...iconSx, color: eventColors.info.border }} />;
    case 'search': return <SearchIcon sx={{ ...iconSx, color: eventColors.warning.border }} />;
    case 'success': return <CheckCircleIcon sx={{ ...iconSx, color: eventColors.success.border }} />;
    case 'error': return <ErrorIcon sx={{ ...iconSx, color: eventColors.error.border }} />;
    case 'task': return <TaskAltIcon sx={{ ...iconSx, color: eventColors.task.border }} />;
    case 'web': return <PublicIcon sx={{ ...iconSx, color: eventColors.web.border }} />;
    default: return <CodeIcon sx={{ ...iconSx, color: eventColors.info.border }} />;
  }
};

const ClaudeCodeInsights = ({
  messages = [],
  formatTimestamp,
  truncateText,
  safeStringify,
}) => {
  const codeHighlights = useMemo(() => {
    if (!messages || messages.length === 0) return [];
    const entries = [];

    messages.forEach((msg, index) => {
      if ((msg?.source || '').toLowerCase() !== 'claude_code') return;

      const rawData = msg?.data || msg?.payload || msg;
      const eventType = rawData?.event_type || rawData?.type || 'event';
      const typeLower = eventType.toLowerCase();
      const nestedData = rawData?.data || {};

      let entry = {
        key: msg.id ?? `${msg.timestamp || 'code'}-${index}`,
        timestamp: msg.timestamp,
        timeLabel: formatTimestamp(msg.timestamp),
        raw: rawData,
      };

      switch (typeLower) {
        case 'textmessage':
        case 'text_message': {
          const content = nestedData.content || rawData.message || '';
          const lines = content.split('\n');
          const preview = lines.length > 3
            ? lines.slice(0, 3).join('\n') + '...'
            : content.substring(0, 300);
          entry = {
            ...entry,
            type: 'message',
            tone: 'info',
            icon: 'code',
            content: preview,
            fullContent: content,
          };
          break;
        }

        case 'toolcallrequestevent':
        case 'tool_call_request_event': {
          const toolName = nestedData.name || 'unknown';
          const args = nestedData.arguments || {};

          if (toolName === 'Bash') {
            entry = {
              ...entry,
              type: 'bash',
              command: args.command,
              description: args.description,
              isRunning: true,
            };
          } else if (toolName === 'Edit') {
            entry = {
              ...entry,
              type: 'edit',
              filePath: args.file_path,
              oldString: args.old_string,
              newString: args.new_string,
            };
          } else if (toolName === 'Read' || toolName === 'Write') {
            entry = {
              ...entry,
              type: 'file',
              tone: 'info',
              icon: 'file',
              content: `${toolName}: ${args.file_path}`,
              filePath: args.file_path,
            };
          } else if (toolName === 'Glob' || toolName === 'Grep') {
            entry = {
              ...entry,
              type: 'search',
              tone: 'warning',
              icon: 'search',
              content: `${toolName}: ${args.pattern}`,
              pattern: args.pattern,
              path: args.path,
            };
          } else if (toolName === 'TodoWrite') {
            entry = {
              ...entry,
              type: 'todo',
              todos: args.todos || [],
            };
          } else if (toolName === 'Task') {
            entry = {
              ...entry,
              type: 'task',
              tone: 'task',
              icon: 'task',
              content: `Task: ${args.description || args.prompt?.slice(0, 100)}`,
            };
          } else if (toolName === 'WebFetch' || toolName === 'WebSearch') {
            entry = {
              ...entry,
              type: 'web',
              tone: 'web',
              icon: 'web',
              content: `${toolName}: ${args.url || args.query}`,
            };
          } else {
            entry = {
              ...entry,
              type: 'tool',
              tone: 'function',
              icon: 'code',
              toolName,
              content: `${toolName}: ${truncateText(safeStringify(args), 100)}`,
            };
          }
          break;
        }

        case 'toolcallexecutionevent':
        case 'tool_call_execution_event': {
          const result = nestedData.result || '';
          const hasError = nestedData.is_error === true;

          if (hasError) {
            entry = {
              ...entry,
              type: 'result',
              tone: 'error',
              icon: 'error',
              content: `Error: ${truncateText(String(result), 200)}`,
              fullContent: String(result),
            };
          } else {
            const resultStr = String(result);
            const lines = resultStr.split('\n').filter(l => l.trim());
            const preview = lines.length > 5
              ? lines.slice(0, 5).join('\n') + `\n... (${lines.length - 5} more lines)`
              : resultStr.substring(0, 300);
            entry = {
              ...entry,
              type: 'result',
              tone: 'success',
              icon: 'success',
              content: preview,
              fullContent: resultStr,
            };
          }
          break;
        }

        case 'taskresult': {
          const outcome = nestedData.outcome || 'completed';
          entry = {
            ...entry,
            type: 'taskResult',
            tone: outcome === 'error' ? 'error' : 'success',
            icon: outcome === 'error' ? 'error' : 'success',
            content: outcome === 'error' ? 'Task failed' : 'Task completed',
            usage: nestedData.usage,
          };
          break;
        }

        case 'error': {
          entry = {
            ...entry,
            type: 'error',
            tone: 'error',
            icon: 'error',
            content: nestedData.message || rawData.message || 'Unknown error',
          };
          break;
        }

        default: {
          const fallback = nestedData.message || nestedData.content || rawData.message || rawData.summary;
          entry = {
            ...entry,
            type: 'default',
            tone: 'output',
            icon: 'code',
            content: fallback ? truncateText(String(fallback), 150) : 'See raw event',
          };
        }
      }

      entries.push(entry);
    });

    return entries.slice(-MAX_CODE_HIGHLIGHTS);
  }, [messages, formatTimestamp, truncateText, safeStringify]);

  const virtuosoRef = useRef(null);
  const isAtBottomRef = useRef(true);

  const handleAtBottomStateChange = (atBottom) => {
    isAtBottomRef.current = atBottom;
  };

  useEffect(() => {
    if (virtuosoRef.current && codeHighlights.length > 0 && isAtBottomRef.current) {
      virtuosoRef.current.scrollToIndex({
        index: codeHighlights.length - 1,
        align: 'end',
        behavior: 'auto',
      });
    }
  }, [codeHighlights]);

  const renderEntry = (index, entry) => {
    return (
      <Box sx={{ mb: 1 }}>
        {/* Timestamp header */}
        {entry.timeLabel && (
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              mb: 0.5,
              color: 'text.secondary',
              fontSize: '0.7rem',
            }}
          >
            {entry.timeLabel}
          </Typography>
        )}

        {/* Render based on entry type */}
        {entry.type === 'bash' && (
          <BashSection
            command={entry.command}
            output={entry.output}
            description={entry.description}
            isRunning={entry.isRunning}
          />
        )}

        {entry.type === 'edit' && (
          <EditSection
            filePath={entry.filePath}
            oldString={entry.oldString}
            newString={entry.newString}
          />
        )}

        {entry.type === 'todo' && <TodoSection todos={entry.todos} />}

        {['message', 'file', 'search', 'tool', 'result', 'error', 'taskResult', 'task', 'web', 'default'].includes(entry.type) && (
          <CodexLine
            type={entry.tone}
            streaming={entry.streaming}
            expandable={entry.fullContent && entry.fullContent !== entry.content}
            fullText={entry.fullContent}
          >
            <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
              {getEventIcon(entry.icon)}
              <Typography
                component="span"
                sx={{
                  fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                  fontSize: 'inherit',
                }}
              >
                {entry.content}
              </Typography>
            </Box>
          </CodexLine>
        )}
      </Box>
    );
  };

  return (
    <Box sx={{ flexGrow: 1, height: '100%' }}>
      {codeHighlights.length === 0 ? (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No Claude Code activity yet. Send a self-editing task to get started.
          </Typography>
        </Box>
      ) : (
        <Virtuoso
          ref={virtuosoRef}
          style={{ height: '100%' }}
          data={codeHighlights}
          itemContent={renderEntry}
          atBottomStateChange={handleAtBottomStateChange}
          followOutput={(isAtBottom) => (isAtBottom ? 'smooth' : false)}
          atBottomThreshold={100}
        />
      )}
    </Box>
  );
};

ClaudeCodeInsights.propTypes = {
  messages: PropTypes.arrayOf(PropTypes.object),
  formatTimestamp: PropTypes.func.isRequired,
  truncateText: PropTypes.func.isRequired,
  safeStringify: PropTypes.func.isRequired,
};

export default ClaudeCodeInsights;
