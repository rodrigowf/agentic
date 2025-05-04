import React, { useEffect, useState } from 'react';
import { Table, TableHead, TableRow, TableCell, TableBody, Button, Typography, Box, Paper, Link } from '@mui/material'; // Added Link
import { useNavigate, Link as RouterLink } from 'react-router-dom'; // Import RouterLink
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
    <Box component={Paper} sx={{ p: 2, overflow: 'auto' }}> {/* Add overflow auto */} 
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}> {/* Flex layout for title and button */} 
        <Typography variant="h5" gutterBottom component="div"> {/* Remove default marginBottom from gutterBottom */} 
          Agents
        </Typography>
        <Button variant="contained" component={RouterLink} to="/agents/new"> {/* Use RouterLink */} 
          New Agent
        </Button>
      </Box>
      {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>}
      <Table size="small">
        <TableHead>
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
            <TableRow><TableCell colSpan={5} align="center">No agents created yet.</TableCell></TableRow>
          )}
          {agents.map(a => (
            <TableRow key={a.name} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}> {/* Remove border on last row */} 
              <TableCell component="th" scope="row"> {/* Use th for semantic correctness */} 
                {/* Link to the agent run page */} 
                <Link component={RouterLink} to={`/runs/${a.name}`} underline="hover">
                  {a.name}
                </Link>
              </TableCell>
              <TableCell>{a.tools.join(', ') || '-'}</TableCell>
              <TableCell>{a.llm.provider}</TableCell>
              <TableCell>{a.llm.model}</TableCell>
              <TableCell sx={{ textAlign: 'right' }}> {/* Align right */} 
                <Button size="small" component={RouterLink} to={`/agents/${a.name}`} sx={{ mr: 1 }}>Edit</Button> {/* Use RouterLink */} 
                <Button size="small" variant="outlined" component={RouterLink} to={`/runs/${a.name}`}>Run</Button> {/* Use RouterLink */} 
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}