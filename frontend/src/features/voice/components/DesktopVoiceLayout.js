import React, { useState } from 'react';
import { Box, Tabs, Tab } from '@mui/material';
import TeamInsightsPanel from './TeamInsightsPanel';
import TeamConsolePanel from './TeamConsolePanel';
import ClaudeCodePanel from './ClaudeCodePanel';
import VoiceControlPanel from './VoiceControlPanel';

/**
 * Desktop layout - 2-column layout with tabs on left, chat on right
 */
const DesktopVoiceLayout = ({
  // For left panel (tabs)
  messages,
  formatTimestamp,
  truncateText,
  safeStringify,
  agentName,

  // For right panel (chat)
  controlPanelProps,

  // Audio element ref
  audioRef,
}) => {
  const [viewTab, setViewTab] = useState(0);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'row',
        height: '100%',
        overflow: 'hidden',
        outline: 'none',
        position: 'relative',
      }}
    >
      {/* Audio element - must stay mounted at all times for continuous playback */}
      <audio ref={audioRef} autoPlay style={{ display: 'none' }} />

      {/* Left panel (Team Insights/Console/Claude Code) */}
      <Box
        sx={{
          flexGrow: 1,
          height: '100%',
          bgcolor: 'background.paper',
          borderRight: 1,
          borderColor: 'divider',
          overflowY: 'auto',
        }}
      >
        {/* Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs
            value={viewTab}
            onChange={(_, newValue) => setViewTab(newValue)}
            sx={{ px: 2, pt: 2 }}
          >
            <Tab label="Team Insights" />
            <Tab label="Team Console" />
            <Tab label="Claude Code" />
          </Tabs>
        </Box>

        {/* Tab content */}
        {viewTab === 0 && (
          <Box sx={{ height: 'calc(100% - 128px)', overflowY: 'auto', p: 2 }}>
            <TeamInsightsPanel
              messages={messages}
              formatTimestamp={formatTimestamp}
              truncateText={truncateText}
              safeStringify={safeStringify}
            />
          </Box>
        )}

        {viewTab === 1 && (
          <Box sx={{ height: 'calc(100% - 128px)' }}>
            <TeamConsolePanel agentName={agentName} isRunning={controlPanelProps.isRunning} />
          </Box>
        )}

        {viewTab === 2 && (
          <Box sx={{ height: 'calc(100% - 128px)', overflowY: 'auto', p: 2 }}>
            <ClaudeCodePanel
              messages={messages}
              formatTimestamp={formatTimestamp}
              truncateText={truncateText}
              safeStringify={safeStringify}
            />
          </Box>
        )}
      </Box>

      {/* Right Panel - Chat */}
      <Box
        sx={{
          width: '35%',
          height: '100%',
          bgcolor: (theme) =>
            theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.02)',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
          overflow: 'hidden',
        }}
      >
        <VoiceControlPanel {...controlPanelProps} isMobile={false} />
      </Box>
    </Box>
  );
};

export default DesktopVoiceLayout;
