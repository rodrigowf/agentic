import React from 'react';
import { useParams } from 'react-router-dom';
import { Box, Grid, Paper, Typography } from '@mui/material';
import AgentEditor from './AgentEditor';
import RunConsole from './RunConsole';

export default function AgentDashboard() {
  const { name } = useParams(); // Both components use useParams, so no need to pass name as prop

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Agent Dashboard: <b>{name}</b>
      </Typography>
      <Grid container spacing={3}> 
        {/* Agent Editor Column */}
        <Grid item xs={12} md={6}> 
          <AgentEditor nested/>
        </Grid>

        {/* Run Console Column */}
        <Grid item xs={12} md={6}>
          {/* RunConsole already uses Paper internally */}
          <RunConsole nested/>
        </Grid>
      </Grid>
    </Box>
  );
}
