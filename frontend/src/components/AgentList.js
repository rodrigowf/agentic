import React, { useEffect, useState } from 'react';
import { Table, TableHead, TableRow, TableCell, TableBody, Button, Typography, Box, Paper } from '@mui/material'; // Added Typography, Box, Paper
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function AgentList() {
  const [agents, setAgents] = useState([]);
  const [error, setError] = useState(null); // Add error state
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
    <Box component={Paper} sx={{ p: 2 }}> {/* Wrap in Paper */}
      <Typography variant="h5" gutterBottom>Agents</Typography>
      <Button variant="contained" onClick={() => nav('/agents/new')} sx={{ mb:2 }}>New Agent</Button>
      {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>} {/* Display error */}
      <Table size="small"> {/* Use small size */}
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Tools</TableCell>
            <TableCell>Provider</TableCell>
            <TableCell>Model</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {agents.length === 0 && !error && (
            <TableRow><TableCell colSpan={5} align="center">No agents created yet.</TableCell></TableRow>
          )} {/* Handle empty list */}
          {agents.map(a => (
            <TableRow key={a.name} hover> {/* Add hover effect */}
              <TableCell>{a.name}</TableCell>
              <TableCell>{a.tools.join(', ') || '-'}</TableCell> {/* Handle empty tools */}
              <TableCell>{a.llm.provider}</TableCell>
              <TableCell>{a.llm.model}</TableCell>
              <TableCell>
                <Button size="small" onClick={() => nav(`/agents/${a.name}`)} sx={{ mr: 1 }}>Edit</Button>
                <Button size="small" variant="outlined" onClick={() => nav(`/runs/${a.name}`)}>Run</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}