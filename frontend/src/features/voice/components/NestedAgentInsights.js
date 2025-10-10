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

const MAX_NESTED_HIGHLIGHTS = 25;

const NestedAgentInsights = ({
  messages,
  formatTimestamp,
  truncateText,
  safeStringify,
}) => {
  const nestedScrollRef = useRef(null);

  const nestedHighlights = useMemo(() => {
    if (!messages || messages.length === 0) return [];
    const entries = [];
    messages.forEach((msg, index) => {
      if ((msg?.source || '').toLowerCase() !== 'nested') return;

      const typeRaw = msg?.type || 'event';
      const typeLower = typeRaw.toLowerCase();
      const data = msg?.data || {};
      const nestedData = (typeof data.data === 'object' && data.data !== null) ? data.data : {};
      const agentName = nestedData.source || data.source || data.agent || 'Nested agent';
      const role = nestedData.role || nestedData.role_name || data.role;
      const metadata = [];
      const contentItems = Array.isArray(data.content) && data.content.length
        ? data.content
        : (Array.isArray(nestedData.content) ? nestedData.content : []);

      let tone = 'default';
      let typeLabel = 'Nested event';
      let descriptiveText = '';
      let previewText = '';

      switch (typeLower) {
        case 'textmessage':
        case 'text_message': {
          typeLabel = 'Inner thought';
          tone = 'info';
          descriptiveText = nestedData.content || nestedData.message || data.message || '';
          previewText = descriptiveText;
          if (nestedData.intent) metadata.push({ label: 'Intent', value: nestedData.intent });
          if (nestedData.channel) metadata.push({ label: 'Channel', value: nestedData.channel });
          break;
        }
        case 'system':
        case 'systemevent': {
          typeLabel = 'System notice';
          descriptiveText = nestedData.message || data.message || '';
          previewText = descriptiveText;
          break;
        }
        case 'toolcallrequestevent':
        case 'tool_call_request_event': {
          typeLabel = 'Tool request';
          tone = 'warning';
          const firstContent = contentItems[0] || {};
          const toolName = firstContent.name || nestedData.name || data.name;
          const rawArgs = firstContent.arguments ?? nestedData.arguments ?? nestedData.args ?? nestedData.input ?? data.message;
          if (toolName) metadata.push({ label: 'Tool', value: toolName });
          let argsText = '';
          if (rawArgs != null) {
            argsText = typeof rawArgs === 'string' ? rawArgs : safeStringify(rawArgs);
            metadata.push({ label: 'Args', value: truncateText(argsText, 140) });
          }
          previewText = toolName ? `Requested ${toolName}` : 'Tool requested';
          descriptiveText = argsText || previewText;
          if (nestedData.reason) metadata.push({ label: 'Reason', value: truncateText(nestedData.reason, 120) });
          break;
        }
        case 'toolcallexecutionevent':
        case 'tool_call_execution_event': {
          typeLabel = 'Tool result';
          tone = 'success';
          const firstContent = contentItems[0] || {};
          const toolName = firstContent.name || nestedData.name || nestedData.tool || data.name;
          const result = nestedData.result ?? data.data?.result ?? data.result;
          if (toolName) metadata.push({ label: 'Tool', value: toolName });
          if (nestedData.duration_ms) metadata.push({ label: 'Duration', value: `${nestedData.duration_ms} ms` });
          const rawArgs = firstContent.arguments ?? nestedData.arguments ?? nestedData.args;
          if (rawArgs != null) {
            const argsText = typeof rawArgs === 'string' ? rawArgs : safeStringify(rawArgs);
            metadata.push({ label: 'Args', value: truncateText(argsText, 140) });
          }
          const hasError = firstContent?.is_error === true
            || firstContent?.status === 'error'
            || nestedData?.is_error === true
            || nestedData?.status === 'error'
            || (Array.isArray(contentItems) && contentItems.some((item) => item?.is_error || item?.status === 'error'));
          const resultText = typeof result === 'string' ? result : safeStringify(result);
          if (hasError) {
            tone = 'error';
            if (toolName) metadata.push({ label: 'Status', value: 'Error' });
            const errorDetail = nestedData.error || nestedData.message || firstContent?.error || resultText;
            previewText = toolName ? `Error in ${toolName}` : 'Tool execution error';
            descriptiveText = typeof errorDetail === 'string' ? errorDetail : safeStringify(errorDetail);
          } else {
            previewText = toolName ? `Completed ${toolName}` : 'Tool execution';
            descriptiveText = resultText || descriptiveText;
          }
          break;
        }
        case 'taskresult': {
          typeLabel = 'Task result';
          tone = 'success';
          const status = nestedData.outcome || nestedData.status || data.status;
          if (status) metadata.push({ label: 'Status', value: status });
          if (nestedData.score != null) metadata.push({ label: 'Score', value: String(nestedData.score) });
          const taskPayload = nestedData.message || nestedData.summary || data.message;
          descriptiveText = taskPayload != null ? (typeof taskPayload === 'string' ? taskPayload : safeStringify(taskPayload)) : safeStringify(nestedData || data);
          previewText = status ? `${status}: ${truncateText(descriptiveText, 160)}` : descriptiveText;
          break;
        }
        default: {
          typeLabel = typeRaw;
          const fallback = nestedData.message || nestedData.content || data.message || data.summary;
          if (fallback != null) {
            descriptiveText = typeof fallback === 'string' ? fallback : safeStringify(fallback);
            previewText = descriptiveText;
          } else {
            descriptiveText = '';
            previewText = 'See raw event details';
          }
        }
      }

      const preview = truncateText(previewText || descriptiveText, 200) || 'No summary available';
      const detail = descriptiveText && descriptiveText !== preview ? descriptiveText : (descriptiveText || '');

      const modelUsage = data.models_usage || nestedData.models_usage;
      if (modelUsage) {
        if (modelUsage.prompt_tokens != null) {
          metadata.push({ label: 'Prompt tokens', value: String(modelUsage.prompt_tokens) });
        }
        if (modelUsage.completion_tokens != null) {
          metadata.push({ label: 'Completion tokens', value: String(modelUsage.completion_tokens) });
        }
        if (modelUsage.total_tokens != null) {
          metadata.push({ label: 'Total tokens', value: String(modelUsage.total_tokens) });
        } else if (modelUsage.prompt_tokens != null && modelUsage.completion_tokens != null) {
          metadata.push({
            label: 'Total tokens',
            value: String(modelUsage.prompt_tokens + modelUsage.completion_tokens),
          });
        }
      }

      entries.push({
        key: msg.id ?? `${msg.timestamp || 'nested'}-${index}`,
        timestamp: msg.timestamp,
        timeLabel: formatTimestamp(msg.timestamp),
        agentName,
        role,
        typeLabel,
        tone,
        preview,
        detail,
        metadata,
        raw: msg.data ?? msg,
      });
    });
    return entries.slice(-MAX_NESTED_HIGHLIGHTS);
  }, [messages, formatTimestamp, truncateText, safeStringify]);

  useEffect(() => {
    const node = nestedScrollRef.current;
    if (node) {
      requestAnimationFrame(() => {
        node.scrollTop = node.scrollHeight;
      });
    }
  }, [nestedHighlights]);

  return (
    <Box
      ref={nestedScrollRef}
      sx={{
        flexGrow: 1,
        overflowY: 'auto',
        height: '100%',
      }}
    >
      {nestedHighlights.length === 0 ? (
        <Typography variant="body2" color="text.secondary">No nested activity captured yet.</Typography>
      ) : (
        <Stack spacing={1.25}>
            {nestedHighlights.map((entry) => {
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
                        <Chip
                          size="small"
                          label={entry.typeLabel}
                          color={chipColor === 'default' ? 'default' : chipColor}
                          variant={chipColor === 'default' ? 'outlined' : 'filled'}
                        />
                        <Chip size="small" label={entry.agentName} variant="outlined" />
                        {entry.role && (
                          <Chip size="small" label={entry.role} variant="outlined" />
                        )}
                        <Box sx={{ flexGrow: 1 }} />
                        {entry.timeLabel && (
                          <Typography variant="caption" color="text.secondary">{entry.timeLabel}</Typography>
                        )}
                      </Stack>
                      <Typography variant="body2" color="text.secondary">{entry.preview}</Typography>
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails sx={{ px: 2, pb: 2 }}>
                    <Stack spacing={1.25}>
                      {entry.detail && (
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{entry.detail}</Typography>
                      )}
                      {(entry.metadata.length > 0 || entry.role) && (
                        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                          {entry.role && (
                            <Chip size="small" variant="outlined" label={`Role: ${entry.role}`} />
                          )}
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

NestedAgentInsights.propTypes = {
  messages: PropTypes.arrayOf(PropTypes.object),
  formatTimestamp: PropTypes.func.isRequired,
  truncateText: PropTypes.func.isRequired,
  safeStringify: PropTypes.func.isRequired,
};

NestedAgentInsights.defaultProps = {
  messages: [],
};

export default NestedAgentInsights;
