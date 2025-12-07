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
import BuildIcon from '@mui/icons-material/Build';
import PsychologyIcon from '@mui/icons-material/Psychology';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import InfoIcon from '@mui/icons-material/Info';
import TokenIcon from '@mui/icons-material/DataUsage';

const MAX_NESTED_HIGHLIGHTS = 25;

const NestedAgentInsights = ({
  messages,
  formatTimestamp,
  truncateText,
  safeStringify,
}) => {
  const nestedHighlights = useMemo(() => {
    if (!messages || messages.length === 0) return [];
    const entries = [];
    messages.forEach((msg, index) => {
      const sourceLower = (msg?.source || '').toLowerCase();
      if (sourceLower !== 'nested' && sourceLower !== 'nested_agent') return;

      const rawData = msg?.data || {};
      const typeRaw = rawData.event_type || msg?.type || 'event';
      const typeLower = typeRaw.toLowerCase();
      const data = rawData || {};
      const nestedData = (typeof data.data === 'object' && data.data !== null) ? { ...data.data } : {};

      // Some backend events come in as {type: 'nested_event', event_type: 'textmessage', message: '[TEAM Agent] ...'}
      // Unpack message so the panel can render it like regular nested events.
      if (!nestedData.message && data.message) {
        const teamMatch = typeof data.message === 'string' ? data.message.match(/^\[TEAM\s+([^\]]+)\]\s*(.*)$/) : null;
        if (teamMatch) {
          const agentLabel = teamMatch[1];
          const contentText = teamMatch[2];
          nestedData.source = nestedData.source || agentLabel;
          nestedData.agent = nestedData.agent || agentLabel;
          nestedData.content = nestedData.content || contentText;
          data.source = data.source || agentLabel;
          data.agent = data.agent || agentLabel;
        } else {
          nestedData.message = data.message;
        }
      }

      const agentName = nestedData.source || data.source || data.agent || 'Nested agent';
      const role = nestedData.role || nestedData.role_name || data.role;
      const metadata = [];
      const previewMeta = []; // Metadata shown in collapsed state
      const contentItems = Array.isArray(data.content) && data.content.length
        ? data.content
        : (Array.isArray(nestedData.content) ? nestedData.content : []);

      let tone = 'default';
      let typeLabel = 'Nested event';
      let descriptiveText = '';
      let previewText = '';
      let icon = 'info';
      let toolName = null;
      let argsPreview = null;

      switch (typeLower) {
        case 'textmessage':
        case 'text_message': {
          typeLabel = 'Inner thought';
          tone = 'info';
          icon = 'thought';
          descriptiveText = nestedData.content || nestedData.message || data.message || '';
          previewText = descriptiveText;
          if (nestedData.intent) metadata.push({ label: 'Intent', value: nestedData.intent });
          if (nestedData.channel) metadata.push({ label: 'Channel', value: nestedData.channel });
          break;
        }
        case 'system':
        case 'systemevent': {
          typeLabel = 'System notice';
          icon = 'info';
          descriptiveText = nestedData.message || data.message || '';
          previewText = descriptiveText;
          break;
        }
        case 'toolcallrequestevent':
        case 'tool_call_request_event': {
          typeLabel = 'Tool request';
          tone = 'warning';
          icon = 'tool';
          const firstContent = contentItems[0] || {};
          toolName = firstContent.name || nestedData.name || data.name;
          const rawArgs = firstContent.arguments ?? nestedData.arguments ?? nestedData.args ?? nestedData.input ?? data.message;
          let argsText = '';
          if (rawArgs != null) {
            argsText = typeof rawArgs === 'string' ? rawArgs : safeStringify(rawArgs);
            argsPreview = truncateText(argsText, 80);
            metadata.push({ label: 'Args', value: truncateText(argsText, 300) });
          }
          previewText = toolName ? `Requesting ${toolName}` : 'Tool requested';
          descriptiveText = argsText || previewText;
          if (nestedData.reason) metadata.push({ label: 'Reason', value: truncateText(nestedData.reason, 120) });
          break;
        }
        case 'toolcallexecutionevent':
        case 'tool_call_execution_event': {
          typeLabel = 'Tool result';
          tone = 'success';
          icon = 'success';
          const firstContent = contentItems[0] || {};
          toolName = firstContent.name || nestedData.name || nestedData.tool || data.name;
          const result = nestedData.result ?? data.data?.result ?? data.result;
          if (nestedData.duration_ms) metadata.push({ label: 'Duration', value: `${nestedData.duration_ms} ms` });
          const rawArgs = firstContent.arguments ?? nestedData.arguments ?? nestedData.args;
          if (rawArgs != null) {
            const argsText = typeof rawArgs === 'string' ? rawArgs : safeStringify(rawArgs);
            argsPreview = truncateText(argsText, 80);
            metadata.push({ label: 'Args', value: truncateText(argsText, 300) });
          }
          const hasError = firstContent?.is_error === true
            || firstContent?.status === 'error'
            || nestedData?.is_error === true
            || nestedData?.status === 'error'
            || (Array.isArray(contentItems) && contentItems.some((item) => item?.is_error || item?.status === 'error'));
          const resultText = typeof result === 'string' ? result : safeStringify(result);
          if (hasError) {
            tone = 'error';
            icon = 'error';
            metadata.push({ label: 'Status', value: 'Error' });
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
          icon = 'success';
          const status = nestedData.outcome || nestedData.status || data.status;
          if (status) {
            metadata.push({ label: 'Status', value: status });
            previewMeta.push({ label: 'Status', value: status, icon: 'status' });
          }
          if (nestedData.score != null) metadata.push({ label: 'Score', value: String(nestedData.score) });
          const taskPayload = nestedData.message || nestedData.summary || data.message;
          descriptiveText = taskPayload != null ? (typeof taskPayload === 'string' ? taskPayload : safeStringify(taskPayload)) : safeStringify(nestedData || data);
          previewText = status ? `${status}: ${truncateText(descriptiveText, 160)}` : descriptiveText;
          break;
        }
        default: {
          typeLabel = typeRaw;
          icon = 'info';
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

      // Token usage - show in preview for visibility
      const modelUsage = data.models_usage || nestedData.models_usage;
      let tokenInfo = null;
      if (modelUsage) {
        const promptTokens = modelUsage.prompt_tokens;
        const completionTokens = modelUsage.completion_tokens;
        const totalTokens = modelUsage.total_tokens ?? (promptTokens != null && completionTokens != null ? promptTokens + completionTokens : null);

        if (promptTokens != null) {
          metadata.push({ label: 'Prompt tokens', value: String(promptTokens) });
        }
        if (completionTokens != null) {
          metadata.push({ label: 'Completion tokens', value: String(completionTokens) });
        }
        if (totalTokens != null) {
          metadata.push({ label: 'Total tokens', value: String(totalTokens) });
          tokenInfo = { prompt: promptTokens, completion: completionTokens, total: totalTokens };
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
        icon,
        toolName,
        argsPreview,
        tokenInfo,
        preview,
        detail,
        metadata,
        previewMeta,
        raw: msg.data ?? msg,
      });
    });
    return entries.slice(-MAX_NESTED_HIGHLIGHTS);
  }, [messages, formatTimestamp, truncateText, safeStringify]);

  const virtuosoRef = useRef(null);

  useEffect(() => {
    if (virtuosoRef.current && nestedHighlights.length > 0) {
      virtuosoRef.current.scrollToIndex({
        index: nestedHighlights.length - 1,
        align: 'end',
        behavior: 'auto'
      });
    }
  }, [nestedHighlights]);

  // Helper to get the right icon for the entry type
  const getEntryIcon = (iconType, tone) => {
    const iconSx = { fontSize: 18 };
    switch (iconType) {
      case 'thought':
        return <PsychologyIcon sx={{ ...iconSx, color: 'info.main' }} />;
      case 'tool':
        return <BuildIcon sx={{ ...iconSx, color: 'warning.main' }} />;
      case 'success':
        return <CheckCircleIcon sx={{ ...iconSx, color: 'success.main' }} />;
      case 'error':
        return <ErrorIcon sx={{ ...iconSx, color: 'error.main' }} />;
      default:
        return <InfoIcon sx={{ ...iconSx, color: 'text.secondary' }} />;
    }
  };

  const renderNestedEntry = (index, entry) => {
    const chipColor = ['info', 'success', 'warning', 'error'].includes(entry.tone) ? entry.tone : 'default';
    const hasToolInfo = entry.toolName || entry.argsPreview;
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
              {/* Top row: Type chip, agent, timestamp */}
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                <Box sx={{ display: 'flex', alignItems: 'center', mr: 0.5 }}>
                  {getEntryIcon(entry.icon, entry.tone)}
                </Box>
                <Chip
                  size="small"
                  label={entry.typeLabel}
                  color={chipColor === 'default' ? 'default' : chipColor}
                  variant={chipColor === 'default' ? 'outlined' : 'filled'}
                  sx={{ fontWeight: 500 }}
                />
                <Chip
                  size="small"
                  label={entry.agentName}
                  variant="outlined"
                  sx={{
                    borderColor: (theme) => alpha(theme.palette.primary.main, 0.5),
                    color: 'primary.main',
                  }}
                />
                {entry.role && (
                  <Chip size="small" label={entry.role} variant="outlined" />
                )}
                <Box sx={{ flexGrow: 1 }} />
                {entry.timeLabel && (
                  <Typography variant="caption" color="text.secondary">{entry.timeLabel}</Typography>
                )}
              </Stack>

              {/* Tool info row - shown when there's tool name or args */}
              {hasToolInfo && (
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
                  {entry.toolName && (
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
                  )}
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
                  lineHeight: 1.5,
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
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
                      maxHeight: 200,
                      overflow: 'auto',
                    }}
                  >
                    {entry.detail}
                  </Typography>
                </Box>
              )}
              {(entry.metadata.length > 0 || entry.role) && (
                <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
                  {entry.role && (
                    <Chip size="small" variant="outlined" label={`Role: ${entry.role}`} sx={{ height: 24 }} />
                  )}
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
      {nestedHighlights.length === 0 ? (
        <Typography variant="body2" color="text.secondary">No nested activity captured yet.</Typography>
      ) : (
        <Virtuoso
          ref={virtuosoRef}
          style={{ height: '100%' }}
          data={nestedHighlights}
          itemContent={renderNestedEntry}
          followOutput="smooth"
        />
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
