import React, { useMemo, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Stack,
  Typography,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CodeIcon from '@mui/icons-material/Code';
import BuildIcon from '@mui/icons-material/Build';
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const MAX_CODE_HIGHLIGHTS = 25;

const ClaudeCodeInsights = ({
  messages = [],
  formatTimestamp,
  truncateText,
  safeStringify,
}) => {
  const codeScrollRef = useRef(null);

  const codeHighlights = useMemo(() => {
    if (!messages || messages.length === 0) return [];
    const entries = [];
    messages.forEach((msg, index) => {
      if ((msg?.source || '').toLowerCase() !== 'claude_code') return;

      // Data structure is: msg.data.type and msg.data.data.{name, arguments, result, content}
      const msgData = msg?.data || msg?.payload || msg;
      const typeRaw = msgData?.type || msg?.type || 'event';
      const typeLower = typeRaw.toLowerCase();
      // The actual nested data with tool info is in msgData.data
      const data = msgData?.data || msgData;
      const metadata = [];

      let tone = 'default';
      let typeLabel = 'Code event';
      let descriptiveText = '';
      let previewText = '';
      let icon = <CodeIcon />;

      switch (typeLower) {
        case 'textmessage':
        case 'text_message': {
          typeLabel = 'Assistant message';
          tone = 'info';
          icon = <CodeIcon />;
          // Content is at data.content
          descriptiveText = data.content || '';
          previewText = truncateText(descriptiveText, 150);
          break;
        }
        case 'systemevent':
        case 'system': {
          typeLabel = 'System event';
          descriptiveText = data.message || data.details?.subtype || '';
          previewText = descriptiveText;
          if (data.details) {
            if (data.details.cwd) metadata.push({ label: 'Working Dir', value: truncateText(data.details.cwd, 60) });
            if (data.details.model) metadata.push({ label: 'Model', value: data.details.model });
            if (data.details.tools) metadata.push({ label: 'Tools', value: `${data.details.tools.length} available` });
          }
          break;
        }
        case 'toolcallrequestevent':
        case 'tool_call_request_event': {
          typeLabel = 'Tool request';
          tone = 'warning';
          icon = <BuildIcon />;
          const toolName = data.name || 'unknown';
          const args = data.arguments || {};

          // Build a descriptive preview based on tool type
          let toolDesc = '';
          if (toolName === 'Bash' && args.command) {
            toolDesc = `$ ${truncateText(args.command, 100)}`;
            previewText = `Bash: ${truncateText(args.command, 80)}`;
          } else if (toolName === 'Glob' && args.pattern) {
            toolDesc = `Pattern: ${args.pattern}`;
            previewText = `Glob: ${args.pattern}`;
          } else if (toolName === 'Read' && args.file_path) {
            toolDesc = `Reading: ${args.file_path}`;
            previewText = `Read: ${truncateText(args.file_path, 80)}`;
          } else if (toolName === 'Edit' && args.file_path) {
            toolDesc = `Editing: ${args.file_path}`;
            previewText = `Edit: ${truncateText(args.file_path, 80)}`;
          } else if (toolName === 'Write' && args.file_path) {
            toolDesc = `Writing: ${args.file_path}`;
            previewText = `Write: ${truncateText(args.file_path, 80)}`;
          } else {
            previewText = `${toolName} tool`;
            toolDesc = safeStringify(args);
          }

          metadata.push({ label: 'Tool', value: toolName });

          // Extract specific args based on tool
          if (args.file_path) metadata.push({ label: 'File', value: truncateText(args.file_path, 60) });
          if (args.pattern) metadata.push({ label: 'Pattern', value: args.pattern });
          if (args.description) metadata.push({ label: 'Desc', value: truncateText(args.description, 60) });

          descriptiveText = toolDesc;
          break;
        }
        case 'toolcallexecutionevent':
        case 'tool_call_execution_event': {
          typeLabel = 'Tool result';
          tone = data.is_error ? 'error' : 'success';
          icon = data.is_error ? <ErrorIcon /> : <CheckCircleIcon />;
          // Result is at data.result
          const result = data.result || '';
          const resultStr = String(result);

          if (data.is_error) {
            metadata.push({ label: 'Status', value: 'Error' });
            previewText = `Error: ${truncateText(resultStr, 100)}`;
            descriptiveText = resultStr;
          } else {
            metadata.push({ label: 'Status', value: 'Success' });
            const resultLines = resultStr.split('\n').filter(line => line.trim());
            const lineCount = resultLines.length;

            if (lineCount > 5) {
              // Show first few lines as preview
              const firstLines = resultLines.slice(0, 3).join('\n');
              previewText = `${truncateText(firstLines, 120)}... (${lineCount} total lines)`;
              metadata.push({ label: 'Lines', value: String(lineCount) });
            } else if (lineCount > 1) {
              previewText = `${lineCount} lines returned`;
              metadata.push({ label: 'Lines', value: String(lineCount) });
            } else {
              previewText = truncateText(resultStr, 120);
            }
            descriptiveText = resultStr;
          }
          break;
        }
        case 'taskresult': {
          typeLabel = 'Task completed';
          tone = data.outcome === 'error' ? 'error' : 'success';
          icon = data.outcome === 'error' ? <ErrorIcon /> : <CheckCircleIcon />;
          const outcome = data.outcome || 'completed';
          if (outcome) metadata.push({ label: 'Outcome', value: outcome });
          if (data.duration_ms) metadata.push({ label: 'Duration', value: `${data.duration_ms} ms` });

          const usage = data.usage || {};
          if (usage.input_tokens) metadata.push({ label: 'Input tokens', value: String(usage.input_tokens) });
          if (usage.output_tokens) metadata.push({ label: 'Output tokens', value: String(usage.output_tokens) });

          descriptiveText = data.message || safeStringify(data);
          previewText = outcome === 'error' ? 'Task failed' : 'Task completed successfully';
          break;
        }
        case 'error': {
          typeLabel = 'Error';
          tone = 'error';
          icon = <ErrorIcon />;
          descriptiveText = data.message || safeStringify(data);
          previewText = 'Error occurred';
          if (data.source) metadata.push({ label: 'Source', value: data.source });
          break;
        }
        case 'raw_stdout': {
          typeLabel = 'Raw output';
          descriptiveText = data.data || safeStringify(data);
          previewText = 'Raw stdout';
          break;
        }
        default: {
          typeLabel = typeRaw;
          const fallback = data.message || data.content || data.summary;
          if (fallback != null) {
            descriptiveText = typeof fallback === 'string' ? fallback : safeStringify(fallback);
            previewText = descriptiveText;
          } else {
            descriptiveText = safeStringify(data);
            previewText = 'See raw event details';
          }
        }
      }

      const preview = truncateText(previewText || descriptiveText, 200) || 'No summary available';
      const detail = descriptiveText && descriptiveText !== preview ? descriptiveText : (descriptiveText || '');

      // Add model usage if present
      const modelUsage = data.models_usage;
      if (modelUsage && typeof modelUsage === 'object') {
        Object.entries(modelUsage).forEach(([modelName, usage]) => {
          if (usage.inputTokens) metadata.push({ label: `${modelName} input`, value: String(usage.inputTokens) });
          if (usage.outputTokens) metadata.push({ label: `${modelName} output`, value: String(usage.outputTokens) });
          if (usage.costUSD) metadata.push({ label: `${modelName} cost`, value: `$${usage.costUSD.toFixed(4)}` });
        });
      }

      entries.push({
        key: msg.id ?? `${msg.timestamp || 'code'}-${index}`,
        timestamp: msg.timestamp,
        timeLabel: formatTimestamp(msg.timestamp),
        typeLabel,
        tone,
        preview,
        detail,
        metadata,
        raw: msgData ?? msg, // Show the extracted data in raw view
        icon,
      });
    });
    return entries.slice(-MAX_CODE_HIGHLIGHTS);
  }, [messages, formatTimestamp, truncateText, safeStringify]);

  useEffect(() => {
    const node = codeScrollRef.current;
    if (node) {
      requestAnimationFrame(() => {
        node.scrollTop = node.scrollHeight;
      });
    }
  }, [codeHighlights]);

  return (
    <Box
      ref={codeScrollRef}
      sx={{
        flexGrow: 1,
        overflowY: 'auto',
        height: '100%',
      }}
    >
      {codeHighlights.length === 0 ? (
        <Typography variant="body2" color="text.secondary">No Claude Code activity yet. Send a self-editing task to get started.</Typography>
      ) : (
        <Stack spacing={1.25}>
            {codeHighlights.map((entry) => {
              const chipColor = ['info', 'success', 'warning', 'error'].includes(entry.tone) ? entry.tone : 'default';
              return (
                <Accordion
                  key={entry.key}
                  disableGutters
                  elevation={0}
                  sx={{
                    border: '1px solid',
                    borderColor: 'divider',
                    borderLeft: '4px solid',
                    borderLeftColor: (theme) => (chipColor === 'default' ? theme.palette.divider : theme.palette[chipColor].main),
                    bgcolor: 'background.paper',
                  }}
                >
                  <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2 }}>
                    <Stack spacing={0.5} sx={{ width: '100%' }}>
                      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          {entry.icon}
                        </Box>
                        <Chip
                          size="small"
                          label={entry.typeLabel}
                          color={chipColor === 'default' ? 'default' : chipColor}
                          variant={chipColor === 'default' ? 'outlined' : 'filled'}
                        />
                        <Box sx={{ flexGrow: 1 }} />
                        {entry.timeLabel && (
                          <Typography variant="caption" color="text.secondary">{entry.timeLabel}</Typography>
                        )}
                      </Stack>
                      <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>{entry.preview}</Typography>
                      {entry.metadata.length > 0 && (
                        <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap" sx={{ mt: 0.5 }}>
                          {entry.metadata.slice(0, 3).map((meta, metaIdx) => (
                            <Chip
                              key={`${entry.key}-preview-meta-${metaIdx}`}
                              size="small"
                              variant="outlined"
                              label={`${meta.label}: ${meta.value}`}
                              sx={{ height: '20px', fontSize: '0.7rem' }}
                            />
                          ))}
                        </Stack>
                      )}
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails sx={{ px: 2, pb: 2 }}>
                    <Stack spacing={1.25}>
                      {entry.detail && entry.detail !== entry.preview && (
                        <Box
                          sx={{
                            bgcolor: 'grey.50',
                            borderRadius: 1,
                            p: 1.5,
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
                              maxHeight: '300px',
                              overflowY: 'auto',
                            }}
                          >
                            {entry.detail}
                          </Typography>
                        </Box>
                      )}
                      {entry.metadata.length > 0 && (
                        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                          {entry.metadata.map((meta, metaIdx) => (
                            <Chip key={`${entry.key}-meta-${metaIdx}`} size="small" variant="outlined" label={`${meta.label}: ${meta.value}`} />
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
                          fontSize: 12,
                          overflowX: 'auto',
                          mb: 0,
                        }}
                      >
                        {safeStringify(entry.raw)}
                      </Box>
                    </Stack>
                  </AccordionDetails>
                </Accordion>
              );
            })}
        </Stack>
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
