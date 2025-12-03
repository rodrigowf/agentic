import React, { useEffect } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { Box, Typography, Paper } from '@mui/material';

/**
 * Debug component to show routing information
 */
function RouteDebug({ routeName }) {
  const location = useLocation();
  const params = useParams();

  useEffect(() => {
    console.log(`[RouteDebug-${routeName}] Component mounted!`);
    console.log(`[RouteDebug-${routeName}] Location:`, location);
    console.log(`[RouteDebug-${routeName}] Params:`, params);
  }, [location, params, routeName]);

  return (
    <Box sx={{ p: 4 }}>
      <Paper sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
        <Typography variant="h4" gutterBottom>
          🔍 Route Debug: {routeName}
        </Typography>

        <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>
          Current Location:
        </Typography>
        <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.900', color: 'success.main', fontFamily: 'monospace' }}>
          <div>pathname: {location.pathname}</div>
          <div>search: {location.search || '(none)'}</div>
          <div>hash: {location.hash || '(none)'}</div>
        </Paper>

        <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>
          URL Parameters:
        </Typography>
        <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.900', color: 'info.main', fontFamily: 'monospace' }}>
          {Object.keys(params).length > 0 ? (
            Object.entries(params).map(([key, value]) => (
              <div key={key}>{key}: {value}</div>
            ))
          ) : (
            <div>(no params)</div>
          )}
        </Paper>

        <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>
          If you're seeing this page:
        </Typography>
        <Paper variant="outlined" sx={{ p: 2, bgcolor: 'success.dark' }}>
          <Typography>
            ✅ The route is working correctly!
          </Typography>
          <Typography sx={{ mt: 1 }}>
            The route {routeName} is NOT redirecting to home.
          </Typography>
        </Paper>

        <Typography variant="body2" sx={{ mt: 3, color: 'text.secondary' }}>
          Check the browser console for additional debugging information.
        </Typography>
      </Paper>
    </Box>
  );
}

export default RouteDebug;
