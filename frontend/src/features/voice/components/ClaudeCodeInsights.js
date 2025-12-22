/**
 * ClaudeCodeInsights - Claude Code activity display
 *
 * Styled to match NestedAgentInsights (Team Insights panel) with:
 * - Accordion-based expandable cards
 * - Color-coded left borders for different event types
 * - Chip-style labels for event types
 * - Token usage displays
 * - Collapsible sections for tool outputs
 * - Diff visualization for file edits
 * - Animated states for streaming/in-progress
 */

import React, { useMemo, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { Virtuoso } from 'react-virtuoso';
import {
  Box,
  Stack,
  Typography,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  alpha,
  keyframes,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TerminalIcon from '@mui/icons-material/Terminal';
import EditIcon from '@mui/icons-material/Edit';
import DescriptionIcon from '@mui/icons-material/Description';
import SearchIcon from '@mui/icons-material/Search';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import CodeIcon from '@mui/icons-material/Code';
import TaskAltIcon from '@mui/icons-material/TaskAlt';
import PublicIcon from '@mui/icons-material/Public';
import BuildIcon from '@mui/icons-material/Build';
import PlaylistAddCheckIcon from '@mui/icons-material/PlaylistAddCheck';
import TokenIcon from '@mui/icons-material/DataUsage';

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

// Map event types to MUI theme colors for consistency with Team Insights
const getEventColor = (type) => {
  switch (type) {
    case 'bash':
    case 'terminal':
    case 'info':
      return 'info';
    case 'edit':
    case 'success':
    case 'result':
      return 'success';
    case 'search':
    case 'tool':
    case 'function':
    case 'warning':
      return 'warning';
    case 'error':
      return 'error';
    case 'task':
    case 'todo':
      return 'secondary';
    case 'web':
      return 'primary';
    default:
      return 'default';
  }
};

// Get icon for event type
const getEventIcon = (iconType, color) => {
  const iconSx = { fontSize: 18 };
  const colorProp = color && color !== 'default' ? `${color}.main` : 'text.secondary';

  switch (iconType) {
    case 'terminal':
    case 'bash':
      return <TerminalIcon sx={{ ...iconSx, color: colorProp }} />;
    case 'edit':
      return <EditIcon sx={{ ...iconSx, color: colorProp }} />;
    case 'file':
      return <DescriptionIcon sx={{ ...iconSx, color: colorProp }} />;
    case 'search':
      return <SearchIcon sx={{ ...iconSx, color: colorProp }} />;
    case 'success':
      return <CheckCircleIcon sx={{ ...iconSx, color: colorProp }} />;
    case 'error':
      return <ErrorIcon sx={{ ...iconSx, color: colorProp }} />;
    case 'task':
      return <TaskAltIcon sx={{ ...iconSx, color: colorProp }} />;
    case 'todo':
      return <PlaylistAddCheckIcon sx={{ ...iconSx, color: colorProp }} />;
    case 'web':
      return <PublicIcon sx={{ ...iconSx, color: colorProp }} />;
    case 'tool':
      return <BuildIcon sx={{ ...iconSx, color: colorProp }} />;
    default:
      return <CodeIcon sx={{ ...iconSx, color: colorProp }} />;
  }
};

// Diff visualization component
const DiffView = ({ oldString, newString }) => {
  const oldLines = (oldString || '').split('\n');
  const newLines = (newString || '').split('\n');

  return (
    <Box
      sx={{
        fontFamily: '"JetBrains Mono", "Fira Code", monospace',
        fontSize: '0.75rem',
        lineHeight: 1.6,
        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
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
              color: 'error.main',
              bgcolor: (theme) => alpha(theme.palette.error.main, 0.1),
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
                color: 'success.main',
                bgcolor: (theme) => alpha(theme.palette.success.main, 0.1),
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
  );
};

// Todo list component
const TodoList = ({ todos }) => (
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
              ? 'success.main'
              : todo.status === 'in_progress'
                ? 'info.main'
                : 'text.secondary',
            bgcolor: todo.status === 'completed'
              ? 'success.main'
              : todo.status === 'in_progress'
                ? (theme) => alpha(theme.palette.info.main, 0.2)
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
                borderColor: 'info.main',
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
);

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
        isStreaming: false,
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
            typeLabel: 'Message',
            tone: 'info',
            icon: 'code',
            preview,
            detail: content,
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
              typeLabel: 'Bash',
              tone: 'info',
              icon: 'terminal',
              toolName: 'Bash',
              command: args.command,
              description: args.description,
              preview: args.description || args.command?.slice(0, 80) || 'Running command...',
              detail: args.command,
              isRunning: true,
            };
          } else if (toolName === 'Edit') {
            const fileName = args.file_path?.split('/').pop() || 'file';
            entry = {
              ...entry,
              type: 'edit',
              typeLabel: 'Edit',
              tone: 'success',
              icon: 'edit',
              toolName: 'Edit',
              filePath: args.file_path,
              oldString: args.old_string,
              newString: args.new_string,
              preview: `Editing ${fileName}`,
              detail: args.file_path,
            };
          } else if (toolName === 'Read' || toolName === 'Write') {
            entry = {
              ...entry,
              type: 'file',
              typeLabel: toolName,
              tone: 'info',
              icon: 'file',
              toolName,
              filePath: args.file_path,
              preview: `${toolName}: ${args.file_path}`,
              detail: args.file_path,
            };
          } else if (toolName === 'Glob' || toolName === 'Grep') {
            entry = {
              ...entry,
              type: 'search',
              typeLabel: toolName,
              tone: 'warning',
              icon: 'search',
              toolName,
              pattern: args.pattern,
              path: args.path,
              preview: `${toolName}: ${args.pattern}`,
              detail: `Pattern: ${args.pattern}${args.path ? `\nPath: ${args.path}` : ''}`,
            };
          } else if (toolName === 'TodoWrite') {
            const todos = args.todos || [];
            const completed = todos.filter(t => t.status === 'completed').length;
            entry = {
              ...entry,
              type: 'todo',
              typeLabel: 'Todos',
              tone: 'secondary',
              icon: 'todo',
              toolName: 'TodoWrite',
              todos,
              preview: `${completed}/${todos.length} tasks completed`,
              detail: todos.map(t => `[${t.status}] ${t.content || t.activeForm}`).join('\n'),
            };
          } else if (toolName === 'Task') {
            entry = {
              ...entry,
              type: 'task',
              typeLabel: 'Task',
              tone: 'secondary',
              icon: 'task',
              toolName: 'Task',
              preview: args.description || args.prompt?.slice(0, 100) || 'Running task...',
              detail: args.prompt,
            };
          } else if (toolName === 'WebFetch' || toolName === 'WebSearch') {
            entry = {
              ...entry,
              type: 'web',
              typeLabel: toolName,
              tone: 'primary',
              icon: 'web',
              toolName,
              preview: `${toolName}: ${args.url || args.query}`,
              detail: args.url || args.query,
            };
          } else {
            entry = {
              ...entry,
              type: 'tool',
              typeLabel: 'Tool Call',
              tone: 'warning',
              icon: 'tool',
              toolName,
              preview: `${toolName}`,
              argsPreview: truncateText(safeStringify(args), 80),
              detail: safeStringify(args),
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
              typeLabel: 'Error',
              tone: 'error',
              icon: 'error',
              preview: truncateText(String(result), 100),
              detail: String(result),
            };
          } else {
            const resultStr = String(result);
            const lines = resultStr.split('\n').filter(l => l.trim());
            const preview = lines.length > 3
              ? lines.slice(0, 3).join('\n') + `\n... (${lines.length - 3} more lines)`
              : resultStr.substring(0, 200);
            entry = {
              ...entry,
              type: 'result',
              typeLabel: 'Result',
              tone: 'success',
              icon: 'success',
              preview,
              detail: resultStr,
            };
          }
          break;
        }

        case 'taskresult': {
          const outcome = nestedData.outcome || 'completed';
          const usage = nestedData.usage;
          entry = {
            ...entry,
            type: 'taskResult',
            typeLabel: 'Task Result',
            tone: outcome === 'error' ? 'error' : 'success',
            icon: outcome === 'error' ? 'error' : 'success',
            preview: outcome === 'error' ? 'Task failed' : 'Task completed',
            detail: nestedData.message || nestedData.summary || '',
            tokenInfo: usage ? {
              prompt: usage.prompt_tokens,
              completion: usage.completion_tokens,
              total: usage.total_tokens ?? (usage.prompt_tokens + usage.completion_tokens),
            } : null,
          };
          break;
        }

        case 'error': {
          entry = {
            ...entry,
            type: 'error',
            typeLabel: 'Error',
            tone: 'error',
            icon: 'error',
            preview: nestedData.message || rawData.message || 'Unknown error',
            detail: nestedData.message || rawData.message || '',
          };
          break;
        }

        default: {
          const fallback = nestedData.message || nestedData.content || rawData.message || rawData.summary;
          entry = {
            ...entry,
            type: 'default',
            typeLabel: eventType,
            tone: 'default',
            icon: 'code',
            preview: fallback ? truncateText(String(fallback), 150) : 'Event received',
            detail: fallback ? String(fallback) : '',
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
    const chipColor = getEventColor(entry.tone);
    const hasToolInfo = entry.toolName || entry.argsPreview;
    const hasTokenInfo = entry.tokenInfo;
    const hasTodos = entry.type === 'todo' && entry.todos?.length > 0;
    const hasEdit = entry.type === 'edit' && (entry.oldString || entry.newString);
    const hasBash = entry.type === 'bash' && entry.command;

    return (
      <Box sx={{ mb: 1.25 }}>
        <Accordion
          disableGutters
          elevation={0}
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderLeft: '4px solid',
            borderLeftColor: (theme) =>
              chipColor === 'default' ? theme.palette.divider : theme.palette[chipColor].main,
            bgcolor: 'background.paper',
            '&:before': { display: 'none' },
            ...(entry.isRunning && {
              animation: `${pulse} 2s ease-in-out infinite`,
            }),
          }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2, py: 1 }}>
            <Stack spacing={1} sx={{ width: '100%' }}>
              {/* Top row: Type chip, tool name, timestamp */}
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                <Box sx={{ display: 'flex', alignItems: 'center', mr: 0.5 }}>
                  {getEventIcon(entry.icon, chipColor)}
                </Box>
                <Chip
                  size="small"
                  label={entry.typeLabel}
                  color={chipColor === 'default' ? 'default' : chipColor}
                  variant={chipColor === 'default' ? 'outlined' : 'filled'}
                  sx={{ fontWeight: 500 }}
                />
                {entry.toolName && entry.toolName !== entry.typeLabel && (
                  <Chip
                    size="small"
                    label={entry.toolName}
                    variant="outlined"
                    sx={{
                      borderColor: (theme) => alpha(theme.palette.primary.main, 0.5),
                      color: 'primary.main',
                    }}
                  />
                )}
                <Box sx={{ flexGrow: 1 }} />
                {entry.timeLabel && (
                  <Typography variant="caption" color="text.secondary">
                    {entry.timeLabel}
                  </Typography>
                )}
              </Stack>

              {/* Tool info row - for tools with args preview */}
              {hasToolInfo && entry.argsPreview && (
                <Box
                  sx={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 1,
                    alignItems: 'center',
                    p: 1,
                    borderRadius: 1,
                    bgcolor: (theme) => alpha(theme.palette.warning.main, 0.08),
                    border: '1px solid',
                    borderColor: (theme) => alpha(theme.palette.warning.main, 0.2),
                  }}
                >
                  <Chip
                    size="small"
                    icon={<BuildIcon sx={{ fontSize: 14 }} />}
                    label={entry.toolName}
                    sx={{
                      bgcolor: (theme) => alpha(theme.palette.warning.main, 0.15),
                      color: 'warning.dark',
                      fontWeight: 600,
                      '& .MuiChip-icon': { color: 'warning.main' },
                    }}
                  />
                  <Typography
                    variant="caption"
                    sx={{
                      fontFamily: 'monospace',
                      color: 'text.secondary',
                      bgcolor: (theme) => alpha(theme.palette.common.black, 0.05),
                      px: 1,
                      py: 0.25,
                      borderRadius: 0.5,
                      maxWidth: '100%',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {entry.argsPreview}
                  </Typography>
                </Box>
              )}

              {/* Preview text */}
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  lineHeight: 1.5,
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  fontFamily: entry.type === 'bash' ? 'monospace' : 'inherit',
                }}
              >
                {entry.preview}
              </Typography>

              {/* Token usage row */}
              {hasTokenInfo && (
                <Box
                  sx={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 1,
                    alignItems: 'center',
                    p: 0.75,
                    borderRadius: 1,
                    bgcolor: (theme) => alpha(theme.palette.info.main, 0.06),
                    border: '1px solid',
                    borderColor: (theme) => alpha(theme.palette.info.main, 0.15),
                  }}
                >
                  <TokenIcon sx={{ fontSize: 16, color: 'info.main' }} />
                  {entry.tokenInfo.prompt != null && (
                    <Chip
                      size="small"
                      label={`Prompt: ${entry.tokenInfo.prompt.toLocaleString()}`}
                      variant="outlined"
                      sx={{
                        height: 22,
                        fontSize: '0.7rem',
                        borderColor: (theme) => alpha(theme.palette.info.main, 0.3),
                        color: 'info.dark',
                      }}
                    />
                  )}
                  {entry.tokenInfo.completion != null && (
                    <Chip
                      size="small"
                      label={`Completion: ${entry.tokenInfo.completion.toLocaleString()}`}
                      variant="outlined"
                      sx={{
                        height: 22,
                        fontSize: '0.7rem',
                        borderColor: (theme) => alpha(theme.palette.success.main, 0.3),
                        color: 'success.dark',
                      }}
                    />
                  )}
                  {entry.tokenInfo.total != null && (
                    <Chip
                      size="small"
                      label={`Total: ${entry.tokenInfo.total.toLocaleString()}`}
                      sx={{
                        height: 22,
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        bgcolor: (theme) => alpha(theme.palette.info.main, 0.15),
                        color: 'info.dark',
                      }}
                    />
                  )}
                </Box>
              )}
            </Stack>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 2, pb: 2, pt: 0 }}>
            <Stack spacing={1.25}>
              {/* Bash command display */}
              {hasBash && (
                <Box>
                  <Box
                    sx={{
                      p: 1.5,
                      borderRadius: 1,
                      bgcolor: (theme) => alpha(theme.palette.info.main, 0.08),
                      border: '1px solid',
                      borderColor: (theme) => alpha(theme.palette.info.main, 0.2),
                      mb: 1,
                    }}
                  >
                    <Chip
                      size="small"
                      label="IN"
                      sx={{
                        mb: 0.5,
                        height: 18,
                        fontSize: '0.65rem',
                        fontWeight: 600,
                        bgcolor: (theme) => alpha(theme.palette.info.main, 0.3),
                        color: 'info.dark',
                      }}
                    />
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
                      $ {entry.command}
                    </Typography>
                  </Box>
                </Box>
              )}

              {/* Edit diff display */}
              {hasEdit && (
                <Box>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 0.5,
                      mb: 1,
                      p: 0.75,
                      borderRadius: 0.5,
                      bgcolor: (theme) => alpha(theme.palette.info.main, 0.08),
                    }}
                  >
                    <DescriptionIcon sx={{ fontSize: 14, color: 'info.main' }} />
                    <Typography
                      variant="caption"
                      sx={{
                        fontFamily: 'monospace',
                        color: 'info.main',
                        fontWeight: 500,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {entry.filePath}
                    </Typography>
                  </Box>
                  <DiffView oldString={entry.oldString} newString={entry.newString} />
                </Box>
              )}

              {/* Todo list display */}
              {hasTodos && <TodoList todos={entry.todos} />}

              {/* Detail text (for non-special types) */}
              {entry.detail && !hasBash && !hasEdit && !hasTodos && (
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 1,
                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
                    border: '1px solid',
                    borderColor: 'divider',
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      fontFamily: 'monospace',
                      fontSize: '0.8rem',
                      maxHeight: 200,
                      overflow: 'auto',
                    }}
                  >
                    {entry.detail}
                  </Typography>
                </Box>
              )}

              <Divider />

              {/* Raw event data */}
              <Box
                component="pre"
                sx={{
                  bgcolor: 'grey.900',
                  color: 'grey.100',
                  borderRadius: 1,
                  p: 1.25,
                  fontSize: 11,
                  overflowX: 'auto',
                  maxHeight: 200,
                  mb: 0,
                }}
              >
                {safeStringify(entry.raw)}
              </Box>
            </Stack>
          </AccordionDetails>
        </Accordion>
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
