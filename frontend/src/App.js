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

import ToolList from './components/ToolList';
import ToolEditor from './components/ToolEditor';
import AgentList from './components/AgentList';
import AgentEditor from './components/AgentEditor';
import RunConsole from './components/RunConsole';

const ColorModeContext = createContext({ toggleColorMode: () => {} });

export default function App() {
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
  const initialMode = localStorage.getItem('themeMode') || (prefersDarkMode ? 'dark' : 'light');
  const [mode, setMode] = useState(initialMode);

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
          primary: {
            main: '#1976d2',
          },
          secondary: {
            main: '#dc004e',
          },
        },
        components: {
          MuiAppBar: {
            styleOverrides: {
              root: ({ theme }) => ({
                backgroundColor: theme.palette.mode === 'dark' ? theme.palette.grey[900] : theme.palette.primary.main,
              }),
            },
          },
          MuiPaper: {
            styleOverrides: {
              root: {
                transition: 'background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out',
              },
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
        <Router>
          <AppBar position="static">
            <Toolbar>
              <Typography variant="h6" component={RouterLink} to="/" sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit' }}>
                AutoGen Dashboard
              </Typography>
              <Button color="inherit" component={RouterLink} to="/">Agents</Button>
              <Button color="inherit" component={RouterLink} to="/tools">Tools</Button>
              <IconButton sx={{ ml: 1 }} onClick={colorMode.toggleColorMode} color="inherit">
                {theme.palette.mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
              </IconButton>
            </Toolbar>
          </AppBar>
          <Box
            sx={{
              bgcolor: 'background.default',
              minHeight: 'calc(100vh - 64px)',
              p: 3,
            }}
          >
            <Container maxWidth="lg">
              <Routes>
                <Route path="/" element={<AgentList />} />
                <Route path="/agents/new" element={<AgentEditor />} />
                <Route path="/agents/:name" element={<AgentEditor />} />
                <Route path="/runs/:name" element={<RunConsole />} />
                <Route path="/tools" element={<ToolList />} />
                <Route path="/tools/new" element={<ToolEditor />} />
                <Route path="/tools/edit/:filename" element={<ToolEditor />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Container>
          </Box>
        </Router>
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}

export const useColorMode = () => useContext(ColorModeContext);