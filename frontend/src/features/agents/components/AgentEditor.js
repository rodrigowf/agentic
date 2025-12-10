import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams, Link as RouterLink } from 'react-router-dom';
import {
  InputBase,
  Button,
  MenuItem,
  Select as MuiSelect,
  Chip,
  Box,
  Typography,
  Paper,
  Alert,
  FormHelperText,
  Grid,
  FormControlLabel,
  Stack,
  CircularProgress,
  Switch,
  Snackbar,
  Collapse,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import api from '../../../api';

// =============================================================================
// CUSTOM FORM COMPONENTS - Unified design using InputBase for consistency
// =============================================================================

// Shared label component
const FieldLabel = ({ label, required, error }) => (
  <Typography
    component="label"
    variant="caption"
    sx={{
      display: 'block',
      mb: 0.5,
      color: error ? 'error.main' : 'text.secondary',
      fontWeight: 500,
    }}
  >
    {label}{required && ' *'}
  </Typography>
);

// Shared field container styles
const fieldContainerSx = {
  backgroundColor: 'rgba(255, 255, 255, 0.05)',
  borderBottom: '1px solid',
  borderColor: 'divider',
  transition: 'border-color 0.2s ease, background-color 0.2s ease',
  '&:hover': {
    borderColor: 'text.secondary',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  '&:focus-within': {
    borderColor: 'primary.main',
    borderBottomWidth: 2,
  },
};

// Shared input styles
const inputSx = {
  px: 1.5,
  py: 0.65,
  width: '100%',
  fontSize: '1rem',
  lineHeight: 1.4,
};

// Custom TextField - using InputBase directly
const TextField = ({ label, helperText, required, error, multiline, minRows, maxRows, type, inputProps, disabled, value, onChange, ...props }) => (
  <Box>
    {label && <FieldLabel label={label} required={required} error={error} />}
    <Box sx={fieldContainerSx}>
      <InputBase
        value={value}
        onChange={onChange}
        multiline={multiline}
        minRows={minRows}
        maxRows={maxRows}
        type={type}
        disabled={disabled}
        inputProps={inputProps}
        sx={inputSx}
        {...props}
      />
    </Box>
    {helperText && (
      <FormHelperText error={error} sx={{ mx: 0, mt: 0.5 }}>
        {helperText}
      </FormHelperText>
    )}
  </Box>
);

// Custom Select - using InputBase as the input component
const Select = ({ label, children, helperText, required, error, multiple, renderValue, disabled, value, onChange, ...props }) => (
  <Box>
    {label && <FieldLabel label={label} required={required} error={error} />}
    <Box sx={fieldContainerSx}>
      <MuiSelect
        value={value}
        onChange={onChange}
        multiple={multiple}
        renderValue={renderValue}
        disabled={disabled}
        variant="standard"
        disableUnderline
        sx={{
          ...inputSx,
          py: 1.25, // Slightly more padding to match TextField height
          '& .MuiSelect-select': {
            p: 0,
            minHeight: 'auto',
            backgroundColor: 'transparent',
            '&:focus': {
              backgroundColor: 'transparent',
            },
          },
          '& .MuiSelect-icon': {
            color: 'text.secondary',
          },
        }}
        MenuProps={{
          PaperProps: {
            sx: {
              mt: 0.5,
              '& .MuiMenuItem-root': {
                fontSize: '1rem',
              },
            },
          },
        }}
        {...props}
      >
        {children}
      </MuiSelect>
    </Box>
    {helperText && (
      <FormHelperText error={error} sx={{ mx: 0, mt: 0.5 }}>
        {helperText}
      </FormHelperText>
    )}
  </Box>
);

// Minimal Section Component - clean divider-based design
const Section = ({ title, children, defaultExpanded = true }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <Box>
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          cursor: 'pointer',
          py: 1,
          mb: expanded ? 2 : 0,
          borderBottom: '1px solid',
          borderColor: 'divider',
          '&:hover': {
            '& .section-title': {
              color: 'primary.main',
            },
          },
        }}
      >
        <Typography
          className="section-title"
          variant="overline"
          sx={{
            flex: 1,
            fontSize: '0.75rem',
            fontWeight: 600,
            letterSpacing: '0.08em',
            color: 'text.secondary',
            transition: 'color 0.15s ease',
          }}
        >
          {title}
        </Typography>
        <ExpandMoreIcon
          fontSize="small"
          sx={{
            color: 'text.disabled',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
          }}
        />
      </Box>
      <Collapse in={expanded}>
        <Box sx={{ pb: 1 }}>
          {children}
        </Box>
      </Collapse>
    </Box>
  );
};

const DEFAULT_AGENT_CONFIG = {
  agent_type: 'assistant',
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
  // CodeExecutorAgent fields
  code_executor: { type: '' },
  system_message: '',
  description: '',
  sources: [],
  model_client_stream: false,
  max_consecutive_auto_reply: null, // Renamed from max_turns
  reflect_on_tool_use: true,
  // Dynamic initialization field
  initialization_function: '',
  // Nested team orchestrator settings
  orchestrator_agent_name: 'Manager',
  orchestrator_pattern: 'NEXT AGENT: <Name>',
};

export default function AgentEditor({nested = false}) {
  // Loading state splits: tools vs agents
  const { name } = useParams();
  const isEditMode = Boolean(name);
  const nav = useNavigate();
  const [allTools, setAllTools] = useState([]);
  const [cfg, setCfg] = useState(DEFAULT_AGENT_CONFIG);
  const [originalCfg, setOriginalCfg] = useState(null);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [models, setModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [notification, setNotification] = useState({ message: '', severity: 'success', open: false });
  // Load existing agents for nested team selection
  const [allAgents, setAllAgents] = useState([]);

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
      max_consecutive_auto_reply: cfg.max_consecutive_auto_reply === null || cfg.max_consecutive_auto_reply === '' ? null : parseInt(cfg.max_consecutive_auto_reply), // Renamed
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
      max_consecutive_auto_reply: originalCfg.max_consecutive_auto_reply === null || originalCfg.max_consecutive_auto_reply === '' ? null : parseInt(originalCfg.max_consecutive_auto_reply), // Renamed
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
    setToolsLoading(true);
    api.getTools()
      .then((r) => {
        setAllTools(r.data);
        console.log('Loaded tools:', r.data);
      })
      .catch((err) => {
        console.error('Error fetching tools:', err);
        setError('Failed to load available tools.');
      })
      .finally(() => setToolsLoading(false));
    // Fetch agents list for nested sub-agent selection
    api.getAgents().then(r => setAllAgents(r.data)).catch(e => console.error('Error fetching agents:', e));
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
      } else if (path === 'max_consecutive_auto_reply') { // Renamed
        current[lastKey] = value === '' ? null : value;
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
      agent_type: cfg.agent_type,
      ...cfg,
      llm: {
        ...cfg.llm,
        temperature: parseFloat(cfg.llm.temperature) || 0.0,
        max_tokens: cfg.llm.max_tokens ? parseInt(cfg.llm.max_tokens) : null,
      },
      max_consecutive_auto_reply: cfg.max_consecutive_auto_reply === null || cfg.max_consecutive_auto_reply === '' ? null : parseInt(cfg.max_consecutive_auto_reply), // Renamed
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

  // Handlers for nested team configuration
  const handleAddSubAgent = () => {
    setCfg(prev => {
      const sub_agents = prev.sub_agents ? [...prev.sub_agents] : [];
      sub_agents.push({
        name: '', tools: [], llm: {provider: 'openai', model: '', temperature: 0.0, max_tokens: null},
        prompt: {system: '', user: ''}, max_consecutive_auto_reply: null, reflect_on_tool_use: true, tool_call_loop: false
      });
      return {...prev, sub_agents};
    });
  };
  const handleRemoveSubAgent = index => {
    setCfg(prev => {
      const sub_agents = prev.sub_agents ? [...prev.sub_agents] : [];
      sub_agents.splice(index,1);
      return {...prev, sub_agents};
    });
  };

  // Handler to select existing agent as sub-agent
  const handleSelectSubAgent = useCallback((index, agentName) => {
    setCfg(prev => {
      const subs = prev.sub_agents ? [...prev.sub_agents] : [];
      const selected = allAgents.find(a => a.name === agentName);
      if (selected) subs[index] = selected;
      return { ...prev, sub_agents: subs };
    });
  }, [allAgents]);

  // Add logging for button disabled state
  const buttonDisabled = loading || (nested && isEditMode && !hasChanges());
  console.log('Save button disabled state:', {
    loading,
    nested,
    isEditMode,
    hasChanges: hasChanges(),
    finalDisabledState: buttonDisabled
  });

  // Helper to get agent type display info
  const getAgentTypeInfo = (type) => {
    const types = {
      'assistant': { label: 'Assistant', description: 'Basic assistant with optional tools' },
      'looping': { label: 'Looping Assistant', description: 'Self-continuing agent with tool loop' },
      'multimodal_tools_looping': { label: 'Multimodal Tools Looping', description: 'Vision-capable agent with tool loop' },
      'dynamic_init_looping': { label: 'Dynamic Init Looping', description: 'Custom initialization with tool loop' },
      'nested_team': { label: 'Nested Team', description: 'Multi-agent coordination' },
      'code_executor': { label: 'Code Executor', description: 'Executes code in sandbox' },
      'looping_code_executor': { label: 'Looping Code Executor', description: 'Code execution with continuation' },
    };
    return types[type] || { label: type, description: '' };
  };

  return (
    <Box component={nested ? Box : Paper} sx={{ p: { xs: 2, sm: 3 }, ...(nested && { border: 'none' }) }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h5"
          sx={{
            fontWeight: 600,
            mb: 0.5,
          }}
        >
          {isEditMode ? `Edit Agent${nested ? '' : `: ${name}`}` : 'Create New Agent'}
        </Typography>
        {isEditMode && cfg.agent_type && (
          <Typography variant="body2" color="text.secondary">
            {getAgentTypeInfo(cfg.agent_type).description}
          </Typography>
        )}
      </Box>

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
        <Stack spacing={4}>
          {/* Basic Info Section */}
          <Section title="Basic Information" defaultExpanded={true}>
            <Grid container spacing={2.5}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Agent Name"
                  value={cfg.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  required
                  disabled={isEditMode || loading}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Select
                  label="Agent Type"
                  value={cfg.agent_type}
                  onChange={(e) => handleInputChange('agent_type', e.target.value)}
                  disabled={loading}
                >
                  <MenuItem value="assistant">Assistant</MenuItem>
                  <MenuItem value="looping">Looping Assistant</MenuItem>
                  <MenuItem value="multimodal_tools_looping">Multimodal Tools Looping</MenuItem>
                  <MenuItem value="dynamic_init_looping">Dynamic Init Looping</MenuItem>
                  <MenuItem value="nested_team">Nested Team</MenuItem>
                  <MenuItem value="code_executor">Code Executor</MenuItem>
                  <MenuItem value="looping_code_executor">Looping Code Executor</MenuItem>
                </Select>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Description"
                  multiline
                  minRows={2}
                  maxRows={4}
                  value={cfg.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  disabled={loading}
                />
              </Grid>
            </Grid>
          </Section>

          {/* Model Configuration Section */}
          <Section title="Model" defaultExpanded={true}>
            <Grid container spacing={2.5}>
              <Grid item xs={12} sm={6} md={3}>
                <Select
                  label="Provider"
                  required
                  error={!cfg.llm.provider && !!error}
                  value={cfg.llm.provider}
                  onChange={(e) => handleInputChange('llm.provider', e.target.value)}
                  disabled={loading}
                >
                  <MenuItem value="openai">OpenAI</MenuItem>
                  <MenuItem value="anthropic">Anthropic</MenuItem>
                  <MenuItem value="gemini">Gemini</MenuItem>
                </Select>
              </Grid>
              <Grid item xs={12} sm={6} md={5}>
                <Select
                  label="Model"
                  required
                  error={!cfg.llm.model && !!error}
                  value={cfg.llm.model}
                  onChange={(e) => handleInputChange('llm.model', e.target.value)}
                  disabled={loading || modelsLoading || !cfg.llm.provider}
                  helperText={modelsLoading ? 'Loading...' : undefined}
                >
                  {modelsLoading ? (
                    <MenuItem value="" disabled>
                      <CircularProgress size={16} sx={{ mr: 1 }} />
                      Loading...
                    </MenuItem>
                  ) : models.length === 0 && cfg.llm.provider ? (
                    <MenuItem value="" disabled>
                      No models available
                    </MenuItem>
                  ) : (
                    models.map((model) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    ))
                  )}
                </Select>
              </Grid>
              <Grid item xs={6} sm={6} md={2}>
                <TextField
                  type="number"
                  label="Temperature"
                  value={cfg.llm.temperature}
                  onChange={(e) => handleInputChange('llm.temperature', e.target.value)}
                  inputProps={{ step: '0.1', min: '0', max: '2' }}
                  disabled={loading}
                />
              </Grid>
              <Grid item xs={6} sm={6} md={2}>
                <TextField
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
                  disabled={loading}
                />
              </Grid>
            </Grid>
          </Section>

          {/* Initialization Function for dynamic_init_looping */}
          {cfg.agent_type === 'dynamic_init_looping' && (
            <Section title="Initialization" defaultExpanded={true}>
              <TextField
                label="Initialization Function"
                value={cfg.initialization_function || ''}
                onChange={(e) => handleInputChange('initialization_function', e.target.value)}
                disabled={loading}
                helperText="e.g., memory.initialize_memory_agent"
              />
            </Section>
          )}

          {/* Tools Section */}
          {cfg.agent_type !== 'nested_team' && cfg.agent_type !== 'code_executor' && (
            <Section title="Tools" defaultExpanded={true}>
              <Select
                label="Select Tools"
                multiple
                value={cfg.tools}
                onChange={(e) => handleInputChange('tools', e.target.value)}
                disabled={toolsLoading}
                helperText={toolsLoading ? 'Loading...' : undefined}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip
                        key={value}
                        label={value}
                        size="small"
                        sx={{ borderRadius: 1 }}
                        onDelete={() => {
                          const newTools = cfg.tools.filter(tool => tool !== value);
                          handleInputChange('tools', newTools);
                        }}
                        onMouseDown={(event) => event.stopPropagation()}
                      />
                    ))}
                  </Box>
                )}
              >
                {allTools.map((tool) => (
                  <MenuItem key={tool.name} value={tool.name}>
                    {tool.name}
                  </MenuItem>
                ))}
              </Select>
            </Section>
          )}

          {/* Behavior Section */}
          {(cfg.agent_type === 'looping' || cfg.agent_type === 'multimodal_tools_looping') && (
            <Section title="Behavior" defaultExpanded={true}>
              <Grid container spacing={2.5} alignItems="flex-end">
                <Grid item xs={12} sm={4}>
                  <TextField
                    type="number"
                    label="Max Auto-Replies"
                    value={cfg.max_consecutive_auto_reply ?? ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      handleInputChange('max_consecutive_auto_reply', val === '' ? null : (Number.isInteger(parseInt(val)) ? parseInt(val) : val));
                    }}
                    inputProps={{ min: '1' }}
                    disabled={loading}
                  />
                </Grid>
                <Grid item xs={12} sm={8}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={cfg.reflect_on_tool_use ?? true}
                        onChange={(e) => handleInputChange('reflect_on_tool_use', e.target.checked)}
                        disabled={loading}
                      />
                    }
                    label="Reflect on tool use"
                  />
                </Grid>
              </Grid>
            </Section>
          )}

          {/* Nested Team Section */}
          {cfg.agent_type === 'nested_team' && (
            <>
              <Section title="Team Configuration" defaultExpanded={true}>
                <Grid container spacing={2.5} alignItems="flex-end">
                  <Grid item xs={12} sm={4}>
                    <Select
                      label="Team Mode"
                      value={cfg.mode || 'round_robin'}
                      onChange={(e) => handleInputChange('mode', e.target.value)}
                      disabled={loading}
                    >
                      <MenuItem value="round_robin">Round Robin</MenuItem>
                      <MenuItem value="selector">Selector</MenuItem>
                    </Select>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      type="number"
                      label="Max Messages"
                      value={cfg.max_consecutive_auto_reply ?? ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        handleInputChange('max_consecutive_auto_reply', val === '' ? null : (Number.isInteger(parseInt(val)) ? parseInt(val) : val));
                      }}
                      inputProps={{ min: '1' }}
                      disabled={loading}
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={cfg.include_inner_dialog ?? true}
                          onChange={(e) => handleInputChange('include_inner_dialog', e.target.checked)}
                          disabled={loading}
                        />
                      }
                      label="Expose inner dialog"
                    />
                  </Grid>

                  {/* Selector Mode Options */}
                  {cfg.mode === 'selector' && (
                    <>
                      <Grid item xs={12} sm={4}>
                        <Select
                          label="Selection Strategy"
                          value={(cfg.orchestrator_prompt && !['', '__function__'].includes(cfg.orchestrator_prompt.trim())) ? 'llm' : 'pattern'}
                          onChange={(e) => {
                            const v = e.target.value;
                            if (v === 'pattern') {
                              handleInputChange('orchestrator_prompt', '__function__');
                            } else {
                              if (!cfg.orchestrator_prompt || cfg.orchestrator_prompt.trim() in ['', '__function__']) {
                                handleInputChange('orchestrator_prompt', '');
                              }
                            }
                          }}
                          disabled={loading}
                        >
                          <MenuItem value="pattern">Pattern-based</MenuItem>
                          <MenuItem value="llm">LLM Prompt</MenuItem>
                        </Select>
                      </Grid>

                      {(!cfg.orchestrator_prompt || cfg.orchestrator_prompt.trim() === '' || cfg.orchestrator_prompt.trim() === '__function__') && (
                        <>
                          <Grid item xs={12} sm={4}>
                            <TextField
                              label="Orchestrator Name"
                              value={cfg.orchestrator_agent_name || 'Manager'}
                              onChange={(e) => handleInputChange('orchestrator_agent_name', e.target.value)}
                              disabled={loading}
                            />
                          </Grid>
                          <Grid item xs={12} sm={4}>
                            <TextField
                              label="Selection Pattern"
                              value={cfg.orchestrator_pattern || 'NEXT AGENT: <Name>'}
                              onChange={(e) => handleInputChange('orchestrator_pattern', e.target.value)}
                              disabled={loading}
                            />
                          </Grid>
                        </>
                      )}

                      {(cfg.orchestrator_prompt && !['', '__function__'].includes(cfg.orchestrator_prompt.trim())) && (
                        <Grid item xs={12}>
                          <TextField
                            label="Selector Prompt"
                            value={cfg.orchestrator_prompt || ''}
                            onChange={(e) => handleInputChange('orchestrator_prompt', e.target.value)}
                            multiline
                            minRows={2}
                            maxRows={6}
                          />
                        </Grid>
                      )}
                    </>
                  )}
                </Grid>
              </Section>

              <Section title="Sub-Agents" defaultExpanded={true}>
                <Stack spacing={1.5}>
                  {(cfg.sub_agents || []).map((sub, idx) => (
                    <Grid container spacing={2} key={idx} alignItems="flex-end">
                      <Grid item xs>
                        <Select
                          label={`Agent ${idx + 1}`}
                          value={sub.name || ''}
                          onChange={(e) => handleSelectSubAgent(idx, e.target.value)}
                        >
                          {allAgents.map(agent => (
                            <MenuItem key={agent.name} value={agent.name}>
                              {agent.name}
                            </MenuItem>
                          ))}
                        </Select>
                      </Grid>
                      <Grid item>
                        <Button
                          size="small"
                          color="inherit"
                          onClick={() => handleRemoveSubAgent(idx)}
                          sx={{ color: 'text.secondary', minWidth: 'auto', mb: 1 }}
                        >
                          Remove
                        </Button>
                      </Grid>
                    </Grid>
                  ))}
                  <Box>
                    <Button
                      size="small"
                      onClick={handleAddSubAgent}
                      sx={{ mt: 1 }}
                    >
                      + Add agent
                    </Button>
                  </Box>
                </Stack>
              </Section>
            </>
          )}

          {/* Code Executor Section */}
          {(cfg.agent_type === 'code_executor' || cfg.agent_type === 'looping_code_executor') && (
            <Section title="Code Executor" defaultExpanded={true}>
              <Grid container spacing={2.5}>
                <Grid item xs={12} sm={6}>
                  <Select
                    label="Executor Type"
                    value={cfg.code_executor.type}
                    onChange={(e) => handleInputChange('code_executor.type', e.target.value)}
                    disabled={loading}
                  >
                    <MenuItem value="local">Local</MenuItem>
                  </Select>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Working Directory"
                    value={cfg.code_executor.work_dir || ''}
                    onChange={(e) => handleInputChange('code_executor.work_dir', e.target.value)}
                    disabled={loading}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    multiline
                    minRows={3}
                    maxRows={8}
                    label="System Message"
                    value={cfg.system_message}
                    onChange={(e) => handleInputChange('system_message', e.target.value)}
                    disabled={loading}
                  />
                </Grid>
                <Grid item xs={12} sm={8}>
                  <TextField
                    label="Sources"
                    value={cfg.sources.join(', ')}
                    onChange={(e) => handleInputChange('sources', e.target.value.split(',').map(s => s.trim()))}
                    disabled={loading}
                    helperText="Comma-separated"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={cfg.model_client_stream}
                        onChange={(e) => handleInputChange('model_client_stream', e.target.checked)}
                        disabled={loading}
                      />
                    }
                    label="Stream responses"
                    sx={{ mt: 3 }}
                  />
                </Grid>
              </Grid>
            </Section>
          )}

          {/* System Prompt Section - at the end for all applicable agent types */}
          {(cfg.agent_type === 'assistant' || cfg.agent_type === 'looping' || cfg.agent_type === 'multimodal_tools_looping' || cfg.agent_type === 'dynamic_init_looping') && (
            <Section title="System Prompt" defaultExpanded={true}>
              <TextField
                label="Instructions"
                multiline
                minRows={4}
                maxRows={20}
                value={cfg.prompt.system}
                onChange={(e) => handleInputChange('prompt.system', e.target.value)}
                disabled={loading}
              />
            </Section>
          )}

          {/* Action Buttons */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 2,
              pt: 4,
            }}
          >
            {!nested && (
              <Button
                component={RouterLink}
                to="/"
                disabled={loading}
                sx={{ color: 'text.secondary' }}
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              variant="contained"
              disabled={buttonDisabled}
            >
              {loading ? (
                <>
                  <CircularProgress size={16} color="inherit" sx={{ mr: 1 }} />
                  Saving...
                </>
              ) : isEditMode ? (
                'Save Changes'
              ) : (
                'Create Agent'
              )}
            </Button>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
}