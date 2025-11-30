import React, { useState, useMemo, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Link as RouterLink, Navigate } from 'react-router-dom';
import {
  Container,
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  ThemeProvider,
  createTheme,
  CssBaseline,
  useMediaQuery,
} from '@mui/material';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';

import AgentEditor from './features/agents/components/AgentEditor';
import RunConsole from './features/agents/components/RunConsole';
import AgentDashboard from './features/agents/pages/AgentDashboard';
import ToolsDashboard from './features/tools/pages/ToolsDashboard';
import VoiceDashboard from './features/voice/pages/VoiceDashboard';
import MobileVoice from './features/voice/pages/MobileVoice';
import DebugNetwork from './features/voice/pages/DebugNetwork';

const ColorModeContext = createContext({ toggleColorMode: () => {} });

const lightPalette = {
  primary: {
    main: '#3f51b5',
  },
  secondary: {
    main: '#f50057',
  },
  background: {
    default: '#f5f7fa',
    paper: '#ffffff',
    subtile: '#e8ecf1',
  },
};

const darkPalette = {
  primary: {
    main: '#90caf9',
  },
  secondary: {
    main: '#f48fb1',
  },
  background: {
    default: '#0d0d0d',
    paper: '#1a1a1a',
    subtile: '#242424',
  },
  text: {
    primary: '#e8e8e8',
    secondary: '#a0a0a0',
  },
  divider: '#2d2d2d',
};

export default function App() {
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
  const initialMode = localStorage.getItem('themeMode') || (prefersDarkMode ? 'dark' : 'light');
  const [mode, setMode] = useState(initialMode);

  // Debug logging for TV WebView
  React.useEffect(() => {
    console.log('[App] Mounted');
    console.log('[App] PUBLIC_URL:', process.env.PUBLIC_URL);
    console.log('[App] Location:', window.location.href);
    console.log('[App] Pathname:', window.location.pathname);
  }, []);

  React.useEffect(() => {
    localStorage.setItem('themeMode', mode);
  }, [mode]);

  const colorMode = useMemo(
    () => ({
      toggleColorMode: () => {
        setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
      },
    }),
    [],
  );

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          ...(mode === 'light' ? lightPalette : darkPalette),
        },
        typography: {
          h5: {
            fontWeight: 500,
          },
          h6: {
            fontWeight: 500,
          },
        },
        shape: {
          borderRadius: 12,
        },
        ...(mode === 'dark' && {
          shadows: [
            'none',
            '0px 2px 4px rgba(0,0,0,0.4)',
            '0px 4px 8px rgba(0,0,0,0.4)',
            '0px 8px 16px rgba(0,0,0,0.4)',
            '0px 12px 24px rgba(0,0,0,0.4)',
            ...Array(20).fill('0px 16px 32px rgba(0,0,0,0.4)')
          ]
        }),
        components: {
          MuiAppBar: {
            styleOverrides: {
              root: ({ theme }) => ({
                backgroundColor: theme.palette.mode === 'dark' ? theme.palette.grey[900] : theme.palette.primary.main,
                boxShadow: 'none',
                borderBottom: `1px solid ${theme.palette.divider}`,
              }),
            },
          },
          MuiPaper: {
            defaultProps: {
              elevation: 0,
              variant: 'outlined',
            },
            styleOverrides: {
              root: ({ theme }) => ({
                transition: 'background-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out, border-color 0.2s ease-in-out',
                backgroundColor: theme.palette.background.paper,
                backdropFilter: 'blur(10px)',
              }),
              outlined: ({ theme }) => ({
                borderColor: theme.palette.divider,
                borderWidth: '1px',
              }),
            },
          },
          MuiButton: {
            defaultProps: {
              disableElevation: true,
            },
            styleOverrides: {
              root: {
                textTransform: 'none',
              },
              contained: ({ theme }) => ({
                fontWeight: 500,
              }),
            },
          },
          MuiTableHead: {
            styleOverrides: {
              root: ({ theme }) => ({
                backgroundColor: theme.palette.mode === 'dark' ? theme.palette.grey[800] : theme.palette.grey[100],
                '& .MuiTableCell-root': {
                  fontWeight: 600,
                },
              }),
            },
          },
          MuiTableCell: {
            styleOverrides: {
              root: ({ theme }) => ({
                borderBottom: `1px solid ${theme.palette.divider}`,
              }),
            },
          },
          MuiChip: {
            styleOverrides: {
              root: ({ theme }) => ({
                borderRadius: theme.shape.borderRadius / 2,
                fontWeight: 500,
              }),
            },
          },
          MuiTextField: {
            defaultProps: {
              variant: 'outlined',
              size: 'small',
            },
            styleOverrides: {
              root: ({ theme }) => ({
                '& .MuiOutlinedInput-root': {
                  backgroundColor: theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.05)'
                    : 'rgba(0, 0, 0, 0.02)',
                  transition: 'all 0.2s ease-in-out',
                  '& fieldset': {
                    borderColor: theme.palette.mode === 'dark'
                      ? 'rgba(255, 255, 255, 0.1)'
                      : 'rgba(0, 0, 0, 0.12)',
                    borderWidth: '1px',
                  },
                  '&:hover': {
                    backgroundColor: theme.palette.mode === 'dark'
                      ? 'rgba(255, 255, 255, 0.08)'
                      : 'rgba(0, 0, 0, 0.04)',
                    '& fieldset': {
                      borderColor: theme.palette.mode === 'dark'
                        ? 'rgba(255, 255, 255, 0.2)'
                        : 'rgba(0, 0, 0, 0.23)',
                    },
                  },
                  '&.Mui-focused': {
                    backgroundColor: theme.palette.mode === 'dark'
                      ? 'rgba(255, 255, 255, 0.09)'
                      : 'rgba(0, 0, 0, 0.05)',
                    '& fieldset': {
                      borderColor: theme.palette.primary.main,
                      borderWidth: '2px',
                    },
                  },
                  '&.Mui-disabled': {
                    backgroundColor: theme.palette.mode === 'dark'
                      ? 'rgba(255, 255, 255, 0.02)'
                      : 'rgba(0, 0, 0, 0.01)',
                  },
                },
                '& .MuiInputLabel-root': {
                  color: theme.palette.text.secondary,
                  '&.Mui-focused': {
                    color: theme.palette.primary.main,
                  },
                },
              }),
            },
          },
          MuiSelect: {
            defaultProps: {
              variant: 'outlined',
              size: 'small',
            },
            styleOverrides: {
              root: ({ theme }) => ({
                backgroundColor: theme.palette.mode === 'dark'
                  ? 'rgba(255, 255, 255, 0.05)'
                  : 'rgba(0, 0, 0, 0.02)',
                transition: 'all 0.2s ease-in-out',
                '& fieldset': {
                  borderColor: theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.1)'
                    : 'rgba(0, 0, 0, 0.12)',
                  borderWidth: '1px',
                },
                '&:hover': {
                  backgroundColor: theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.08)'
                    : 'rgba(0, 0, 0, 0.04)',
                  '& fieldset': {
                    borderColor: theme.palette.mode === 'dark'
                      ? 'rgba(255, 255, 255, 0.2)'
                      : 'rgba(0, 0, 0, 0.23)',
                  },
                },
                '&.Mui-focused': {
                  backgroundColor: theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.09)'
                    : 'rgba(0, 0, 0, 0.05)',
                  '& fieldset': {
                    borderColor: theme.palette.primary.main,
                    borderWidth: '2px',
                  },
                },
              }),
            },
          },
          MuiOutlinedInput: {
            styleOverrides: {
              root: ({ theme }) => ({
                backgroundColor: theme.palette.mode === 'dark'
                  ? 'rgba(255, 255, 255, 0.05)'
                  : 'rgba(0, 0, 0, 0.02)',
                transition: 'all 0.2s ease-in-out',
                '& fieldset': {
                  borderColor: theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.1)'
                    : 'rgba(0, 0, 0, 0.12)',
                  borderWidth: '1px',
                },
                '&:hover': {
                  backgroundColor: theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.08)'
                    : 'rgba(0, 0, 0, 0.04)',
                  '& fieldset': {
                    borderColor: theme.palette.mode === 'dark'
                      ? 'rgba(255, 255, 255, 0.2)'
                      : 'rgba(0, 0, 0, 0.23)',
                  },
                },
                '&.Mui-focused': {
                  backgroundColor: theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.09)'
                    : 'rgba(0, 0, 0, 0.05)',
                  '& fieldset': {
                    borderColor: theme.palette.primary.main,
                    borderWidth: '2px',
                  },
                },
                '&.Mui-disabled': {
                  backgroundColor: theme.palette.mode === 'dark'
                    ? 'rgba(255, 255, 255, 0.02)'
                    : 'rgba(0, 0, 0, 0.01)',
                },
              }),
              notchedOutline: {
                transition: 'all 0.2s ease-in-out',
              },
            },
          },
          MuiInputLabel: {
            styleOverrides: {
              root: ({ theme }) => ({
                color: theme.palette.text.secondary,
                '&.Mui-focused': {
                  color: theme.palette.primary.main,
                },
              }),
            },
          },
        },
      }),
    [mode],
  );

  return (
    <ColorModeContext.Provider value={colorMode}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <style>
          {`
            /* Global scrollbar styling */
            * {
              scrollbar-width: thin;
              scrollbar-color: ${mode === 'dark' ? '#3a3a3a #1a1a1a' : '#c0c0c0 #ffffff'};
            }

            *::-webkit-scrollbar {
              width: 12px;
              height: 12px;
            }

            *::-webkit-scrollbar-track {
              background: ${mode === 'dark' ? '#1a1a1a' : '#ffffff'};
            }

            *::-webkit-scrollbar-thumb {
              background-color: ${mode === 'dark' ? '#3a3a3a' : '#c0c0c0'};
              border-radius: 6px;
              border: 2px solid ${mode === 'dark' ? '#1a1a1a' : '#ffffff'};
            }

            *::-webkit-scrollbar-thumb:hover {
              background-color: ${mode === 'dark' ? '#4a4a4a' : '#a0a0a0'};
            }
          `}
        </style>
        <Router basename={process.env.PUBLIC_URL || ''}>
          <Routes>
            {/* Debug route */}
            <Route path="/debug-network" element={<DebugNetwork />} />

            {/* Mobile Voice routes - full screen, no AppBar, no Container (WebRTC enabled) */}
            <Route path="/mobile-voice" element={<MobileVoice />} />
            <Route path="/mobile-voice/:conversationId" element={<MobileVoice />} />

            {/* Legacy WebRTC routes - redirect to main mobile-voice */}
            <Route path="/mobile-voice-webrtc" element={<MobileVoice />} />
            <Route path="/mobile-voice-webrtc/:conversationId" element={<MobileVoice />} />

            {/* Regular routes with AppBar and Container */}
            <Route
              path="*"
              element={
                <>
                  <AppBar position="static">
                    <Toolbar>
                      <Typography variant="h6" component={RouterLink} to="/" sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit', pt: 1 }}>
                        Agentic
                      </Typography>
                      <Button color="inherit" component={RouterLink} to="/">Agents</Button>
                      <Button color="inherit" component={RouterLink} to="/tools">Tools</Button>
                      <Button color="inherit" component={RouterLink} to="/voice">Voice</Button>
                      <IconButton sx={{ ml: 1 }} onClick={colorMode.toggleColorMode} color="inherit">
                        {theme.palette.mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
                      </IconButton>
                    </Toolbar>
                  </AppBar>
                  <Box
                    component="main"
                    sx={{
                      flexGrow: 1,
                      bgcolor: 'background.default',
                      minHeight: 'calc(100vh - 64px)',
                      height: 'calc(100vh - 64px)',  // Explicit height for WebView
                      overflow: 'auto',              // Enable scrolling
                      p: { xs: 2, sm: 3 },
                    }}
                  >
                    <Container maxWidth="xl">
                      <Routes>
                        <Route path="/" element={<AgentDashboard />} />
                        <Route path="/agents/new" element={<AgentEditor />} />
                        <Route path="/agents/:name" element={<AgentDashboard />} />
                        <Route path="/agents/:name/edit" element={<AgentEditor nested={true} />} />
                        <Route path="/runs/:name" element={<RunConsole />} />
                        <Route path="/tools" element={<ToolsDashboard />} />
                        <Route path="/tools/:filename" element={<ToolsDashboard />} />
                        <Route path="/voice" element={<VoiceDashboard />} />
                        <Route path="/voice/:conversationId" element={<VoiceDashboard />} />
                        <Route path="*" element={<Navigate to="/" replace />} />
                      </Routes>
                    </Container>
                  </Box>
                </>
              }
            />
          </Routes>
        </Router>
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}

export const useColorMode = () => useContext(ColorModeContext);