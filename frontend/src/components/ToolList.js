import React, { useEffect, useState } from 'react';
import { List, ListItem, ListItemText, Button, Typography, Box } from '@mui/material'; // Added Typography, Box
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function ToolList() {
  const [tools, setTools] = useState([]);
  const [error, setError] = useState(null); // Add error state
  const nav = useNavigate();

  useEffect(() => {
    api.getTools()
       .then(res => setTools(res.data))
       .catch(err => {
         console.error("Error fetching tools:", err);
         setError("Failed to load tools. Is the backend running?");
       });
  }, []);

  return (
    <Box> {/* Use Box for layout */}
      <Typography variant="h5" gutterBottom>Available Tools</Typography>
      <Button variant="contained" onClick={() => nav('/tools/new')} sx={{ mb:2 }}>Add Tool</Button>
      {error && <Typography color="error" sx={{ mb: 2 }}>{error}</Typography>} {/* Display error */}
      <List>
        {tools.length === 0 && !error && <Typography>No tools defined yet.</Typography>} {/* Handle empty list */}
        {tools.map(t => (
          <ListItem key={t.name} divider> {/* Add divider */}
            <ListItemText primary={t.name} secondary={t.description || 'No description'} />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}