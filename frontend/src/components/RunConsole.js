import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import {
  Paper,
  Typography,
  Box,
  Chip,
  CircularProgress,
  Alert,
  Link,
  Button,
  IconButton,
  TextField,
} from '@mui/material';
import ReplayIcon from '@mui/icons-material/Replay';
import api from '../api';

// Function to determine color based on log type
const getLogTypeColor = (type) => {
  const lowerType = type?.toLowerCase();
  switch (lowerType) {
    // Error types
    case 'error':
    case 'system_error':
    case 'websocketdisconnect': // Treat disconnects visually
      return 'error.main';

    // Warning types
    case 'warning':
      return 'warning.main';

    // Informational types
    case 'info':
    case 'system':
    case 'textmessage': // Regular text response from agent
      return 'info.main';

    // Debug / Verbose types
    case 'debug':
      return 'text.secondary';

    // LLM Interaction types
    case 'llmrequestevent': // Renamed from llm_request
    case 'chatcompletionrequest': // Could be another name depending on exact event
      return 'primary.light';
    case 'llmresponseevent': // Renamed from llm_response
    case 'chatcompletionresponseevent': // Could be another name
    case 'textmessagechunk': // Streaming chunks
      return 'success.light';

    // Tool Interaction types
    case 'toolcallrequestevent': // Renamed from tool_call
    case 'toolcallrequestmessage': // Specific message type
      return 'secondary.light';
    case 'toolcallexecutionevent': // Renamed from tool_response
    case 'toolcallresultmessage': // Specific message type
      return 'secondary.main';

    // Other potential types from v0.4+ streaming
    case 'agentstartevent':
    case 'agentfinishevent':
        return 'primary.main'; // Or another distinct color

    default:
      console.warn("Unknown log type received:", type); // Log unknown types
      return 'text.primary';
  }
};

// Helper to format log data
const formatLogData = (data) => {
    if (typeof data === 'object' && data !== null) {
        try {
            return JSON.stringify(data, null, 2);
        } catch (e) {
            console.error("Error stringifying log data:", e);
            return "[Unserializable Data]";
        }
    }
    return String(data); // Fallback to string conversion
};

export default function RunConsole() {
  const { name } = useParams();
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);
  const logContainerRef = useRef(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [taskInput, setTaskInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);

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
      console.log('WebSocket Disconnected', event.code, event.reason, `Was Clean: ${event.wasClean}`);
      setIsConnected(false);
      setIsConnecting(false);
      setIsRunning(false);
      if (!event.wasClean && !error) {
        setError(`WebSocket closed unexpectedly (Code: ${event.code}). Check backend status.`);
      }
      setLogs(prevLogs => [
        ...prevLogs,
        { type: 'system', data: `WebSocket connection closed${event.reason ? `: ${event.reason}` : ''} (Code: ${event.code})`, timestamp: new Date().toISOString() }
      ]);
    };

  }, [name, error]);

  const handleRunAgent = () => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      setError("WebSocket is not connected. Cannot run agent.");
      console.error("Attempted to run agent while WebSocket is not open.");
      return;
    }
    if (!taskInput.trim()) {
        setError("Please enter a task for the agent.");
        return;
    }

    try {
      const runMessage = JSON.stringify({ type: 'run', data: taskInput });
      console.log('Sending run message:', runMessage);
      ws.current.send(runMessage);
      setIsRunning(true);
      setError(null);
      setLogs([{ type: 'system', data: `Sending run command with task: ${taskInput.substring(0, 100)}...`, timestamp: new Date().toISOString() }]);
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
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 110px)' }}>
      <Box component={Paper} sx={{ p: 2, mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h5">
          Agent Run: <Link component={RouterLink} to={`/agents/${name}`} underline="hover">{name}</Link>
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="caption">Status:</Typography>
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
            <Button variant="outlined" size="small" component={RouterLink} to="/">Back to Agents</Button>
        </Box>
      </Box>

      <Box component={Paper} sx={{ p: 2, mb: 2, display: 'flex', gap: 1, alignItems: 'flex-start' }}>
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
          />
          <Button 
              variant="contained" 
              onClick={handleRunAgent} 
              disabled={!isConnected || isRunning || !taskInput.trim()}
              sx={{ height: 'fit-content', mt: '4px' }}
          >
              {isRunning ? <CircularProgress size={24} color="inherit" /> : 'Run Agent'}
          </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper ref={logContainerRef} sx={{
           flexGrow: 1,
           p: 2,
           overflowY: 'auto',
           fontFamily: 'monospace',
           fontSize: '0.85rem',
           bgcolor: 'background.paper',
           border: '1px solid',
           borderColor: 'divider'
         }}>
        {logs.length === 0 && !isConnecting && (
            <Typography sx={{ color: 'text.secondary' }}>Waiting for connection. Enter task and click Run.</Typography>
        )}
        {logs.map((log, i) => (
          <Box key={i} sx={{ mb: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            <Typography component="span" variant="caption" sx={{ color: 'text.secondary', mr: 1 }}>
              {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '?:??:??'}
            </Typography>
            <Typography component="span" variant="caption" sx={{ color: getLogTypeColor(log.type), fontWeight: 'bold', mr: 1 }}>
              [{log.type?.toUpperCase() || 'UNKNOWN'}]
            </Typography>
            <Typography component="span" sx={{ color: getLogTypeColor(log.type) }}>
              {formatLogData(log.data)}
            </Typography>
          </Box>
        ))}
      </Paper>
    </Box>
  );
}