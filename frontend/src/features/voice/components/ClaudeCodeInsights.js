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
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CodeIcon from '@mui/icons-material/Code';
import BuildIcon from '@mui/icons-material/Build';
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import TerminalIcon from '@mui/icons-material/Terminal';
import EditIcon from '@mui/icons-material/Edit';
import DescriptionIcon from '@mui/icons-material/Description';
import SearchIcon from '@mui/icons-material/Search';
import InfoIcon from '@mui/icons-material/Info';
import TokenIcon from '@mui/icons-material/DataUsage';

const MAX_CODE_HIGHLIGHTS = 25;

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

      // Data structure from backend:
      // msg.data = { type: "claude_code_event", event_type: "toolcallrequestevent", message: "...", source: "ClaudeCode", data: { name, arguments, ... } }
      const rawData = msg?.data || msg?.payload || msg;
      const eventType = rawData?.event_type || rawData?.type || 'event';
      const typeLower = eventType.toLowerCase();

      // The actual nested data with tool info is in rawData.data
      const nestedData = rawData?.data || {};
      const metadata = [];

      let tone = 'default';
      let typeLabel = 'Code event';
      let descriptiveText = '';
      let previewText = '';
      let icon = 'code';
      let toolName = null;
      let argsPreview = null;
      let fileInfo = null;

      switch (typeLower) {
        case 'textmessage':
        case 'text_message': {
          typeLabel = 'Assistant message';
          tone = 'info';
          icon = 'code';
          // Content is at nestedData.content
          descriptiveText = nestedData.content || rawData.message || '';
          // Show up to 3 lines as preview
          const lines = descriptiveText.split('\n');
          if (lines.length > 3) {
            previewText = lines.slice(0, 3).join('\n') + '...';
          } else {
            previewText = descriptiveText.substring(0, 300);
          }
          break;
        }
        case 'systemevent':
        case 'system': {
          typeLabel = 'System event';
          icon = 'info';
          descriptiveText = nestedData.message || rawData.message || '';
          previewText = descriptiveText;
          if (nestedData.cwd) metadata.push({ label: 'Working Dir', value: truncateText(nestedData.cwd, 60) });
          if (nestedData.model) metadata.push({ label: 'Model', value: nestedData.model });
          if (nestedData.tools) metadata.push({ label: 'Tools', value: `${nestedData.tools.length} available` });
          break;
        }
        case 'toolcallrequestevent':
        case 'tool_call_request_event': {
          typeLabel = 'Tool request';
          tone = 'warning';
          toolName = nestedData.name || 'unknown';
          const args = nestedData.arguments || {};

          // Set icon based on tool type
          if (toolName === 'Bash') {
            icon = 'terminal';
          } else if (toolName === 'Edit') {
            icon = 'edit';
          } else if (toolName === 'Read' || toolName === 'Write') {
            icon = 'file';
          } else if (toolName === 'Glob' || toolName === 'Grep') {
            icon = 'search';
          } else {
            icon = 'tool';
          }

          // Build a descriptive preview based on tool type
          if (toolName === 'Bash' && args.command) {
            previewText = `$ ${truncateText(args.command, 120)}`;
            argsPreview = args.command;
            if (args.description) metadata.push({ label: 'Desc', value: truncateText(args.description, 80) });
          } else if (toolName === 'Glob' && args.pattern) {
            previewText = `Pattern: ${args.pattern}`;
            argsPreview = args.pattern;
            if (args.path) fileInfo = args.path;
          } else if (toolName === 'Grep' && args.pattern) {
            previewText = `Search: ${args.pattern}`;
            argsPreview = args.pattern;
            if (args.path) fileInfo = args.path;
            if (args.glob) metadata.push({ label: 'Glob', value: args.glob });
          } else if (toolName === 'Read' && args.file_path) {
            previewText = `Reading file`;
            fileInfo = args.file_path;
            if (args.offset) metadata.push({ label: 'Offset', value: String(args.offset) });
            if (args.limit) metadata.push({ label: 'Limit', value: String(args.limit) });
          } else if (toolName === 'Edit' && args.file_path) {
            previewText = `Editing file`;
            fileInfo = args.file_path;
            if (args.old_string) argsPreview = truncateText(args.old_string, 80);
          } else if (toolName === 'Write' && args.file_path) {
            previewText = `Writing file`;
            fileInfo = args.file_path;
          } else {
            previewText = `Requesting ${toolName}`;
            const argsText = safeStringify(args);
            argsPreview = truncateText(argsText, 80);
          }

          descriptiveText = safeStringify(args);
          break;
        }
        case 'toolcallexecutionevent':
        case 'tool_call_execution_event': {
          typeLabel = 'Tool result';
          toolName = nestedData.name || null;
          const result = nestedData.result || '';
          const resultStr = String(result);
          const hasError = nestedData.is_error === true;

          if (hasError) {
            tone = 'error';
            icon = 'error';
            metadata.push({ label: 'Status', value: 'Error' });
            previewText = `Error: ${truncateText(resultStr, 120)}`;
            descriptiveText = resultStr;
          } else {
            tone = 'success';
            icon = 'success';
            metadata.push({ label: 'Status', value: 'Success' });
            const resultLines = resultStr.split('\n').filter(line => line.trim());
            const lineCount = resultLines.length;

            if (lineCount > 8) {
              // Show first 5 lines as preview
              const firstLines = resultLines.slice(0, 5).join('\n');
              previewText = `${firstLines}\n... (${lineCount - 5} more lines)`;
              metadata.push({ label: 'Lines', value: String(lineCount) });
            } else if (lineCount > 1) {
              previewText = resultLines.join('\n');
              metadata.push({ label: 'Lines', value: String(lineCount) });
            } else {
              previewText = truncateText(resultStr, 200);
            }
            descriptiveText = resultStr;
          }
          break;
        }
        case 'taskresult': {
          typeLabel = 'Task completed';
          const outcome = nestedData.outcome || 'completed';
          tone = outcome === 'error' ? 'error' : 'success';
          icon = outcome === 'error' ? 'error' : 'success';

          if (outcome) metadata.push({ label: 'Outcome', value: outcome });
          if (nestedData.duration_ms) metadata.push({ label: 'Duration', value: `${nestedData.duration_ms} ms` });

          const usage = nestedData.usage || {};
          if (usage.input_tokens) metadata.push({ label: 'Input tokens', value: String(usage.input_tokens) });
          if (usage.output_tokens) metadata.push({ label: 'Output tokens', value: String(usage.output_tokens) });

          descriptiveText = nestedData.message || safeStringify(nestedData);
          previewText = outcome === 'error' ? 'Task failed' : 'Task completed successfully';
          break;
        }
        case 'error': {
          typeLabel = 'Error';
          tone = 'error';
          icon = 'error';
          descriptiveText = nestedData.message || rawData.message || safeStringify(nestedData);
          previewText = truncateText(descriptiveText, 150);
          if (nestedData.source) metadata.push({ label: 'Source', value: nestedData.source });
          break;
        }
        case 'raw_stdout': {
          typeLabel = 'Raw output';
          icon = 'terminal';
          descriptiveText = nestedData.data || safeStringify(nestedData);
          previewText = truncateText(descriptiveText, 150);
          break;
        }
        default: {
          typeLabel = eventType;
          icon = 'info';
          const fallback = nestedData.message || nestedData.content || rawData.message || rawData.summary;
          if (fallback != null) {
            descriptiveText = typeof fallback === 'string' ? fallback : safeStringify(fallback);
            previewText = truncateText(descriptiveText, 150);
          } else {
            descriptiveText = safeStringify(nestedData || rawData);
            previewText = 'See raw event details';
          }
        }
      }

      const preview = truncateText(previewText || descriptiveText, 200) || 'No summary available';
      const detail = descriptiveText && descriptiveText !== preview ? descriptiveText : (descriptiveText || '');

      // Token usage info
      const modelUsage = nestedData.models_usage || rawData.models_usage;
      let tokenInfo = null;
      if (modelUsage) {
        const inputTokens = modelUsage.inputTokens || modelUsage.input_tokens;
        const outputTokens = modelUsage.outputTokens || modelUsage.output_tokens;
        const costUSD = modelUsage.costUSD;

        if (inputTokens != null || outputTokens != null) {
          tokenInfo = { input: inputTokens, output: outputTokens, cost: costUSD };
          if (inputTokens) metadata.push({ label: 'Input tokens', value: String(inputTokens) });
          if (outputTokens) metadata.push({ label: 'Output tokens', value: String(outputTokens) });
          if (costUSD) metadata.push({ label: 'Cost', value: `$${costUSD.toFixed(4)}` });
        }
      }

      entries.push({
        key: msg.id ?? `${msg.timestamp || 'code'}-${index}`,
        timestamp: msg.timestamp,
        timeLabel: formatTimestamp(msg.timestamp),
        typeLabel,
        tone,
        icon,
        toolName,
        argsPreview,
        fileInfo,
        tokenInfo,
        preview,
        detail,
        metadata,
        raw: rawData ?? msg,
      });
    });
    return entries.slice(-MAX_CODE_HIGHLIGHTS);
  }, [messages, formatTimestamp, truncateText, safeStringify]);

  const virtuosoRef = useRef(null);
  const isAtBottomRef = useRef(true);

  // Track whether user is scrolled to bottom
  const handleAtBottomStateChange = (atBottom) => {
    isAtBottomRef.current = atBottom;
  };

  useEffect(() => {
    // Only auto-scroll if user is already at the bottom
    if (virtuosoRef.current && codeHighlights.length > 0 && isAtBottomRef.current) {
      virtuosoRef.current.scrollToIndex({
        index: codeHighlights.length - 1,
        align: 'end',
        behavior: 'auto'
      });
    }
  }, [codeHighlights]);

  // Helper to get the right icon for the entry type
  const getEntryIcon = (iconType) => {
    const iconSx = { fontSize: 18 };
    switch (iconType) {
      case 'code':
        return <CodeIcon sx={{ ...iconSx, color: 'info.main' }} />;
      case 'tool':
        return <BuildIcon sx={{ ...iconSx, color: 'warning.main' }} />;
      case 'terminal':
        return <TerminalIcon sx={{ ...iconSx, color: 'warning.main' }} />;
      case 'edit':
        return <EditIcon sx={{ ...iconSx, color: 'warning.main' }} />;
      case 'file':
        return <DescriptionIcon sx={{ ...iconSx, color: 'warning.main' }} />;
      case 'search':
        return <SearchIcon sx={{ ...iconSx, color: 'warning.main' }} />;
      case 'success':
        return <CheckCircleIcon sx={{ ...iconSx, color: 'success.main' }} />;
      case 'error':
        return <ErrorIcon sx={{ ...iconSx, color: 'error.main' }} />;
      default:
        return <InfoIcon sx={{ ...iconSx, color: 'text.secondary' }} />;
    }
  };

  const renderCodeEntry = (index, entry) => {
    const chipColor = ['info', 'success', 'warning', 'error'].includes(entry.tone) ? entry.tone : 'default';
    const hasToolInfo = entry.toolName || entry.argsPreview;
    const hasFileInfo = entry.fileInfo;
    const hasTokenInfo = entry.tokenInfo;

    return (
      <Box sx={{ mb: 1.25 }}>
        <Accordion
          disableGutters
          elevation={0}
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderLeft: '4px solid',
            borderLeftColor: (theme) => (chipColor === 'default' ? theme.palette.divider : theme.palette[chipColor].main),
            bgcolor: 'background.paper',
            '&:before': { display: 'none' },
          }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2, py: 1 }}>
            <Stack spacing={1} sx={{ width: '100%' }}>
              {/* Top row: Type chip, tool name, timestamp */}
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                <Box sx={{ display: 'flex', alignItems: 'center', mr: 0.5 }}>
                  {getEntryIcon(entry.icon)}
                </Box>
                <Chip
                  size="small"
                  label={entry.typeLabel}
                  color={chipColor === 'default' ? 'default' : chipColor}
                  variant={chipColor === 'default' ? 'outlined' : 'filled'}
                  sx={{ fontWeight: 500 }}
                />
                {entry.toolName && (
                  <Chip
                    size="small"
                    label={entry.toolName}
                    variant="outlined"
                    sx={{
                      borderColor: (theme) => alpha(theme.palette.primary.main, 0.5),
                      color: 'primary.main',
                      fontWeight: 600,
                    }}
                  />
                )}
                <Box sx={{ flexGrow: 1 }} />
                {entry.timeLabel && (
                  <Typography variant="caption" color="text.secondary">{entry.timeLabel}</Typography>
                )}
              </Stack>

              {/* File info row - shown when there's a file path */}
              {hasFileInfo && (
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                    p: 0.75,
                    borderRadius: 1,
                    bgcolor: (theme) => alpha(theme.palette.info.main, 0.08),
                    border: '1px solid',
                    borderColor: (theme) => alpha(theme.palette.info.main, 0.2),
                  }}
                >
                  <DescriptionIcon sx={{ fontSize: 14, color: 'info.main' }} />
                  <Typography
                    variant="caption"
                    sx={{
                      fontFamily: 'monospace',
                      color: 'info.dark',
                      fontWeight: 500,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {entry.fileInfo}
                  </Typography>
                </Box>
              )}

              {/* Tool args row - shown when there's tool info without file */}
              {hasToolInfo && !hasFileInfo && (
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
                  {entry.argsPreview && (
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
                  )}
                </Box>
              )}

              {/* Preview text */}
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  lineHeight: 1.5,
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {entry.preview}
              </Typography>

              {/* Token usage row - always visible when present */}
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
                  {entry.tokenInfo.input != null && (
                    <Chip
                      size="small"
                      label={`In: ${entry.tokenInfo.input.toLocaleString()}`}
                      variant="outlined"
                      sx={{
                        height: 22,
                        fontSize: '0.7rem',
                        borderColor: (theme) => alpha(theme.palette.info.main, 0.3),
                        color: 'info.dark',
                      }}
                    />
                  )}
                  {entry.tokenInfo.output != null && (
                    <Chip
                      size="small"
                      label={`Out: ${entry.tokenInfo.output.toLocaleString()}`}
                      variant="outlined"
                      sx={{
                        height: 22,
                        fontSize: '0.7rem',
                        borderColor: (theme) => alpha(theme.palette.success.main, 0.3),
                        color: 'success.dark',
                      }}
                    />
                  )}
                  {entry.tokenInfo.cost != null && (
                    <Chip
                      size="small"
                      label={`$${entry.tokenInfo.cost.toFixed(4)}`}
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

              {/* Preview metadata chips */}
              {entry.metadata.length > 0 && (
                <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                  {entry.metadata.slice(0, 3).map((meta, metaIdx) => (
                    <Chip
                      key={`${entry.key}-preview-meta-${metaIdx}`}
                      size="small"
                      variant="outlined"
                      label={`${meta.label}: ${meta.value}`}
                      sx={{ height: 22, fontSize: '0.7rem' }}
                    />
                  ))}
                </Stack>
              )}
            </Stack>
          </AccordionSummary>
          <AccordionDetails sx={{ px: 2, pb: 2, pt: 0 }}>
            <Stack spacing={1.25}>
              {entry.detail && (
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
                      maxHeight: 300,
                      overflow: 'auto',
                    }}
                  >
                    {entry.detail}
                  </Typography>
                </Box>
              )}
              {entry.metadata.length > 0 && (
                <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                  {entry.metadata.map((meta, metaIdx) => (
                    <Chip
                      key={`${entry.key}-meta-${metaIdx}`}
                      size="small"
                      variant="outlined"
                      label={`${meta.label}: ${meta.value}`}
                      sx={{ height: 24, fontSize: '0.75rem' }}
                    />
                  ))}
                </Stack>
              )}
              <Divider />
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
    <Box
      sx={{
        flexGrow: 1,
        height: '100%',
      }}
    >
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
          itemContent={renderCodeEntry}
          atBottomStateChange={handleAtBottomStateChange}
          followOutput={(isAtBottom) => isAtBottom ? 'smooth' : false}
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
