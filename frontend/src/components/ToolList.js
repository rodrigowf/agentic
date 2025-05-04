import React, { useEffect, useState } from 'react';
import { Table, TableHead, TableRow, TableCell, TableBody, Button, Typography, Box, Paper, Link, Alert } from '@mui/material';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import api from '../api';

export default function ToolList() {
  const [tools, setTools] = useState([]);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    api.getTools()
      .then(res => setTools(res.data))
      .catch(err => {
        console.error("Error fetching tools:", err);
        setError("Failed to load tools. Is the backend running?");
      });
  }, []);

  const handleDelete = (filename) => {
    console.warn(`Delete functionality not implemented for ${filename}`);
  };

  return (
    <Box component={Paper} sx={{ p: { xs: 2, sm: 3 }, overflow: 'hidden' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" component="div">
          Tools
        </Typography>
        <Button variant="contained" component={RouterLink} to="/tools/new">
          New Tool
        </Button>
      </Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Box sx={{ overflowX: 'auto' }}>
        <Table size="small" sx={{ minWidth: 400 }}>
          <TableHead>
            <TableRow>
              <TableCell>Filename</TableCell>
              <TableCell>Description (from docstring)</TableCell>
              <TableCell sx={{ textAlign: 'right' }}>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tools.length === 0 && !error && (
              <TableRow>
                <TableCell colSpan={3} align="center" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                  No tools created or uploaded yet.
                </TableCell>
              </TableRow>
            )}
            {tools.map(t => (
              <TableRow key={t.filename} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                <TableCell component="th" scope="row">
                  <Link component={RouterLink} to={`/tools/edit/${t.filename}`} underline="hover" fontWeight="medium">
                    {t.filename}
                  </Link>
                </TableCell>
                <TableCell sx={{ color: 'text.secondary', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {t.definition?.description || '-'}
                </TableCell>
                <TableCell sx={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <Button size="small" variant="outlined" component={RouterLink} to={`/tools/edit/${t.filename}`} sx={{ mr: 1 }}>Edit</Button>
                  {/* Add Delete button (functionality pending) */}
                  {/* <Button size="small" color="error" onClick={() => handleDelete(t.filename)}>Delete</Button> */}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}