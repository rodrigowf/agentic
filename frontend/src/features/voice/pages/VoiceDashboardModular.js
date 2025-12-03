// This is a copy of VoiceDashboard.js but uses VoiceAssistantModular
// For side-by-side testing of the original implementation

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
import VoiceAssistantModular from './VoiceAssistantModular';
import {
  listVoiceConversations,
  createVoiceConversation,
  updateVoiceConversation,
  deleteVoiceConversation,
} from '../../../api';

function VoiceDashboardModular() {
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
          navigate(`/voice-modular/${mostRecent.id}`, { replace: true });
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
      const name = `Conversation ${timestamp}`;
      const res = await createVoiceConversation(name);
      const newConv = res.data;
      if (newConv?.id) {
        navigate(`/voice-modular/${newConv.id}`);
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

  const handleDelete = async (conv) => {
    if (!window.confirm(`Delete conversation "${conv.name || conv.id}"?`)) return;
    try {
      const deleteTarget = conv;
      await deleteVoiceConversation(deleteTarget.id);
      await fetchConversations();
      if (deleteTarget.id === conversationId) {
        navigate('/voice-modular');
      }
    } catch (err) {
      console.error('Failed to delete conversation', err);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Left Sidebar - Conversation List */}
      <Box
        sx={{
          width: 280,
          height: '100%',
          bgcolor: 'background.default',
          borderRight: 1,
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Box
          sx={{
            p: 2,
            borderBottom: 1,
            borderColor: 'divider',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Typography variant="h6">Voice (Modular)</Typography>
          <Tooltip title="Create new conversation">
            <IconButton size="small" onClick={handleCreate}>
              <AddIcon />
            </IconButton>
          </Tooltip>
        </Box>

        <List sx={{ flexGrow: 1, overflowY: 'auto', py: 0 }}>
          {loading ? (
            <ListItem>
              <ListItemText primary="Loading..." />
            </ListItem>
          ) : conversations.length === 0 ? (
            <ListItem>
              <ListItemText
                primary="No conversations"
                secondary="Click + to create one"
              />
            </ListItem>
          ) : (
            conversations.map((conv) => (
              <ListItem
                key={conv.id}
                disablePadding
                secondaryAction={
                  <Box>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRename(conv);
                      }}
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(conv);
                      }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                }
              >
                <ListItemButton
                  selected={conv.id === conversationId}
                  component={RouterLink}
                  to={`/voice-modular/${conv.id}`}
                  sx={{ pr: 10 }}
                >
                  <ListItemText
                    primary={conv.name || conv.id}
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
      </Box>

      {/* Main Content - Voice Assistant */}
      <Box
        sx={{
          flexGrow: 1,
          height: '100%',
          bgcolor: 'background.paper',
          overflowY: 'auto',
        }}
      >
        {conversationId ? (
          <VoiceAssistantModular nested onConversationUpdate={fetchConversations} />
        ) : (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              p: 4,
            }}
          >
            <Typography variant="h6" color="text.secondary">
              Select a conversation or create a new one to get started
            </Typography>
          </Box>
        )}
      </Box>

      {/* Rename Dialog */}
      <Dialog open={renameOpen} onClose={() => setRenameOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Rename Conversation</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Conversation Name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRenameConfirm();
            }}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameOpen(false)}>Cancel</Button>
          <Button onClick={handleRenameConfirm} variant="contained">
            Rename
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default VoiceDashboardModular;
