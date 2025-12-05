import React, { useState, useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import RunConsole from '../../agents/components/RunConsole';

// Get WebSocket URL
const getWsUrl = (path) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${path}`;
};

/**
 * Team console panel with its own WebSocket connection
 */
const TeamConsolePanel = ({ agentName = 'MainConversation', isRunning = false }) => {
  const [socket, setSocket] = useState(null);
  const socketRef = useRef(null);

  // Create WebSocket when panel is visible and session is running
  useEffect(() => {
    if (!isRunning) {
      // Close socket if session stops
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
        setSocket(null);
      }
      return;
    }

    // Create WebSocket for this console
    const wsUrl = getWsUrl(`/api/runs/${agentName}`);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log(`[TeamConsolePanel] WebSocket connected to ${agentName}`);
      setSocket(ws);
    };

    ws.onerror = (err) => {
      console.error('[TeamConsolePanel] WebSocket error:', err);
    };

    ws.onclose = () => {
      console.log('[TeamConsolePanel] WebSocket closed');
      setSocket(null);
    };

    // Cleanup on unmount or when session stops
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [isRunning, agentName]);

  if (!isRunning) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Start a voice session to see nested team console
        </Typography>
      </Box>
    );
  }

  if (!socket) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Connecting to team console...
        </Typography>
      </Box>
    );
  }

  return (
    <RunConsole
      nested
      agentName={agentName}
      sharedSocket={socket}
      readOnlyControls
    />
  );
};

export default TeamConsolePanel;
