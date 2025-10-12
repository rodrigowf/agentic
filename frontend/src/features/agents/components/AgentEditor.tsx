import { FC, useEffect, useState, useCallback, FormEvent, ChangeEvent } from 'react';
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
  SelectChangeEvent,
} from '@mui/material';
import api from '../../../api';
import { AgentConfig, AgentSummary, AgentType, ToolFile } from '../../../types';

// ============================================================================
// Type Definitions
// ============================================================================

interface AgentEditorProps {
  nested?: boolean;
}

interface Params extends Record<string, string | undefined> {
  name?: string;
}

interface NotificationState {
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
  open: boolean;
}

// ============================================================================
// Default Configuration
// ============================================================================

const DEFAULT_AGENT_CONFIG: AgentConfig = {
  agent_type: 'looping' as AgentType,
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
  code_executor: { type: '' },
  system_message: '',
  description: '',
  sources: [],
  model_client_stream: false,
  max_consecutive_auto_reply: null,
  reflect_on_tool_use: true,
  terminate_on_text: false,
  tool_call_loop: false,
  sub_agents: null,
  mode: null,
  orchestrator_prompt: null,
  include_inner_dialog: true,
};

// ============================================================================
// AgentEditor Component
// ============================================================================

const AgentEditor: FC<AgentEditorProps> = ({ nested = false }) => {
  const { name } = useParams<Params>();
  const isEditMode = Boolean(name);
  const nav = useNavigate();
  const [allTools, setAllTools] = useState<ToolFile[]>([]);
  const [cfg, setCfg] = useState<AgentConfig>(DEFAULT_AGENT_CONFIG);
  const [originalCfg, setOriginalCfg] = useState<AgentConfig | null>(null);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [notification, setNotification] = useState<NotificationState>({
    message: '',
    severity: 'success',
    open: false
  });
  const [allAgents, setAllAgents] = useState<AgentSummary[]>([]);

  const handleCloseNotification = () => {
    setNotification(prev => ({ ...prev, open: false }));
  };

  const showNotification = (message: string, severity: 'success' | 'error' | 'warning' | 'info' = 'success') => {
    setNotification({ message, severity, open: true });
    setTimeout(() => {
      setNotification(prev => ({ ...prev, open: false }));
    }, 3000);
  };

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

    const cleanCfg = {
      ...cfg,
      llm: {
        ...cfg.llm,
        temperature: parseFloat(String(cfg.llm.temperature)) || 0.0,
        max_tokens: cfg.llm.max_tokens ? parseInt(String(cfg.llm.max_tokens)) : null,
      },
      prompt: {
        system: cfg.prompt?.system || '',
        user: cfg.prompt?.user || ''
      },
      max_consecutive_auto_reply: cfg.max_consecutive_auto_reply === null ? null : parseInt(String(cfg.max_consecutive_auto_reply)),
      tool_call_loop: Boolean(cfg.tool_call_loop),
      reflect_on_tool_use: Boolean(cfg.reflect_on_tool_use),
    };

    const cleanOriginalCfg = {
      ...originalCfg,
      llm: {
        ...originalCfg.llm,
        temperature: parseFloat(String(originalCfg.llm.temperature)) || 0.0,
        max_tokens: originalCfg.llm.max_tokens ? parseInt(String(originalCfg.llm.max_tokens)) : null,
      },
      prompt: {
        system: originalCfg.prompt?.system || '',
        user: originalCfg.prompt?.user || ''
      },
      max_consecutive_auto_reply: originalCfg.max_consecutive_auto_reply === null ? null : parseInt(String(originalCfg.max_consecutive_auto_reply)),
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
        setAllTools(r.data.tools);
        console.log('Loaded tools:', r.data.tools);
      })
      .catch((err) => {
        console.error('Error fetching tools:', err);
        setError('Failed to load available tools.');
      })
      .finally(() => setToolsLoading(false));

    api.getAgents()
      .then(r => setAllAgents(r.data.agents))
      .catch(e => console.error('Error fetching agents:', e));
  }, []);

  useEffect(() => {
    if (isEditMode && name) {
      console.log('Loading agent in edit mode:', { name });
      setLoading(true);
      setError(null);
      api
        .getAgents()
        .then((r) => {
          const agentToEdit = r.data.agents.find((x: AgentSummary) => x.name === name);
          if (agentToEdit) {
            console.log('Found agent to edit:', agentToEdit);
            const config = {
              ...DEFAULT_AGENT_CONFIG,
              ...agentToEdit,
            };
            console.log('Setting initial config:', config);
            setCfg(config);
            setOriginalCfg(config);
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

  const handleInputChange = useCallback((path: string, value: any) => {
    console.log('Input changed:', { path, value });
    setCfg((prevCfg) => {
      const keys = path.split('.');
      const newCfg = JSON.parse(JSON.stringify(prevCfg)) as AgentConfig;
      let current: any = newCfg;

      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) {
          current[keys[i]] = {};
        }
        current = current[keys[i]];
      }

      const lastKey = keys[keys.length - 1];
      if (path === 'tool_call_loop' || path === 'reflect_on_tool_use') {
        current[lastKey] = Boolean(value);
      } else if (path === 'max_consecutive_auto_reply') {
        current[lastKey] = value === '' || value === null ? null : value;
      } else {
        current[lastKey] = value;
      }

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

    const payload: AgentConfig = {
      ...cfg,
      llm: {
        ...cfg.llm,
        temperature: parseFloat(String(cfg.llm.temperature)) || 0.0,
        max_tokens: cfg.llm.max_tokens ? parseInt(String(cfg.llm.max_tokens)) : null,
      },
      max_consecutive_auto_reply: cfg.max_consecutive_auto_reply === null ? null : parseInt(String(cfg.max_consecutive_auto_reply)),
      reflect_on_tool_use: Boolean(cfg.reflect_on_tool_use),
    };

    const action = isEditMode && name
      ? api.updateAgent(name, payload)
      : api.createAgent(payload);

    action
      .then(() => {
        setSuccess(
          `Agent '${cfg.name}' ${
            isEditMode ? 'updated' : 'created'
          } successfully!`
        );
        if (!nested) {
          setTimeout(() => nav('/'), 1500);
        } else {
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

  const handleAddSubAgent = () => {
    setCfg(prev => {
      const sub_agents = prev.sub_agents ? [...prev.sub_agents] : [];
      sub_agents.push({
        name: '',
        agent_type: 'looping' as AgentType,
        tools: [],
        llm: { provider: 'openai', model: '', temperature: 0.0, max_tokens: null },
        prompt: { system: '', user: '' },
        code_executor: null,
        model_client_stream: false,
        sources: null,
        description: '',
        system_message: null,
        max_consecutive_auto_reply: null,
        reflect_on_tool_use: true,
        terminate_on_text: false,
        tool_call_loop: false,
        sub_agents: null,
        mode: null,
        orchestrator_prompt: null,
        include_inner_dialog: true,
      });
      return { ...prev, sub_agents };
    });
  };

  const handleRemoveSubAgent = (index: number) => {
    setCfg(prev => {
      const sub_agents = prev.sub_agents ? [...prev.sub_agents] : [];
      sub_agents.splice(index, 1);
      return { ...prev, sub_agents };
    });
  };

  const handleSelectSubAgent = useCallback((index: number, agentName: string) => {
    setCfg(prev => {
      const subs = prev.sub_agents ? [...prev.sub_agents] : [];
      const selected = allAgents.find(a => a.name === agentName);
      if (selected) {
        // Convert AgentSummary to full AgentConfig
        const fullAgent: AgentConfig = {
          ...DEFAULT_AGENT_CONFIG,
          ...selected,
          llm: selected.llm || DEFAULT_AGENT_CONFIG.llm,
        };
        subs[index] = fullAgent;
      }
      return { ...prev, sub_agents: subs };
    });
  }, [allAgents]);

  const buttonDisabled = loading || (nested && isEditMode && !hasChanges());
  console.log('Save button disabled state:', {
    loading,
    nested,
    isEditMode,
    hasChanges: hasChanges(),
    finalDisabledState: buttonDisabled
  });

  return (
    <Box component={nested ? Box : Paper} sx={{ p: { xs: 2, sm: 3 }, ...(nested && { border: 'none' }) }}>
      <Typography variant="h5" gutterBottom mb={4}>
        {isEditMode ? `Edit Agent${nested ? '' : ': ' + name}` : 'Create New Agent'}
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
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          handleSave();
        }}
      >
        <Stack spacing={3}>
          <TextField
            label="Agent Name"
            value={cfg.name}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('name', e.target.value)}
            required
            disabled={isEditMode || loading}
          />
          <FormControl fullWidth>
            <InputLabel>Agent Type</InputLabel>
            <Select
              label="Agent Type"
              value={cfg.agent_type}
              onChange={(e: SelectChangeEvent) => handleInputChange('agent_type', e.target.value)}
              disabled={loading}
            >
              <MenuItem value="assistant">Assistant</MenuItem>
              <MenuItem value="looping">Looping Assistant</MenuItem>
              <MenuItem value="multimodal_tools_looping">Multimodal Tools Looping Agent</MenuItem>
              <MenuItem value="nested_team">Nested Team Agent</MenuItem>
              <MenuItem value="code_executor">Code Executor</MenuItem>
              <MenuItem value="looping_code_executor">Looping Code Executor</MenuItem>
            </Select>
          </FormControl>

          <TextField
            label="Description"
            multiline
            minRows={2}
            maxRows={6}
            value={cfg.description}
            onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('description', e.target.value)}
            disabled={loading}
            helperText="Short description of the agent's purpose."
            fullWidth
          />

          <Divider />

          {(cfg.agent_type === 'assistant' || cfg.agent_type === 'looping' || cfg.agent_type === 'multimodal_tools_looping') && (
            <Box>
              <Stack spacing={2}>
                <TextField
                  label="System Prompt"
                  multiline
                  minRows={4}
                  maxRows={20}
                  value={cfg.prompt.system}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('prompt.system', e.target.value)}
                  disabled={loading}
                  helperText="Instructions defining the agent's role, personality, and constraints."
                  fullWidth
                />
              </Stack>
            </Box>
          )}

          {cfg.agent_type !== 'nested_team' && cfg.agent_type !== 'code_executor' && (
            <Stack spacing={2}>
              <FormControl fullWidth disabled={toolsLoading} size="small">
                <InputLabel id="tools-select-label">Tools</InputLabel>
                <Select
                  labelId="tools-select-label"
                  multiple
                  value={cfg.tools}
                  onChange={(e: SelectChangeEvent<string[]>) => handleInputChange('tools', e.target.value)}
                  input={<OutlinedInput label="Tools" size="small" />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {(selected as string[]).map((value) => (
                        <Chip
                          key={value}
                          label={value}
                          onDelete={() => {
                            const newTools = cfg.tools.filter(tool => tool !== value);
                            handleInputChange('tools', newTools);
                          }}
                          onMouseDown={(event) => {
                            event.stopPropagation();
                          }}
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
                {(!toolsLoading && allTools.length === 0) && (
                  <FormHelperText>No tools found. Make sure the backend has loaded them.</FormHelperText>
                )}
                {!toolsLoading && (
                  <FormHelperText>Select the tools this agent can use.</FormHelperText>
                )}
              </FormControl>
            </Stack>
          )}

          {(cfg.agent_type === 'looping' || cfg.agent_type === 'multimodal_tools_looping') && (
            <Box>
              <Stack spacing={2}>
                <FormControl fullWidth sx={{ width: '300px' }}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Max Consecutive Auto-Reply"
                    value={cfg.max_consecutive_auto_reply ?? ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => {
                      const val = e.target.value;
                      handleInputChange('max_consecutive_auto_reply', val === '' ? null : (Number.isInteger(parseInt(val)) ? parseInt(val) : val));
                    }}
                    inputProps={{ min: '1' }}
                    helperText="Optional. Max auto-replies."
                    disabled={loading}
                  />
                </FormControl>
                <FormControl fullWidth>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={cfg.reflect_on_tool_use ?? true}
                        onChange={(e: ChangeEvent<HTMLInputElement>) =>
                          handleInputChange('reflect_on_tool_use', e.target.checked)
                        }
                        disabled={loading}
                      />
                    }
                    label="Reflect on Tool Use"
                  />
                  <FormHelperText sx={{ mt: -1, mb: 1, ml: 1.8 }}>
                    Allows the agent to reflect on the success/failure of tool calls.
                  </FormHelperText>
                </FormControl>
              </Stack>
            </Box>
          )}

          {cfg.agent_type === 'nested_team' && (
            <Box sx={{ pb: 2 }}>
              <Typography variant="h6" sx={{ mb: 3 }}>Inner GroupChat Config</Typography>

              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={24} sm={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={cfg.include_inner_dialog ?? true}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('include_inner_dialog', e.target.checked)}
                        disabled={loading}
                      />
                    }
                    label="Expose Inner Dialog"
                  />
                </Grid>
                <Grid item xs={24} sm={12}>
                  <FormControl fullWidth size='small'>
                    <InputLabel>Team Mode</InputLabel>
                    <Select
                      label="Team Mode"
                      value={cfg.mode || 'round_robin'}
                      onChange={(e: SelectChangeEvent) => handleInputChange('mode', e.target.value)}
                      disabled={loading}
                    >
                      <MenuItem value="round_robin">Round Robin</MenuItem>
                      <MenuItem value="selector">Selector (Orchestrator)</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                {cfg.mode === 'selector' && (
                  <>
                    <Grid item xs={12} sm={6}>
                      <FormControl fullWidth size='small'>
                        <InputLabel>Selection Strategy</InputLabel>
                        <Select
                          label="Selection Strategy"
                          value={(cfg.orchestrator_prompt && !['', '__function__'].includes(cfg.orchestrator_prompt.trim())) ? 'llm' : 'pattern'}
                          onChange={(e: SelectChangeEvent) => {
                            const v = e.target.value;
                            if (v === 'pattern') {
                              handleInputChange('orchestrator_prompt', '__function__');
                            } else {
                              if (!cfg.orchestrator_prompt || ['', '__function__'].includes(cfg.orchestrator_prompt.trim())) {
                                handleInputChange('orchestrator_prompt', '');
                              }
                            }
                          }}
                          disabled={loading}
                        >
                          <MenuItem value='pattern'>Pattern (NEXT AGENT: &lt;Name&gt;)</MenuItem>
                          <MenuItem value='llm'>LLM Prompt</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    {(cfg.orchestrator_prompt && !['', '__function__'].includes(cfg.orchestrator_prompt.trim())) && (
                      <Grid item xs={12}>
                        <TextField
                          label="Selector Prompt"
                          value={cfg.orchestrator_prompt || ''}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('orchestrator_prompt', e.target.value)}
                          multiline
                          minRows={2}
                          maxRows={12}
                          fullWidth
                          helperText="LLM decides next agent. Leave empty & switch strategy to use pattern-based selection."
                        />
                      </Grid>
                    )}
                  </>
                )}
              </Grid>

              <FormControl fullWidth sx={{ width: '300px', mb: 3 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Max Consecutive Auto-Reply"
                  value={cfg.max_consecutive_auto_reply ?? ''}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    const val = e.target.value;
                    handleInputChange('max_consecutive_auto_reply', val === '' ? null : (Number.isInteger(parseInt(val)) ? parseInt(val) : val));
                  }}
                  inputProps={{ min: '1' }}
                  helperText="Optional. Team message limit (default 5)."
                  disabled={loading}
                />
              </FormControl>

              {cfg.mode === 'selector' && (!cfg.orchestrator_prompt || cfg.orchestrator_prompt.trim() === '' || cfg.orchestrator_prompt.trim() === '__function__') && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" sx={{ mb: 2 }}>Orchestrator Configuration</Typography>
                  <Stack spacing={2}>
                    <TextField
                      fullWidth
                      label="Orchestrator Agent Name"
                      value={(cfg as any).orchestrator_agent_name || 'Manager'}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('orchestrator_agent_name', e.target.value)}
                      disabled={loading}
                      helperText="Name of the agent that orchestrates the team (default: Manager)."
                      sx={{ maxWidth: '400px' }}
                    />
                    <TextField
                      fullWidth
                      label="Selection Pattern"
                      value={(cfg as any).orchestrator_pattern || 'NEXT AGENT: <Name>'}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('orchestrator_pattern', e.target.value)}
                      disabled={loading}
                      helperText="Pattern to identify next agent. Use <Name> as placeholder (e.g., 'NEXT AGENT: <Name>')."
                      sx={{ maxWidth: '600px' }}
                    />
                  </Stack>
                </Box>
              )}

              <Typography variant="h6" sx={{ mb: 2 }}>Sub-Agents</Typography>
              <Grid container spacing={2}>
                {(cfg.sub_agents || []).map((sub, idx) => (
                  <Grid item xs={12} key={idx}>
                    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
                      <FormControl fullWidth size='small'>
                        <InputLabel>Sub-Agent {idx + 1}</InputLabel>
                        <Select
                          value={typeof sub === 'string' ? sub : sub.name || ''}
                          label={`Sub-Agent ${idx + 1}`}
                          onChange={(e: SelectChangeEvent) => handleSelectSubAgent(idx, e.target.value)}
                        >
                          {allAgents.map(agent => (
                            <MenuItem key={agent.name} value={agent.name}>
                              {agent.name}
                            </MenuItem>
                          ))}
                        </Select>
                        <FormHelperText>Select an existing agent</FormHelperText>
                      </FormControl>
                      <Button color="error" onClick={() => handleRemoveSubAgent(idx)}>Remove</Button>
                    </Box>
                  </Grid>
                ))}
                <Grid item xs={12}>
                  <Button variant="outlined" onClick={handleAddSubAgent} sx={{ alignSelf: 'flex-start' }}>
                    Add Sub-Agent
                  </Button>
                </Grid>
              </Grid>
            </Box>
          )}

          {(cfg.agent_type === 'code_executor' || cfg.agent_type === 'looping_code_executor') && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>Code Executor Settings</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth size='small'>
                    <InputLabel>Executor Type</InputLabel>
                    <Select
                      value={cfg.code_executor?.type || ''}
                      label="Executor Type"
                      onChange={(e: SelectChangeEvent) => handleInputChange('code_executor.type', e.target.value)}
                      disabled={loading}
                    >
                      <MenuItem value="local">Local</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Working Directory"
                    value={(cfg.code_executor as any)?.work_dir || ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('code_executor.work_dir', e.target.value)}
                    disabled={loading}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    multiline
                    minRows={2}
                    maxRows={12}
                    label="System Message"
                    value={cfg.system_message || ''}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('system_message', e.target.value)}
                    disabled={loading}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Sources (comma-separated)"
                    value={(cfg.sources || []).join(',')}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('sources', e.target.value.split(',').map(s => s.trim()))}
                    disabled={loading}
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={cfg.model_client_stream}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('model_client_stream', e.target.checked)}
                        disabled={loading}
                      />
                    }
                    label="Stream Model Client"
                  />
                </Grid>
              </Grid>
            </Box>
          )}

          <Divider />

          <Box>
            <Typography variant="h6" sx={{ mb: 4 }}>LLM Configuration</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size='small' required error={!cfg.llm.provider && !!error}>
                  <InputLabel>LLM Provider</InputLabel>
                  <Select
                    value={cfg.llm.provider}
                    onChange={(e: SelectChangeEvent) => handleInputChange('llm.provider', e.target.value)}
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
                <FormControl fullWidth size='small' required error={!cfg.llm.model && !!error}>
                  <InputLabel>Model Name</InputLabel>
                  <Select
                    value={cfg.llm.model}
                    onChange={(e: SelectChangeEvent) => handleInputChange('llm.model', e.target.value)}
                    label="Model Name"
                    disabled={loading || modelsLoading || !cfg.llm.provider}
                  >
                    {modelsLoading ? (
                      <MenuItem value="" disabled>
                        <CircularProgress size={20} sx={{ mr: 1 }} />
                        Loading models...
                      </MenuItem>
                    ) : models.length === 0 && cfg.llm.provider ? (
                      <MenuItem value="" disabled>
                        No models found for {cfg.llm.provider} or failed to load.
                      </MenuItem>
                    ) : (
                      models.map((model) => (
                        <MenuItem key={model} value={model}>
                          {model}
                        </MenuItem>
                      ))
                    )}
                  </Select>
                  {(!cfg.llm.model && !!error) && (
                    <FormHelperText>Model Name is required</FormHelperText>
                  )}
                  {!modelsLoading && models.length === 0 && cfg.llm.provider && (
                    <FormHelperText>Ensure API key for {cfg.llm.provider} is set in the backend.</FormHelperText>
                  )}
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Temperature"
                  value={cfg.llm.temperature}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('llm.temperature', e.target.value)}
                  inputProps={{ step: '0.1', min: '0', max: '2' }}
                  helperText="0 = deterministic, >0 = creative"
                  disabled={loading}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Max Tokens"
                  value={cfg.llm.max_tokens ?? ''}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
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
            </Grid>
          </Box>

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
};

export default AgentEditor;
