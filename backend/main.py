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