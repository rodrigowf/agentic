import React, { useState } from 'react';
import { Box, Tabs, Tab } from '@mui/material';
import TeamInsightsPanel from './TeamInsightsPanel';
import TeamConsolePanel from './TeamConsolePanel';
import ClaudeCodePanel from './ClaudeCodePanel';
import VoiceControlPanel from './VoiceControlPanel';

/**
 * Mobile layout - Tabbed layout with all panels as tabs
 */
const MobileVoiceLayout = ({
  // For panels
  messages,
  formatTimestamp,
  truncateText,
  safeStringify,
  sharedNestedWs,
  agentName,

  // For chat
  controlPanelProps,

  // Audio element ref
  audioRef,
}) => {
  const [mainTab, setMainTab] = useState(3); // 0 = Team Insights, 1 = Team Console, 2 = Claude Code, 3 = Chat

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        flexGrow: 1,
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Audio element - must stay mounted at all times for continuous playback */}
      <audio ref={audioRef} autoPlay style={{ display: 'none' }} />

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs
          value={mainTab}
          onChange={(_, newValue) => setMainTab(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Team Insights" />
          <Tab label="Team Console" />
          <Tab label="Claude Code" />
          <Tab label="Chat" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box sx={{ flexGrow: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {mainTab === 0 && (
          <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2 }}>
            <TeamInsightsPanel
              messages={messages}
              formatTimestamp={formatTimestamp}
              truncateText={truncateText}
              safeStringify={safeStringify}
            />
          </Box>
        )}

        {mainTab === 1 && (
          <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
            <TeamConsolePanel sharedSocket={sharedTeamWs} agentName={agentName} />
          </Box>
        )}

        {mainTab === 2 && (
          <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2 }}>
            <ClaudeCodePanel
              messages={messages}
              formatTimestamp={formatTimestamp}
              truncateText={truncateText}
              safeStringify={safeStringify}
            />
          </Box>
        )}

        {mainTab === 3 && (
          <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <VoiceControlPanel {...controlPanelProps} isMobile={true} />
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default MobileVoiceLayout;
