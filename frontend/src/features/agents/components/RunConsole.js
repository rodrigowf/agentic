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
  Tooltip,
} from '@mui/material';
import ReplayIcon from '@mui/icons-material/Replay';
import ClearIcon from '@mui/icons-material/Clear';
import DownloadIcon from '@mui/icons-material/Download';
import StopIcon from '@mui/icons-material/Stop';
import api from '../../../api';
import LogEntry from './LogMessageDisplay';
import { KEYBOARD_SHORTCUTS } from '../../../hooks/useKeyboardNavigation';

export default function RunConsole({ nested = false, agentName, sharedSocket, readOnlyControls }) {
  const params = useParams();
  const name = agentName || params.name;
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);
  const logContainerRef = useRef(null);
  const isAtBottomRef = useRef(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [taskInput, setTaskInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const containerRef = useRef(null);

  // Keep local refs to listeners so we can remove them on cleanup when sharing
  const listenersRef = useRef({ open: null, message: null, error: null, close: null });

  const attachSharedSocket = useCallback((socket) => {
    if (!socket) return;
    ws.current = socket;

    // Remove previous listeners if any
    const prev = listenersRef.current;
    if (prev.open) socket.removeEventListener('open', prev.open);
    if (prev.message) socket.removeEventListener('message', prev.message);
    if (prev.error) socket.removeEventListener('error', prev.error);
    if (prev.close) socket.removeEventListener('close', prev.close);

    // Define listeners
    const onOpen = () => {
      setIsConnected(true);
      setIsConnecting(false);
      setError(null);
      setLogs((prev) => [
        ...prev,
        { type: 'system', data: 'Connection established. Enter task and click Run.', timestamp: new Date().toISOString() },
      ]);
    };
    const onMessage = (event) => {
      try {
        const messageData = JSON.parse(event.data);
        if (!messageData.timestamp) messageData.timestamp = new Date().toISOString();
        setLogs((prev) => [...prev, messageData]);
        const t = messageData.type?.toLowerCase();
        if (t?.includes('error')) {
          setError(messageData.data?.message || messageData.data || 'An error occurred.');
          setIsRunning(false);
        } else if (t === 'system' && messageData.data?.message?.includes('Agent run finished')) {
          setIsRunning(false);
        } else if (t === 'websocketdisconnect') {
          setIsRunning(false);
        }
      } catch (e) {
        const errorMsg = `Received unparsable message: ${event.data}`;
        setError('Received an invalid message from the backend.');
        setLogs((prev) => [
          ...prev,
          { type: 'system_error', data: errorMsg, timestamp: new Date().toISOString() },
        ]);
        setIsRunning(false);
      }
    };
    const onError = () => {
      setError('WebSocket connection error. Check backend logs and network.');
      setIsConnected(false);
      setIsConnecting(false);
      setIsRunning(false);
      setLogs((prev) => [
        ...prev,
        { type: 'system_error', data: 'WebSocket connection error occurred.', timestamp: new Date().toISOString() },
      ]);
    };
    const onClose = (event) => {
      setIsConnected(false);
      setIsConnecting(false);
      setIsRunning(false);
      if (event.code !== 1000) {
        setError(`WebSocket disconnected unexpectedly: ${event.reason || 'Unknown reason'} (Code: ${event.code})`);
      }
    };

    // Attach and save
    socket.addEventListener('open', onOpen);
    socket.addEventListener('message', onMessage);
    socket.addEventListener('error', onError);
    socket.addEventListener('close', onClose);
    listenersRef.current = { open: onOpen, message: onMessage, error: onError, close: onClose };

    // If already open, run onOpen immediately
    if (socket.readyState === WebSocket.OPEN) onOpen();
    else if (socket.readyState === WebSocket.CONNECTING) setIsConnecting(true);
  }, []);

  const connectWebSocket = useCallback(() => {
    if (sharedSocket) {
      attachSharedSocket(sharedSocket);
      return;
    }

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      return;
    }

    // Don't connect if no agent name is defined
    if (!name) {
      setError('No agent name provided');
      return;
    }

    setIsConnecting(true);
    setIsConnected(false);
    setError(null);
    setLogs([]);

    ws.current = api.runAgent(name);

    ws.current.onopen = () => {
      setIsConnected(true);
      setIsConnecting(false);
      setError(null);
      setLogs((prevLogs) => [
        ...prevLogs,
        { type: 'system', data: 'Connection established. Enter task and click Run.', timestamp: new Date().toISOString() },
      ]);
    };

    ws.current.onmessage = (event) => {
      try {
        const messageData = JSON.parse(event.data);
        if (!messageData.timestamp) messageData.timestamp = new Date().toISOString();
        setLogs((prevLogs) => [...prevLogs, messageData]);

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
        const errorMsg = `Received unparsable message: ${event.data}`;
        setError('Received an invalid message from the backend.');
        setLogs((prevLogs) => [
          ...prevLogs,
          { type: 'system_error', data: errorMsg, timestamp: new Date().toISOString() },
        ]);
        setIsRunning(false);
      }
    };

    ws.current.onerror = () => {
      setError('WebSocket connection error. Check backend logs and network.');
      setIsConnected(false);
      setIsConnecting(false);
      setIsRunning(false);
      setLogs((prevLogs) => [
        ...prevLogs,
        { type: 'system_error', data: 'WebSocket connection error occurred.', timestamp: new Date().toISOString() },
      ]);
    };

    ws.current.onclose = (event) => {
      setIsConnected(false);
      setIsConnecting(false);
      setIsRunning(false);
      if (event.code !== 1000) {
        setError(`WebSocket disconnected unexpectedly: ${event.reason || 'Unknown reason'} (Code: ${event.code})`);
      }
    };
  }, [name, sharedSocket, attachSharedSocket]);

  const handleRunAgent = () => {
    const socket = ws.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setError('WebSocket is not connected. Cannot run agent.');
      return;
    }
    if (!taskInput.trim()) {
      setError('Please enter a task for the agent.');
      return;
    }
    try {
      const runMessage = JSON.stringify({ type: 'run', data: taskInput });
      socket.send(runMessage);
      setIsRunning(true);
      setError(null);
      setLogs([{ type: 'system', data: `Sending run command with task: ${taskInput.substring(0, 100)}...`, timestamp: new Date().toISOString() }]);
    } catch (e) {
      setError('Failed to send run command to backend.');
      setIsRunning(false);
      setLogs((prevLogs) => [
        ...prevLogs,
        { type: 'system_error', data: `Failed to send run command: ${e.message}`, timestamp: new Date().toISOString() },
      ]);
    }
  };

  const handleClearLogs = () => {
    // If sharing a socket, do not close it; just clear logs
    if (sharedSocket) {
      setLogs([]);
      return;
    }
    if (ws.current) {
      try { ws.current.close(); } catch {}
    }
    connectWebSocket();
  };

  const handleStopAgent = () => {
    const socket = ws.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      try {
        const cancelMessage = JSON.stringify({ type: 'cancel' });
        socket.send(cancelMessage);
        setIsRunning(false);
        setLogs((prev) => [
          ...prev,
          { type: 'system', data: 'Stop signal sent to agent', timestamp: new Date().toISOString() },
        ]);
      } catch (e) {
        setError('Failed to send stop command to backend.');
      }
    }
  };

  const handleDownloadLogs = () => {
    const logText = logs
      .map((log) => {
        const timestamp = new Date(log.timestamp).toLocaleString();
        return `[${timestamp}] [${log.type}] ${typeof log.data === 'string' ? log.data : JSON.stringify(log.data)}`;
      })
      .join('\n');

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

  // Keyboard shortcuts handler
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl+R to run
      if (e.ctrlKey && e.key === 'r' && !e.shiftKey) {
        e.preventDefault();
        if (isConnected && !isRunning && taskInput.trim()) {
          handleRunAgent();
        }
      }
      // Ctrl+X to stop
      if (e.ctrlKey && e.key === 'x') {
        e.preventDefault();
        if (isRunning) {
          handleStopAgent();
        }
      }
      // Ctrl+Shift+L to clear logs
      if (e.ctrlKey && e.shiftKey && e.key === 'L') {
        e.preventDefault();
        if (logs.length > 0) {
          handleClearLogs();
        }
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('keydown', handleKeyDown);
      return () => {
        container.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [isConnected, isRunning, taskInput, logs.length, handleRunAgent, handleStopAgent, handleClearLogs]);

  useEffect(() => {
    connectWebSocket();
    return () => {
      // Only close socket if we created it; never close a shared one
      if (!sharedSocket && ws.current) {
        try { ws.current.close(); } catch {}
      }
      // Clean up listeners on a shared socket
      if (sharedSocket) {
        const s = sharedSocket;
        const { open, message, error, close } = listenersRef.current;
        if (open) s.removeEventListener('open', open);
        if (message) s.removeEventListener('message', message);
        if (error) s.removeEventListener('error', error);
        if (close) s.removeEventListener('close', close);
      }
    };
  }, [connectWebSocket, sharedSocket]);

  // Track scroll position to determine if user is at bottom
  const handleScroll = useCallback(() => {
    if (logContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logContainerRef.current;
      // Consider "at bottom" if within 100px of the bottom
      isAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 100;
    }
  }, []);

  useEffect(() => {
    // Only auto-scroll if user is already at the bottom
    if (logContainerRef.current && isAtBottomRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const controlsReadOnly = readOnlyControls ?? Boolean(sharedSocket);

  return (
    <Stack ref={containerRef} spacing={2} sx={{ height: '100%', overflowX: 'hidden' }} tabIndex={-1}>
      <Box component={nested ? Box : Paper} sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0, overflowX: 'hidden', ...(nested && { border: 'none' }) }}>
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
          <Tooltip title="Reconnect" arrow>
            <span>
              <IconButton onClick={connectWebSocket} size="small" disabled={controlsReadOnly || isConnecting || isConnected} aria-label="Reconnect">
                <ReplayIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Clear Logs (Ctrl+Shift+L)" arrow>
            <span>
              <IconButton onClick={handleClearLogs} size="small" disabled={logs.length === 0} aria-label="Clear logs">
                <ClearIcon />
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title="Download Logs" arrow>
            <span>
              <IconButton onClick={handleDownloadLogs} size="small" disabled={logs.length === 0} aria-label="Download logs">
                <DownloadIcon />
              </IconButton>
            </span>
          </Tooltip>
          {isRunning && (
            <Tooltip title="Stop Agent (Ctrl+X)" arrow>
              <Button
                variant="outlined"
                size="small"
                color="error"
                onClick={handleStopAgent}
                startIcon={<StopIcon />}
                aria-label="Stop agent"
              >
                Stop
              </Button>
            </Tooltip>
          )}
          {!nested && (
            <Button variant="outlined" size="small" component={RouterLink} to="/">Back to Agents</Button>
          )}
        </Box>
      </Box>

      <Box component={nested ? Box : Paper} sx={{ p: 2, display: 'flex', gap: 1, alignItems: 'flex-start', flexShrink: 0, overflowX: 'hidden', ...(nested && { border: 'none' }) }}>
        <TextField
          fullWidth
          label="Initial Task for Agent"
          variant="outlined"
          size="small"
          value={taskInput}
          onChange={(e) => setTaskInput(e.target.value)}
          disabled={!isConnected || isRunning}
          multiline
          minRows={3}
          maxRows={20}
          sx={{ flexGrow: 1 }}
          placeholder="Enter the task description here..."
          aria-label="Task description for agent"
        />
        <Tooltip title={isRunning ? "Agent is running" : !taskInput.trim() ? "Enter a task first" : "Run Agent (Ctrl+R)"} arrow>
          <span>
            <Button
              variant="contained"
              onClick={handleRunAgent}
              disabled={!isConnected || isRunning || !taskInput.trim()}
              sx={{ height: '86px', px: 4 }}
              aria-label="Run agent"
            >
              {isRunning ? <CircularProgress size={24} color="inherit" /> : 'Run'}
            </Button>
          </span>
        </Tooltip>
      </Box>

      {error && <Alert severity="error" sx={{ flexShrink: 0 }}>{error}</Alert>}

      <Box component={nested ? Box : Paper} ref={logContainerRef} onScroll={handleScroll} sx={{
        flexGrow: 1,
        p: 2,
        overflowY: 'auto',
        overflowX: 'hidden',
        fontFamily: 'inherit',
        fontSize: '0.9rem',
        bgcolor: 'background.default',
        ...(nested ? {} : { border: '1px solid', borderColor: 'divider', borderRadius: 1 }),
      }}>
        {logs.length === 0 && !isConnecting && (
          <Typography sx={{ color: 'text.secondary', fontStyle: 'italic', textAlign: 'center', mt: 2 }}>
            {isConnected ? 'Enter a task above and click Run Agent.' : 'Attempting to connect...'}
          </Typography>
        )}
        {logs.map((log, i) => (
          <LogEntry key={i} log={log} />
        ))}
      </Box>
    </Stack>
  );
}