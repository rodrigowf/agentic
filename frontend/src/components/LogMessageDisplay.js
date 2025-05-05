import React, { useState } from 'react';
import {
  Typography,
  Box,
  Chip,
  Link,
  Stack,
  Divider,
  Card,
  CardHeader,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  useTheme,
  IconButton,
  Collapse,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline';
import BuildOutlinedIcon from '@mui/icons-material/BuildOutlined';
import CodeIcon from '@mui/icons-material/Code';
import NotesIcon from '@mui/icons-material/Notes'; // Generic icon
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vs, vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

// Function to determine color based on log type
export const getLogTypeColor = (type) => {
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

// Helper to safely parse JSON-like strings
function safeJsonParse(str) {
  if (typeof str !== 'string') return null;
  try {
    const jsonString = str
      .replace(/\\'/g, "'")
      .replace(/\\"/g, '"')
      .replace(/: None\b/g, ': null')
      .replace(/: True\b/g, ': true')
      .replace(/: False\b/g, ': false')
      .replace(/'/g, '"');
    return JSON.parse(jsonString);
  } catch (e) {
    return null;
  }
}

// Helper to parse Python Repr content string
function parseReprContent(contentStr) {
  const fields = {};
  const pairs = contentStr.split(/,(?=(?:(?:[^\']*'){2})*[^\']*$)(?=(?:(?:[^"]*"){2})*[^"]*$)(?![^\[]*\])(?![^\(]*\))(?![^\{]*\})/) || [];

  pairs.forEach(pair => {
    const parts = pair.match(/^\s*([a-zA-Z_][a-zA-Z0-9_]*)=(.*)\s*$/);
    if (parts) {
      const key = parts[1].trim();
      let value = parts[2].trim();

      if ((value.startsWith("'") && value.endsWith("'")) || (value.startsWith('"') && value.endsWith('"'))) {
        value = value.slice(1, -1);
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
    return JSON.parse(str);
  } catch (e) {
    if (str.includes('(') && str.includes(')')) {
      try {
        const match = str.match(/\((.*)\)/);
        if (match) {
          const inner = match[1];
          if (inner.includes('=')) {
            const pairs = inner.split(',').map(pair => {
              const [key, value] = pair.split('=').map(s => s.trim());
              return [key, safeParse(value)];
            });
            return Object.fromEntries(pairs);
          }
          return safeParse(inner);
        }
      } catch (e2) {
        console.warn('Failed to parse Python repr:', e2);
      }
    }
    return str;
  }
};

const processMessageContent = (content) => {
  if (!content) return '';
  if (typeof content === 'object') return content;
  return safeParse(content);
};

// Icon Mapping
const getLogTypeIcon = (type) => {
  const lowerType = type?.toLowerCase();
  switch (lowerType) {
    case 'error':
    case 'system_error':
      return <ErrorOutlineIcon fontSize="inherit" sx={{ mr: 0.5 }} />;
    case 'warning':
      return <WarningAmberIcon fontSize="inherit" sx={{ mr: 0.5 }} />;
    case 'system':
    case 'info':
      return <InfoOutlinedIcon fontSize="inherit" sx={{ mr: 0.5 }} />;
    case 'assistant':
    case 'textmessage':
    case 'llmresponseevent':
    case 'chatcompletionresponseevent':
      return <CheckCircleOutlineIcon fontSize="inherit" sx={{ mr: 0.5 }} />;
    case 'user':
    case 'llmrequestevent':
    case 'chatcompletionrequest':
      return <PlayCircleOutlineIcon fontSize="inherit" sx={{ mr: 0.5 }} />;
    case 'tools':
    case 'toolcallrequestevent':
    case 'toolcallexecutionevent':
    case 'functioncall':
      return <BuildOutlinedIcon fontSize="inherit" sx={{ mr: 0.5 }} />;
    default:
      return <NotesIcon fontSize="inherit" sx={{ mr: 0.5 }} />;
  }
};

// Updated TextMessage Renderer
const renderTextMessage = (fields, theme) => {
  const [tokensVisible, setTokensVisible] = useState(false);

  return (
    <Card 
      variant="outlined" 
      sx={{ 
        width: '100%', 
        bgcolor: 'transparent',
        border: 'none',
        my: 0,
        boxShadow: 'none',
        position: 'relative',
      }}
    >
      <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
        {fields.models_usage && (
          <Box sx={{ position: 'absolute', top: -5, right: -5, zIndex: 2 }}>
            <IconButton 
              size="small" 
              onClick={() => setTokensVisible(!tokensVisible)} 
              title="Toggle Token Usage"
              sx={{ 
                bgcolor: 'action.hover', 
                '&:hover': { bgcolor: 'action.selected' },
                p: 0.5
              }}
            >
              <CodeIcon fontSize="small" sx={{ color: 'text.secondary' }} />
            </IconButton>
          </Box>
        )}
        <Collapse in={tokensVisible}>
          {fields.models_usage && (
            <Stack 
              direction="row" 
              spacing={1} 
              sx={{ 
                mb: 1.5,
                p: 1,
                bgcolor: 'action.focus',
                borderRadius: 1,
              }}
            >
              <Chip
                icon={<Typography variant="caption" sx={{ mr: -0.5, color: 'inherit', opacity: 0.7 }}>🔄</Typography>}
                label={`${fields.models_usage.prompt_tokens || '-'} Prompt`}
                color="primary"
                size="small"
                variant="outlined"
                sx={{ height: '24px', '& .MuiChip-label': { px: 1, fontSize: '0.75rem' } }}
              />
              <Chip
                icon={<Typography variant="caption" sx={{ mr: -0.5, color: 'inherit', opacity: 0.7 }}>↪</Typography>}
                label={`${fields.models_usage.completion_tokens || '-'} Completion`}
                color="success"
                size="small"
                variant="outlined"
                sx={{ height: '24px', '& .MuiChip-label': { px: 1, fontSize: '0.75rem' } }}
              />
            </Stack>
          )}
        </Collapse>
        {fields.source && (
          <Chip 
            label={fields.source.replace(/['"]/g, '')}
            size="small"
            variant="outlined"
            sx={{ 
              mb: 1.5, 
              fontWeight: 500,
              textTransform: 'capitalize',
              borderColor: 'divider',
              color: 'text.secondary',
              fontSize: '0.75rem'
            }}
          />
        )}
        {fields.content && <RenderData data={fields.content} level={1} />}
      </CardContent>
    </Card>
  );
}

// Updated Recursive Data Rendering Component
function RenderData({ data, level = 0 }) {
  const theme = useTheme();
  const [showDetails] = useState(level < 1);

  // Handle null and primitive types - Use Chips!
  if (data === null) {
    return <Chip label="null" size="small" sx={{ bgcolor: 'grey.300', color: 'text.secondary', fontFamily: 'monospace', fontWeight: 600, height: '20px' }} />;
  }
  if (typeof data === 'boolean') {
    return <Chip 
             label={String(data)} 
             size="small" 
             color={data ? 'success' : 'error'} 
             variant="outlined"
             sx={{ fontFamily: 'monospace', fontWeight: 600, height: '20px', 
                   borderColor: data ? 'success.main' : 'error.main', 
                   color: data ? 'success.dark' : 'error.dark',
                   bgcolor: data ? 'success.light' : 'error.light',
                   opacity: 0.8
                 }}
           />;
  }
  if (typeof data === 'number') {
    return <Chip 
             label={String(data)} 
             size="small" 
             color="info"
             variant="filled"
             sx={{ fontFamily: 'monospace', fontWeight: 600, height: '20px', 
                   bgcolor: 'info.light', 
                   color: 'info.dark' 
                 }}
            />;
  }

  // Handle strings
  if (typeof data === 'string') {
    if (data === 'None') return <RenderData data={null} level={level} />;
    if (data === 'True') return <RenderData data={true} level={level} />;
    if (data === 'False') return <RenderData data={false} level={level} />;

    const trimmedData = data.trim();

    if (/^(```|# |\*\*|\d+\.|- )/.test(trimmedData) || trimmedData.includes('\n')) {
      return (
        <Box sx={{ my: 1, fontSize: '0.95rem' }}>
          <ReactMarkdown
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline ? (
                  <SyntaxHighlighter
                    style={theme.palette.mode === 'dark' ? vscDarkPlus : vs}
                    language={match?.[1] || 'text'}
                    PreTag="div"
                    customStyle={{ 
                      borderRadius: 8, 
                      fontSize: '0.9em',
                      margin: '8px 0', 
                      padding: '12px' 
                    }}
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code 
                    style={{ 
                      background: theme.palette.action.selected, 
                      borderRadius: 4, 
                      padding: '2px 6px', 
                      fontFamily: 'monospace', 
                      fontSize: '0.9em' 
                    }}
                    {...props}
                  >
                    {children}
                  </code>
                );
              },
              a({ node, ...props }) {
                return <Link {...props} target="_blank" rel="noopener noreferrer" sx={{ color: 'primary.main', textDecoration: 'underline' }} />;
              },
              p({ node, ...props }) {
                return <Typography variant="body2" component="p" sx={{ mb: 1 }} {...props} />;
              },
              li({ node, ...props }) {
                return <li style={{ marginBottom: 4, fontSize: '0.95rem' }} {...props} />;
              }
            }}
          >
            {trimmedData}
          </ReactMarkdown>
        </Box>
      );
    }

    if (trimmedData.startsWith('Response(')) {
      const responseContentMatch = trimmedData.match(/^Response\((.*)\)$/s);
      if (responseContentMatch) {
        const fields = parseReprContent(responseContentMatch[1]);
        return (
          <Card variant="outlined" sx={{ width: '100%', bgcolor: 'action.hover', mt: 1, boxShadow: 0, borderRadius: 2 }}>
            <CardHeader 
              title="Agent Response" 
              titleTypographyProps={{ variant: 'caption', fontWeight: 'bold', color: 'text.secondary' }}
              sx={{ pb: 0, pt: 1, px: 1.5 }}
            />
            <CardContent sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}>
              {fields.chat_message && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.disabled', display: 'block', mb: 0.5 }}>Chat Message:</Typography>
                  <RenderData data={fields.chat_message} level={level + 1} />
                </Box>
              )}
              {fields.inner_messages && (
                <Box>
                  <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.disabled', display: 'block', mb: 0.5 }}>Inner Messages:</Typography>
                  <RenderData data={fields.inner_messages} level={level + 1} />
                </Box>
              )}
            </CardContent>
          </Card>
        );
      }
    }

    const reprMatch = trimmedData.match(/^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$/s);
    if (reprMatch) {
      const typeName = reprMatch[1];
      const contentStr = reprMatch[2];
      const fields = parseReprContent(contentStr);

      switch (typeName) {
        case 'TextMessage':
          return renderTextMessage(fields, theme);

        case 'RequestUsage':
          return (
            <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
              <Chip
                label={`${fields.prompt_tokens || '-'} Prompt`}
                size="small"
                variant="outlined"
                color="primary"
                sx={{ fontSize: '0.7rem' }}
              />
              <Chip
                label={`${fields.completion_tokens || '-'} Completion`}
                size="small"
                variant="outlined"
                color="success"
                sx={{ fontSize: '0.7rem' }}
              />
            </Stack>
          );

        case 'ToolCallRequestEvent':
          return (
            <Accordion elevation={0} sx={{ bgcolor: 'action.hover', width: '100%', mt: 1, borderRadius: 2, boxShadow: 0, border: '1px solid', borderColor: 'divider', '&.Mui-expanded': { mt: 1, mb: 1 }, '&:before': { display: 'none' } }} defaultExpanded={level < 1}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ minHeight: '36px', '.MuiAccordionSummary-content': { my: '8px', alignItems: 'center' } }}>
                <BuildOutlinedIcon fontSize="small" sx={{ mr: 1, color: 'secondary.main' }} />
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'secondary.main', letterSpacing: 0.5 }}>Tool Call Request</Typography>
                {fields.source && <Chip label={fields.source.replace(/['"]/g, '')} size="small" sx={{ ml: 1.5, fontSize: '0.7rem' }} />}
              </AccordionSummary>
              <AccordionDetails sx={{ p: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
                {fields.models_usage && <Box sx={{ mb: 1 }}><RenderData data={fields.models_usage} level={level + 1} /></Box>}
                {fields.content && <RenderData data={fields.content} level={level + 1} />}
              </AccordionDetails>
            </Accordion>
          );

        case 'FunctionCall':
          return (
            <Card variant="outlined" sx={{ width: '100%', mb: 1, bgcolor: 'action.focus', border: '1px solid', borderColor: 'divider', boxShadow: 0, borderRadius: 2 }}>
              <CardContent sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Stack direction="row" spacing={1} alignItems="center" mb={1.5}>
                  <Chip 
                    icon={<BuildOutlinedIcon fontSize="small" />}
                    label={fields.name?.replace(/['"]/g, '') || 'Unknown Tool'} 
                    color="secondary" 
                    size="small" 
                    sx={{ fontWeight: 'bold' }}
                  />
                  {fields.id && <Chip label={`ID: ${fields.id.replace(/['"]/g, '')}`} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />}
                </Stack>
                <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.secondary', display: 'block', mb: 0.5 }}>
                  Arguments:
                </Typography>
                <RenderData data={fields.arguments} level={level + 1} />
              </CardContent>
            </Card>
          );
        default:
          return (
            <Box sx={{ p: 1, bgcolor: 'action.hover', borderRadius: 1, border: '1px solid', borderColor: 'divider' }}>
              <Typography variant="caption" sx={{ fontWeight: 'bold', color: 'text.secondary' }}>{typeName}</Typography>
              <RenderData data={fields} level={level + 1} />
            </Box>
          );
      }
    }
    
    return <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.6 }}>{data}</Typography>;
  }

  // Handle arrays
  if (Array.isArray(data)) {
    if (data.length === 0) return <Typography variant="caption" color="text.secondary">(Empty array)</Typography>;
    return (
      <Stack spacing={1} sx={{ ml: level > 0 ? 1 : 0, my: 1, pl: 1, borderLeft: level > 0 ? '2px solid' : undefined, borderColor: 'divider' }}>
        {data.map((item, index) => (
          <Box key={index}>
            <RenderData data={item} level={level + 1} />
          </Box>
        ))}
      </Stack>
    );
  }

  // Special Handling for Token Usage Object
  if (typeof data === 'object' && data !== null && ('prompt_tokens' in data || 'completion_tokens' in data) && !('content' in data)) {
    return (
      <Stack 
        direction="row" 
        spacing={1} 
        sx={{ 
          mt: 0.5, 
          p: 0.5, 
        }}
      >
        <Chip
          icon={<Typography variant="caption" sx={{ mr: -0.5, color: 'inherit', opacity: 0.7 }}>🔄</Typography>}
          label={`${data.prompt_tokens ?? '-'} Prompt`}
          color="primary"
          size="small"
          variant="outlined"
          sx={{ height: '24px', '& .MuiChip-label': { px: 1, fontSize: '0.75rem' } }}
        />
        <Chip
          icon={<Typography variant="caption" sx={{ mr: -0.5, color: 'inherit', opacity: 0.7 }}>↪</Typography>}
          label={`${data.completion_tokens ?? '-'} Completion`}
          color="success"
          size="small"
          variant="outlined"
          sx={{ height: '24px', '& .MuiChip-label': { px: 1, fontSize: '0.75rem' } }}
        />
      </Stack>
    );
  }

  // Handle regular objects - cleaner key/value display
  return (
    <Box sx={{ ml: level > 0 ? 1 : 0, my: 1, p: 1, bgcolor: level > 0 ? 'action.focus' : undefined, borderRadius: 1 }}>
      <Stack spacing={1} divider={<Divider flexItem sx={{ my: 0.5, borderColor: 'divider' }} />}>
        {Object.entries(data)
          .filter(([key, value]) => {
            // Filter out null, undefined, or empty string values
            if (value === null || value === undefined || value === '') {
              return false;
            }
            // Filter out empty objects
            if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) {
              return false;
            }
            // Filter out empty arrays (optional, uncomment if needed)
            // if (Array.isArray(value) && value.length === 0) {
            //   return false;
            // }
            return true; // Keep the entry if none of the above conditions are met
          })
          .map(([key, value]) => (
            <Box key={key}>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 'bold', letterSpacing: 0.5, display: 'block' }}>{humanizeKey(key)}:</Typography>
              <Box sx={{ pl: 1, mt: 0.5 }}>
                <RenderData data={value} level={level + 1} />
              </Box>
            </Box>
        ))}
      </Stack>
    </Box>
  );
}

// Main LogMessage Component
export const LogMessage = ({ data, type }) => {
  return <RenderData data={data} />;
};

// Updated LogEntry Component
export const LogEntry = ({ log }) => {
  const theme = useTheme();
  const color = getLogTypeColor(log.type);
  const Icon = getLogTypeIcon(log.type);
  
  return (
    <Box sx={{
      mb: 2,
      display: 'flex',
      alignItems: 'flex-start',
      position: 'relative',
      pl: 5,
      pb: 2,
      borderBottom: `1px solid ${theme.palette.divider}`,
      '&:last-child': { borderBottom: 0, mb: 0, pb: 0 }
    }}>
      <Box sx={{
        position: 'absolute',
        left: 16,
        top: 0,
        bottom: 0,
        width: '2px',
        bgcolor: theme.palette.divider,
        display: 'flex',
        justifyContent: 'center',
      }}>
        <Box sx={{
          position: 'absolute',
          top: 4,
          bgcolor: theme.palette.background.paper,
          p: 0.5,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: color,
          border: `2px solid ${theme.palette.divider}`
        }}>
          {Icon}
        </Box>
      </Box>
      <Typography 
        component="span" 
        variant="caption" 
        sx={{ 
          position: 'absolute',
          left: 40,
          top: 8,
          color: 'text.disabled',
          fontFamily: 'monospace',
          fontSize: '0.7rem',
        }}
      >
        {log.timestamp ? new Date(log.timestamp).toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit', 
          second: '2-digit' 
        }) : '?:??:??'}
      </Typography>
      <Box sx={{ 
        flexGrow: 1,
        width: '100%',
        pt: 0.5,
      }}>
        <LogMessage data={log.data} type={log.type} />
      </Box>
    </Box>
  );
};

export default LogEntry;