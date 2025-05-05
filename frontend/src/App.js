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

const lightPalette = {
  primary: {
    main: '#3f51b5',
  },
  secondary: {
    main: '#f50057',
  },
  // background: {
  //   default: '#f4f6f8',
  //   paper: '#ffffff',
  //   subtile: '#e0e0e0',
  // },
};

const darkPalette = {
  primary: {
    main: '#90caf9',
  },
  secondary: {
    main: '#f48fb1',
  },
  background: {
    default: '#121212',
    paper: '#1e1e1e',
    subtile: '#2c2c2c',
  },
  text: {
    primary: '#ffffff',
    secondary: '#b0b0b0',
  },
  divider: '#373737',
};

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
          borderRadius: 8,
        },
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
                transition: 'background-color 0.3s ease-in-out, box-shadow 0.3s ease-in-out',
                backgroundColor: theme.palette.background.paper,
              }),
              outlined: ({ theme }) => ({
                borderColor: theme.palette.divider,
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
          },
          MuiSelect: {
            defaultProps: {
              variant: 'outlined',
              size: 'small',
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
            component="main"
            sx={{
              flexGrow: 1,
              bgcolor: 'background.default',
              minHeight: 'calc(100vh - 64px)',
              p: { xs: 2, sm: 3 },
            }}
          >
            <Container maxWidth="xl">
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