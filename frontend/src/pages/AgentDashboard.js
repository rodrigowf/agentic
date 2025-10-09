import { useState, useEffect } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { Box, List, ListItem, ListItemButton, ListItemText, Typography, Divider } from '@mui/material';
import AgentEditor from '../components/AgentEditor';
import RunConsole from '../components/RunConsole';
import api from '../api';

export default function AgentDashboard() {
  const { name } = useParams();
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    api.getAgents()
      .then(res => setAgents(res.data))
      .catch(err => console.error("Error fetching agents:", err));
  }, []);

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
      {/* Left Panel - Agents List */}
      <Box sx={{
        width: '250px',
        height: '100%',
        bgcolor: theme => theme.palette.mode === 'dark'
          ? 'rgba(255, 255, 255, 0.03)'
          : 'rgba(0, 0, 0, 0.02)',
        borderRight: 1,
        borderColor: 'divider',
        overflowY: 'auto',
        flexShrink: 0,
      }}>
        <Box sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Agents
          </Typography>
        </Box>
        <Divider />
        <List disablePadding>
          {agents.map(agent => (
            <ListItem key={agent.name} disablePadding>
              <ListItemButton
                component={RouterLink}
                to={`/agents/${agent.name}`}
                selected={agent.name === name}
                sx={{
                  '&.Mui-selected': {
                    bgcolor: theme => theme.palette.mode === 'dark'
                      ? 'rgba(144, 202, 249, 0.16)'
                      : 'rgba(63, 81, 181, 0.08)',
                    borderLeft: 3,
                    borderColor: 'primary.main',
                  }
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
      </Box>

      {/* Center Panel - Agent Editor */}
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

      {/* Right Panel - Run Console */}
      <Box sx={{
        width: '700px',
        height: '100%',
        bgcolor: theme => theme.palette.mode === 'dark'
          ? 'rgba(255, 255, 255, 0.03)'
          : 'rgba(0, 0, 0, 0.02)',
        overflowY: 'auto',
        flexShrink: 0,
      }}>
        <RunConsole nested/>
      </Box>
    </Box>
  );
}
