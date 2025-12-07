import React from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  Chip,
  Alert,
} from '@mui/material';
import VoiceSessionControls from './VoiceSessionControls';
import ConversationHistory from './ConversationHistory';

/**
 * Voice control panel with session controls, message input, and conversation history
 */
const VoiceControlPanel = ({
  // Session state
  isRunning,
  isStarting,
  isMuted,
  isSpeakerMuted,
  sessionLocked,
  remoteSessionActive,
  noMicrophoneMode,

  // Config
  voiceConfig,
  setConfigEditorOpen,

  // Errors
  conversationError,
  error,

  // Message input
  transcript,
  setTranscript,
  onSendToVoice,
  onSendToNested,
  onSendToClaude,
  nestedWsConnected,
  claudeCodeWsConnected,

  // Session controls
  onStart,
  onStop,
  onForceStop,
  onToggleMute,
  onToggleSpeakerMute,

  // Conversation
  conversationLoading,
  messages,
  formatTimestamp,

  // Other
  micStream,
  isMobile,
}) => {
  return (
    <>
      {/* Header with controls */}
      <Box sx={{ pt: isMobile ? 2 : 2, pb: 1, px: 2, borderBottom: 1, borderColor: 'divider', flexShrink: 0 }}>
        {/* Configuration Button */}
        <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
            Agent: {voiceConfig.agentName} | Voice: {voiceConfig.voice}
          </Typography>
          <Button
            size="small"
            variant="outlined"
            onClick={() => setConfigEditorOpen(true)}
            disabled={isRunning}
          >
            Configure
          </Button>
        </Box>

        {/* Modern Voice Session Controls with Force Stop */}
        <VoiceSessionControls
          isRunning={isRunning}
          isStarting={isStarting}
          isMuted={isMuted}
          isSpeakerMuted={isSpeakerMuted}
          onStart={onStart}
          onStop={onStop}
          onToggleMute={onToggleMute}
          onToggleSpeakerMute={onToggleSpeakerMute}
          onForceStop={onForceStop}
          showForceStop={!isRunning && !isStarting && remoteSessionActive && !conversationError}
          disabled={isStarting || conversationLoading || Boolean(conversationError)}
          stream={micStream}
          statusLabel={isStarting ? 'Connecting...' : isRunning ? 'Connected' : remoteSessionActive ? 'Active (joinable)' : 'Idle'}
          statusColor={isStarting ? 'warning' : isRunning ? 'success' : remoteSessionActive ? 'info' : 'default'}
          style={{ mb: 3 }}
        />

        {!isRunning && remoteSessionActive && !conversationError && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Voice session is active. Click Start to join from this tab.
          </Alert>
        )}

        {isRunning && noMicrophoneMode && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            No microphone detected. Connect with mobile-voice page.
          </Alert>
        )}

        {conversationError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {conversationError}
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Message input */}
        <Box sx={{ display: 'flex', gap: 1, flexDirection: 'column' }}>
          <TextField
            label="Message"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Type a message"
            multiline
            minRows={2}
            maxRows={4}
            fullWidth
            disabled={!isRunning}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && transcript.trim()) {
                e.preventDefault();
                onSendToVoice();
              }
            }}
          />
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
            <Chip
              label={isRunning ? 'Connected' : remoteSessionActive ? 'Active (joinable)' : 'Idle'}
              color={isRunning ? 'success' : remoteSessionActive ? 'info' : 'default'}
              size="small"
            />
            <Box sx={{ flexGrow: 1 }} />
            <Button
              variant="contained"
              color="success"
              onClick={onSendToVoice}
              disabled={!isRunning || !transcript.trim()}
              size="small"
            >
              Voice
            </Button>
            <Button
              variant="contained"
              color="secondary"
              onClick={onSendToNested}
              disabled={!isRunning || !transcript.trim() || !nestedWsConnected}
              size="small"
            >
              Nested
            </Button>
            <Button
              variant="contained"
              color="info"
              onClick={onSendToClaude}
              disabled={!isRunning || !transcript.trim() || !claudeCodeWsConnected}
              size="small"
            >
              Claude
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Conversation History */}
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', p: 0 }}>
        <Box sx={{ flexGrow: 1, overflowY: 'auto', height: "100%" }}>
          <ConversationHistory
            messages={messages}
            conversationLoading={conversationLoading}
            isRunning={isRunning}
            formatTimestamp={formatTimestamp}
          />
        </Box>
      </Box>
    </>
  );
};

export default VoiceControlPanel;
