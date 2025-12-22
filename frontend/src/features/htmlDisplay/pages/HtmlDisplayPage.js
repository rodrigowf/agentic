import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Stack,
  Button,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import SensorsIcon from '@mui/icons-material/Sensors';
import TextSnippetIcon from '@mui/icons-material/TextSnippet';
import { getHtmlDisplayConfig, getActiveHtmlDisplay } from '../../../api';

const POLL_INTERVAL_MS = 5000;

export default function HtmlDisplayPage() {
  const [config, setConfig] = useState(null);
  const [htmlContent, setHtmlContent] = useState('');
  const [loadingConfig, setLoadingConfig] = useState(false);
  const [loadingHtml, setLoadingHtml] = useState(false);
  const [error, setError] = useState(null);
  const lastActiveRef = useRef(null);

  const activeMeta = useMemo(() => {
    if (!config?.config?.files) return null;
    return config.config.files.find((file) => file.path === config.config.active_file) || null;
  }, [config]);

  const fetchConfig = async (force = false) => {
    if (loadingConfig && !force) return;
    setLoadingConfig(true);
    try {
      const response = await getHtmlDisplayConfig();
      setConfig(response.data);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load display config');
    } finally {
      setLoadingConfig(false);
    }
  };

  const fetchHtml = async () => {
    setLoadingHtml(true);
    try {
      const response = await getActiveHtmlDisplay();
      setHtmlContent(response.data || '');
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load active HTML');
      setHtmlContent('');
    } finally {
      setLoadingHtml(false);
    }
  };

  // Initial load + polling for active_file changes
  useEffect(() => {
    fetchConfig(true);
    const interval = setInterval(() => fetchConfig(), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  // When config changes, reload HTML if active_file changed
  useEffect(() => {
    const activeFile = config?.config?.active_file;
    if (!activeFile) return;
    if (activeFile !== lastActiveRef.current) {
      lastActiveRef.current = activeFile;
      fetchHtml();
    }
  }, [config]);

  const handleManualRefresh = () => {
    fetchConfig(true);
    fetchHtml();
  };

  const activeFilePath = config?.config?.active_file || 'Not set';

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
            disabled={loadingConfig || loadingHtml}
          >
            Refresh
          </Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error">{error}</Alert>}

      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ xs: 'flex-start', sm: 'center' }} justifyContent="space-between">
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <TextSnippetIcon color="action" />
            <Typography variant="body1" sx={{ wordBreak: 'break-all' }}>
              Active file: {activeFilePath}
            </Typography>
            {activeMeta?.label && <Chip label={activeMeta.label} size="small" color="primary" />}
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            {loadingConfig && <CircularProgress size={18} />}
            {activeMeta?.updated_at && (
              <Typography variant="body2" color="text.secondary">
                Updated: {activeMeta.updated_at}
              </Typography>
            )}
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 1, minHeight: '60vh' }}>
        {loadingHtml && !htmlContent ? (
          <Box display="flex" alignItems="center" justifyContent="center" height="100%" py={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ border: (theme) => `1px solid ${theme.palette.divider}`, borderRadius: 1, overflow: 'hidden', minHeight: '60vh' }}>
            <iframe
              title="HTML Display"
              srcDoc={htmlContent}
              sandbox="allow-scripts allow-same-origin allow-forms allow-pointer-lock allow-downloads"
              style={{ width: '100%', height: '70vh', border: 'none', background: '#0b1224' }}
              key={config?.config?.active_file || 'html-display' }
            />
          </Box>
        )}
      </Paper>
    </Stack>
  );
}
