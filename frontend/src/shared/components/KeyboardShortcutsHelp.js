import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Divider,
} from '@mui/material';
import KeyboardIcon from '@mui/icons-material/Keyboard';
import { KEYBOARD_SHORTCUTS } from '../../hooks/useKeyboardNavigation';

/**
 * Format keyboard shortcut for display
 */
function formatShortcut(shortcut) {
  const parts = [];

  if (shortcut.ctrl) parts.push('Ctrl');
  if (shortcut.alt) parts.push('Alt');
  if (shortcut.shift) parts.push('Shift');
  if (shortcut.meta) parts.push('Cmd');

  // Format the key
  let keyDisplay = shortcut.key;
  if (keyDisplay === 'Escape') keyDisplay = 'Esc';
  parts.push(keyDisplay.toUpperCase());

  return parts;
}

/**
 * Keyboard Shortcuts Help Dialog Component
 */
export default function KeyboardShortcutsHelp({ open, onClose }) {
  // Group shortcuts by category
  const categories = {
    'Navigation': [
      { name: 'AGENTS', ...KEYBOARD_SHORTCUTS.AGENTS },
      { name: 'TOOLS', ...KEYBOARD_SHORTCUTS.TOOLS },
      { name: 'VOICE', ...KEYBOARD_SHORTCUTS.VOICE },
    ],
    'Voice Controls': [
      { name: 'VOICE_START_STOP', ...KEYBOARD_SHORTCUTS.VOICE_START_STOP },
      { name: 'VOICE_MUTE', ...KEYBOARD_SHORTCUTS.VOICE_MUTE },
      { name: 'VOICE_SPEAKER', ...KEYBOARD_SHORTCUTS.VOICE_SPEAKER },
    ],
    'Agent Controls': [
      { name: 'AGENT_RUN', ...KEYBOARD_SHORTCUTS.AGENT_RUN },
      { name: 'AGENT_STOP', ...KEYBOARD_SHORTCUTS.AGENT_STOP },
      { name: 'AGENT_CLEAR', ...KEYBOARD_SHORTCUTS.AGENT_CLEAR },
    ],
    'General': [
      { name: 'SEARCH', ...KEYBOARD_SHORTCUTS.SEARCH },
      { name: 'SAVE', ...KEYBOARD_SHORTCUTS.SAVE },
      { name: 'HELP', ...KEYBOARD_SHORTCUTS.HELP },
      { name: 'ESCAPE', ...KEYBOARD_SHORTCUTS.ESCAPE },
    ],
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          maxHeight: '80vh',
        },
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <KeyboardIcon />
          <Typography variant="h6">Keyboard Shortcuts</Typography>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Use these keyboard shortcuts to navigate and control the application more efficiently.
          </Typography>
        </Box>

        {Object.entries(categories).map(([category, shortcuts], index) => (
          <Box key={category} sx={{ mb: 3 }}>
            <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
              {category}
            </Typography>

            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600, width: '40%' }}>Shortcut</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {shortcuts.map((shortcut) => {
                    const keys = formatShortcut(shortcut);
                    return (
                      <TableRow key={shortcut.name} hover>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            {keys.map((key, idx) => (
                              <React.Fragment key={idx}>
                                <Chip
                                  label={key}
                                  size="small"
                                  sx={{
                                    fontFamily: 'monospace',
                                    fontWeight: 600,
                                    minWidth: '40px',
                                  }}
                                />
                                {idx < keys.length - 1 && (
                                  <Typography
                                    variant="body2"
                                    sx={{ alignSelf: 'center', mx: 0.5 }}
                                  >
                                    +
                                  </Typography>
                                )}
                              </React.Fragment>
                            ))}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">{shortcut.description}</Typography>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>

            {index < Object.keys(categories).length - 1 && (
              <Divider sx={{ mt: 2 }} />
            )}
          </Box>
        ))}

        <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Additional Tips
          </Typography>
          <Typography variant="body2" color="text.secondary" component="ul" sx={{ m: 0, pl: 2 }}>
            <li>Use <strong>Tab</strong> to navigate between interactive elements</li>
            <li>Use <strong>Shift+Tab</strong> to navigate backwards</li>
            <li>Press <strong>Enter</strong> to activate focused buttons</li>
            <li>Press <strong>Space</strong> to toggle checkboxes and switches</li>
            <li>Use <strong>Arrow keys</strong> to navigate within lists and menus</li>
          </Typography>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}
