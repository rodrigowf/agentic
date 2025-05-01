import React from 'react';
import Editor from '@monaco-editor/react';

export default function CodeEditor({ value, language='javascript', onChange, height='200px', readOnly = false, options = {} }) {
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
      value={value}
      onChange={onChange} // onChange won't be called if readOnly is true
      options={editorOptions}
      // theme="vs-dark" // Optional: Set a theme
    />
  );
}