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

// --- Recursive Data Rendering Component ---
function RenderData({ data, level = 0 }) {
  const theme = useTheme();
  const syntaxHighlightStyle = theme.palette.mode === 'dark' ? vscDarkPlus : vs;
  const [showDetails, setShowDetails] = useState(level < 1);

  // 1. Primitive Types & Null
  if (data === null || typeof data === 'number' || typeof data === 'boolean') {
    return <Typography component="span" variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>{String(data)}</Typography>;
  }
  if (data === 'None') return <Typography component="span" variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>null</Typography>;
  if (data === 'True') return <Typography component="span" variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>true</Typography>;
  if (data === 'False') return <Typography component="span" variant="body2" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>false</Typography>;

  // 2. String Type - Handle Repr, JSON, Markdown, and plain text
  if (typeof data === 'string') {
    const trimmedData = data.trim(); // Trim whitespace once

    // --- Handle top-level Response(...) string ---
    if (trimmedData.startsWith('Response(')) {
      // Extract content string inside Response(...)
      const responseContentMatch = trimmedData.match(/^Response\((.*)\)$/s);
      if (responseContentMatch) {
        const fields = parseReprContent(responseContentMatch[1]);
        // Render using the Response structure format
        return (
          <Card variant="outlined" sx={{ width: '100%', bgcolor: 'background.paper', mt: 1 }}>
            <CardContent sx={{ p: 1, "&:last-child": { pb: 1 } }}>
              <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'primary.main', mb: 1, display: 'block' }}>Agent Response</Typography>
              {fields.chat_message && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'block' }}>Chat Message:</Typography>
                  <RenderData data={fields.chat_message} level={level + 1} />
                </Box>
              )}
              {fields.inner_messages && (
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'block' }}>Inner Messages:</Typography>
                  <RenderData data={fields.inner_messages} level={level + 1} />
                </Box>
              )}
            </CardContent>
          </Card>
        );
      }
    }
    // --- End Response(...) string handling ---

    // --- Handle TypeName(...) strings ---
    const reprMatch = trimmedData.match(/^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$/s);
    if (reprMatch) {
      const typeName = reprMatch[1];
      const contentStr = reprMatch[2];
      const fields = parseReprContent(contentStr);

      // Render known types based on typeName
      switch (typeName) {
        case 'TextMessage':
          return (
            <Box sx={{ width: '100%' }}>
              {fields.source && <Chip label={`Source: ${fields.source.replace(/['"]/g, '')}`} size="small" sx={{ mr: 1, mb: 0.5, mt: 0.5 }} />}
              {fields.models_usage && <RenderData data={fields.models_usage} level={level + 1} />}
              {fields.content && <RenderData data={fields.content} level={level + 1} />}
            </Box>
          );
        case 'RequestUsage':
          return (
            <Chip
              label={`Tokens: ${fields.prompt_tokens || '-'} (prompt), ${fields.completion_tokens || '-'} (completion)`}
              size="small"
              variant="outlined"
              sx={{ fontSize: '0.75em', mt: 0.5 }}
            />
          );
        case 'ToolCallRequestEvent':
          return (
            <Accordion elevation={1} sx={{ bgcolor: 'action.hover', width: '100%', mt: 0.5 }} defaultExpanded={level < 1}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: '36px', '.MuiAccordionSummary-content': { my: '8px' } }}>
                <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'secondary.light' }}>Tool Call Request</Typography>
                {fields.source && <Chip label={`Source: ${fields.source.replace(/['"]/g, '')}`} size="small" sx={{ ml: 1 }} />}
              </AccordionSummary>
              <AccordionDetails sx={{ p: 1 }}>
                {fields.models_usage && <Box sx={{ mb: 1 }}><RenderData data={fields.models_usage} level={level + 1} /></Box>}
                {fields.content && <RenderData data={fields.content} level={level + 1} />}
              </AccordionDetails>
            </Accordion>
          );
        case 'FunctionCall':
          let argsData = fields.arguments;
          const parsedArgs = safeJsonParse(argsData);
          if (parsedArgs !== null) {
            argsData = parsedArgs;
          }
          return (
            <Card variant="outlined" sx={{ width: '100%', mb: 1, bgcolor: 'action.hover' }}>
              <CardContent sx={{ p: 1, "&:last-child": { pb: 1 } }}>
                <Chip label={`${fields.name?.replace(/['"]/g, '') || 'Unknown Tool'}`} color="secondary" size="small" sx={{ mb: 0.5 }} />
                <Typography variant="caption" display="block" sx={{ color: 'text.secondary', mb: 0.5 }}>
                  Call ID: {fields.id?.replace(/['"]/g, '')}
                </Typography>
                <Typography variant="subtitle2" sx={{ mt: 1, mb: 0.5 }}>
                  Arguments:
                </Typography>
                <RenderData data={argsData} level={level + 1} />
              </CardContent>
            </Card>
          );
        default:
          return <RenderData data={fields} level={level} />;
      }
    }
    // --- End TypeName(...) string handling ---

    // --- Handle list-like strings [...] ---
    if (trimmedData.startsWith('[') && trimmedData.endsWith(']')) {
      const listContent = trimmedData.slice(1, -1).trim();
      if (!listContent) {
        return <Typography component="span" variant="body2" sx={{ color: 'text.disabled' }}>[]</Typography>;
      }
      // Split items respecting nested structures
      // FIX: Use a simpler, robust split for top-level commas only (does not break on nested parens/brackets/braces)
      // This will not split inside nested structures, but will split top-level items correctly for most repr lists
      let depth = 0;
      let current = '';
      const items = [];
      for (let i = 0; i < listContent.length; i++) {
        const char = listContent[i];
        if (char === '(' || char === '[' || char === '{') depth++;
        if (char === ')' || char === ']' || char === '}') depth--;
        if (char === ',' && depth === 0) {
          items.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }
      if (current.trim()) items.push(current.trim());
      return (
        <Stack spacing={1} sx={{ width: '100%', mt: 0.5 }}>
          {items.map((itemStr, index) => {
            const trimmedItemStr = itemStr.trim();
            // Pass the individual item string back for recursive processing
            // RenderData will handle parsing it if it's a TypeName(...) string,
            // JSON, or plain text.
            return (
              <Box key={index} sx={{ borderLeft: '2px solid', borderColor: 'divider', pl: 1, width: '100%' }}>
                <RenderData data={trimmedItemStr} level={level + 1} />
              </Box>
            );
          })}
        </Stack>
      );
    }
    // --- End list-like string handling ---

    // Attempt to parse as JSON
    const parsedJson = safeJsonParse(trimmedData);
    if (parsedJson !== null) {
      return <RenderData data={parsedJson} level={level} />;
    }

    // Fallback: Render as Markdown or plain text
    if (trimmedData.includes('\n') || trimmedData.match(/[*_`[#]/)) {
      return (
        <Box sx={{ width: '100%', wordBreak: 'break-word' }}>
          <ReactMarkdown
            components={{
              p: ({ node, ...props }) => <Typography component="span" variant="body2" {...props} />,
              code: ({ node, inline, className, children, ...props }) => {
                const match = /language-(\w+)/.exec(className || '');
                return !inline ? (
                  <SyntaxHighlighter
                    style={syntaxHighlightStyle}
                    language={match ? match[1] : 'text'}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <Typography component="code" sx={{ fontFamily: 'monospace', bgcolor: 'action.hover', px: 0.5, borderRadius: 0.5, fontSize: '0.85em' }} {...props}>
                    {children}
                  </Typography>
                );
              },
              a: ({ node, ...props }) => <Link target="_blank" rel="noopener noreferrer" {...props} />,
            }}
          >
            {trimmedData}
          </ReactMarkdown>
        </Box>
      );
    } else {
      return <Typography component="span" variant="body2">{trimmedData}</Typography>;
    }
  }

  // 3. Array Type
  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <Typography component="span" variant="body2" sx={{ color: 'text.disabled' }}>[]</Typography>;
    }
    return (
      <Stack spacing={1} sx={{ width: '100%', mt: 0.5 }}>
        {data.map((item, index) => (
          <Box key={index} sx={{ borderLeft: '2px solid', borderColor: 'divider', pl: 1 }}>
            <RenderData data={item} level={level + 1} />
          </Box>
        ))}
      </Stack>
    );
  }

  // 4. Object Type
  if (typeof data === 'object') {
    const entries = Object.entries(data);
    if (entries.length === 0) {
      return <Typography component="span" variant="body2" sx={{ color: 'text.disabled' }}>{`{}`}</Typography>;
    }

    // --- Specific Object Structure Rendering ---
    if ('name' in data && 'arguments' in data && 'id' in data) {
      let argsData = data.arguments;
      if (typeof argsData === 'string') {
        const parsedArgs = safeJsonParse(argsData);
        if (parsedArgs !== null) argsData = parsedArgs;
      }
      return (
        <Card variant="outlined" sx={{ width: '100%', mb: 1, bgcolor: 'action.hover' }}>
          <CardContent sx={{ p: 1, "&:last-child": { pb: 1 } }}>
            <Chip label={data.name || 'Unknown Tool'} color="secondary" size="small" sx={{ mb: 0.5 }} />
            <Typography variant="caption" display="block" sx={{ color: 'text.secondary', mb: 0.5 }}>
              Call ID: {data.id}
            </Typography>
            <Typography variant="subtitle2" sx={{ mt: 1, mb: 0.5 }}>
              Arguments:
            </Typography>
            <RenderData data={argsData} level={level + 1} />
          </CardContent>
        </Card>
      );
    }

    if ('name' in data && 'call_id' in data && 'content' in data) {
      const isError = data.is_error === true;
      return (
        <Card variant="outlined" sx={{ width: '100%', mb: 1, borderColor: isError ? 'error.main' : 'divider', bgcolor: 'action.hover' }}>
          <CardContent sx={{ p: 1, "&:last-child": { pb: 1 } }}>
            <Chip label={data.name || 'Unknown Tool'} color={isError ? 'error' : 'secondary'} size="small" sx={{ mb: 0.5 }} />
            <Typography variant="caption" display="block" sx={{ color: 'text.secondary' }}>Call ID: {data.call_id}</Typography>
            {isError && <Chip label="Error" color="error" size="small" sx={{ mr: 1, mt: 0.5 }} />}
            <Typography variant="subtitle2" sx={{ mt: 1, mb: 0.5 }}>Result:</Typography>
            <RenderData data={data.content} level={level + 1} />
          </CardContent>
        </Card>
      );
    }

    if ('content' in data && ('source' in data || 'models_usage' in data || entries.length <= 3)) {
      const isLikelyTextMessage = 'source' in data || 'models_usage' in data || (typeof data.content === 'string' && entries.length === 1);
      if (isLikelyTextMessage) {
        return (
          <Box sx={{ width: '100%' }}>
            {data.source && <Chip label={`Source: ${data.source}`} size="small" sx={{ mr: 1, mb: 0.5, mt: 0.5 }} />}
            {data.models_usage && <RenderData data={data.models_usage} level={level + 1} />}
            <RenderData data={data.content} level={level + 1} />
          </Box>
        );
      }
    }

    if ('prompt_tokens' in data || 'completion_tokens' in data) {
      return (
        <Chip
          label={`Tokens: ${data.prompt_tokens || '-'} (prompt), ${data.completion_tokens || '-'} (completion)`}
          size="small"
          variant="outlined"
          sx={{ fontSize: '0.75em', mt: 0.5 }}
        />
      );
    }

    if ('chat_message' in data && 'inner_messages' in data) {
      return (
        <Card variant="outlined" sx={{ width: '100%', bgcolor: 'background.paper', mt: 1 }}>
          <CardContent sx={{ p: 1, "&:last-child": { pb: 1 } }}>
            <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'primary.main', mb: 1, display: 'block' }}>Agent Response</Typography>
            {data.chat_message && (
              <Box sx={{ mb: 1 }}>
                <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'block' }}>Chat Message:</Typography>
                <RenderData data={data.chat_message} level={level + 1} />
              </Box>
            )}
            {data.inner_messages && (
              <Box>
                <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'block' }}>Inner Messages:</Typography>
                <RenderData data={data.inner_messages} level={level + 1} />
              </Box>
            )}
          </CardContent>
        </Card>
      );
    }

    if ('content' in data && 'source' in data && entries.length <= 3) {
      const isRequest = data.source?.toLowerCase().includes('request');
      const title = isRequest ? 'Tool Call Request' : 'Tool Execution Result';
      const color = isRequest ? 'secondary.light' : 'secondary.main';
      return (
        <Accordion elevation={1} sx={{ bgcolor: 'action.hover', width: '100%', mt: 0.5 }} defaultExpanded={level < 1}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: '36px', '.MuiAccordionSummary-content': { my: '8px' } }}>
            <Typography variant="caption" sx={{ fontWeight: 'bold', color: color }}>{title}</Typography>
            <Chip label={`Source: ${data.source}`} size="small" sx={{ ml: 1 }} />
          </AccordionSummary>
          <AccordionDetails sx={{ p: 1 }}>
            {data.models_usage && <Box sx={{ mb: 1 }}><RenderData data={data.models_usage} level={level + 1} /></Box>}
            <RenderData data={data.content} level={level + 1} />
          </AccordionDetails>
        </Accordion>
      );
    }

    const isComplex = entries.length > 3 || entries.some(([k, v]) => typeof v === 'object' || (typeof v === 'string' && v.length > 80));

    if (!isComplex && level > 0) {
      return (
        <Typography component="span" variant="body2" sx={{ fontFamily: 'monospace', bgcolor: 'action.hover', px: 0.5, borderRadius: 0.5, fontSize: '0.85em' }}>
          {JSON.stringify(data)}
        </Typography>
      );
    }

    return (
      <Box sx={{ width: '100%', mt: 0.5 }}>
        <Button
          size="small"
          variant="text"
          startIcon={showDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          onClick={() => setShowDetails(v => !v)}
          sx={{ fontSize: '0.75em', color: 'text.secondary', p: '2px 4px', minWidth: 'auto', textTransform: 'none', "&:hover": { bgcolor: 'action.hover' } }}
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </Button>
        <Collapse in={showDetails}>
          <Stack spacing={0.5} sx={{ mt: 0.5, pl: 1, borderLeft: '2px solid', borderColor: 'divider' }}>
            {entries.map(([key, value]) => (
              <Box key={key} sx={{ display: 'flex' }}>
                <Typography variant="caption" sx={{ fontWeight: 'bold', mr: 1, minWidth: '100px', color: 'text.secondary', flexShrink: 0 }}>
                  {humanizeKey(key)}:
                </Typography>
                <Box sx={{ flexGrow: 1 }}>
                  <RenderData data={value} level={level + 1} />
                </Box>
              </Box>
            ))}
          </Stack>
          <Accordion elevation={0} sx={{ bgcolor: 'transparent', '.MuiAccordionSummary-root': { minHeight: '24px' }, '.MuiAccordionSummary-content': { my: 0 } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ p: 0 }}>
              <Typography variant="caption" sx={{ color: 'text.disabled' }}>Raw JSON</Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0 }}>
              <SyntaxHighlighter
                language="json"
                style={syntaxHighlightStyle}
                PreTag="div"
              >
                {JSON.stringify(data, null, 2)}
              </SyntaxHighlighter>
            </AccordionDetails>
          </Accordion>
        </Collapse>
      </Box>
    );
  }

  return <Typography component="span" variant="body2">{`[Unknown Data Type: ${typeof data}]`}</Typography>;
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