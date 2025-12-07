import React from 'react';
import { Box, Typography } from '@mui/material';
import ClaudeCodeInsights from './ClaudeCodeInsights';

/**
 * Claude Code panel with empty state
 * Filters messages to only show Claude Code events
 */
const ClaudeCodePanel = ({ messages, formatTimestamp, truncateText, safeStringify }) => {
  // Filter messages to only show Claude Code events
  const claudeCodeMessages = React.useMemo(() => {
    return messages.filter(msg => msg.source === 'claude_code');
  }, [messages]);

  if (claudeCodeMessages.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Start a voice session to see Claude Code activity
        </Typography>
      </Box>
    );
  }

  return (
    <ClaudeCodeInsights
      messages={claudeCodeMessages}
      formatTimestamp={formatTimestamp}
      truncateText={truncateText}
      safeStringify={safeStringify}
    />
  );
};

export default ClaudeCodePanel;
