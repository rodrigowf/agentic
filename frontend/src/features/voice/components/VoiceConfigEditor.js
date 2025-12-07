import React, { useState, useEffect } from 'react';
import {
  Box,
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
  listVoiceConfigs,
  updateVoiceConfig,
  getSelectedVoiceConfig,
  setSelectedVoiceConfig,
} from '../../../api';

/**
 * Component for configuring voice assistant settings.
 *
 * Configuration is saved to the backend's voice config files.
 * The selected config is stored in voice/selected_config.json.
 * When the voice session starts, it loads config from the backend.
 */
function VoiceConfigEditor({ open, onClose, onSave }) {
  const [agents, setAgents] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [configFiles, setConfigFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);

  // Form state - reflects what's in the selected config file
  const [selectedConfigFile, setSelectedConfigFile] = useState('default');
  const [selectedAgent, setSelectedAgent] = useState('MainConversation');
  const [selectedPromptFile, setSelectedPromptFile] = useState('default.txt');
  const [promptContent, setPromptContent] = useState('');
  const [newPromptName, setNewPromptName] = useState('');
  const [selectedVoice, setSelectedVoice] = useState('alloy');
  const [memoryFilePath, setMemoryFilePath] = useState('backend/data/memory/short_term_memory.txt');

  // Available OpenAI Realtime API voices
  // See: https://platform.openai.com/docs/guides/realtime
  const availableVoices = [
    { value: 'alloy', label: 'Alloy' },
    { value: 'ash', label: 'Ash' },
    { value: 'ballad', label: 'Ballad' },
    { value: 'cedar', label: 'Cedar' },
    { value: 'coral', label: 'Coral' },
    { value: 'echo', label: 'Echo' },
    { value: 'marin', label: 'Marin' },
    { value: 'sage', label: 'Sage' },
    { value: 'shimmer', label: 'Shimmer' },
    { value: 'verse', label: 'Verse' },
  ];

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    setSuccessMessage(null);
    try {
      // Load agents
      const agentsRes = await getAgents();
      setAgents(agentsRes.data || []);

      // Load voice config files
      const configsRes = await listVoiceConfigs();
      setConfigFiles(configsRes.data || []);

      // Load prompt files
      const promptsRes = await listVoicePrompts();
      setPrompts(promptsRes.data?.prompts || []);

      // Load the currently selected config from backend
      const selectedRes = await getSelectedVoiceConfig();
      const selectedName = selectedRes.data?.selected || 'default';
      const config = selectedRes.data?.config;

      setSelectedConfigFile(selectedName);

      if (config) {
        setSelectedAgent(config.agent_name || 'MainConversation');
        setSelectedVoice(config.voice || 'alloy');
        setMemoryFilePath(config.memory_file_path || 'backend/data/memory/short_term_memory.txt');
        setSelectedPromptFile(config.system_prompt_file || 'default.txt');

        // Load prompt content
        if (config.system_prompt_file) {
          try {
            const contentRes = await getVoicePrompt(config.system_prompt_file);
            setPromptContent(contentRes.data || '');
          } catch (err) {
            console.warn('Failed to load prompt content:', err);
          }
        }
      }
    } catch (err) {
      console.error('Failed to load voice configuration data:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleConfigFileChange = async (configName) => {
    setSelectedConfigFile(configName);
    setError(null);

    // Load the config file content
    const config = configFiles.find((c) => c.name === configName);
    if (config) {
      setSelectedAgent(config.agent_name || 'MainConversation');
      setSelectedVoice(config.voice || 'alloy');
      setMemoryFilePath(config.memory_file_path || 'backend/data/memory/short_term_memory.txt');
      setSelectedPromptFile(config.system_prompt_file || 'default.txt');

      // Load prompt content
      if (config.system_prompt_file) {
        try {
          const contentRes = await getVoicePrompt(config.system_prompt_file);
          setPromptContent(contentRes.data || '');
        } catch (err) {
          console.warn('Failed to load prompt content:', err);
        }
      }
    }

    // Update the selected config in backend
    try {
      await setSelectedVoiceConfig(configName);
    } catch (err) {
      console.error('Failed to update selected config:', err);
      setError(`Failed to select config: ${err.message}`);
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
      setSuccessMessage('Prompt saved successfully');
    } catch (err) {
      console.error('Failed to save prompt:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to save prompt');
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Save the config to the backend config file
      const configData = {
        name: selectedConfigFile,
        agent_name: selectedAgent,
        system_prompt_file: selectedPromptFile,
        voice_model: 'gpt-realtime',
        voice: selectedVoice,
        memory_file_path: memoryFilePath,
        description: `Voice configuration: ${selectedAgent} with ${selectedVoice} voice`,
        metadata: {},
      };

      await updateVoiceConfig(selectedConfigFile, configData);

      // Make sure this config is selected
      await setSelectedVoiceConfig(selectedConfigFile);

      // Reload config files
      const configsRes = await listVoiceConfigs();
      setConfigFiles(configsRes.data || []);

      setSuccessMessage('Configuration saved to backend');

      // Notify parent (for local state if needed)
      onSave({
        agentName: selectedAgent,
        systemPromptFile: selectedPromptFile,
        systemPromptContent: promptContent,
        voice: selectedVoice,
        memoryFilePath: memoryFilePath,
      });

      // Close after short delay to show success
      setTimeout(() => onClose(), 500);
    } catch (err) {
      console.error('Failed to save configuration:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
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

            {successMessage && (
              <Alert severity="success" onClose={() => setSuccessMessage(null)}>
                {successMessage}
              </Alert>
            )}

            {/* Config File Selection */}
            <FormControl fullWidth>
              <InputLabel id="config-select-label">Configuration File</InputLabel>
              <Select
                labelId="config-select-label"
                id="config-select"
                value={selectedConfigFile}
                label="Configuration File"
                onChange={(e) => handleConfigFileChange(e.target.value)}
              >
                {configFiles.map((config) => (
                  <MenuItem key={config.name} value={config.name}>
                    {config.name}
                    {config.description && ` - ${config.description}`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

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
