import React, { useState, useEffect, useCallback } from 'react';
import { Button, Typography, Box, TextField, Alert, Paper, CircularProgress, Collapse, IconButton, Stack } from '@mui/material';
import { useNavigate, useParams, Link as RouterLink } from 'react-router-dom';
import CloseIcon from '@mui/icons-material/Close';
import api from '../../../api';
import CodeEditor from './CodeEditor';

const DEFAULT_TOOL_CODE = `"""
Define multiple tools in this file.
Each tool needs its own function and a corresponding ToolDefinition instance.
Make sure to set the 'function' attribute in each ToolDefinition.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Callable

# Placeholder ToolDefinition (Backend loader uses the real one)
class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable | None = None
    filename: str | None = None

# --- Tool 1: Simple Greeter ---

class GreeterInput(BaseModel):
    name: str = Field(description="The name of the person to greet.")

def greet(name: str) -> str:
    """Greets the person."""
    return f"Hello, {name}!"

greet_tool_def = ToolDefinition(
    name="greet",
    description="Greets the specified person.",
    parameters=GreeterInput.model_json_schema(),
    function=greet # CRITICAL: Assign the function object
)

# --- Tool 2: Simple Adder ---

class AdderInput(BaseModel):
    num1: int = Field(description="The first number.")
    num2: int = Field(description="The second number.")

def add_numbers(num1: int, num2: int) -> int:
    """Adds two numbers together."""
    return num1 + num2

add_numbers_tool_def = ToolDefinition(
    name="add_numbers",
    description="Adds two integer numbers.",
    parameters=AdderInput.model_json_schema(),
    function=add_numbers # CRITICAL: Assign the function object
)

# You can add more functions and ToolDefinition instances below
`;

export default function ToolEditor({ nested = false, filenameOverride, onSaved }) {
  const params = useParams();
  const routeFilenameParam = params.filename;
  const routeFilename = filenameOverride !== undefined ? filenameOverride : routeFilenameParam;
  const isEditMode = Boolean(routeFilename);
  const nav = useNavigate();

  const [filename, setFilename] = useState(routeFilename || '');
  const [code, setCode] = useState('');
  const [initialCode, setInitialCode] = useState(''); // To check for changes
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // State for generation
  const [generationPrompt, setGenerationPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState(null);

  useEffect(() => {
    if (isEditMode) {
      setFilename(routeFilename || '');
      setLoading(true);
      setError(null);
      api.getToolContent(routeFilename)
        .then(res => {
          setCode(res.data);
          setInitialCode(res.data);
        })
        .catch(err => {
          console.error("Error fetching tool content:", err);
          setError(`Failed to load tool '${routeFilename}'. ${err.response?.data || err.message}`);
        })
        .finally(() => setLoading(false));
    } else {
      // New tool mode
      setCode(DEFAULT_TOOL_CODE);
      setInitialCode(DEFAULT_TOOL_CODE);
      setFilename(''); // Ensure filename is empty for new tool
    }
    // Reset messages on mode change
    setError(null);
    setSuccess(null);
    // Reset generation state on mode change
    setGenerationPrompt('');
    setGenerating(false);
    setGenerationError(null);
  }, [isEditMode, routeFilename]);

  const handleGenerateCode = useCallback(() => {
    if (!generationPrompt.trim()) {
      setGenerationError("Please enter a description for the tool you want to generate.");
      return;
    }
    setGenerating(true);
    setGenerationError(null);
    setError(null); // Clear other errors
    setSuccess(null);

    api.generateToolCode(generationPrompt)
      .then(generatedCode => {
        setCode(generatedCode.data); // API returns plain text in data
        setSuccess("Code generated successfully! Review and save.");
        // Optionally clear prompt after generation
        // setGenerationPrompt('');
      })
      .catch(err => {
        console.error("Error generating tool code:", err);
        setGenerationError(`Failed to generate code: ${err.response?.data?.detail || err.response?.data || err.message}`);
      })
      .finally(() => setGenerating(false));
  }, [generationPrompt]);

  const handleSave = useCallback(() => {
    setError(null);
    setSuccess(null);

    if (!filename.trim()) {
      setError('Filename is required.');
      return;
    }
    if (!filename.endsWith('.py')) {
        setError('Filename must end with .py');
        return;
    }
    // Basic validation for filename characters
    if (!/^[a-zA-Z0-9_]+\.py$/.test(filename)) {
        setError('Filename can only contain letters, numbers, and underscores, and must end with .py');
        return;
    }

    setSaving(true);
    api.saveToolContent(filename, code)
      .then(() => {
        setSuccess(`Tool '${filename}' saved successfully!`);
        setInitialCode(code); // Update initial code to prevent unsaved changes warning
        onSaved?.(filename);
        // If creating new, navigate to edit mode for the new file
        if (!isEditMode) {
          const path = nested ? `/tools/${filename}` : `/tools/edit/${filename}`;
          setTimeout(() => nav(path, { replace: true }), 1000);
        } else {
          // Optional: Add a short delay or keep the success message visible
          setTimeout(() => setSuccess(null), 3000);
        }
      })
      .catch(err => {
        console.error("Error saving tool:", err);
        setError(`Failed to save tool '${filename}'. ${err.response?.data?.detail || err.message}`);
      })
      .finally(() => setSaving(false));
  }, [filename, code, isEditMode, nav]);

  // Basic check for unsaved changes (can be improved)
  const hasUnsavedChanges = code !== initialCode;

  return (
    <Box component={nested ? Box : Paper} sx={{ p: { xs: 2, sm: 3 }, display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h5" gutterBottom>
        {isEditMode ? `Edit Tool: ${routeFilename}` : 'Create New Tool'}
      </Typography>

      {/* Combined Error/Success Alerts */}
      <Collapse in={!!error || !!success || !!generationError}>
         {error && <Alert severity="error" sx={{ mb: 1 }} action={<IconButton size="small" onClick={() => setError(null)}><CloseIcon fontSize="inherit" /></IconButton>}>{error}</Alert>}
         {success && <Alert severity="success" sx={{ mb: 1 }} action={<IconButton size="small" onClick={() => setSuccess(null)}><CloseIcon fontSize="inherit" /></IconButton>}>{success}</Alert>}
         {generationError && <Alert severity="error" sx={{ mb: 1 }} action={<IconButton size="small" onClick={() => setGenerationError(null)}><CloseIcon fontSize="inherit" /></IconButton>}>{generationError}</Alert>}
      </Collapse>

      {hasUnsavedChanges && !success && <Alert severity="warning" sx={{ mt: -1, mb: 1 }}>You have unsaved changes.</Alert>}

      <Stack spacing={2}>
        <TextField
          label="Filename"
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
          required
          disabled={isEditMode || loading || saving}
          error={(!filename.trim() || !filename.endsWith('.py') || !/^[a-zA-Z0-9_]+\.py$/.test(filename)) && !!error}
          helperText={isEditMode ? "Filename cannot be changed." : "Enter a valid Python filename (e.g., my_tool.py)"}
          fullWidth
        />

        {/* Generation Section (only in Create mode) */}
        {!isEditMode && (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack spacing={1.5}>
              <Typography variant="subtitle1">Generate Code from Prompt</Typography>
              <TextField
                label="Describe the tool you want to create"
                multiline
                maxRows={10}
                fullWidth
                value={generationPrompt}
                onChange={(e) => setGenerationPrompt(e.target.value)}
                disabled={generating || loading || saving}
                variant="outlined"
                size="small"
              />
              <Box>
                <Button
                  variant="contained"
                  color="secondary"
                  onClick={handleGenerateCode}
                  disabled={generating || loading || saving || !generationPrompt.trim()}
                  startIcon={generating ? <CircularProgress size={20} color="inherit" /> : null}
                >
                  {generating ? 'Generating...' : 'Generate Code'}
                </Button>
              </Box>
            </Stack>
          </Paper>
        )}

        <Typography variant="subtitle1">
          {isEditMode ? 'Tool Code' : 'Tool Code (Edit generated code or write your own)'}
        </Typography>
        <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1, flexGrow: 1, minHeight: '400px', display: 'flex' }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%' }}>
              <CircularProgress />
            </Box>
          ) : (
            <CodeEditor
              language="python"
              value={code}
              onChange={(value) => setCode(value || '')}
              height={nested ? "calc(100vh - 400px)" : "50vh"}
              options={{ automaticLayout: true }}
            />
          )}
        </Box>

        {!nested && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, pt: 1 }}>
            <Button
              variant="outlined"
              component={RouterLink}
              to="/tools"
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={loading || saving || !filename || (isEditMode && !hasUnsavedChanges)}
            >
              {saving ? <CircularProgress size={24} color="inherit" /> : (isEditMode ? 'Save Changes' : 'Create Tool')}
            </Button>
          </Box>
        )}
        {nested && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, pt: 1, position: 'sticky', bottom: 0, bgcolor: 'background.paper', py: 2, borderTop: 1, borderColor: 'divider', mt: 2 }}>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={loading || saving || !filename || (isEditMode && !hasUnsavedChanges)}
            >
              {saving ? <CircularProgress size={24} color="inherit" /> : (isEditMode ? 'Save Changes' : 'Create Tool')}
            </Button>
          </Box>
        )}
      </Stack>
    </Box>
  );
}