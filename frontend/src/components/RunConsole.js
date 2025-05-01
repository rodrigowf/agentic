import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Paper, Typography, Box, Button, CircularProgress, Alert } from '@mui/material'; // Added Box, Button, CircularProgress, Alert
import ReconnectingWebSocket from 'reconnecting-websocket'; // Use reconnecting-websocket
import api from '../api'; // Assuming api.js exports the base WS URL correctly

export default function RunConsole() {
  const { name } = useParams();
  const nav = useNavigate();
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);
  const logContainerRef = useRef(null); // Ref for scrolling

  const connectWebSocket = useCallback(() => {
    // Construct WebSocket URL using the function from api.js
    // Need to get the base URL part first
    const wsUrl = (process.env.REACT_APP_WS_URL || 'ws://localhost:8000') + `/api/runs/${name}`;
    console.log(`Connecting to WebSocket: ${wsUrl}`);

    // Close existing connection if any
    if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
        ws.current.close();
    }

    ws.current = new ReconnectingWebSocket(wsUrl, [], {
        maxReconnectionDelay: 10000, // Max delay 10s
        minReconnectionDelay: 1000 + Math.random() * 4000, // Start with 1-5s
        reconnectionDelayGrowFactor: 1.3,
        minUptime: 5000, // Minimum time connection must be up to reset delays
        connectionTimeout: 4000,
        maxRetries: Infinity,
        debug: false,
    });

    ws.current.onopen = () => {
      console.log('WebSocket Connected');
      setIsConnected(true);
      setError(null); // Clear error on successful connection
      setLogs([{ type: 'system', message: 'Connection established. Waiting for agent run...', timestamp: new Date().toISOString() }]);
    };

    ws.current.onmessage = (event) => {
      try {
        const messageData = JSON.parse(event.data);
        console.log('Message received:', messageData);
        // Add a timestamp to each log entry
        setLogs(prevLogs => [...prevLogs, { ...messageData, timestamp: new Date().toISOString() }]);
      } catch (e) {
        console.error('Failed to parse message or invalid message format:', event.data, e);
        // Add raw message if parsing fails
        setLogs(prevLogs => [...prevLogs, { type: 'system_error', message: `Received unparsable message: ${event.data}`, timestamp: new Date().toISOString() }]);
      }
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket Disconnected', event.code, event.reason);
      setIsConnected(false);
      // Don't set error immediately on close, ReconnectingWebSocket will handle retries
      if (!event.wasClean) {
          // Set error only if it wasn't a clean close and retries might be failing
          // setError(`Connection closed unexpectedly (Code: ${event.code}). Attempting to reconnect...`);
          setLogs(prevLogs => [...prevLogs, { type: 'system_error', message: `Connection closed (Code: ${event.code}). Reconnecting...`, timestamp: new Date().toISOString() }]);
      } else {
          setLogs(prevLogs => [...prevLogs, { type: 'system', message: 'Connection closed cleanly.', timestamp: new Date().toISOString() }]);
      }
    };

    ws.current.onerror = (errorEvent) => {
      console.error('WebSocket Error:', errorEvent);
      setError('WebSocket connection error. Check the console and backend status.');
      // Add error log
      setLogs(prevLogs => [...prevLogs, { type: 'system_error', message: 'WebSocket error occurred.', timestamp: new Date().toISOString() }]);
    };

  }, [name]); // Dependency: agent name

  useEffect(() => {
    connectWebSocket();
    // Cleanup function to close WebSocket when component unmounts or name changes
    return () => {
      if (ws.current) {
        console.log('Closing WebSocket connection.');
        ws.current.close();
      }
    };
  }, [connectWebSocket]); // Run effect when connectWebSocket function updates (due to name change)

  // Auto-scroll to bottom
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]); // Scroll whenever logs update

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 150px)' }}> {/* Adjust height as needed */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Agent Run: {name}</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="caption">Status:</Typography>
            {isConnected ? (
                <Chip label="Connected" color="success" size="small" />
            ) : (
                <Chip label="Connecting..." color="warning" size="small" icon={<CircularProgress size={14} color="inherit" />} />
            )}
            <Button variant="outlined" size="small" onClick={() => nav('/')}>Back to Agents</Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper ref={logContainerRef} sx={{ flexGrow: 1, p: 2, overflowY: 'auto', background: '#f5f5f5' }}>
        {logs.length === 0 && !isConnected && !error && <Typography>Connecting...</Typography>}
        {logs.map((logEntry, i) => (
          <Box key={i} sx={{ mb: 1, fontFamily: 'monospace', fontSize: '0.8rem' }}>
            <Typography variant="caption" color="textSecondary" sx={{ mr: 1 }}>
              [{new Date(logEntry.timestamp).toLocaleTimeString()}]
            </Typography>
            <Typography component="span" sx={{ color: logEntry.type?.includes('error') ? 'red' : 'inherit' }}>
              {/* Attempt to pretty-print if it's an object, otherwise display as string */} 
              {typeof logEntry === 'object' && logEntry !== null ? JSON.stringify(logEntry, null, 2) : String(logEntry)}
            </Typography>
          </Box>
        ))}
      </Paper>
    </Box>
  );
}