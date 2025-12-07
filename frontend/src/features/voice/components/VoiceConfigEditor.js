import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Stack,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  getAgents,
  listVoicePrompts,
  getVoicePrompt,
  saveVoicePrompt,
} from '../../../api';

/**
 * Component for configuring voice assistant settings.
 * Allows selecting the agent and editing the system prompt.
 */
function VoiceConfigEditor({ open, onClose, onSave }) {
  const [agents, setAgents] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  // Form state
  const [selectedAgent, setSelectedAgent] = useState('MainConversation');
  const [selectedPromptFile, setSelectedPromptFile] = useState('default.txt');
  const [promptContent, setPromptContent] = useState('');
  const [newPromptName, setNewPromptName] = useState('');
  const [selectedVoice, setSelectedVoice] = useState('alloy');
  const [memoryFilePath, setMemoryFilePath] = useState('backend/data/memory/short_term_memory.txt');

  // Available OpenAI voices
  const availableVoices = [
    { value: 'alloy', label: 'Alloy' },
    { value: 'echo', label: 'Echo' },
    { value: 'fable', label: 'Fable' },
    { value: 'onyx', label: 'Onyx' },
    { value: 'nova', label: 'Nova' },
    { value: 'shimmer', label: 'Shimmer' },
  ];

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Load agents
      const agentsRes = await getAgents();
      setAgents(agentsRes.data || []);

      // Load prompt files
      const promptsRes = await listVoicePrompts();
      setPrompts(promptsRes.data?.prompts || []);

      // Load default prompt content
      if (selectedPromptFile) {
        const contentRes = await getVoicePrompt(selectedPromptFile);
        setPromptContent(contentRes.data || '');
      }
    } catch (err) {
      console.error('Failed to load voice configuration data:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handlePromptFileChange = async (filename) => {
    setSelectedPromptFile(filename);
    try {
      const res = await getVoicePrompt(filename);
      setPromptContent(res.data || '');
    } catch (err) {
      console.error('Failed to load prompt:', err);
      setError(`Failed to load prompt: ${err.message}`);
    }
  };

  const handleSavePrompt = async () => {
    setSaving(true);
    setError(null);
    try {
      const filename = newPromptName.trim() || selectedPromptFile;
      await saveVoicePrompt(filename, promptContent);

      // Reload prompts list
      const promptsRes = await listVoicePrompts();
      setPrompts(promptsRes.data?.prompts || []);

      setSelectedPromptFile(filename);
      setNewPromptName('');
      setError(null);
    } catch (err) {
      console.error('Failed to save prompt:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to save prompt');
    } finally {
      setSaving(false);
    }
  };

  const handleSave = () => {
    onSave({
      agentName: selectedAgent,
      systemPromptFile: selectedPromptFile,
      systemPromptContent: promptContent,
      voice: selectedVoice,
      memoryFilePath: memoryFilePath,
    });
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Voice Assistant Configuration</DialogTitle>
      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Stack spacing={3} sx={{ mt: 2 }}>
            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}

            {/* Agent Selection */}
            <FormControl fullWidth>
              <InputLabel id="agent-select-label">Agent</InputLabel>
              <Select
                labelId="agent-select-label"
                id="agent-select"
                value={selectedAgent}
                label="Agent"
                onChange={(e) => setSelectedAgent(e.target.value)}
              >
                {agents.map((agent) => (
                  <MenuItem key={agent.name} value={agent.name}>
                    {agent.name}
                    {agent.description && ` - ${agent.description}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Voice Selection */}
            <FormControl fullWidth>
              <InputLabel id="voice-select-label">Voice</InputLabel>
              <Select
                labelId="voice-select-label"
                id="voice-select"
                value={selectedVoice}
                label="Voice"
                onChange={(e) => setSelectedVoice(e.target.value)}
              >
                {availableVoices.map((voice) => (
                  <MenuItem key={voice.value} value={voice.value}>
                    {voice.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Memory File Path */}
            <TextField
              fullWidth
              label="Memory File"
              value={memoryFilePath}
              onChange={(e) => setMemoryFilePath(e.target.value)}
              placeholder="backend/data/memory/short_term_memory.txt"
              helperText="Path to memory file for context injection (relative to project root)"
              size="small"
            />

            {/* Prompt File Selection */}
            <FormControl fullWidth>
              <InputLabel id="prompt-select-label">System Prompt</InputLabel>
              <Select
                labelId="prompt-select-label"
                id="prompt-select"
                value={selectedPromptFile}
                label="System Prompt"
                onChange={(e) => handlePromptFileChange(e.target.value)}
              >
                {prompts.map((filename) => (
                  <MenuItem key={filename} value={filename}>
                    {filename}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Prompt Content Editor */}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                System Prompt Content
              </Typography>
              <TextField
                multiline
                fullWidth
                rows={12}
                value={promptContent}
                onChange={(e) => setPromptContent(e.target.value)}
                placeholder="Enter system prompt..."
                variant="outlined"
                sx={{
                  '& .MuiInputBase-root': {
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                  },
                }}
              />
            </Box>

            {/* Save As New Prompt */}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Save as new prompt file (optional)
              </Typography>
              <Stack direction="row" spacing={1}>
                <TextField
                  size="small"
                  fullWidth
                  value={newPromptName}
                  onChange={(e) => setNewPromptName(e.target.value)}
                  placeholder="new-prompt.txt"
                  helperText="Leave empty to overwrite current file"
                />
                <Button
                  variant="outlined"
                  onClick={handleSavePrompt}
                  disabled={saving || !promptContent.trim()}
                >
                  {saving ? <CircularProgress size={20} /> : 'Save Prompt'}
                </Button>
              </Stack>
            </Box>
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={loading || !selectedAgent || !promptContent.trim()}
        >
          Apply Configuration
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default VoiceConfigEditor;
