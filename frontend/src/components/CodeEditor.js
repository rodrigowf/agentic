import React from 'react';
import Editor from '@monaco-editor/react';
import { useTheme } from '@mui/material/styles'; // Import useTheme

export default function CodeEditor({ value, language='javascript', onChange, height='200px', readOnly = false, options = {} }) {
  const theme = useTheme(); // Get the current MUI theme
  const editorTheme = theme.palette.mode === 'dark' ? 'vs-dark' : 'light'; // Determine Monaco theme

  const editorOptions = {
    minimap: { enabled: false },
    readOnly: readOnly,
    automaticLayout: true, // Adjust layout on container resize
    scrollBeyondLastLine: false,
    ...options, // Allow overriding default options
  };

  return (
    <Editor
      height={height}
      language={language}
      theme={editorTheme} // Set the theme dynamically
      value={value}
      onChange={onChange} // onChange won't be called if readOnly is true
      options={editorOptions}
    />
  );
}