# GitHub Copilot Edit‑Mode Setup Instructions
Below is a complete file‑by‑file scaffold for your AutoGen v0.5.3 + FastAPI + React/Material UI application. Create each file at the specified path with the given content.

---

## 1. Project Root

### 1.1 README.md
```markdown
# AutoGen Agent Dashboard

This repository contains:

- **backend/**: FastAPI server powered by AutoGen v0.5.3 for managing and running agents.
- **frontend/**: React + Material UI dashboard to create/edit agents, tools, and view live runs.

## Prerequisites

- Python 3.10+
- Node.js 16+
- GitHub Copilot in Edit mode

## Setup

### Backend
```bash
cd backend
cp .env.example .env        # fill in your API keys
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
cp .env.local.example .env.local  # adjust URLs if needed
npm install
npm start
```
```

### 1.2 .gitignore
```gitignore
# Python
venv/
__pycache__/
.env

# Node
node_modules/
build/
```

---

## 2. Backend

Directory: `backend/`

### 2.1 backend/requirements.txt
```text
fastapi
uvicorn[standard]
pydantic
python-dotenv
openai
anthropic
# placeholder for Gemini Python SDK
gemini-sdk
```

### 2.2 backend/.env.example
```dotenv
# OpenAI
OPENAI_API_KEY=your-openai-key
# Anthropic
ANTHROPIC_API_KEY=your-anthropic-key
# Google Gemini (if using)
GEMINI_API_KEY=your-gemini-key
``` 

### 2.3 backend/main.py
```python
from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from schemas import AgentConfig, ToolDefinition
from config_loader import load_tools, load_agents, save_agent, save_tool
from runner import run_agent_ws

load_dotenv()  # loads .env

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup cache
TOOLS_DIR = "tools"
AGENTS_DIR = "agents"
TOOLS = load_tools(TOOLS_DIR)
AGENTS = load_agents(AGENTS_DIR)

@app.get("/api/tools", response_model=list[ToolDefinition])
def list_tools():
    return TOOLS

@app.post("/api/tools/upload", response_model=ToolDefinition)
async def upload_tool(file: UploadFile = File(...)):
    content = await file.read()
    path = os.path.join(TOOLS_DIR, file.filename)
    with open(path, 'wb') as f:
        f.write(content)
    # reload tools
    global TOOLS
    TOOLS = load_tools(TOOLS_DIR)
    # return new tool metadata
    new = next(t for t in TOOLS if t.name == file.filename[:-3])
    return new

@app.get("/api/agents", response_model=list[AgentConfig])
def list_agents():
    return AGENTS

@app.post("/api/agents", response_model=AgentConfig)
def create_agent(cfg: AgentConfig):
    if any(a.name == cfg.name for a in AGENTS):
        raise HTTPException(400, "Agent with this name already exists")
    AGENTS.append(cfg)
    save_agent(cfg, AGENTS_DIR)
    return cfg

@app.put("/api/agents/{agent_name}", response_model=AgentConfig)
def update_agent(agent_name: str, cfg: AgentConfig):
    for i,a in enumerate(AGENTS):
        if a.name == agent_name:
            AGENTS[i] = cfg
            save_agent(cfg, AGENTS_DIR)
            return cfg
    raise HTTPException(404, "Agent not found")

@app.websocket("/api/runs/{agent_name}")
async def run_ws(websocket: WebSocket, agent_name: str):
    await websocket.accept()
    agent = next((a for a in AGENTS if a.name == agent_name), None)
    if not agent:
        await websocket.close(code=1003)
        return
    await run_agent_ws(agent, TOOLS, websocket)
```

### 2.4 backend/schemas.py
```python
from pydantic import BaseModel
from typing import Any, Dict, List

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class LLMConfig(BaseModel):
    provider: str  # openai, anthropic, gemini
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None

class PromptConfig(BaseModel):
    system: str
    user: str

class AgentConfig(BaseModel):
    name: str
    tools: List[str]
    llm: LLMConfig
    prompt: PromptConfig
    max_turns: int = 5
```  

### 2.5 backend/config_loader.py
```python
import os, importlib.util, json
from typing import List
from schemas import ToolDefinition, AgentConfig

def load_tools(tools_dir: str) -> List[ToolDefinition]:
    tools = []
    for fname in os.listdir(tools_dir):
        if fname.endswith('.py') and fname != '__init__.py':
            module_name = fname[:-3]
            spec = importlib.util.spec_from_file_location(module_name, os.path.join(tools_dir, fname))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, 'tool_def'):
                tools.append(mod.tool_def)
    return tools

def save_tool(tools_dir: str, filename: str, content: bytes):
    os.makedirs(tools_dir, exist_ok=True)
    path = os.path.join(tools_dir, filename)
    with open(path, 'wb') as f:
        f.write(content)


def load_agents(agents_dir: str) -> List[AgentConfig]:
    agents = []
    os.makedirs(agents_dir, exist_ok=True)
    for fname in os.listdir(agents_dir):
        if fname.endswith('.json'):
            data = json.load(open(os.path.join(agents_dir, fname)))
            agents.append(AgentConfig(**data))
    return agents


def save_agent(cfg: AgentConfig, agents_dir: str):
    os.makedirs(agents_dir, exist_ok=True)
    path = os.path.join(agents_dir, f"{cfg.name}.json")
    with open(path, 'w') as f:
        f.write(cfg.json(indent=2))
```

### 2.6 backend/runner.py
```python
import os
from fastapi import WebSocket
from schemas import AgentConfig, ToolDefinition
from autogen import Agent, create_openai_llm, create_anthropic_llm, create_gemini_llm

async def run_agent_ws(agent_cfg: AgentConfig, tools: list[ToolDefinition], websocket: WebSocket):
    # Build tool instances
    tool_funcs = {}
    for t in tools:
        if t.name in agent_cfg.tools:
            module = __import__(f"tools.{t.name}", fromlist=[t.name])
            tool_funcs[t.name] = getattr(module, t.name)

    # Select LLM
    key = None
    prov = agent_cfg.llm.provider.lower()
    if prov == 'openai':
        key = os.getenv('OPENAI_API_KEY')
        llm = create_openai_llm(api_key=key, model=agent_cfg.llm.model)
    elif prov == 'anthropic':
        key = os.getenv('ANTHROPIC_API_KEY')
        llm = create_anthropic_llm(api_key=key, model=agent_cfg.llm.model)
    else:
        key = os.getenv('GEMINI_API_KEY')
        llm = create_gemini_llm(api_key=key, model=agent_cfg.llm.model)

    # Instantiate agent
    agent = Agent(
        name=agent_cfg.name,
        llm=llm,
        tools=list(tool_funcs.values()),
        system_message=agent_cfg.prompt.system,
        human_message=agent_cfg.prompt.user,
        max_turns=agent_cfg.max_turns
    )

    # Stream events
    async for evt in agent.stream():
        await websocket.send_json(evt.to_dict())
```

---

## 3. Frontend

Directory: `frontend/`

### 3.1 frontend/package.json
```json
{
  "name": "autogen-dashboard",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "@mui/material": "^5.0.0",
    "@emotion/react": "^11.0.0",
    "@emotion/styled": "^11.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "react-scripts": "5.0.1",
    "react-router-dom": "^6.3.0",
    "web-vitals": "^2.0.0",
    "reconnecting-websocket": "^4.4.0",
    "axios": "^0.27.0",
    "@monaco-editor/react": "^4.4.6"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  }
}
```

### 3.2 frontend/.gitignore
```gitignore
node_modules/
build/
.env.local
```

### 3.3 frontend/.env.local.example
```dotenv
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_WS_URL=ws://localhost:8000
```

### 3.4 frontend/src/index.js
```javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import CssBaseline from '@mui/material/CssBaseline';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <>
    <CssBaseline />
    <App />
  </>
);
```

### 3.5 frontend/src/App.js
```javascript
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
```

### 3.6 frontend/src/api.js
```javascript
import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
});

export const getTools    = () => API.get('/tools');
export const uploadTool  = (file) => {
  const fd = new FormData(); fd.append('file', file);
  return API.post('/tools/upload', fd);
};
export const getAgents   = () => API.get('/agents');
export const createAgent = (agent) => API.post('/agents', agent);
export const updateAgent = (name, agent) => API.put(`/agents/${name}`, agent);
export const runAgent    = (name) => new WebSocket(process.env.REACT_APP_WS_URL + `/api/runs/${name}`);

export default { getTools, uploadTool, getAgents, createAgent, updateAgent, runAgent };
```

### 3.7 frontend/src/components/ToolList.js
```javascript
import React, { useEffect, useState } from 'react';
import { List, ListItem, ListItemText, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function ToolList() {
  const [tools, setTools] = useState([]);
  const nav = useNavigate();

  useEffect(() => {
    api.getTools().then(res => setTools(res.data));
  }, []);

  return (
    <>
      <Button variant="contained" onClick={() => nav('/tools/new')} sx={{ mb:2 }}>Add Tool</Button>
      <List>
        {tools.map(t => (
          <ListItem key={t.name}>
            <ListItemText primary={t.name} secondary={t.description} />
          </ListItem>
        ))}
      </List>
    </>
  );
}
```

### 3.8 frontend/src/components/ToolEditor.js
```javascript
import React, { useState } from 'react';
import { Button, Typography } from '@mui/material';
import api from '../api';
import CodeEditor from './CodeEditor';

export default function ToolEditor() {
  const [file, setFile] = useState(null);
  const [code, setCode] = useState('# Write Python tool here');

  const handleUpload = () => {
    if (file) {
      api.uploadTool(file).then(() => window.location.href = '/tools');
    }
  };

  return (
    <div>
      <Typography variant="h6">Create / Upload Tool</Typography>
      <input type="file" accept=".py" onChange={e=>setFile(e.target.files[0])} />
      <Typography variant="subtitle1" sx={{ mt:2 }}>Or edit inline:</Typography>
      <CodeEditor value={code} onChange={setCode} language="python" height="300px" />
      <Button variant="contained" sx={{ mt:2 }} onClick={handleUpload}>Save Tool</Button>
    </div>
}
```

### 3.9 frontend/src/components/AgentList.js
```javascript
import React, { useEffect, useState } from 'react';
import { Table, TableHead, TableRow, TableCell, TableBody, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function AgentList() {
  const [agents, setAgents] = useState([]);
  const nav = useNavigate();

  useEffect(() => {
    api.getAgents().then(res => setAgents(res.data));
  }, []);

  return (
    <>
      <Button variant="contained" onClick={() => nav('/agents/new')} sx={{ mb:2 }}>New Agent</Button>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Tools</TableCell>
            <TableCell>Model</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {agents.map(a => (
            <TableRow key={a.name}>
              <TableCell>{a.name}</TableCell>
              <TableCell>{a.tools.join(', ')}</TableCell>
              <TableCell>{a.llm.model}</TableCell>
              <TableCell>
                <Button onClick={() => nav(`/agents/${a.name}`)}>Edit</Button>
                <Button onClick={() => nav(`/runs/${a.name}`)}>Run</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}
```

### 3.10 frontend/src/components/AgentEditor.js
```javascript
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { TextField, Button, MenuItem, FormControl, InputLabel, Select, OutlinedInput, Chip, Box } from '@mui/material';
import api from '../api';

export default function AgentEditor() {
  const { name } = useParams();
  const editMode = Boolean(name);
  const nav = useNavigate();
  const [tools, setTools] = useState([]);
  const [cfg, setCfg] = useState({ name:'', tools:[], llm:{provider:'openai',model:'',temperature:0.0}, prompt:{system:'',user:''}, max_turns:5 });

  useEffect(()=>{ api.getTools().then(r=>setTools(r.data)); if(editMode){ api.getAgents().then(r=>{ const a=r.data.find(x=>x.name===name); setCfg(a); }); }}, []);

  const handleSave = ()=>{
    const action = editMode ? api.updateAgent(name,cfg) : api.createAgent(cfg);
    action.then(()=>nav('/'));  
  };

  return (
    <Box component="form" sx={{ display:'flex', flexDirection:'column', gap:2 }}>
      <TextField label="Agent Name" value={cfg.name} onChange={e=>setCfg({...cfg,name:e.target.value})} />
      <FormControl>
        <InputLabel>Tools</InputLabel>
        <Select multiple value={cfg.tools} onChange={e=>setCfg({...cfg,tools:e.target.value})} input={<OutlinedInput label="Tools" />} renderValue={(sel)=>(<Box sx={{display:'flex',flexWrap:'wrap',gap:0.5}}>{sel.map(t=><Chip key={t} label={t}/>)}</Box>)}>
          {tools.map(t=><MenuItem key={t.name} value={t.name}>{t.name}</MenuItem>)}
        </Select>
      </FormControl>
      <TextField label="System Prompt" multiline value={cfg.prompt.system} onChange={e=>setCfg({...cfg,prompt:{...cfg.prompt,system:e.target.value}})} />
      <TextField label="User Prompt" multiline value={cfg.prompt.user} onChange={e=>setCfg({...cfg,prompt:{...cfg.prompt,user:e.target.value}})} />
      <FormControl>
        <InputLabel>Provider</InputLabel>
        <Select value={cfg.llm.provider} onChange={e=>setCfg({...cfg,llm:{...cfg.llm,provider:e.target.value}})} label="Provider">
          <MenuItem value="openai">OpenAI</MenuItem>
          <MenuItem value="anthropic">Anthropic</MenuItem>
          <MenuItem value="gemini">Gemini</MenuItem>
        </Select>
      </FormControl>
      <TextField label="Model" value={cfg.llm.model} onChange={e=>setCfg({...cfg,llm:{...cfg.llm,model:e.target.value}})} />
      <TextField type="number" label="Temperature" value={cfg.llm.temperature} onChange={e=>setCfg({...cfg,llm:{...cfg.llm,temperature:parseFloat(e.target.value)}})} />
      <TextField type="number" label="Max Turns" value={cfg.max_turns} onChange={e=>setCfg({...cfg,max_turns:parseInt(e.target.value)})} />
      <Button variant="contained" onClick={handleSave}>Save Agent</Button>
    </Box>
  );
}
```

### 3.11 frontend/src/components/RunConsole.js
```javascript
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Paper, Typography } from '@mui/material';
import api from '../api';

export default function RunConsole() {
  const { name } = useParams();
  const [logs, setLogs] = useState([]);

  useEffect(()=>{
    const ws = api.runAgent(name);
    ws.onmessage = e => setLogs(l=>[...l, JSON.parse(e.data)]);
    ws.onclose = ()=>console.log('Connection closed');
    return ()=>ws.close();
  }, []);

  return (
    <div>
      <Typography variant="h6">Run: {name}</Typography>
      <Paper sx={{ p:2, height:400, overflow:'auto' }}>
        {logs.map((evt,i)=>(<pre key={i}>{JSON.stringify(evt,null,2)}</pre>))}
      </Paper>
    </div>
  );
}
```

### 3.12 frontend/src/components/CodeEditor.js
```javascript
import React from 'react';
import Editor from '@monaco-editor/react';

export default function CodeEditor({ value, language='javascript', onChange, height='200px' }) {
  return (
    <Editor
      height={height}
      defaultLanguage={language}
      value={value}
      onChange={(v) => onChange(v)}
      options={{ minimap:{ enabled:false } }}
    />
  );
}
```

---

Once all files are created, run the setup commands described in **README.md**. Your dashboard will be fully functional for defining tools, configuring agents, and watching live runs.

