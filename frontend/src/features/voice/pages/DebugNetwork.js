import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import { getEnvironmentInfo, getHttpBase, getWsUrl, getApiUrl } from '../../../utils/urlBuilder';

export default function DebugNetwork() {
  const envInfo = getEnvironmentInfo();
  const httpBase = getHttpBase();
  const sampleWsUrl = getWsUrl('/runs/MainConversation');
  const sampleApiUrl = getApiUrl('/realtime/conversations');

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Network Debug Info
      </Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6">Current Page</Typography>
        <Typography><strong>Full URL:</strong> {envInfo.currentUrl}</Typography>
        <Typography><strong>Protocol:</strong> {envInfo.protocol}</Typography>
        <Typography><strong>Hostname:</strong> {envInfo.hostname}</Typography>
        <Typography><strong>Port:</strong> {envInfo.port || '(default)'}</Typography>
        <Typography><strong>Host:</strong> {envInfo.host}</Typography>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6">Environment Detection</Typography>
        <Typography><strong>Type:</strong> {envInfo.type}</Typography>
        <Typography><strong>HTTP Base:</strong> {envInfo.httpBase}</Typography>
        <Typography><strong>WebSocket Base:</strong> {envInfo.wsBase}</Typography>
        <Typography><strong>API Path:</strong> {envInfo.apiPath}</Typography>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6">Sample URLs</Typography>
        <Typography><strong>REST API:</strong> {sampleApiUrl}</Typography>
        <Typography><strong>WebSocket:</strong> {sampleWsUrl}</Typography>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6">Environment Variables</Typography>
        <Typography><strong>REACT_APP_BACKEND_URL:</strong> {process.env.REACT_APP_BACKEND_URL || '(not set)'}</Typography>
        <Typography><strong>REACT_APP_API_URL:</strong> {process.env.REACT_APP_API_URL || '(not set)'}</Typography>
        <Typography><strong>NODE_ENV:</strong> {process.env.NODE_ENV}</Typography>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6">Test API Call</Typography>
        <button onClick={async () => {
          try {
            const url = getApiUrl('/realtime/conversations');
            console.log('Testing API call to:', url);
            const res = await fetch(url);
            const data = await res.json();
            alert(`Success! Found ${data.length} conversations`);
            console.log('API Response:', data);
          } catch (err) {
            alert(`Error: ${err.message}`);
            console.error('API Error:', err);
          }
        }}>
          Test API Connection
        </button>
      </Paper>
    </Box>
  );
}
