import React from 'react';
import { Box, IconButton, Tooltip, Typography, Chip, CircularProgress } from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import VolumeOffIcon from '@mui/icons-material/VolumeOff';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import AudioVisualizer from './AudioVisualizer';

/**
 * VoiceSessionControls - Modern, elegant voice conversation controls
 * Displays start/stop, mute/unmute buttons with audio visualization
 */
export default function VoiceSessionControls({
  isRunning,
  isStarting = false,
  isMuted,
  isSpeakerMuted = false,
  onStart,
  onStop,
  onToggleMute,
  onToggleSpeakerMute,
  onForceStop,
  showForceStop = false,
  disabled = false,
  stream = null,
  statusLabel = 'Idle',
  statusColor = 'default',
  ...props
}) {
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
          <>
            <Tooltip title={isStarting ? "Connecting..." : "Start voice session (Ctrl+S)"} arrow>
              <span>
                <IconButton
                  onClick={onStart}
                  disabled={disabled || isStarting}
                  data-tv-focusable="true"
                  aria-label={isStarting ? "Connecting" : "Start voice session"}
                  sx={{
                    width: 56,
                    height: 56,
                    bgcolor: isStarting ? 'warning.main' : 'primary.main',
                    color: 'white',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: isStarting ? 'warning.main' : 'primary.dark',
                      transform: isStarting ? 'none' : 'scale(1.05)',
                    },
                    '&:focus': {
                      outline: '3px solid',
                      outlineColor: 'primary.light',
                      outlineOffset: '4px',
                    },
                    '&[data-tv-focused="true"]': {
                      outline: '4px solid',
                      outlineColor: 'primary.light',
                      outlineOffset: '4px',
                      transform: 'scale(1.1)',
                      boxShadow: '0 0 20px rgba(25, 118, 210, 0.6)',
                    },
                    '&:disabled': {
                      bgcolor: isStarting ? 'warning.main' : 'action.disabledBackground',
                      color: isStarting ? 'white' : undefined,
                    },
                  }}
                >
                  {isStarting ? (
                    <CircularProgress size={28} sx={{ color: 'white' }} />
                  ) : (
                    <PlayArrowIcon sx={{ fontSize: 32 }} />
                  )}
                </IconButton>
              </span>
            </Tooltip>

            {/* Force Stop button - visible when session is active elsewhere */}
            {showForceStop && onForceStop && (
              <Tooltip title="Force stop session for all connected tabs" arrow>
                <IconButton
                  onClick={onForceStop}
                  aria-label="Force stop session"
                  sx={{
                    width: 56,
                    height: 56,
                    bgcolor: 'error.main',
                    color: 'white',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: 'error.dark',
                      transform: 'scale(1.05)',
                    },
                  }}
                >
                  <StopIcon sx={{ fontSize: 28 }} />
                </IconButton>
              </Tooltip>
            )}
          </>
        ) : (
          <Tooltip title="Stop voice session (Ctrl+S)" arrow>
            <span>
              <IconButton
                onClick={onStop}
                disabled={disabled && !isRunning}
                data-tv-focusable="true"
                aria-label="Stop voice session"
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
                  '&:focus': {
                    outline: '3px solid',
                    outlineColor: 'error.light',
                    outlineOffset: '4px',
                  },
                  '&[data-tv-focused="true"]': {
                    outline: '4px solid',
                    outlineColor: 'error.light',
                    outlineOffset: '4px',
                    transform: 'scale(1.1)',
                    boxShadow: '0 0 20px rgba(244, 67, 54, 0.6)',
                  },
                }}
              >
                <StopIcon sx={{ fontSize: 32 }} />
              </IconButton>
            </span>
          </Tooltip>
        )}

        {/* Mute/Unmute Microphone Button */}
        {isRunning && (
          <Tooltip title={isMuted ? 'Unmute microphone (Ctrl+M)' : 'Mute microphone (Ctrl+M)'} arrow>
            <span>
              <IconButton
                onClick={onToggleMute}
                data-tv-focusable="true"
                aria-label={isMuted ? 'Unmute microphone' : 'Mute microphone'}
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
                  '&:focus': {
                    outline: '3px solid',
                    outlineColor: isMuted ? 'warning.light' : 'primary.main',
                    outlineOffset: '4px',
                  },
                  '&[data-tv-focused="true"]': {
                    outline: '4px solid',
                    outlineColor: isMuted ? 'warning.light' : 'primary.main',
                    outlineOffset: '4px',
                    transform: 'scale(1.1)',
                    boxShadow: isMuted
                      ? '0 0 20px rgba(237, 108, 2, 0.6)'
                      : '0 0 20px rgba(25, 118, 210, 0.6)',
                  },
                }}
              >
                {isMuted ? <MicOffIcon sx={{ fontSize: 28 }} /> : <MicIcon sx={{ fontSize: 28 }} />}
              </IconButton>
            </span>
          </Tooltip>
        )}

        {/* Mute/Unmute Speaker Button */}
        {isRunning && onToggleSpeakerMute && (
          <Tooltip title={isSpeakerMuted ? 'Unmute speaker (Ctrl+K)' : 'Mute speaker (Ctrl+K)'} arrow>
            <span>
              <IconButton
                onClick={onToggleSpeakerMute}
                data-tv-focusable="true"
                aria-label={isSpeakerMuted ? 'Unmute speaker' : 'Mute speaker'}
                sx={{
                  width: 56,
                  height: 56,
                  bgcolor: isSpeakerMuted ? 'warning.main' : 'rgba(0, 0, 0, 0.1)',
                  color: isSpeakerMuted ? 'white' : 'text.primary',
                  border: '2px solid',
                  borderColor: isSpeakerMuted ? 'warning.dark' : 'divider',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    bgcolor: isSpeakerMuted ? 'warning.dark' : 'rgba(0, 0, 0, 0.15)',
                    transform: 'scale(1.05)',
                  },
                  '&:focus': {
                    outline: '3px solid',
                    outlineColor: isSpeakerMuted ? 'warning.light' : 'primary.main',
                    outlineOffset: '4px',
                  },
                  '&[data-tv-focused="true"]': {
                    outline: '4px solid',
                    outlineColor: isSpeakerMuted ? 'warning.light' : 'primary.main',
                    outlineOffset: '4px',
                    transform: 'scale(1.1)',
                    boxShadow: isSpeakerMuted
                      ? '0 0 20px rgba(237, 108, 2, 0.6)'
                      : '0 0 20px rgba(25, 118, 210, 0.6)',
                  },
                }}
              >
                {isSpeakerMuted ? <VolumeOffIcon sx={{ fontSize: 28 }} /> : <VolumeUpIcon sx={{ fontSize: 28 }} />}
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
