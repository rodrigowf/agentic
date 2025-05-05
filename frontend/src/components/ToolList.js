import React, { useEffect, useState } from 'react';
import { 
  Table, TableHead, TableRow, TableCell, TableBody, Button, Typography,
  Box, Paper, Link, Alert, IconButton, Collapse
} from '@mui/material';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import api from '../api';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';

// Row component for file groups with collapsible tool rows
function FileGroup({ fileData, onEdit }) {
  const [open, setOpen] = useState(true);
  const { filename, tools } = fileData;

  return (
    <>
      <TableRow hover sx={{ '& > *': { borderBottom: 'unset' } }}>
        <TableCell>
          <IconButton
            aria-label="expand row"
            size="small"
            onClick={() => setOpen(!open)}
          >
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row">
          <Link component={RouterLink} to={`/tools/edit/${filename}`} underline="hover" fontWeight="medium">
            {filename}
          </Link>
        </TableCell>
        <TableCell>
          {tools.length} tool{tools.length !== 1 ? 's' : ''}
        </TableCell>
        <TableCell sx={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
          <Button size="small" variant="outlined" component={RouterLink} to={`/tools/edit/${filename}`} sx={{ mr: 1 }}>
            Edit File
          </Button>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={4}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>
              <Table size="small" aria-label="tools">
                <TableBody>
                  {tools.map((tool) => (
                    <TableRow key={tool.name} hover>
                      <TableCell sx={{ color: 'text.secondary', pl: 4 }}>
                        {tool.name || '-'}
                      </TableCell>
                      <TableCell sx={{ color: 'text.secondary', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {tool.description || '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

export default function ToolList() {
  const [tools, setTools] = useState([]);
  const [error, setError] = useState(null);
  const nav = useNavigate();
  
  // Group tools by filename for display
  const groupedTools = React.useMemo(() => {
    const groups = {};
    tools.forEach(tool => {
      if (!groups[tool.filename]) {
        groups[tool.filename] = {
          filename: tool.filename,
          tools: []
        };
      }
      groups[tool.filename].tools.push(tool);
    });
    return Object.values(groups);
  }, [tools]);

  useEffect(() => {
    api.getTools()
      .then(res => setTools(res.data))
      .catch(err => {
        console.error("Error fetching tools:", err);
        setError("Failed to load tools. Is the backend running?");
      });
  }, []);

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
        <Table size="medium" sx={{ minWidth: 400 }}>
          <TableHead>
            <TableRow>
              <TableCell width="50px" /> {/* Column for expand/collapse icon */}
              <TableCell>Filename</TableCell>
              <TableCell>Tools Count</TableCell>
              <TableCell sx={{ textAlign: 'right' }}>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {groupedTools.length === 0 && !error && (
              <TableRow>
                <TableCell colSpan={4} align="center" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                  No tools created or uploaded yet.
                </TableCell>
              </TableRow>
            )}
            {groupedTools.map((fileGroup) => (
              <FileGroup 
                key={fileGroup.filename} 
                fileData={fileGroup} 
              />
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}