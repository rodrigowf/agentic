import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import {
  Paper,
  Typography,
  Link,
  Box,
  Chip,
  CircularProgress,
  Alert,
  Button,
  IconButton,
  TextField,
  Stack,
} from '@mui/material';
import ReplayIcon from '@mui/icons-material/Replay';
import ClearIcon from '@mui/icons-material/Clear';
import DownloadIcon from '@mui/icons-material/Download';
import api from '../api';
import LogEntry from './LogMessageDisplay';

export default function RunConsole({nested = false}) {
  const { name } = useParams();
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);
  const logContainerRef = useRef(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [taskInput, setTaskInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [uploadedAudio, setUploadedAudio] = useState(null);

  const connectWebSocket = useCallback(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log("WebSocket already open.");
      return;
    }

    setIsConnecting(true);
    setIsConnected(false);
    setError(null);
    setLogs([]);

    console.log(`Attempting to connect WebSocket for agent: ${name}`);
    ws.current = api.runAgent(name);

    ws.current.onopen = () => {
      console.log('WebSocket Connected');
      setIsConnected(true);
      setIsConnecting(false);
      setError(null);
      setLogs(prevLogs => [
        ...prevLogs,
        { type: 'system', data: 'Connection established. Enter task and click Run.', timestamp: new Date().toISOString() }
      ]);
    };

    ws.current.onmessage = (event) => {
      try {
        const messageData = JSON.parse(event.data);
        console.log('Message received:', messageData);

        if (!messageData.timestamp) {
          messageData.timestamp = new Date().toISOString();
        }

        setLogs(prevLogs => [...prevLogs, messageData]);

        const messageTypeLower = messageData.type?.toLowerCase();

        if (messageTypeLower?.includes('error')) {
          setError(messageData.data?.message || messageData.data || 'An error occurred.');
          setIsRunning(false);
        } else if (messageTypeLower === 'system' && messageData.data?.message?.includes('Agent run finished')) {
          setIsRunning(false);
        } else if (messageTypeLower === 'websocketdisconnect') {
          setIsRunning(false);
        }
      } catch (e) {
        console.error('Failed to parse message or invalid message format:', event.data, e);
        const errorMsg = `Received unparsable message: ${event.data}`;
        setError('Received an invalid message from the backend.');
        setLogs(prevLogs => [...prevLogs, { type: 'system_error', data: errorMsg, timestamp: new Date().toISOString() }]);
        setIsRunning(false);
      }
    };

    ws.current.onerror = (event) => {
      console.error('WebSocket Error:', event);
      setError('WebSocket connection error. Check backend logs and network.');
      setIsConnected(false);
      setIsConnecting(false);
      setIsRunning(false);
      setLogs(prevLogs => [
        ...prevLogs,
        { type: 'system_error', data: 'WebSocket connection error occurred.', timestamp: new Date().toISOString() }
      ]);
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket Disconnected', event.code, event.reason);
      setIsConnected(false);
      setIsConnecting(false);
      setIsRunning(false);
      if (event.code !== 1000) {
        setError(`WebSocket disconnected unexpectedly: ${event.reason || 'Unknown reason'} (Code: ${event.code})`);
      }
    };

  }, [name, error]);

  // Handler for image upload
  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      const base64 = dataUrl.split(',')[1];
      setUploadedImage(base64);
    };
    reader.readAsDataURL(file);
  };

  // Handler for audio upload
  const handleAudioUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setUploadedAudio(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleRunAgent = () => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      setError("WebSocket is not connected. Cannot run agent.");
      console.error("Attempted to run agent while WebSocket is not open.");
      return;
    }
    if (!taskInput.trim() && !uploadedImage && !uploadedAudio) {
      setError("Please enter a task or upload media for the agent.");
      return;
    }

    try {
      // Build payload including text, image, or audio
      let dataPayload;
      if (uploadedImage || uploadedAudio) {
        dataPayload = {};
        if (taskInput.trim()) dataPayload.text = taskInput;
        if (uploadedImage) dataPayload.image = uploadedImage;
        else if (uploadedAudio) dataPayload.audio = uploadedAudio;
      } else {
        dataPayload = taskInput;
      }
      const runMessage = JSON.stringify({ type: 'run', data: dataPayload });
      console.log('Sending run message:', runMessage);
      ws.current.send(runMessage);
      setIsRunning(true);
      setError(null);
      setLogs([{ type: 'system', data: `Sending run command with task: ${taskInput.substring(0, 100)}...`, timestamp: new Date().toISOString() }]);
      // Clear uploads after sending
      setUploadedImage(null);
      setUploadedAudio(null);
    } catch (e) {
      console.error('Failed to send run message:', e);
      setError('Failed to send run command to backend.');
      setIsRunning(false);
      setLogs(prevLogs => [
        ...prevLogs,
        { type: 'system_error', data: `Failed to send run command: ${e.message}`, timestamp: new Date().toISOString() }
      ]);
    }
  };

  const handleClearLogs = () => {
    if (ws.current) {
      ws.current.close();
    }
    connectWebSocket();
  };

  const handleDownloadLogs = () => {
    const logText = logs.map(log => {
      const timestamp = new Date(log.timestamp).toLocaleString();
      return `[${timestamp}] [${log.type}] ${typeof log.data === 'string' ? log.data : JSON.stringify(log.data)}`;
    }).join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agent-${name}-logs-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (ws.current) {
        console.log("Closing WebSocket connection.");
        ws.current.close();
      }
    };
  }, [connectWebSocket]);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <Stack spacing={2} sx={{ height: '100%', overflowX: 'hidden' }}>
      <Box component={Paper} sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0, overflowX: 'hidden' }}>
        <Typography variant="h5">
          Run {!nested ? <Link component={RouterLink} to={`/agents/${name}`} underline="hover">{name}</Link> : ''}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, overflowX: 'hidden' }}>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>Status:</Typography>
          {isConnecting ? (
            <Chip label="Connecting..." color="warning" size="small" icon={<CircularProgress size={14} color="inherit" />} />
          ) : isConnected ? (
            <Chip label="Connected" color="success" size="small" />
          ) : (
            <Chip label="Disconnected" color="error" size="small" />
          )}
          <IconButton onClick={connectWebSocket} size="small" title="Reconnect" disabled={isConnecting || isConnected}>
            <ReplayIcon />
          </IconButton>
          <IconButton onClick={handleClearLogs} size="small" title="Clear Logs" disabled={logs.length === 0}>
            <ClearIcon />
          </IconButton>
          <IconButton onClick={handleDownloadLogs} size="small" title="Download Logs" disabled={logs.length === 0}>
            <DownloadIcon />
          </IconButton>
          {!nested && (
            <Button variant="outlined" size="small" component={RouterLink} to="/">Back to Agents</Button>
          )}
        </Box>
      </Box>

      <Box component={Paper} sx={{ p: 2, display: 'flex', gap: 1, alignItems: 'flex-start', flexShrink: 0, overflowX: 'hidden' }}>
        <TextField
          fullWidth
          label="Initial Task for Agent"
          variant="outlined"
          size="small"
          value={taskInput}
          onChange={(e) => setTaskInput(e.target.value)}
          disabled={!isConnected || isRunning}
          multiline
          rows={2}
          maxRows={6}
          sx={{ flexGrow: 1 }}
          placeholder="Enter the task description here..."
        />
        <Button variant="outlined" component="label" sx={{ height: '100%' }}>
          Upload Image
          <input hidden accept="image/*" type="file" onChange={handleImageUpload} />
        </Button>
        <Button variant="outlined" component="label" sx={{ height: '100%' }}>
          Upload Audio
          <input hidden accept="audio/*" type="file" onChange={handleAudioUpload} />
        </Button>
        {/* Previews for uploaded media */}
        {uploadedImage && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <img src={`data:image/*;base64,${uploadedImage}`} alt="preview" style={{ maxHeight: 80 }} />
            <Button size="small" onClick={() => setUploadedImage(null)}>Remove Image</Button>
          </Box>
        )}
        {uploadedAudio && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <audio controls src={uploadedAudio} style={{ maxHeight: 80 }} />
            <Button size="small" onClick={() => setUploadedAudio(null)}>Remove Audio</Button>
          </Box>
        )}
        <Button
          variant="contained"
          onClick={handleRunAgent}
          disabled={!isConnected || isRunning || (!taskInput.trim() && !uploadedImage && !uploadedAudio)}
          sx={{ height: '100%', px: 4}}
        >
          {isRunning ? <CircularProgress size={24} color="inherit" /> : 'Run'}
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ flexShrink: 0 }}>{error}</Alert>}

      <Paper ref={logContainerRef} sx={{
        flexGrow: 1,
        p: 2,
        overflowY: 'auto', 
        overflowX: 'hidden',
        fontFamily: 'inherit',
        fontSize: '0.9rem',
        bgcolor: 'background.default',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
      }}>
        {logs.length === 0 && !isConnecting && (
          <Typography sx={{ color: 'text.secondary', fontStyle: 'italic', textAlign: 'center', mt: 2 }}>
            {isConnected ? 'Enter a task above and click Run Agent.' : 'Attempting to connect...'}
          </Typography>
        )}
        {logs.map((log, i) => (
          <LogEntry key={i} log={log} />
        ))}
      </Paper>
    </Stack>
  );
}