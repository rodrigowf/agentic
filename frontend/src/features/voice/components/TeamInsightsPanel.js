import React from 'react';
import { Box, Typography } from '@mui/material';
import NestedAgentInsights from './NestedAgentInsights';

/**
 * Team insights panel with empty state
 * Filters messages to only show nested team events
 */
const TeamInsightsPanel = ({ messages, formatTimestamp, truncateText, safeStringify }) => {
  // Filter messages to only show nested team events
  const nestedMessages = React.useMemo(() => {
    return messages.filter(msg => msg.source === 'nested' || msg.source === 'nested_agent');
  }, [messages]);

  if (nestedMessages.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Start a voice session to see nested team insights
        </Typography>
      </Box>
    );
  }

  return (
    <NestedAgentInsights
      messages={nestedMessages}
      formatTimestamp={formatTimestamp}
      truncateText={truncateText}
      safeStringify={safeStringify}
    />
  );
};

export default TeamInsightsPanel;
