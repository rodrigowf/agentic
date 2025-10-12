import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
  Divider,
  Collapse,
  IconButton,
  Button,
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import ToolEditor from '../components/ToolEditor';
import api from '../../../api';
import { ToolFile } from '../../../types';

interface ToolFileGroup {
  filename: string;
  tools: ToolFile[];
}

interface ExpandedFilesState {
  [key: string]: boolean;
}

export default function ToolsDashboard(): JSX.Element {
  const { filename } = useParams<{ filename?: string }>();
  const navigate = useNavigate();
  const isCreating = filename === 'new';
  const activeFilename = isCreating ? null : filename;
  const [toolFiles, setToolFiles] = useState<ToolFileGroup[]>([]);
  const [expandedFiles, setExpandedFiles] = useState<ExpandedFilesState>({});

  const fetchTools = useCallback(() => {
    api.getTools()
      .then(res => {
        const groups: { [key: string]: ToolFileGroup } = {};
        res.data.forEach((tool: ToolFile) => {
          if (!groups[tool.filename]) {
            groups[tool.filename] = {
              filename: tool.filename,
              tools: []
            };
          }
          groups[tool.filename].tools.push(tool);
        });
        setToolFiles(Object.values(groups));

        if (activeFilename) {
          setExpandedFiles(prev => ({ ...prev, [activeFilename]: true }));
        }
      })
      .catch(err => console.error("Error fetching tools:", err));
  }, [activeFilename]);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  const toggleExpand = (fname: string) => {
    setExpandedFiles(prev => ({ ...prev, [fname]: !prev[fname] }));
  };

  const handleToolSaved = useCallback((savedFilename: string) => {
    fetchTools();
    if (savedFilename && savedFilename !== activeFilename) {
      navigate(`/tools/${savedFilename}`);
    }
  }, [fetchTools, navigate, activeFilename]);

  return (
    <Box sx={{
      display: 'flex',
      height: 'calc(100vh - 64px)',
      width: '100%',
      position: 'fixed',
      left: 0,
      top: 64,
      overflow: 'hidden',
      bgcolor: 'background.default',
    }}>
      {/* Left Panel - Tools List */}
      <Box sx={{
        width: '360px',
        height: '100%',
        bgcolor: theme => theme.palette.mode === 'dark'
          ? 'rgba(255, 255, 255, 0.03)'
          : 'rgba(0, 0, 0, 0.02)',
        borderRight: 1,
        borderColor: 'divider',
        overflowY: 'auto',
        flexShrink: 0,
      }}>
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
          <Typography variant="h6">
            Tools
          </Typography>
          <Button
            variant="contained"
            size="small"
            onClick={() => navigate('/tools/new')}
            sx={{ textTransform: 'none', whiteSpace: 'nowrap' }}
          >
            + Add new Tool
          </Button>
        </Box>
        <Divider />
        <List disablePadding>
          {toolFiles.map(fileGroup => (
            <Box key={fileGroup.filename}>
              <ListItem
                disablePadding
                secondaryAction={
                  <IconButton
                    edge="end"
                    size="small"
                    onClick={() => toggleExpand(fileGroup.filename)}
                  >
                    {expandedFiles[fileGroup.filename] ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                  </IconButton>
                }
              >
                <ListItemButton
                  component={RouterLink}
                  to={`/tools/${fileGroup.filename}`}
                  selected={fileGroup.filename === activeFilename}
                  sx={{
                    '&.Mui-selected': {
                      bgcolor: theme => theme.palette.mode === 'dark'
                        ? 'rgba(144, 202, 249, 0.16)'
                        : 'rgba(63, 81, 181, 0.08)',
                      borderLeft: 3,
                      borderColor: 'primary.main',
                    }
                  }}
                >
                  <ListItemText
                    primary={fileGroup.filename}
                    secondary={`${fileGroup.tools.length} tool${fileGroup.tools.length !== 1 ? 's' : ''}`}
                    primaryTypographyProps={{
                      fontSize: '0.9rem',
                      fontWeight: fileGroup.filename === filename ? 600 : 400
                    }}
                    secondaryTypographyProps={{
                      fontSize: '0.75rem'
                    }}
                  />
                </ListItemButton>
              </ListItem>

              <Collapse in={expandedFiles[fileGroup.filename]} timeout="auto" unmountOnExit>
                <List component="div" disablePadding>
                  {fileGroup.tools.map(tool => (
                    <ListItem
                      key={tool.name || tool.filename}
                      sx={{
                        pl: 4,
                        py: 0.5,
                        bgcolor: theme => theme.palette.mode === 'dark'
                          ? 'rgba(0, 0, 0, 0.2)'
                          : 'rgba(0, 0, 0, 0.02)',
                      }}
                    >
                      <ListItemText
                        primary={tool.name}
                        secondary={tool.description}
                        primaryTypographyProps={{
                          fontSize: '0.8rem',
                          color: 'text.secondary'
                        }}
                        secondaryTypographyProps={{
                          fontSize: '0.7rem',
                          noWrap: true,
                          sx: {
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            maxWidth: '220px'
                          }
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            </Box>
          ))}
        </List>
      </Box>

      {/* Right Panel - Tool Editor */}
      <Box sx={{
        flexGrow: 1,
        height: '100%',
        bgcolor: 'background.paper',
        overflowY: 'auto',
        '&::-webkit-scrollbar': {
          width: '12px',
        },
        '&::-webkit-scrollbar-track': {
          bgcolor: 'background.paper',
        },
        '&::-webkit-scrollbar-thumb': {
          bgcolor: theme => theme.palette.mode === 'dark' ? '#3a3a3a' : '#c0c0c0',
          borderRadius: '6px',
          border: theme => `2px solid ${theme.palette.mode === 'dark' ? '#1a1a1a' : '#ffffff'}`,
          '&:hover': {
            bgcolor: theme => theme.palette.mode === 'dark' ? '#4a4a4a' : '#a0a0a0',
          },
        },
      }}>
        {isCreating ? (
          <ToolEditor nested filenameOverride={null} onSaved={handleToolSaved} />
        ) : activeFilename ? (
          <ToolEditor nested onSaved={handleToolSaved} />
        ) : (
          <Box sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            p: 4
          }}>
            <Typography variant="h6" color="text.secondary">
              Select a tool file to edit
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
}
