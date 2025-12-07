import React, { useState } from 'react';
import { Box, useTheme, useMediaQuery } from '@mui/material';
import DesktopVoiceLayout from './DesktopVoiceLayout';
import MobileVoiceLayout from './MobileVoiceLayout';

/**
 * Full-featured voice assistant layout
 * Adapts between desktop (2-column) and mobile (tabbed) layouts
 */
const FullVoiceLayout = ({
  // For panels
  messages,
  formatTimestamp,
  truncateText,
  safeStringify,
  sharedTeamWs,
  agentName,

  // For chat
  controlPanelProps,

  // Audio element ref
  audioRef,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  if (isMobile) {
    return (
      <MobileVoiceLayout
        messages={messages}
        formatTimestamp={formatTimestamp}
        truncateText={truncateText}
        safeStringify={safeStringify}
        sharedTeamWs={sharedTeamWs}
        agentName={agentName}
        controlPanelProps={controlPanelProps}
        audioRef={audioRef}
      />
    );
  }

  return (
    <DesktopVoiceLayout
      messages={messages}
      formatTimestamp={formatTimestamp}
      truncateText={truncateText}
      safeStringify={safeStringify}
      sharedTeamWs={sharedTeamWs}
      agentName={agentName}
      controlPanelProps={controlPanelProps}
      audioRef={audioRef}
    />
  );
};

export default FullVoiceLayout;
