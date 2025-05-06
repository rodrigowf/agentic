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
  FormControlLabel,
  Stack,
  CircularProgress,
  Switch,
  Snackbar,
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
  max_turns: 15,
  reflect_on_tool_use: true,
  tool_call_loop: false,
};

export default function AgentEditor({nested = false}) {
  const { name } = useParams();
  const isEditMode = Boolean(name);
  const nav = useNavigate();
  const [allTools, setAllTools] = useState([]);
  const [cfg, setCfg] = useState(DEFAULT_AGENT_CONFIG);
  const [originalCfg, setOriginalCfg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [models, setModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [notification, setNotification] = useState({ message: '', severity: 'success', open: false });

  const handleCloseNotification = () => {
    setNotification(prev => ({ ...prev, open: false }));
  };

  const showNotification = (message, severity = 'success') => {
    setNotification({ message, severity, open: true });
    // Auto-dismiss after 3 seconds
    setTimeout(() => {
      setNotification(prev => ({ ...prev, open: false }));
    }, 3000);
  };

  // Keep track of whether any fields have changed
  const hasChanges = useCallback(() => {
    console.log('hasChanges called with:', {
      originalCfg,
      currentCfg: cfg,
      isEditMode
    });

    if (!originalCfg || !isEditMode) {
      console.log('hasChanges returning true - no originalCfg or not in edit mode');
      return true;
    }
    
    // Deep compare the configurations, ignoring loading states
    const cleanCfg = {
      ...cfg,
      llm: {
        ...cfg.llm,
        temperature: parseFloat(cfg.llm.temperature) || 0.0,
        max_tokens: cfg.llm.max_tokens ? parseInt(cfg.llm.max_tokens) : null,
      },
      prompt: {
        system: cfg.prompt?.system || '',
        user: cfg.prompt?.user || ''
      },
      max_turns: parseInt(cfg.max_turns) || 5,
      tool_call_loop: Boolean(cfg.tool_call_loop),
      reflect_on_tool_use: Boolean(cfg.reflect_on_tool_use),
    };

    const cleanOriginalCfg = {
      ...originalCfg,
      llm: {
        ...originalCfg.llm,
        temperature: parseFloat(originalCfg.llm.temperature) || 0.0,
        max_tokens: originalCfg.llm.max_tokens ? parseInt(originalCfg.llm.max_tokens) : null,
      },
      prompt: {
        system: originalCfg.prompt?.system || '',
        user: originalCfg.prompt?.user || ''
      },
      max_turns: parseInt(originalCfg.max_turns) || 5,
      tool_call_loop: Boolean(originalCfg.tool_call_loop),
      reflect_on_tool_use: Boolean(originalCfg.reflect_on_tool_use),
    };
    
    console.log('Comparing configurations:', {
      cleanCfg,
      cleanOriginalCfg,
      areEqual: JSON.stringify(cleanCfg) === JSON.stringify(cleanOriginalCfg)
    });
    
    return JSON.stringify(cleanCfg) !== JSON.stringify(cleanOriginalCfg);
  }, [cfg, originalCfg, isEditMode]);

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

  // Add logging to track when originalCfg is set
  useEffect(() => {
    if (isEditMode) {
      console.log('Loading agent in edit mode:', { name });
      setLoading(true);
      setError(null);
      api
        .getAgents()
        .then((r) => {
          const agentToEdit = r.data.find((x) => x.name === name);
          if (agentToEdit) {
            console.log('Found agent to edit:', agentToEdit);
            const config = {
              ...DEFAULT_AGENT_CONFIG,
              ...agentToEdit,
              tool_call_loop: agentToEdit.tool_call_loop ?? false,
              reflect_on_tool_use: agentToEdit.reflect_on_tool_use ?? true,
            };
            console.log('Setting initial config:', config);
            setCfg(config);
            setOriginalCfg(config); // Store original config for comparison
          } else {
            console.error('Agent not found:', name);
            setError(`Agent '${name}' not found.`);
          }
        })
        .catch((err) => {
          console.error('Error fetching agent:', err);
          setError('Failed to load agent configuration.');
        })
        .finally(() => setLoading(false));
    } else {
      console.log('Creating new agent - setting default config');
      setCfg(DEFAULT_AGENT_CONFIG);
      setOriginalCfg(null);
    }
  }, [isEditMode, name]);

  useEffect(() => {
    if (cfg.llm.provider) {
      setModelsLoading(true);
      api
        .getModelsByProvider(cfg.llm.provider)
        .then((r) => setModels(r.data.models))
        .catch((err) => {
          console.error('Error fetching models:', err);
          setError('Failed to load models for the selected provider.');
        })
        .finally(() => setModelsLoading(false));
    }
  }, [cfg.llm.provider]);

  useEffect(() => {
    if (error) {
      showNotification(error, 'error');
      setError(null);
    }
  }, [error]);

  useEffect(() => {
    if (success) {
      showNotification(success, 'success');
      setSuccess(null);
    }
  }, [success]);

  // Add logging for input changes
  const handleInputChange = useCallback((path, value) => {
    console.log('Input changed:', { path, value });
    setCfg((prevCfg) => {
      const keys = path.split('.');
      const newCfg = JSON.parse(JSON.stringify(prevCfg)); // Deep clone to ensure proper object references
      let current = newCfg;
      
      // Handle all but the last key by traversing/creating the path
      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) {
          current[keys[i]] = {};
        }
        current = current[keys[i]];
      }

      // Handle the final value assignment
      const lastKey = keys[keys.length - 1];
      if (path === 'tool_call_loop' || path === 'reflect_on_tool_use') {
        current[lastKey] = Boolean(value);
      } else {
        current[lastKey] = value;
      }

      // Special case for provider change
      if (path === 'llm.provider') {
        newCfg.llm.model = '';
      }

      console.log('Config after update:', {
        path,
        value,
        newConfig: newCfg,
        originalConfig: prevCfg
      });

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
      tool_call_loop: Boolean(cfg.tool_call_loop),
      reflect_on_tool_use: Boolean(cfg.reflect_on_tool_use),
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
        // Only navigate away if not in nested mode
        if (!nested) {
          setTimeout(() => nav('/'), 1500);
        } else {
          // In nested mode, update the original config to reflect the new state
          setOriginalCfg(payload);
        }
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

  // Add logging for button disabled state
  const buttonDisabled = loading || (nested && isEditMode && !hasChanges());
  console.log('Save button disabled state:', {
    loading,
    nested,
    isEditMode,
    hasChanges: hasChanges(),
    finalDisabledState: buttonDisabled
  });

  return (
    <Box component={Paper} sx={{ p: { xs: 2, sm: 3 } }}>
      <Typography variant="h5" gutterBottom mb={4}>
        {isEditMode ? `Edit Agent${nested ? '' : ': '+name}` : 'Create New Agent'}
      </Typography>

      <Snackbar 
        open={notification.open}
        autoHideDuration={3000}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseNotification}
          severity={notification.severity}
          sx={{ width: '100%' }}
          elevation={6}
        >
          {notification.message}
        </Alert>
      </Snackbar>

      <Box
        component="form"
        noValidate
        autoComplete="off"
        onSubmit={(e) => {
          e.preventDefault();
          handleSave();
        }}
      >
        <Stack spacing={3}>
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
            fullWidth
          />

          <Divider sx={{ my: 1 }} />

          <Typography variant="h6">Prompts</Typography>
          <TextField
            label="System Prompt"
            multiline
            minRows={4}
            maxRows={20}
            value={cfg.prompt.system}
            onChange={(e) => handleInputChange('prompt.system', e.target.value)}
            disabled={loading}
            helperText="Instructions defining the agent's role, personality, and constraints."
            fullWidth
          />
          <TextField
            label="User Prompt / Initial Task"
            multiline
            minRows={2}
            maxRows={10}
            value={cfg.prompt.user}
            onChange={(e) => handleInputChange('prompt.user', e.target.value)}
            disabled={loading}
            helperText="The initial message or task to start the conversation."
            fullWidth
          />

          <Divider sx={{ my: 1 }} />

          <Typography variant="h6">LLM Configuration</Typography>
          <Grid container spacing={2} sx={{marginLeft: "-16px !important"}}>
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
              <FormControl fullWidth required error={!cfg.llm.model && !!error}>
                <InputLabel>Model Name</InputLabel>
                <Select
                  value={cfg.llm.model}
                  onChange={(e) => handleInputChange('llm.model', e.target.value)}
                  label="Model Name"
                  disabled={modelsLoading || loading}
                >
                  {modelsLoading && (
                    <MenuItem disabled>
                      <CircularProgress size={24} />
                    </MenuItem>
                  )}
                  {!modelsLoading &&
                    models.map((model) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    ))}
                </Select>
                {!cfg.llm.model && !!error && (
                  <FormHelperText>Model Name is required</FormHelperText>
                )}
              </FormControl>
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

          <Divider sx={{ my: 1 }} />
          <Typography variant="h6">Behavior</Typography>

          <FormControlLabel
            control={
              <Switch
                checked={cfg.tool_call_loop ?? false}
                onChange={(e) =>
                  handleInputChange('tool_call_loop', e.target.checked)
                }
                disabled={loading}
              />
            }
            label="Enable Tool Call Loop (Uses LoopingAssistantAgent)"
          />
          <FormHelperText sx={{ mt: -1, mb: 1, ml: 1.8 }}>
            Allows the agent to repeatedly call tools within a single turn if needed.
          </FormHelperText>

          <FormControlLabel
            control={
              <Switch
                checked={cfg.reflect_on_tool_use ?? true}
                onChange={(e) =>
                  handleInputChange('reflect_on_tool_use', e.target.checked)
                }
                disabled={loading}
              />
            }
            label="Reflect on Tool Use (Applies to Looping Agent)"
          />
          <FormHelperText sx={{ mt: -1, mb: 1, ml: 1.8 }}>
            Allows the agent to reflect on the success/failure of tool calls.
          </FormHelperText>
          
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, pt: 2 }}>
            {!nested && (
              <Button
                variant="outlined"
                component={RouterLink}
                to="/"
                disabled={loading}
              >
                Cancel
              </Button>
              )}
            <Button 
              type="submit" 
              variant="contained" 
              disabled={buttonDisabled}
            >
              {loading
                ? 'Saving...'
                : isEditMode
                ? 'Update Agent'
                : 'Create Agent'}
            </Button>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
}