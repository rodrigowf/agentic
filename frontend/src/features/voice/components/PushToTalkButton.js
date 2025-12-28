import React from 'react';
import { Box, IconButton, Typography, CircularProgress } from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import AudioVisualizer from './AudioVisualizer';

/**
 * Push-to-talk button for disconnected voice mode.
 * Press and hold to record, release to send.
 */
export default function PushToTalkButton({
  isRecording,
  isProcessing,
  isSending,
  onPressStart,
  onPressEnd,
  disabled,
  stream
}) {
  const handleMouseDown = (e) => {
    e.preventDefault();
    if (!disabled && !isProcessing && !isSending) {
      onPressStart?.();
    }
  };

  const handleMouseUp = (e) => {
    e.preventDefault();
    if (isRecording) {
      onPressEnd?.();
    }
  };

  const handleTouchStart = (e) => {
    e.preventDefault();
    if (!disabled && !isProcessing && !isSending) {
      onPressStart?.();
    }
  };

  const handleTouchEnd = (e) => {
    e.preventDefault();
    if (isRecording) {
      onPressEnd?.();
    }
  };

  // Prevent context menu on long press (mobile)
  const handleContextMenu = (e) => {
    e.preventDefault();
  };

  const getStatusText = () => {
    if (isRecording) return 'Recording... Release to send';
    if (isProcessing) return 'Processing audio...';
    if (isSending) return 'Sending to assistant...';
    return 'Press and hold to speak';
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2,
        p: 3,
        borderRadius: 2,
        bgcolor: (theme) =>
          theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Typography
        variant="subtitle2"
        color="text.secondary"
        sx={{ textAlign: 'center', minHeight: 24 }}
      >
        {getStatusText()}
      </Typography>

      <IconButton
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onContextMenu={handleContextMenu}
        disabled={disabled || isProcessing || isSending}
        aria-label={isRecording ? 'Release to send' : 'Press and hold to speak'}
        sx={{
          width: 80,
          height: 80,
          bgcolor: isRecording ? 'error.main' : 'primary.main',
          color: 'white',
          transition: 'all 0.2s ease',
          transform: isRecording ? 'scale(1.1)' : 'scale(1)',
          animation: isRecording ? 'pulse 1s ease-in-out infinite' : 'none',
          '@keyframes pulse': {
            '0%, 100%': { boxShadow: '0 0 0 0 rgba(244, 67, 54, 0.7)' },
            '50%': { boxShadow: '0 0 0 12px rgba(244, 67, 54, 0)' },
          },
          '&:hover': {
            bgcolor: isRecording ? 'error.dark' : 'primary.dark',
          },
          '&:disabled': {
            bgcolor: 'action.disabledBackground',
            color: 'action.disabled',
          },
          // Touch feedback
          WebkitTapHighlightColor: 'transparent',
          touchAction: 'none',
          userSelect: 'none',
        }}
      >
        {isProcessing || isSending ? (
          <CircularProgress size={32} sx={{ color: 'white' }} />
        ) : (
          <MicIcon sx={{ fontSize: 40 }} />
        )}
      </IconButton>

      {/* Audio visualizer when recording */}
      {isRecording && stream && (
        <Box sx={{ mt: 1, width: '100%', maxWidth: 200 }}>
          <AudioVisualizer stream={stream} isActive={true} isMuted={false} />
        </Box>
      )}

      {/* Helper text */}
      <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
        Disconnected mode - uses Chat API
      </Typography>
    </Box>
  );
}
