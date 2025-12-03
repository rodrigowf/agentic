// VoiceDashboardWebSocket.js - Dashboard for Pipecat WebSocket voice assistant
// Similar to VoiceDashboardModular but uses WebSocket transport instead of WebRTC

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tooltip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import VoiceAssistantWebSocket from './VoiceAssistantWebSocket';
import {
  listVoiceConversations,
  createVoiceConversation,
  updateVoiceConversation,
  deleteVoiceConversation,
} from '../../../api';

function VoiceDashboardWebSocket() {
  const { conversationId } = useParams();
  const navigate = useNavigate();

  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState(null);
  const [newName, setNewName] = useState('');

  const fetchConversations = useCallback(async () => {
    try {
      const res = await listVoiceConversations();
      const sorted = (res.data || []).sort((a, b) => {
        return new Date(b.updated_at) - new Date(a.updated_at);
      });
      setConversations(sorted);

      // Auto-navigate to most recent if no conversation selected
      if (!conversationId && sorted.length > 0) {
        const mostRecent = sorted[0];
        if (mostRecent?.id) {
          navigate(`/voice-ws/${mostRecent.id}`, { replace: true });
        }
      }
    } catch (err) {
      console.error('Failed to load conversations', err);
    } finally {
      setLoading(false);
    }
  }, [conversationId, navigate]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleCreate = async () => {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
      const name = `WebSocket Conversation ${timestamp}`;
      const res = await createVoiceConversation(name);
      const newConv = res.data;
      if (newConv?.id) {
        navigate(`/voice-ws/${newConv.id}`);
        await fetchConversations();
      }
    } catch (err) {
      console.error('Failed to create conversation', err);
    }
  };

  const handleRename = (conv) => {
    setRenameTarget(conv);
    setNewName(conv.name || '');
    setRenameOpen(true);
  };

  const handleRenameConfirm = async () => {
    if (!renameTarget || !newName.trim()) return;
    try {
      await updateVoiceConversation(renameTarget.id, { name: newName.trim() });
      setRenameOpen(false);
      setRenameTarget(null);
      setNewName('');
      await fetchConversations();
    } catch (err) {
      console.error('Failed to rename conversation', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this conversation?')) return;
    try {
      await deleteVoiceConversation(id);
      if (conversationId === id) {
        navigate('/voice-ws', { replace: true });
      }
      await fetchConversations();
    } catch (err) {
      console.error('Failed to delete conversation', err);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 64px)' }}>
      {/* Sidebar */}
      <Box
        sx={{
          width: 280,
          borderRight: 1,
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
          bgcolor: 'background.paper',
        }}
      >
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6" gutterBottom>
            Voice WebSocket
          </Typography>
          <Button
            fullWidth
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreate}
            size="small"
          >
            New Conversation
          </Button>
        </Box>

        <List sx={{ flexGrow: 1, overflow: 'auto' }}>
          {loading ? (
            <ListItem>
              <ListItemText primary="Loading..." />
            </ListItem>
          ) : conversations.length === 0 ? (
            <ListItem>
              <ListItemText
                primary="No conversations"
                secondary="Create one to start"
              />
            </ListItem>
          ) : (
            conversations.map((conv) => (
              <ListItem
                key={conv.id}
                disablePadding
                secondaryAction={
                  <>
                    <Tooltip title="Rename">
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRename(conv);
                        }}
                        sx={{ mr: 0.5 }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(conv.id);
                        }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </>
                }
              >
                <ListItemButton
                  selected={conv.id === conversationId}
                  component={RouterLink}
                  to={`/voice-ws/${conv.id}`}
                  sx={{
                    pr: 10,
                    '&.Mui-selected': {
                      bgcolor: 'action.selected',
                      '&:hover': {
                        bgcolor: 'action.selected',
                      },
                    },
                  }}
                >
                  <ListItemText
                    primary={conv.name || 'Untitled'}
                    secondary={new Date(conv.updated_at).toLocaleString()}
                    primaryTypographyProps={{
                      noWrap: true,
                      fontSize: '0.9rem',
                    }}
                    secondaryTypographyProps={{
                      noWrap: true,
                      fontSize: '0.75rem',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            ))
          )}
        </List>

        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary">
            Pipecat + FastAPI WebSocket
            <br />
            Self-hosted, zero cost
          </Typography>
        </Box>
      </Box>

      {/* Main content */}
      <Box sx={{ flexGrow: 1, overflow: 'hidden', bgcolor: 'background.default' }}>
        {conversationId ? (
          <VoiceAssistantWebSocket
            key={conversationId}
            onConversationUpdate={fetchConversations}
          />
        ) : (
          <Box
            sx={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column',
              gap: 2,
              p: 4,
            }}
          >
            <Typography variant="h5" color="text.secondary">
              Welcome to WebSocket Voice Assistant
            </Typography>
            <Typography variant="body2" color="text.secondary" textAlign="center" maxWidth={400}>
              This version uses Pipecat + FastAPI WebSocket for self-hosted, zero-cost voice conversations.
              No Daily.co or external services required!
            </Typography>
            <Button variant="contained" startIcon={<AddIcon />} onClick={handleCreate}>
              Create Your First Conversation
            </Button>
          </Box>
        )}
      </Box>

      {/* Rename Dialog */}
      <Dialog open={renameOpen} onClose={() => setRenameOpen(false)}>
        <DialogTitle>Rename Conversation</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRenameConfirm();
            }}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameOpen(false)}>Cancel</Button>
          <Button onClick={handleRenameConfirm} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default VoiceDashboardWebSocket;
