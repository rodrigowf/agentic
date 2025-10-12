import React, { useMemo, useEffect, useRef } from 'react';
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
import { ClaudeCodeInsightsProps, AgentMessage } from '../../../types';

const MAX_CODE_HIGHLIGHTS = 25;

interface MetadataItem {
  label: string;
  value: string;
}

interface CodeHighlight {
  key: string | number;
  timestamp?: string;
  timeLabel: string;
  typeLabel: string;
  tone: string;
  preview: string;
  detail: string;
  metadata: MetadataItem[];
  raw: any;
  icon: JSX.Element;
}

const ClaudeCodeInsights = ({
  messages = [],
  formatTimestamp,
  truncateText,
  safeStringify,
}: ClaudeCodeInsightsProps): JSX.Element => {
  const codeScrollRef = useRef<HTMLDivElement>(null);

  const codeHighlights = useMemo<CodeHighlight[]>(() => {
    if (!messages || messages.length === 0) return [];
    const entries: CodeHighlight[] = [];
    messages.forEach((msg: AgentMessage, index: number) => {
      if ((msg?.source || '').toLowerCase() !== 'claude_code') return;

      // Data structure is: msg.data.type and msg.data.data.{name, arguments, result, content}
      const msgData = (msg?.data as any) || (msg as any)?.payload || msg;
      const typeRaw = msgData?.type || msg?.type || 'event';
      const typeLower = typeRaw.toLowerCase();
      // The actual nested data with tool info is in msgData.data
      const data = msgData?.data || msgData;
      const metadata: MetadataItem[] = [];

      let tone = 'default';
      let typeLabel = 'Code event';
      let descriptiveText = '';
      let previewText = '';
      let icon: JSX.Element = <CodeIcon />;

      switch (typeLower) {
        case 'textmessage':
        case 'text_message': {
          typeLabel = 'Assistant message';
          tone = 'info';
          icon = <CodeIcon />;
          // Content is at data.content
          descriptiveText = data.content || '';
          // Show up to 250 chars or 3 lines, whichever comes first
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
            toolDesc = `$ ${args.command}`;
            previewText = `${args.command}`;
          } else if (toolName === 'Glob' && args.pattern) {
            toolDesc = `Pattern: ${args.pattern}`;
            previewText = `Pattern: ${args.pattern}`;
          } else if (toolName === 'Read' && args.file_path) {
            toolDesc = `Reading: ${args.file_path}`;
            previewText = `${args.file_path}`;
          } else if (toolName === 'Edit' && args.file_path) {
            toolDesc = `Editing: ${args.file_path}`;
            previewText = `${args.file_path}`;
          } else if (toolName === 'Write' && args.file_path) {
            toolDesc = `Writing: ${args.file_path}`;
            previewText = `${args.file_path}`;
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
            previewText = `Error: ${resultStr}`;
            descriptiveText = resultStr;
          } else {
            metadata.push({ label: 'Status', value: 'Success' });
            const resultLines = resultStr.split('\n').filter((line: string) => line.trim());
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
              previewText = resultStr;
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
        Object.entries(modelUsage).forEach(([modelName, usage]: [string, any]) => {
          if (usage.inputTokens) metadata.push({ label: `${modelName} input`, value: String(usage.inputTokens) });
          if (usage.outputTokens) metadata.push({ label: `${modelName} output`, value: String(usage.outputTokens) });
          if (usage.costUSD) metadata.push({ label: `${modelName} cost`, value: `$${usage.costUSD.toFixed(4)}` });
        });
      }

      entries.push({
        key: msg.id ?? `${msg.timestamp || 'code'}-${index}`,
        timestamp: msg.timestamp,
        timeLabel: formatTimestamp(msg.timestamp || ''),
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
                    borderLeftColor: (theme) => (chipColor === 'default' ? theme.palette.divider : (theme.palette as any)[chipColor].main),
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
                          color={chipColor === 'default' ? 'default' : chipColor as any}
                          variant={chipColor === 'default' ? 'outlined' : 'filled'}
                        />
                        <Box sx={{ flexGrow: 1 }} />
                        {entry.timeLabel && (
                          <Typography variant="caption" color="text.secondary">{entry.timeLabel}</Typography>
                        )}
                      </Stack>
                      <Typography
                        variant="body2"
                        color="text.primary"
                        sx={{
                          fontFamily: 'monospace',
                          fontSize: '0.9rem',
                          lineHeight: 1.6,
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          mt: 0.5,
                        }}
                      >
                        {entry.preview}
                      </Typography>
                      {entry.metadata.length > 0 && (
                        <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap" sx={{ mt: 0.75 }}>
                          {entry.metadata.slice(0, 3).map((meta, metaIdx) => (
                            <Chip
                              key={`${entry.key}-preview-meta-${metaIdx}`}
                              size="small"
                              variant="outlined"
                              label={`${meta.label}: ${meta.value}`}
                              sx={{ height: '22px', fontSize: '0.75rem' }}
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

export default ClaudeCodeInsights;
