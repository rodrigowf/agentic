import React from 'react';
import Editor from '@monaco-editor/react';
import { useTheme } from '@mui/material/styles';
import { CodeEditorProps } from '../../../types';

export default function CodeEditor({
  value,
  language = 'javascript',
  onChange,
  height = '200px',
  readOnly = false
}: CodeEditorProps): JSX.Element {
  const theme = useTheme();
  const editorTheme = theme.palette.mode === 'dark' ? 'vs-dark' : 'light';

  const editorOptions = {
    minimap: { enabled: false },
    readOnly: readOnly,
    automaticLayout: true,
    scrollBeyondLastLine: false,
  };

  const handleChange = (value: string | undefined) => {
    onChange(value || '');
  };

  return (
    <Editor
      height={height}
      language={language}
      theme={editorTheme}
      value={value}
      onChange={handleChange}
      options={editorOptions}
    />
  );
}
