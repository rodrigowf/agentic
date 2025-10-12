import React from 'react';
import { Box, IconButton, Tooltip, Typography, Chip } from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import AudioVisualizer from './AudioVisualizer';
import { VoiceSessionControlsProps } from '../../../types';

/**
 * VoiceSessionControls - Modern, elegant voice conversation controls
 * Displays start/stop, mute/unmute buttons with audio visualization
 */
export default function VoiceSessionControls({
  isRunning,
  isMuted,
  onStart,
  onStop,
  onToggleMute,
  disabled = false,
  stream = null,
  statusLabel = 'Idle',
  statusColor = 'default',
  ...props
}: VoiceSessionControlsProps & { stream?: MediaStream | null; [key: string]: any }): JSX.Element {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        p: 2,
        borderRadius: 2,
        bgcolor: (theme) =>
          theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
        border: '1px solid',
        borderColor: 'divider',
        transition: 'all 0.3s ease',
        ...props.style,
      }}
    >
      {/* Primary Control Buttons */}
      <Box sx={{ display: 'flex', gap: 1 }}>
        {!isRunning ? (
          <Tooltip title="Start voice session">
            <span>
              <IconButton
                onClick={onStart}
                disabled={disabled}
                sx={{
                  width: 56,
                  height: 56,
                  bgcolor: 'primary.main',
                  color: 'white',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    bgcolor: 'primary.dark',
                    transform: 'scale(1.05)',
                  },
                  '&:disabled': {
                    bgcolor: 'action.disabledBackground',
                  },
                }}
              >
                <PlayArrowIcon sx={{ fontSize: 32 }} />
              </IconButton>
            </span>
          </Tooltip>
        ) : (
          <Tooltip title="Stop voice session">
            <span>
              <IconButton
                onClick={onStop}
                disabled={disabled && !isRunning}
                sx={{
                  width: 56,
                  height: 56,
                  bgcolor: 'error.main',
                  color: 'white',
                  transition: 'all 0.2s ease',
                  animation: 'pulse 2s ease-in-out infinite',
                  '@keyframes pulse': {
                    '0%, 100%': {
                      boxShadow: '0 0 0 0 rgba(244, 67, 54, 0.7)',
                    },
                    '50%': {
                      boxShadow: '0 0 0 8px rgba(244, 67, 54, 0)',
                    },
                  },
                  '&:hover': {
                    bgcolor: 'error.dark',
                    transform: 'scale(1.05)',
                  },
                }}
              >
                <StopIcon sx={{ fontSize: 32 }} />
              </IconButton>
            </span>
          </Tooltip>
        )}

        {/* Mute/Unmute Button */}
        {isRunning && (
          <Tooltip title={isMuted ? 'Unmute microphone' : 'Mute microphone'}>
            <span>
              <IconButton
                onClick={onToggleMute}
                sx={{
                  width: 56,
                  height: 56,
                  bgcolor: isMuted ? 'warning.main' : 'rgba(0, 0, 0, 0.1)',
                  color: isMuted ? 'white' : 'text.primary',
                  border: '2px solid',
                  borderColor: isMuted ? 'warning.dark' : 'divider',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    bgcolor: isMuted ? 'warning.dark' : 'rgba(0, 0, 0, 0.15)',
                    transform: 'scale(1.05)',
                  },
                }}
              >
                {isMuted ? <MicOffIcon sx={{ fontSize: 28 }} /> : <MicIcon sx={{ fontSize: 28 }} />}
              </IconButton>
            </span>
          </Tooltip>
        )}
      </Box>

      {/* Audio Visualizer */}
      {isRunning && (
        <AudioVisualizer
          stream={stream}
          isActive={isRunning}
          isMuted={isMuted}
        />
      )}

      {/* Status Indicator */}
      <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 0.5 }}>
          <Chip
            label={statusLabel}
            color={statusColor}
            size="medium"
            sx={{
              fontWeight: 500,
              minWidth: '120px',
              transition: 'all 0.3s ease',
            }}
          />
          {isRunning && (
            <Typography
              variant="caption"
              sx={{
                color: isMuted ? 'warning.main' : 'success.main',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
              }}
            >
              <Box
                component="span"
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  bgcolor: isMuted ? 'warning.main' : 'success.main',
                  animation: isMuted ? 'none' : 'blink 1.5s ease-in-out infinite',
                  '@keyframes blink': {
                    '0%, 100%': { opacity: 1 },
                    '50%': { opacity: 0.3 },
                  },
                }}
              />
              {isMuted ? 'Microphone muted' : 'Listening...'}
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  );
}
