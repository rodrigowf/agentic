import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
  Divider,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import VoiceAssistant from './VoiceAssistant';
import {
  listVoiceConversations,
  createVoiceConversation,
  updateVoiceConversation,
  deleteVoiceConversation,
} from '../api';

const formatTimestamp = (value) => {
  if (!value) return '—';
  try {
    const date = new Date(value);
    const now = new Date();
    const sameDay = date.toDateString() === now.toDateString();
    if (sameDay) {
      return date.toLocaleTimeString();
    }
    return date.toLocaleDateString();
  } catch (e) {
    return value;
  }
};

export default function VoiceDashboard() {
  const { conversationId } = useParams();
  const navigate = useNavigate();

  // Conversations list state
  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  // Load conversations list
  const fetchConversations = useCallback(async () => {
    setConversationsLoading(true);
    try {
      const res = await listVoiceConversations();
      const convs = res.data ?? [];
      setConversations(convs);

      // Auto-select most recent conversation if no conversation is currently selected
      if (!conversationId && convs.length > 0) {
        const mostRecent = convs.reduce((latest, conv) => {
          const latestDate = new Date(latest.updated_at || latest.created_at || 0);
          const convDate = new Date(conv.updated_at || conv.created_at || 0);
          return convDate > latestDate ? conv : latest;
        }, convs[0]);

        if (mostRecent?.id) {
          navigate(`/voice/${mostRecent.id}`, { replace: true });
        }
      }
    } catch (err) {
      console.error('Failed to load conversations', err);
    } finally {
      setConversationsLoading(false);
    }
  }, [conversationId, navigate]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleCreate = async () => {
    setIsCreating(true);
    try {
      const res = await createVoiceConversation({});
      const newConv = res.data;
      if (newConv?.id) {
        navigate(`/voice/${newConv.id}`);
        await fetchConversations();
      }
    } catch (err) {
      console.error('Failed to create conversation', err);
    } finally {
      setIsCreating(false);
    }
  };

  const openRenameDialog = (conv) => {
    setRenameTarget(conv);
    setRenameValue(conv?.name || '');
  };

  const handleRename = async () => {
    if (!renameTarget?.id) return;
    try {
      await updateVoiceConversation(renameTarget.id, { name: renameValue });
      setRenameTarget(null);
      setRenameValue('');
      await fetchConversations();
    } catch (err) {
      console.error('Failed to rename conversation', err);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget?.id) return;
    try {
      await deleteVoiceConversation(deleteTarget.id);
      setDeleteTarget(null);
      await fetchConversations();
      if (deleteTarget.id === conversationId) {
        navigate('/voice');
      }
    } catch (err) {
      console.error('Failed to delete conversation', err);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        height: 'calc(100vh - 64px)',
        width: '100%',
        position: 'fixed',
        left: 0,
        top: 64,
        overflow: 'hidden',
        bgcolor: 'background.default',
      }}
    >
      {/* Left Panel - Conversations List */}
      <Box
        sx={{
          width: '360px',
          height: '100%',
          bgcolor: (theme) =>
            theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.02)',
          borderRight: 1,
          borderColor: 'divider',
          overflowY: 'auto',
          flexShrink: 0,
        }}
      >
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">Voice Chats</Typography>
          <IconButton size="small" onClick={handleCreate} disabled={isCreating} title="New conversation">
            <AddIcon />
          </IconButton>
        </Box>
        <Divider />
        <List disablePadding>
          {conversations.map((conv) => (
            <ListItem
              key={conv.id}
              disablePadding
              secondaryAction={
                <Box>
                  <IconButton
                    edge="end"
                    size="small"
                    onClick={() => openRenameDialog(conv)}
                    title="Rename"
                  >
                    <EditIcon fontSize="inherit" />
                  </IconButton>
                  <IconButton
                    edge="end"
                    size="small"
                    color="error"
                    onClick={() => setDeleteTarget(conv)}
                    title="Delete"
                  >
                    <DeleteIcon fontSize="inherit" />
                  </IconButton>
                </Box>
              }
            >
              <ListItemButton
                component={RouterLink}
                to={`/voice/${conv.id}`}
                selected={conv.id === conversationId}
                sx={{
                  '&.Mui-selected': {
                    bgcolor: (theme) =>
                      theme.palette.mode === 'dark'
                        ? 'rgba(144, 202, 249, 0.16)'
                        : 'rgba(63, 81, 181, 0.08)',
                    borderLeft: 3,
                    borderColor: 'primary.main',
                  },
                }}
              >
                <ListItemText
                  primary={conv.name || `Conversation ${conv.id.slice(0, 8)}`}
                  secondary={formatTimestamp(conv.updated_at)}
                  primaryTypographyProps={{
                    fontSize: '0.9rem',
                    fontWeight: conv.id === conversationId ? 600 : 400,
                    noWrap: true,
                  }}
                  secondaryTypographyProps={{
                    fontSize: '0.75rem',
                  }}
                  sx={{ pr: 8 }}
                />
              </ListItemButton>
            </ListItem>
          ))}
          {conversations.length === 0 && !conversationsLoading && (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                No conversations yet
              </Typography>
              <Button
                variant="outlined"
                size="small"
                startIcon={<AddIcon />}
                onClick={handleCreate}
                sx={{ mt: 2 }}
              >
                Create one
              </Button>
            </Box>
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
          <VoiceAssistant nested onConversationUpdate={fetchConversations} />
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
      <Dialog open={Boolean(renameTarget)} onClose={() => setRenameTarget(null)} fullWidth maxWidth="sm">
        <DialogTitle>Rename conversation</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Choose a descriptive title to make this session easy to find later.
          </DialogContentText>
          <TextField
            autoFocus
            fullWidth
            label="Conversation name"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameTarget(null)}>Cancel</Button>
          <Button onClick={handleRename} variant="contained" disabled={!renameValue.trim()}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete conversation</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will remove the conversation history permanently. This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
