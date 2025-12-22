import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Stack,
  Button,
  CircularProgress,
  Alert,
  List,
  ListItemButton,
  ListItemText,
  Collapse,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import SensorsIcon from '@mui/icons-material/Sensors';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { getHtmlDisplayLatest, getHtmlDisplayContent } from '../../../api';

const POLL_INTERVAL_MS = 3000;

export default function HtmlDisplayPage() {
  const [latestInfo, setLatestInfo] = useState(null);
  const [htmlContent, setHtmlContent] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const lastModifiedRef = useRef(null);

  const fetchLatest = async (force = false) => {
    try {
      const response = await getHtmlDisplayLatest();
      const data = response.data;
      setLatestInfo(data);
      setError(null);

      // If latest file changed, fetch its content
      if (data.has_content && data.modified !== lastModifiedRef.current) {
        lastModifiedRef.current = data.modified;
        // Only auto-load if no file is manually selected, or if viewing latest
        if (!selectedFile || selectedFile === data.filename) {
          setSelectedFile(data.filename);
          await fetchHtmlContent(data.filename);
        }
      }
    } catch (e) {
      if (force) {
        setError(e?.response?.data?.detail || 'Failed to load display info');
      }
    }
  };

  const fetchHtmlContent = async (filename = null) => {
    setLoading(true);
    try {
      const response = await getHtmlDisplayContent(filename);
      setHtmlContent(response.data || '');
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load HTML content');
      setHtmlContent('');
    } finally {
      setLoading(false);
    }
  };

  // Initial load + polling
  useEffect(() => {
    fetchLatest(true);
    const interval = setInterval(() => fetchLatest(), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const handleManualRefresh = () => {
    lastModifiedRef.current = null;
    setSelectedFile(null);
    fetchLatest(true);
  };

  const handleSelectFile = async (filename) => {
    setSelectedFile(filename);
    await fetchHtmlContent(filename);
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return '';
    return new Date(timestamp * 1000).toLocaleString();
  };

  const isViewingLatest = !selectedFile || selectedFile === latestInfo?.filename;

  return (
    <Stack spacing={2}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
        <Stack direction="row" spacing={1} alignItems="center">
          <SensorsIcon color="primary" />
          <Typography variant="h5" component="h1">
            HTML Display
          </Typography>
        </Stack>
        <Stack direction="row" spacing={1}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleManualRefresh}
            disabled={loading}
          >
            Refresh
          </Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error">{error}</Alert>}

      <Paper sx={{ p: 2 }}>
        <Stack spacing={1}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ xs: 'flex-start', sm: 'center' }} justifyContent="space-between">
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <Typography variant="body1" sx={{ wordBreak: 'break-all' }}>
                {latestInfo?.has_content ? (
                  <>
                    Viewing: <strong>{selectedFile || latestInfo.filename}</strong>
                    {isViewingLatest && <Typography component="span" color="primary.main" sx={{ ml: 1 }}>(latest)</Typography>}
                  </>
                ) : (
                  'No HTML files yet'
                )}
              </Typography>
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center">
              {loading && <CircularProgress size={18} />}
              {latestInfo?.has_content && (
                <Typography variant="body2" color="text.secondary">
                  {formatDate(latestInfo.modified)}
                </Typography>
              )}
            </Stack>
          </Stack>

          {/* File history toggle */}
          {latestInfo?.files?.length > 1 && (
            <>
              <Button
                size="small"
                onClick={() => setShowHistory(!showHistory)}
                endIcon={showHistory ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                sx={{ alignSelf: 'flex-start' }}
              >
                History ({latestInfo.files.length} files)
              </Button>
              <Collapse in={showHistory}>
                <List dense sx={{ maxHeight: 200, overflow: 'auto', bgcolor: 'background.default', borderRadius: 1 }}>
                  {latestInfo.files.map((file) => (
                    <ListItemButton
                      key={file.filename}
                      selected={selectedFile === file.filename}
                      onClick={() => handleSelectFile(file.filename)}
                    >
                      <ListItemText
                        primary={file.filename}
                        secondary={formatDate(file.modified)}
                      />
                    </ListItemButton>
                  ))}
                </List>
              </Collapse>
            </>
          )}
        </Stack>
      </Paper>

      <Paper sx={{ p: 1, minHeight: '60vh' }}>
        {loading && !htmlContent ? (
          <Box display="flex" alignItems="center" justifyContent="center" height="100%" py={4}>
            <CircularProgress />
          </Box>
        ) : !latestInfo?.has_content ? (
          <Box display="flex" alignItems="center" justifyContent="center" height="100%" py={4}>
            <Typography color="text.secondary">
              Run the HTMLDisplay agent to generate content
            </Typography>
          </Box>
        ) : (
          <Box sx={{ border: (theme) => `1px solid ${theme.palette.divider}`, borderRadius: 1, overflow: 'hidden', minHeight: '60vh' }}>
            <iframe
              title="HTML Display"
              srcDoc={htmlContent}
              sandbox="allow-scripts allow-same-origin allow-forms allow-pointer-lock allow-downloads"
              style={{ width: '100%', height: '70vh', border: 'none', background: '#0b1224' }}
              key={selectedFile || 'html-display'}
            />
          </Box>
        )}
      </Paper>
    </Stack>
  );
}
