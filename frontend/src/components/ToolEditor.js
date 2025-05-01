import React, { useState } from 'react';
import { Button, Typography, Box, TextField, Alert } from '@mui/material'; // Added Box, TextField, Alert
import { useNavigate } from 'react-router-dom'; // Import useNavigate
import api from '../api';
// Removed CodeEditor import as inline editing wasn't fully implemented in the plan

export default function ToolEditor() {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState(""); // Store filename
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const nav = useNavigate(); // Initialize useNavigate

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
        setFile(selectedFile);
        setFileName(selectedFile.name);
        setError(null); // Clear previous errors
        setSuccess(null);
    } else {
        setFile(null);
        setFileName("");
    }
  };

  const handleUpload = () => {
    setError(null);
    setSuccess(null);
    if (file) {
      api.uploadTool(file)
        .then((res) => {
            setSuccess(`Tool '${res.data.name}' uploaded successfully!`);
            setFile(null); // Clear file input after success
            setFileName("");
            // Optionally navigate back after a delay
            setTimeout(() => nav('/tools'), 1500);
        })
        .catch(err => {
            console.error("Error uploading tool:", err);
            setError(err.response?.data?.detail || "Failed to upload tool. Check backend logs.");
        });
    } else {
        setError("Please select a Python file (.py) to upload.");
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h5">Upload New Tool</Typography>

      {error && <Alert severity="error">{error}</Alert>}
      {success && <Alert severity="success">{success}</Alert>}

      <TextField
        type="file"
        label="Python Tool File (.py)"
        InputLabelProps={{
          shrink: true,
        }}
        inputProps={{
          accept: ".py",
        }}
        onChange={handleFileChange}
        helperText={fileName ? `Selected: ${fileName}` : "Select the Python file defining your tool."}
      />

      {/* The plan mentioned inline editing but didn't fully spec it out. */}
      {/* Removing the CodeEditor part for now to match the upload focus. */}
      {/* <Typography variant="subtitle1" sx={{ mt:2 }}>Or edit inline:</Typography> */}
      {/* <CodeEditor value={code} onChange={setCode} language="python" height="300px" /> */}

      <Button variant="contained" onClick={handleUpload} disabled={!file}>
        Upload and Save Tool
      </Button>
      <Button variant="outlined" onClick={() => nav('/tools')}>
        Cancel
      </Button>
    </Box>
  );
}