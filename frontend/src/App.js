import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Container, AppBar, Toolbar, Typography, Button } from '@mui/material';
import ToolList from './components/ToolList';
import ToolEditor from './components/ToolEditor';
import AgentList from './components/AgentList';
import AgentEditor from './components/AgentEditor';
import RunConsole from './components/RunConsole';

export default function App() {
  return (
    <Router>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            AutoGen Dashboard
          </Typography>
          <Button color="inherit" href="/">Agents</Button>
          <Button color="inherit" href="/tools">Tools</Button>
        </Toolbar>
      </AppBar>
      <Container sx={{ mt: 4 }}>
        <Routes>
          <Route path="/" element={<AgentList />} />
          <Route path="/agents/new" element={<AgentEditor />} />
          <Route path="/agents/:name" element={<AgentEditor />} />
          <Route path="/runs/:name" element={<RunConsole />} />
          <Route path="/tools" element={<ToolList />} />
          <Route path="/tools/new" element={<ToolEditor />} />
        </Routes>
      </Container>
    </Router>
  );
}