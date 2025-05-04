import React, { useEffect, useState, useCallback } from 'react'; // Added useCallback
import { List, ListItem, ListItemText, Button, Typography, Box, Paper, Divider, IconButton, Tooltip, CircularProgress, Alert } from '@mui/material'; // Added Alert, CircularProgress
import { Link as RouterLink } from 'react-router-dom';
import EditIcon from '@mui/icons-material/Edit';
import CloudUploadIcon from '@mui/icons-material/CloudUpload'; // For upload button
import api from '../api';

export default function ToolList() {
  const [tools, setTools] = useState([]); // Now holds flat list of ToolDefinition
  const [loading, setLoading] = useState(true); // Loading state
  const [error, setError] = useState(null);
  const [uploadError, setUploadError] = useState(null); // Specific error for uploads
  const fileInputRef = React.useRef(null); // Ref for hidden file input

  const fetchTools = useCallback(() => {
    setLoading(true);
    setError(null);
    api.getTools()
       .then(res => {
         // Sort tools by filename, then by name for consistent display
         const sortedTools = res.data.sort((a, b) => {
           if (a.filename < b.filename) return -1;
           if (a.filename > b.filename) return 1;
           if (a.name < b.name) return -1;
           if (a.name > b.name) return 1;
           return 0;
         });
         setTools(sortedTools);
       })
       .catch(err => {
         console.error("Error fetching tools:", err);
         setError(`Failed to load tools. ${err.response?.data?.detail || err.message}. Is the backend running?`);
       })
       .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  const handleUploadClick = () => {
    fileInputRef.current?.click(); // Trigger hidden file input
  };

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true); // Show loading indicator during upload
    setUploadError(null);
    setError(null);

    try {
      // API now returns list of tools found in the uploaded file
      const response = await api.uploadTool(file);
      console.log("Upload successful, tools found:", response.data);
      // Refresh the entire list to show the newly added tools
      fetchTools();
    } catch (err) {
      console.error("Error uploading tool:", err);
      setUploadError(`Upload failed: ${err.response?.data?.detail || err.message}`);
      setLoading(false); // Stop loading on error
    } finally {
       // Reset file input value so the same file can be uploaded again if needed
       if (fileInputRef.current) {
           fileInputRef.current.value = '';
       }
    }
  };


  return (
    <Box component={Paper} sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h5" gutterBottom component="div" sx={{ mb: 0 }}>
          Available Tools
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
           {/* Hidden file input */}
           <input
             type="file"
             accept=".py"
             ref={fileInputRef}
             onChange={handleFileChange}
             style={{ display: 'none' }}
           />
           {/* Upload Button */}
           <Button
             variant="outlined"
             startIcon={<CloudUploadIcon />}
             onClick={handleUploadClick}
             disabled={loading}
           >
             Upload File
           </Button>
           {/* Create Button */}
           <Button variant="contained" component={RouterLink} to="/tools/new" disabled={loading}>
             Create Tool
           </Button>
        </Box>
      </Box>

      {/* Display errors */}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {uploadError && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setUploadError(null)}>{uploadError}</Alert>}

      {/* Loading Indicator */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Tool List */}
      {!loading && (
        <List disablePadding>
          {tools.length === 0 && !error && <Typography sx={{ textAlign: 'center', my: 2 }}>No tools defined or loaded.</Typography>}
          {tools.map((tool, index) => (
            <React.Fragment key={`${tool.filename}-${tool.name}`}> {/* Use composite key */}
              <ListItem
                sx={{ py: 1.5 }}
                secondaryAction={ // Edit button links to the file
                  <Tooltip title={`Edit File: ${tool.filename}`}>
                    <IconButton edge="end" aria-label="edit" component={RouterLink} to={`/tools/edit/${tool.filename}`}>
                      <EditIcon />
                    </IconButton>
                  </Tooltip>
                }
              >
                <ListItemText
                  primary={tool.name} // Display tool definition name
                  secondary={
                    <>
                      <Typography component="span" variant="body2" color="text.primary">
                        {tool.description || 'No description'}
                      </Typography>
                      <Typography component="span" variant="caption" sx={{ display: 'block', mt: 0.5, fontFamily: 'monospace' }}>
                        (File: {tool.filename}) {/* Show filename */}
                      </Typography>
                    </>
                  }
                  primaryTypographyProps={{ fontWeight: 'medium' }}
                />
              </ListItem>
              {index < tools.length - 1 && <Divider component="li" />} 
            </React.Fragment>
          ))}
        </List>
      )}
    </Box>
  );
}