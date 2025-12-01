import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link as RouterLink, useNavigate } from 'react-router-dom';
import { Box, List, ListItem, ListItemButton, ListItemText, Typography, Divider, Drawer, IconButton, useTheme, useMediaQuery, Tabs, Tab } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import AgentEditor from '../components/AgentEditor';
import RunConsole from '../components/RunConsole';
import api from '../../../api';

export default function AgentDashboard() {
  const { name } = useParams();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [agents, setAgents] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState(0); // 0 = Agent Editor, 1 = Run Console
  const listRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.getAgents()
      .then(res => {
        setAgents(res.data);
        // Set initial selected index based on current agent
        const currentIndex = res.data.findIndex(agent => agent.name === name);
        if (currentIndex >= 0) {
          setSelectedIndex(currentIndex);
        }
      })
      .catch(err => console.error("Error fetching agents:", err));
  }, [name]);

  // Keyboard navigation for agent list
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!agents.length) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => {
            const newIndex = Math.min(prev + 1, agents.length - 1);
            return newIndex;
          });
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => {
            const newIndex = Math.max(prev - 1, 0);
            return newIndex;
          });
          break;
        case 'Enter':
          e.preventDefault();
          if (selectedIndex >= 0 && agents[selectedIndex]) {
            navigate(`/agents/${agents[selectedIndex].name}`);
          }
          break;
        default:
          break;
      }
    };

    const listElement = listRef.current;
    if (listElement) {
      listElement.addEventListener('keydown', handleKeyDown);
      return () => {
        listElement.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [agents, selectedIndex, navigate]);

  // Extract agent list content for reuse in drawer
  const AgentListContent = (
    <>
      <Box sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Agents
        </Typography>
        {!isMobile && (
          <Typography variant="caption" color="text.secondary">
            Use ↑↓ arrows to navigate, Enter to select
          </Typography>
        )}
      </Box>
      <Divider />
      <List disablePadding>
          {agents.map((agent, index) => (
            <ListItem key={agent.name} disablePadding>
              <ListItemButton
                component={RouterLink}
                to={`/agents/${agent.name}`}
                selected={agent.name === name}
                aria-label={`${agent.name} - ${agent.agent_type}`}
                aria-current={agent.name === name ? 'page' : undefined}
                onMouseEnter={() => setSelectedIndex(index)}
                sx={{
                  '&.Mui-selected': {
                    bgcolor: theme => theme.palette.mode === 'dark'
                      ? 'rgba(144, 202, 249, 0.16)'
                      : 'rgba(63, 81, 181, 0.08)',
                    borderLeft: 3,
                    borderColor: 'primary.main',
                  },
                  ...(selectedIndex === index && {
                    outline: theme => `2px solid ${theme.palette.primary.main}`,
                    outlineOffset: '-2px',
                  }),
                }}
              >
                <ListItemText
                  primary={agent.name}
                  secondary={agent.agent_type}
                  primaryTypographyProps={{
                    fontSize: '0.9rem',
                    fontWeight: agent.name === name ? 600 : 400
                  }}
                  secondaryTypographyProps={{
                    fontSize: '0.75rem'
                  }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </>
    );

  return (
    <Box sx={{
      display: 'flex',
      height: 'calc(100vh - 64px)',
      width: '100%',
      position: 'fixed',
      left: 0,
      top: 64,
      overflow: 'hidden',
      bgcolor: 'background.default',
    }}>
      {/* Mobile: Hamburger menu button - always show */}
      {isMobile && (
        <Box sx={{
          position: 'absolute',
          top: 8,
          left: 8,
          zIndex: 1201
        }}>
          <IconButton
            onClick={() => setDrawerOpen(true)}
            sx={{
              bgcolor: 'background.paper',
              boxShadow: 2,
              '&:hover': { bgcolor: 'action.hover' }
            }}
          >
            <MenuIcon />
          </IconButton>
        </Box>
      )}

      {/* Mobile: Drawer for agent list */}
      {isMobile && (
        <Drawer
          anchor="left"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          sx={{
            '& .MuiDrawer-paper': {
              width: '85%',
              maxWidth: 350,
              bgcolor: theme => theme.palette.mode === 'dark'
                ? 'rgba(255, 255, 255, 0.03)'
                : 'rgba(0, 0, 0, 0.02)',
            },
          }}
        >
          {AgentListContent}
        </Drawer>
      )}

      {/* Desktop: Left Panel - Agents List */}
      {!isMobile && (
        <Box
          ref={listRef}
          tabIndex={0}
          role="navigation"
          aria-label="Agents list"
          sx={{
            width: '20%',
            minWidth: '280px',
            maxWidth: '400px',
            height: '100%',
            bgcolor: theme => theme.palette.mode === 'dark'
              ? 'rgba(255, 255, 255, 0.03)'
              : 'rgba(0, 0, 0, 0.02)',
            borderRight: 1,
            borderColor: 'divider',
            overflowY: 'auto',
            flexShrink: 0,
            outline: 'none',
            '&:focus-within': {
              boxShadow: theme => `inset 0 0 0 2px ${theme.palette.primary.main}`,
            },
          }}
        >
          {AgentListContent}
        </Box>
      )}

      {/* Center/Main Panel */}
      <Box sx={{
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        flexGrow: 1,
        height: '100%',
        overflow: 'hidden',
      }}>
        {/* Mobile: Tabs with Agent Editor and Run Console */}
        {isMobile ? (
          <Box sx={{
            display: 'flex',
            flexDirection: 'column',
            flexGrow: 1,
            height: '100%',
            overflow: 'hidden',
          }}>
            {/* Tabs */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider', pt: 6 }}>
              <Tabs value={mobileTab} onChange={(_, newValue) => setMobileTab(newValue)}>
                <Tab label="Agent Editor" />
                <Tab label="Run Console" />
              </Tabs>
            </Box>

            {/* Tab Content */}
            {mobileTab === 0 ? (
              <Box sx={{
                flexGrow: 1,
                bgcolor: 'background.paper',
                overflowY: 'auto',
                '&::-webkit-scrollbar': {
                  width: '12px',
                },
                '&::-webkit-scrollbar-track': {
                  bgcolor: 'background.paper',
                },
                '&::-webkit-scrollbar-thumb': {
                  bgcolor: theme => theme.palette.mode === 'dark' ? '#3a3a3a' : '#c0c0c0',
                  borderRadius: '6px',
                  border: theme => `2px solid ${theme.palette.mode === 'dark' ? '#1a1a1a' : '#ffffff'}`,
                  '&:hover': {
                    bgcolor: theme => theme.palette.mode === 'dark' ? '#4a4a4a' : '#a0a0a0',
                  },
                },
              }}>
                <AgentEditor nested/>
              </Box>
            ) : (
              <Box sx={{
                flexGrow: 1,
                bgcolor: theme => theme.palette.mode === 'dark'
                  ? 'rgba(255, 255, 255, 0.03)'
                  : 'rgba(0, 0, 0, 0.02)',
                overflowY: 'auto',
              }}>
                <RunConsole nested/>
              </Box>
            )}
          </Box>
        ) : (
          <>
            {/* Desktop: Agent Editor - Left */}
            <Box sx={{
              flexGrow: 1,
              height: '100%',
              bgcolor: 'background.paper',
              overflowY: 'auto',
              borderRight: 1,
              borderColor: 'divider',
              '&::-webkit-scrollbar': {
                width: '12px',
              },
              '&::-webkit-scrollbar-track': {
                bgcolor: 'background.paper',
              },
              '&::-webkit-scrollbar-thumb': {
                bgcolor: theme => theme.palette.mode === 'dark' ? '#3a3a3a' : '#c0c0c0',
                borderRadius: '6px',
                border: theme => `2px solid ${theme.palette.mode === 'dark' ? '#1a1a1a' : '#ffffff'}`,
                '&:hover': {
                  bgcolor: theme => theme.palette.mode === 'dark' ? '#4a4a4a' : '#a0a0a0',
                },
              },
            }}>
              <AgentEditor nested/>
            </Box>

            {/* Desktop: Run Console - Right */}
            <Box sx={{
              width: '35%',
              minWidth: '500px',
              maxWidth: '800px',
              height: '100%',
              bgcolor: theme => theme.palette.mode === 'dark'
                ? 'rgba(255, 255, 255, 0.03)'
                : 'rgba(0, 0, 0, 0.02)',
              overflowY: 'auto',
              flexShrink: 0,
            }}>
              <RunConsole nested/>
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
}
