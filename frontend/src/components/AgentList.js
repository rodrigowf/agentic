import React, { useEffect, useState } from 'react';
import { Table, TableHead, TableRow, TableCell, TableBody, Button, Typography, Box, Paper, Link, Alert } from '@mui/material'; // Added Link, Alert
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import api from '../api';

export default function AgentList() {
  const [agents, setAgents] = useState([]);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    api.getAgents()
      .then(res => setAgents(res.data))
      .catch(err => {
        console.error("Error fetching agents:", err);
        setError("Failed to load agents. Is the backend running?");
      });
  }, []);

  return (
    <Box component={Paper} sx={{ p: { xs: 2, sm: 3 }, overflow: 'hidden' }}> {/* Responsive padding, hide overflow initially */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" component="div"> {/* Removed gutterBottom */}
          Agents
        </Typography>
        <Button variant="contained" component={RouterLink} to="/agents/new">
          New Agent
        </Button>
      </Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>} {/* Use Alert component */}
      <Box sx={{ overflowX: 'auto' }}> {/* Make table scrollable horizontally */}
        <Table size="small" sx={{ minWidth: 650 }}> {/* Ensure minimum width for table */}
          <TableHead sx={{ backgroundColor: 'background.subtile' }}> {/* Set background color for header */}
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Tools</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell>Model</TableCell>
              <TableCell sx={{ textAlign: 'right' }}>Actions</TableCell> {/* Align right */}
            </TableRow>
          </TableHead>
          <TableBody>
            {agents.length === 0 && !error && (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                  No agents created yet.
                </TableCell>
              </TableRow>
            )}
            {agents.map(a => (
              <TableRow key={a.name} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                <TableCell component="th" scope="row">
                  <Link component={RouterLink} to={`/agents/${a.name}`} underline="hover" fontWeight="medium"> {/* Bolder link */}
                    {a.name}
                  </Link>
                </TableCell>
                <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}> {/* Truncate long tool lists */}
                  {a.tools.join(', ') || '-'}
                </TableCell>
                <TableCell>{a.llm.provider}</TableCell>
                <TableCell>{a.llm.model}</TableCell>
                <TableCell sx={{ textAlign: 'right', whiteSpace: 'nowrap' }}> {/* Prevent wrapping */}
                  <Button size="small" variant="outlined" component={RouterLink} to={`/agents/${a.name}`} sx={{ mr: 1 }}>Edit</Button> {/* Outlined Edit */}
                  <Button size="small" variant="contained" component={RouterLink} to={`/runs/${a.name}`}>Run</Button> {/* Contained Run */}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}