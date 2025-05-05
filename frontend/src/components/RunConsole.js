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
  Stack,
  Collapse,
  Divider,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  useTheme,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vs, vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ReplayIcon from '@mui/icons-material/Replay';
import api from '../api';

// Function to determine color based on log type
const getLogTypeColor = (type) => {
  const lowerType = type?.toLowerCase();
  switch (lowerType) {
    case 'error':
    case 'system_error':
    case 'websocketdisconnect':
      return 'error.main';
    case 'warning':
      return 'warning.main';
    case 'info':
    case 'system':
    case 'textmessage':
      return 'info.main';
    case 'debug':
      return 'text.secondary';
    case 'llmrequestevent':
    case 'chatcompletionrequest':
      return 'primary.light';
    case 'llmresponseevent':
    case 'chatcompletionresponseevent':
    case 'textmessagechunk':
      return 'success.light';
    case 'toolcallrequestevent':
    case 'toolcallrequestmessage':
      return 'secondary.light';
    case 'toolcallexecutionevent':
    case 'toolcallresultmessage':
      return 'secondary.main';
    case 'agentstartevent':
    case 'agentfinishevent':
      return 'primary.main';
    default:
      console.warn("Unknown log type received:", type);
      return 'text.primary';
  }
};

// Helper to convert keys into human-friendly labels
function humanizeKey(key) {
  return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

// Helper to safely parse JSON-like strings (handles single quotes, Python consts)
function safeJsonParse(str) {
  if (typeof str !== 'string') return null;
  try {
    const jsonString = str
      .replace(/\\'/g, "'") // Handle escaped single quotes if any
      .replace(/\\"/g, '"') // Handle escaped double quotes if any
      .replace(/: None\b/g, ': null')
      .replace(/: True\b/g, ': true')
      .replace(/: False\b/g, ': false')
      .replace(/'/g, '"'); // Replace single quotes
    return JSON.parse(jsonString);
  } catch (e) {
    return null;
  }
}

// Helper to parse Python Repr content string: key='value', key=Repr(...), ...
function parseReprContent(contentStr) {
  const fields = {};
  // Regex to split by comma, respecting nested structures and quotes
  const pairs = contentStr.split(/,(?=(?:(?:[^\']*'){2})*[^\']*$)(?=(?:(?:[^"]*"){2})*[^"]*$)(?![^\[]*\])(?![^\(]*\))(?![^\{]*\})/) || [];

  pairs.forEach(pair => {
    const parts = pair.match(/^\s*([a-zA-Z_][a-zA-Z0-9_]*)=(.*)\s*$/);
    if (parts) {
      const key = parts[1].trim();
      let value = parts[2].trim();

      // Remove surrounding quotes if value is a simple string literal
      if ((value.startsWith("'") && value.endsWith("'")) || (value.startsWith('"') && value.endsWith('"'))) {
        value = value.slice(1, -1);
        // Basic escape handling (might need refinement)
        value = value.replace(/\\'/g, "'").replace(/\\"/g, '"').replace(/\\\\/g, '\\');
      }

      fields[key] = value;
    }
  });
  return fields;
}

// Safe parsing helper for potentially non-JSON strings
const safeParse = (str) => {
  if (typeof str !== 'string') return str;
  try {
    // First try parsing as JSON
    return JSON.parse(str);
  } catch (e) {
    // If not JSON, try to extract content from Python repr strings
    if (str.includes('(') && str.includes(')')) {
      try {
        // Extract content between parentheses
        const match = str.match(/\((.*)\)/);
        if (match) {
          const inner = match[1];
          // Handle key-value pairs in Python repr
          if (inner.includes('=')) {
            const pairs = inner.split(',').map(pair => {
              const [key, value] = pair.split('=').map(s => s.trim());
              return [key, safeParse(value)];
            });
            return Object.fromEntries(pairs);
          }
          // Try parsing the inner content
          return safeParse(inner);
        }
      } catch (e2) {
        console.warn('Failed to parse Python repr:', e2);
      }
    }
    return str; // Return as-is if all parsing attempts fail
  }
};

const processMessageContent = (content) => {
  if (!content) return '';
  if (typeof content === 'object') return content;
  return safeParse(content);
};

// --- Recursive Data Rendering Component ---
function RenderData({ data, level = 0 }) {
  if (!data) return null;
  
  // Handle string data directly
  if (typeof data === 'string') {
    return <Typography sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{data}</Typography>;
  }

  // Handle error messages
  if (data.message && (data.type === 'error' || level === 0)) {
    return <Typography color="error">{data.message}</Typography>;
  }

  // If data is an array, render each item
  if (Array.isArray(data)) {
    return data.map((item, index) => (
      <Box key={index} sx={{ ml: level > 0 ? 2 : 0, mb: 1 }}>
        <RenderData data={item} level={level + 1} />
      </Box>
    ));
  }

  // Handle messages with content and source (most common case)
  if ('content' in data) {
    const source = data.source || 'system';
    const content = data.content;
    const colorMap = {
      system: 'text.primary',
      tools: 'secondary.main',
      user: 'primary.main',
      assistant: 'success.main',
      error: 'error.main',
      warning: 'warning.main'
    };
    const color = colorMap[source.toLowerCase()] || 'text.primary';

    return (
      <Box sx={{ ml: level > 0 ? 2 : 0, mb: 1 }}>
        {source !== 'system' && (
          <Typography variant="caption" sx={{ color, fontWeight: 'bold', display: 'block', mb: 0.5 }}>
            {source}:
          </Typography>
        )}
        {typeof content === 'string' ? (
          <Typography sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color }}>
            {content}
          </Typography>
        ) : Array.isArray(content) ? (
          content.map((item, idx) => (
            <Box key={idx} sx={{ ml: 2 }}>
              <RenderData data={item} level={level + 1} />
            </Box>
          ))
        ) : typeof content === 'object' ? (
          <Typography component="pre" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace' }}>
            {JSON.stringify(content, null, 2)}
          </Typography>
        ) : (
          <Typography sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color }}>
            {String(content)}
          </Typography>
        )}
      </Box>
    );
  }

  // For objects, render each key-value pair
  const entries = Object.entries(data);
  return (
    <Box sx={{ ml: level > 0 ? 2 : 0 }}>
      {entries.map(([key, value]) => (
        <Box key={key} sx={{ mb: 1 }}>
          {typeof value === 'object' && value !== null ? (
            <>
              <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'block' }}>
                {humanizeKey(key)}:
              </Typography>
              <RenderData data={value} level={level + 1} />
            </>
          ) : (
            <Typography>
              <Box component="span" sx={{ fontWeight: 'bold', color: 'text.secondary' }}>
                {humanizeKey(key)}:
              </Box>{' '}
              {String(value)}
            </Typography>
          )}
        </Box>
      ))}
    </Box>
  );
}

// Main LogMessage component - delegates rendering
function LogMessage({ data, type }) {
  return <RenderData data={data} />;
}

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

        messageData.data = processMessageContent(messageData.data);

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
    <Stack spacing={2} sx={{ height: 'calc(100vh - 110px)' }}>
      <Box component={Paper} sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <Typography variant="h5">
          Agent Run: <Link component={RouterLink} to={`/agents/${name}`} underline="hover">{name}</Link>
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
          <Button variant="outlined" size="small" component={RouterLink} to="/">Back to Agents</Button>
        </Box>
      </Box>

      <Box component={Paper} sx={{ p: 2, display: 'flex', gap: 1, alignItems: 'flex-start', flexShrink: 0 }}>
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
        <Button
          variant="contained"
          onClick={handleRunAgent}
          disabled={!isConnected || isRunning || !taskInput.trim()}
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
          <Box key={i} sx={{
            mb: 1.5,
            display: 'flex',
            alignItems: 'flex-start',
            borderBottom: '1px solid',
            borderBottomColor: 'divider',
            pb: 1.5,
            "&:last-child": { borderBottom: 0, mb: 0, pb: 0 }
          }}>
            <Typography component="span" variant="caption" sx={{ color: 'text.disabled', mr: 1.5, flexShrink: 0, pt: '2px', fontFamily: 'monospace' }}>
              {log.timestamp ? new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '?:??:??'}
            </Typography>
            <Typography component="span" variant="caption" sx={{ color: getLogTypeColor(log.type), fontWeight: 'bold', mr: 1.5, flexShrink: 0, pt: '2px', minWidth: '150px', textAlign: 'right' }}>
              [{log.type?.toUpperCase() || 'UNKNOWN'}]
            </Typography>
            <Box sx={{ flexGrow: 1, width: 'calc(100% - 200px)' }}>
              <LogMessage data={log.data} type={log.type} />
            </Box>
          </Box>
        ))}
      </Paper>
    </Stack>
  );
}