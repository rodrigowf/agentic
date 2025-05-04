import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams, Link as RouterLink } from 'react-router-dom';
import {
  TextField,
  Button,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  OutlinedInput,
  Chip,
  Box,
  Typography,
  Paper,
  Alert,
  FormHelperText,
  Grid,
  Divider,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import api from '../api';

const DEFAULT_AGENT_CONFIG = {
  name: '',
  tools: [],
  llm: {
    provider: 'openai',
    model: '',
    temperature: 0.0,
    max_tokens: null,
  },
  prompt: {
    system: '',
    user: '',
  },
  max_turns: 15, // Default to 15 as per previous discussion
  reflect_on_tool_use: true,
  terminate_on_text: true, // <-- Add default value
};

export default function AgentEditor() {
  const { name } = useParams();
  const isEditMode = Boolean(name);
  const nav = useNavigate();
  const [allTools, setAllTools] = useState([]);
  const [cfg, setCfg] = useState(DEFAULT_AGENT_CONFIG);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    setLoading(true);
    api
      .getTools()
      .then((r) => setAllTools(r.data))
      .catch((err) => {
        console.error('Error fetching tools:', err);
        setError('Failed to load available tools.');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (isEditMode) {
      setLoading(true);
      setError(null);
      api
        .getAgents()
        .then((r) => {
          const agentToEdit = r.data.find((x) => x.name === name);
          if (agentToEdit) {
            setCfg({ ...DEFAULT_AGENT_CONFIG, ...agentToEdit });
          } else {
            setError(`Agent '${name}' not found.`);
          }
        })
        .catch((err) => {
          console.error('Error fetching agent:', err);
          setError('Failed to load agent configuration.');
        })
        .finally(() => setLoading(false));
    } else {
      setCfg(DEFAULT_AGENT_CONFIG);
    }
  }, [isEditMode, name]);

  const handleInputChange = useCallback((path, value) => {
    setCfg((prevCfg) => {
      const keys = path.split('.');
      const newCfg = { ...prevCfg };
      let current = newCfg;
      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) {
          current[keys[i]] = {};
        }
        current = current[keys[i]];
      }
      if (typeof current[keys[keys.length - 1]] === 'boolean') {
        current[keys[keys.length - 1]] = Boolean(value);
      } else {
        current[keys[keys.length - 1]] = value;
      }
      return newCfg;
    });
    setSuccess(null);
    setError(null);
  }, []);

  const handleSave = () => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    if (!cfg.name.trim()) {
      setError('Agent Name is required.');
      setLoading(false);
      return;
    }
    if (!cfg.llm.model.trim()) {
      setError('Model Name is required.');
      setLoading(false);
      return;
    }

    const payload = {
      ...cfg,
      llm: {
        ...cfg.llm,
        temperature: parseFloat(cfg.llm.temperature) || 0.0,
        max_tokens: cfg.llm.max_tokens ? parseInt(cfg.llm.max_tokens) : null,
      },
      max_turns: parseInt(cfg.max_turns) || 5,
    };

    const action = isEditMode
      ? api.updateAgent(name, payload)
      : api.createAgent(payload);
    action
      .then(() => {
        setSuccess(
          `Agent '${cfg.name}' ${
            isEditMode ? 'updated' : 'created'
          } successfully!`
        );
        setTimeout(() => nav('/'), 1500);
      })
      .catch((err) => {
        console.error('Error saving agent:', err);
        setError(
          err.response?.data?.detail ||
            `Failed to ${isEditMode ? 'update' : 'create'} agent.`
        );
      })
      .finally(() => setLoading(false));
  };

  return (
    <Box component={Paper} sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        {isEditMode ? `Edit Agent: ${name}` : 'Create New Agent'}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Box
        component="form"
        noValidate
        autoComplete="off"
        onSubmit={(e) => {
          e.preventDefault();
          handleSave();
        }}
        sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}
      >
        <TextField
          label="Agent Name"
          value={cfg.name}
          onChange={(e) => handleInputChange('name', e.target.value)}
          required
          disabled={isEditMode || loading}
          error={!cfg.name.trim() && !!error}
          helperText={
            !cfg.name.trim() && !!error
              ? 'Agent Name is required'
              : 'Unique name for the agent'
          }
        />

        <Typography variant="h6" sx={{ mt: 1 }}>
          Prompts
        </Typography>
        <TextField
          label="System Prompt"
          multiline
          rows={4}
          value={cfg.prompt.system}
          onChange={(e) => handleInputChange('prompt.system', e.target.value)}
          disabled={loading}
          helperText="Instructions defining the agent's role, personality, and constraints."
        />
        <TextField
          label="User Prompt / Initial Task"
          multiline
          rows={2}
          value={cfg.prompt.user}
          onChange={(e) => handleInputChange('prompt.user', e.target.value)}
          disabled={loading}
          helperText="The initial message or task to start the conversation."
        />

        <Divider sx={{ my: 1 }} />

        <Typography variant="h6">LLM Configuration</Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth required error={!cfg.llm.provider && !!error}>
              <InputLabel>LLM Provider</InputLabel>
              <Select
                value={cfg.llm.provider}
                onChange={(e) => handleInputChange('llm.provider', e.target.value)}
                label="LLM Provider"
                disabled={loading}
              >
                <MenuItem value="openai">OpenAI</MenuItem>
                <MenuItem value="anthropic">Anthropic</MenuItem>
                <MenuItem value="gemini">Gemini</MenuItem>
              </Select>
              {!cfg.llm.provider && !!error && (
                <FormHelperText>Provider is required</FormHelperText>
              )}
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Model Name"
              value={cfg.llm.model}
              onChange={(e) => handleInputChange('llm.model', e.target.value)}
              required
              error={!cfg.llm.model.trim() && !!error}
              helperText={
                !cfg.llm.model.trim() && !!error
                  ? 'Model Name is required'
                  : 'e.g., gpt-4, claude-3-opus, gemini-pro'
              }
              disabled={loading}
            />
          </Grid>
          <Grid item xs={6} sm={4}>
            <TextField
              fullWidth
              type="number"
              label="Temperature"
              value={cfg.llm.temperature}
              onChange={(e) => handleInputChange('llm.temperature', e.target.value)}
              inputProps={{ step: '0.1', min: '0', max: '2' }}
              helperText="0 = deterministic, >0 = creative"
              disabled={loading}
            />
          </Grid>
          <Grid item xs={6} sm={4}>
            <TextField
              fullWidth
              type="number"
              label="Max Tokens"
              value={cfg.llm.max_tokens ?? ''}
              onChange={(e) =>
                handleInputChange(
                  'llm.max_tokens',
                  e.target.value ? parseInt(e.target.value) : null
                )
              }
              inputProps={{ min: '1' }}
              helperText="Optional limit"
              disabled={loading}
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              type="number"
              label="Max Turns"
              value={cfg.max_turns}
              onChange={(e) => handleInputChange('max_turns', e.target.value)}
              inputProps={{ min: '1' }}
              helperText="Max conversation steps"
              disabled={loading}
            />
          </Grid>
        </Grid>

        <Divider sx={{ my: 1 }} />

        <Typography variant="h6">Tools</Typography>
        <FormControl fullWidth disabled={loading}>
          <InputLabel>Available Tools</InputLabel>
          <Select
            multiple
            value={cfg.tools}
            onChange={(e) => handleInputChange('tools', e.target.value)}
            input={<OutlinedInput label="Available Tools" />}
            renderValue={(selected) => (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {selected.map((toolName) => (
                  <Chip key={toolName} label={toolName} size="small" />
                ))}
              </Box>
            )}
          >
            {allTools.length === 0 && (
              <MenuItem disabled>Loading tools...</MenuItem>
            )}
            {allTools.map((t) => (
              <MenuItem key={t.name} value={t.name}>
                {t.name}
              </MenuItem>
            ))}
          </Select>
          <FormHelperText>Select the tools this agent can use.</FormHelperText>
        </FormControl>

        <FormControlLabel
          control={
            <Checkbox
              checked={cfg.terminate_on_text}
              onChange={(e) =>
                handleInputChange('terminate_on_text', e.target.checked)
              }
              disabled={loading}
            />
          }
          label="Terminate chat if agent outputs 'TERMINATE'"
        />

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 2 }}>
          <Button
            variant="outlined"
            component={RouterLink}
            to="/"
            disabled={loading}
          >
            Cancel
          </Button>
          <Button type="submit" variant="contained" disabled={loading}>
            {loading
              ? 'Saving...'
              : isEditMode
              ? 'Update Agent'
              : 'Create Agent'}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}