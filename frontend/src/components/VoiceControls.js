import React from 'react';
import { Box, Button, TextField, Stack, Chip, Typography } from '@mui/material';

export default function VoiceControls({
  isRunning,
  remoteSessionActive,
  conversationLoading,
  conversationError,
  transcript,
  setTranscript,
  onSendToVoice,
  onSendToNested,
  nestedWsRef,
  formatTimestamp,
  conversation,
}) {
  const sessionLocked = isRunning || remoteSessionActive;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Status bar */}
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
        <Chip
          label={isRunning ? 'Voice connected' : remoteSessionActive ? 'Voice active elsewhere' : 'Voice idle'}
          color={isRunning ? 'success' : remoteSessionActive ? 'warning' : 'default'}
          size="small"
        />
        <Chip
          label={conversationError ? 'History error' : conversationLoading ? 'Syncing history' : 'History synced'}
          color={conversationError ? 'error' : conversationLoading ? 'warning' : 'info'}
          size="small"
        />
        {conversation?.updated_at && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
            Updated {formatTimestamp(conversation.updated_at)}
          </Typography>
        )}
      </Box>

      {/* Message input and send buttons */}
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
        <TextField
          label="Message"
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="Type a message to send to Voice or Nested"
          multiline
          minRows={3}
          maxRows={8}
          sx={{ flexGrow: 1 }}
          disabled={!isRunning}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (transcript.trim()) {
                onSendToVoice();
              }
            }
          }}
        />
        <Stack direction="column" spacing={1} sx={{ minWidth: '180px' }}>
          <Button
            variant="contained"
            color="success"
            onClick={onSendToVoice}
            disabled={!isRunning || !transcript.trim()}
            fullWidth
          >
            Send to Voice
          </Button>
          <Button
            variant="contained"
            color="secondary"
            onClick={onSendToNested}
            disabled={!isRunning || !transcript.trim() || !nestedWsRef.current}
            fullWidth
          >
            Send to Nested
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}
