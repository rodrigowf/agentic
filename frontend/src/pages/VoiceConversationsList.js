import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import LaunchIcon from '@mui/icons-material/Launch';
import AddIcon from '@mui/icons-material/Add';
import {
  createVoiceConversation,
  listVoiceConversations,
  updateVoiceConversation,
  deleteVoiceConversation,
} from '../api';

const formatTimestamp = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch (e) {
    return value;
  }
};

export default function VoiceConversationsList() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  const fetchConversations = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listVoiceConversations();
      setItems(res.data ?? []);
    } catch (err) {
      console.error('Failed to load conversations', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  const handleCreate = async () => {
    setIsCreating(true);
    setError(null);
    try {
      const res = await createVoiceConversation({});
      const conversation = res.data;
      if (conversation?.id) {
        navigate(`/voice/${conversation.id}`);
      } else {
        await fetchConversations();
      }
    } catch (err) {
      console.error('Failed to create conversation', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to create conversation');
    } finally {
      setIsCreating(false);
    }
  };

  const openRenameDialog = (conversation) => {
    setRenameTarget(conversation);
    setRenameValue(conversation?.name || '');
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
      setError(err?.response?.data?.detail || err.message || 'Failed to rename conversation');
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget?.id) return;
    try {
      await deleteVoiceConversation(deleteTarget.id);
      setDeleteTarget(null);
      await fetchConversations();
    } catch (err) {
      console.error('Failed to delete conversation', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to delete conversation');
    }
  };

  const hasItems = useMemo(() => items && items.length > 0, [items]);

  return (
    <Stack spacing={3}>
      <Box component={Paper} sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box>
          <Typography variant="h4" gutterBottom>Voice Conversations</Typography>
          <Typography variant="body2" color="text.secondary">
            Create, organize, and reopen realtime voice sessions shared across tabs.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, marginLeft: 'auto' }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchConversations}
            disabled={loading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreate}
            disabled={isCreating}
          >
            New conversation
          </Button>
        </Box>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      <Paper sx={{ p: 0, overflowX: 'auto' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Voice</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Last updated</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {!hasItems && !loading && (
              <TableRow>
                <TableCell colSpan={5} sx={{ textAlign: 'center', py: 6, color: 'text.secondary' }}>
                  No conversations yet. Click “New conversation” to start.
                </TableCell>
              </TableRow>
            )}
            {hasItems && items.map((item) => (
              <TableRow key={item.id} hover>
                <TableCell>
                  <Typography variant="subtitle2">{item.name}</Typography>
                  <Typography variant="caption" color="text.secondary">{item.id}</Typography>
                </TableCell>
                <TableCell>{item.voice_model || item.metadata?.voice || '—'}</TableCell>
                <TableCell>{formatTimestamp(item.created_at)}</TableCell>
                <TableCell>{formatTimestamp(item.updated_at)}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => navigate(`/voice/${item.id}`)} title="Open conversation">
                    <LaunchIcon fontSize="inherit" />
                  </IconButton>
                  <IconButton size="small" onClick={() => openRenameDialog(item)} title="Rename conversation">
                    <EditIcon fontSize="inherit" />
                  </IconButton>
                  <IconButton size="small" color="error" onClick={() => setDeleteTarget(item)} title="Delete conversation">
                    <DeleteIcon fontSize="inherit" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

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
          <Button onClick={handleRename} variant="contained" disabled={!renameValue.trim()}>Save</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete conversation</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will remove the conversation history permanently. This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">Delete</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
