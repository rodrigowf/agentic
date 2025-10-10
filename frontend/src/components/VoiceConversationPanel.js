import React from 'react';
import { Box, Button, Alert, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import VoiceControls from './VoiceControls';
import ConversationHistory from './ConversationHistory';

export default function VoiceConversationPanel({
  conversation,
  conversationTitle,
  conversationLoading,
  conversationError,
  isRunning,
  remoteSessionActive,
  error,
  startSession,
  stopSession,
  audioRef,
  transcript,
  setTranscript,
  sendText,
  sendToNested,
  nestedWsRef,
  messages,
  formatTimestamp,
}) {
  const sessionLocked = isRunning || remoteSessionActive;

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box sx={{ p: 3, borderBottom: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <Typography variant="h5" noWrap sx={{ flexGrow: 1 }}>
            {conversationTitle}
          </Typography>
          <Button
            component={RouterLink}
            to="/voice"
            variant="outlined"
            size="small"
          >
            Back to list
          </Button>
        </Box>
        <Typography variant="body2" color="text.secondary">
          Realtime voice with nested team controller
        </Typography>
        {conversation?.id && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            ID: {conversation.id}
          </Typography>
        )}
      </Box>

      {/* Session controls */}
      <Box sx={{ p: 3, borderBottom: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <audio ref={audioRef} autoPlay style={{ display: 'none' }} />
          <Button
            variant="contained"
            onClick={startSession}
            disabled={sessionLocked || conversationLoading || Boolean(conversationError)}
            size="small"
          >
            Start
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={stopSession}
            disabled={!isRunning}
            size="small"
          >
            Stop
          </Button>
        </Box>

        {!isRunning && remoteSessionActive && !conversationError && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Another tab is currently running this voice session. You can monitor live updates here.
          </Alert>
        )}

        {conversationError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {conversationError} —{' '}
            <Button color="inherit" size="small" component={RouterLink} to="/voice">
              Return to list
            </Button>
          </Alert>
        )}

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <VoiceControls
          isRunning={isRunning}
          remoteSessionActive={remoteSessionActive}
          conversationLoading={conversationLoading}
          conversationError={conversationError}
          transcript={transcript}
          setTranscript={setTranscript}
          onSendToVoice={sendText}
          onSendToNested={sendToNested}
          nestedWsRef={nestedWsRef}
          formatTimestamp={formatTimestamp}
          conversation={conversation}
        />
      </Box>

      {/* Conversation History */}
      <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 3 }}>
        <ConversationHistory
          messages={messages}
          conversationLoading={conversationLoading}
          isRunning={isRunning}
          formatTimestamp={formatTimestamp}
        />
      </Box>
    </Box>
  );
}
