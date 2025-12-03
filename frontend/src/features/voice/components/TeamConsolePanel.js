import React from 'react';
import { Box, Typography } from '@mui/material';
import RunConsole from '../../agents/components/RunConsole';

/**
 * Team console panel with empty state
 */
const TeamConsolePanel = ({ sharedSocket, agentName = 'MainConversation' }) => {
  if (!sharedSocket) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Start a voice session to see nested team console
        </Typography>
      </Box>
    );
  }

  return (
    <RunConsole
      nested
      agentName={agentName}
      sharedSocket={sharedSocket}
      readOnlyControls
    />
  );
};

export default TeamConsolePanel;
