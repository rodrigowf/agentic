# CLAUDE.md - Comprehensive Development Guide

**Last Updated:** 2025-10-11
**For:** Future Claude instances working on this codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Debugging Tools & Workflows](#debugging-tools--workflows)
4. [Backend Development](#backend-development)
5. [Frontend Development](#frontend-development)
6. [Creating New Agents](#creating-new-agents)
7. [Creating New Tools](#creating-new-tools)
8. [Voice Assistant System](#voice-assistant-system)
9. [Claude Code Self-Editor](#claude-code-self-editor)
10. [Best Practices](#best-practices)

---

## Project Overview

This is an **agentic AI system** with a Python backend using AutoGen and a React frontend. The system features:

- **Multi-agent coordination** using nested team agents
- **Multimodal vision agents** that can interpret images from tool responses
- **Voice assistant interface** using OpenAI Realtime API
- **Claude Code self-editor integration** for live code modification
- **Real-time WebSocket communication**
- **Memory management** with ChromaDB and embeddings
- **Screenshot-based UI development** workflow

### Tech Stack

**Backend:**
- Python 3.x
- FastAPI (WebSocket + REST API)
- AutoGen (agent framework)
- ChromaDB (vector storage)
- SQLite (voice conversation storage)
- OpenAI API, Anthropic API

**Frontend:**
- React 18
- Material-UI (MUI)
- WebSocket client
- React Router

**Debug Tools:**
- Puppeteer (screenshots)
- SQLite exports
- Logging system

---

## Architecture

### Directory Structure

```
/home/rodrigo/agentic/
├── backend/                    # Python FastAPI server
│   ├── main.py                 # FastAPI app entry point (root)
│   ├── requirements.txt        # Python dependencies
│   ├── run.sh                  # Backend startup script
│   ├── .env                    # Environment variables
│   │
│   ├── config/                 # Configuration & schemas
│   │   ├── __init__.py
│   │   ├── schemas.py          # Pydantic data models
│   │   └── config_loader.py    # Agent/tool configuration loading
│   │
│   ├── utils/                  # Utility modules
│   │   ├── __init__.py
│   │   ├── context.py          # Agent context management
│   │   └── voice_conversation_store.py  # SQLite storage
│   │
│   ├── core/                   # Core agent logic
│   │   ├── __init__.py
│   │   ├── agent_factory.py    # Agent instantiation
│   │   ├── runner.py           # Agent execution engine
│   │   ├── looping_agent.py    # Single looping agent
│   │   ├── looping_code_executor_agent.py  # Code executor agent
│   │   ├── multimodal_tools_looping_agent.py  # Multimodal vision agent
│   │   └── nested_agent.py     # Nested team logic
│   │
│   ├── api/                    # API-specific modules
│   │   ├── __init__.py
│   │   ├── realtime_voice.py   # Voice assistant backend
│   │   └── claude_code_controller.py  # Claude Code integration
│   │
│   ├── agents/                 # Agent JSON configurations
│   │   └── *.json              # Agent config files
│   │
│   ├── tools/                  # Custom tool implementations
│   │   ├── memory.py           # Memory management tools
│   │   ├── research.py         # Research/web tools
│   │   └── image_tools.py      # Screenshot & image generation tools
│   │
│   ├── tests/                  # Test files
│   │   ├── README.md           # Test documentation
│   │   ├── test_image_tools.py # Image tools test suite
│   │   ├── unit/               # Unit tests
│   │   │   ├── test_screenshot.py
│   │   │   └── test_working_image_tools.py
│   │   └── integration/        # Integration tests
│   │       ├── test_claude_code_permissions.py
│   │       ├── test_multimodal_api.py
│   │       ├── test_multimodal_integration.py
│   │       ├── test_real_screenshot.py
│   │       ├── test_system_message_update.py
│   │       └── test_voice_claude_integration.py
│   │
│   ├── scripts/                # Utility scripts
│   │   ├── README.md           # Scripts documentation
│   │   ├── fix_x11_and_test.sh # X11 permission fix & test
│   │   └── fix_gnome_screenshot.sh # GNOME screenshot fix
│   │
│   ├── docs/                   # Backend-specific documentation
│   │   ├── SCREENSHOT_FIX_GUIDE.md
│   │   ├── SCREENSHOT_TESTING_REPORT.md
│   │   ├── SCREENSHOT_TEST_SUMMARY.md
│   │   ├── SCREENSHOT_TOOL_README.md
│   │   ├── MULTIMODAL_AGENT_GUIDE.md
│   │   └── MULTIMODAL_AGENT_IMPLEMENTATION_SUMMARY.md
│   │
│   ├── workspace/              # Agent workspace
│   ├── venv/                   # Python virtual environment
│   └── voice_conversations.db  # SQLite database
│
├── frontend/                   # React application
│   ├── src/
│   │   ├── api.js              # Backend API client
│   │   ├── App.js              # Root component
│   │   ├── index.js            # Entry point
│   │   ├── features/           # Feature-based architecture
│   │   │   ├── agents/         # Agent management
│   │   │   │   ├── components/ # Agent-specific components
│   │   │   │   └── pages/      # Agent pages
│   │   │   ├── tools/          # Tool management
│   │   │   │   ├── components/ # Tool-specific components
│   │   │   │   └── pages/      # Tool pages
│   │   │   └── voice/          # Voice assistant
│   │   │       ├── components/ # Voice-specific components
│   │   │       └── pages/      # Voice pages
│   │   └── shared/             # Shared components
│   │       └── components/
│   └── public/                 # Static assets
│
├── debug/                      # Debugging & export tools
│   ├── screenshot.js           # Puppeteer screenshot automation
│   ├── screenshots/            # Screenshot storage
│   ├── export_voice_conversations.py  # Voice DB export script
│   ├── db_exports/             # Database exports
│   │   └── voice_conversations/  # Voice conversation JSON exports
│   ├── AUTOMATED_UI_DEVELOPMENT.md  # UI dev workflow guide
│   └── package.json            # Debug tool dependencies
│
├── logs/                       # Log files
│   └── voice_exports/          # Voice conversation exports
│
├── docs/                       # Documentation
│
├── CLAUDE.md                   # This file
└── REFACTORING_SUMMARY.md      # Latest refactoring details

```

### Data Flow

```
User Input (Frontend)
    ↓
WebSocket Connection
    ↓
FastAPI Backend (main.py)
    ↓
Agent Factory (core/agent_factory.py)
    ↓
Agent Execution (core/runner.py)
    ↓
Tool Execution (tools/*.py)
    ↓
WebSocket Stream (events back to frontend)
    ↓
Frontend Components (React)
    ↓
UI Display
```

---

## Debugging Tools & Workflows

### 1. Screenshot Automation (Critical for UI Development)

**Location:** `/home/rodrigo/agentic/debug/screenshot.js`

**Purpose:** Take automated screenshots of the running React app for visual verification during development.

**Usage:**

```bash
# Basic screenshot
node /home/rodrigo/agentic/debug/screenshot.js http://localhost:3000

# Screenshot specific route with custom output
node /home/rodrigo/agentic/debug/screenshot.js \
  http://localhost:3000/agents/MainConversation \
  /home/rodrigo/agentic/debug/screenshots/my-screenshot.png \
  3000  # wait time in ms
```

**Parameters:**
1. `URL` - Target page (default: http://localhost:3000)
2. `OUTPUT_PATH` - Where to save (default: auto-generated timestamp)
3. `WAIT_TIME_MS` - Wait for dynamic content (default: 1000ms)

**Workflow for UI Changes:**

```bash
# 1. Take "before" screenshot
node /home/rodrigo/agentic/debug/screenshot.js \
  http://localhost:3000/voice \
  /home/rodrigo/agentic/debug/screenshots/before-change.png \
  2000

# 2. Read the screenshot to understand current state
# (Use Read tool on the screenshot file)

# 3. Make code changes using Edit tool

# 4. Wait for hot reload
sleep 3

# 5. Take "after" screenshot
node /home/rodrigo/agentic/debug/screenshot.js \
  http://localhost:3000/voice \
  /home/rodrigo/agentic/debug/screenshots/after-change.png \
  3000

# 6. Read and compare screenshots
```

**Best Practices:**
- **Always** screenshot before and after UI changes
- Use descriptive filenames (e.g., `before-refactor-dashboard.png`)
- Wait 2-3 seconds after code changes for hot reload
- Immediately Read screenshots after taking them
- Keep screenshots during development session for comparison

### 2. Voice Conversation Database Export

**Location:** `/home/rodrigo/agentic/debug/export_voice_conversations.py`

**Purpose:** Export voice conversation data from SQLite to JSON for debugging and analysis.

**Usage:**

```bash
cd /home/rodrigo/agentic

# Export all conversations (default location: debug/db_exports/voice_conversations/)
python3 debug/export_voice_conversations.py

# Export to custom location
python3 debug/export_voice_conversations.py \
  --out /tmp/voice_exports

# Custom database path
python3 debug/export_voice_conversations.py \
  --db /path/to/voice_conversations.db \
  --out /path/to/output/
```

**Output Structure:**

```json
{
  "conversation": {
    "id": "uuid",
    "name": "ConversationName",
    "created_at": "timestamp",
    "updated_at": "timestamp",
    "voice_model": null,
    "metadata": {}
  },
  "events": [
    {
      "id": 123,
      "conversation_id": "uuid",
      "timestamp": "timestamp",
      "source": "claude_code",  // or "voice", "nested", "controller"
      "type": "ToolCallRequestEvent",
      "data": {
        "type": "ToolCallRequestEvent",
        "data": {
          "name": "Bash",
          "arguments": {...},
          "id": "tool_use_id"
        }
      }
    }
  ]
}
```

**Debugging Workflow:**

1. **Export conversations** after a voice session
2. **Search for specific events** in the JSON (exported to `debug/db_exports/voice_conversations/`)
3. **Analyze event sequences** to debug agent behavior
4. **Verify data structures** for frontend display

**Key Event Types:**
- `source: "voice"` - OpenAI Realtime API events
- `source: "nested"` - Nested team agent events
- `source: "claude_code"` - Claude Code self-editor events
- `source: "controller"` - Voice controller system events

**Common Debug Patterns:**

```bash
# Find all Claude Code tool calls
jq '.events[] | select(.source == "claude_code" and .type == "ToolCallRequestEvent")' conversation.json

# Find errors
jq '.events[] | select(.type == "Error" or .type == "error")' conversation.json

# Extract tool usage timeline
jq '.events[] | select(.source == "claude_code") | {timestamp, type, tool: .data.data.name}' conversation.json
```

### 3. Backend Logging

**Location:** Various `logger` instances in Python modules

**Log Levels:**
- `DEBUG` - Detailed diagnostic info
- `INFO` - General system events
- `WARNING` - Non-critical issues
- `ERROR` - Serious problems

**View Logs:**

```bash
# Backend logs (if running with uvicorn)
cd /home/rodrigo/agentic/backend
uvicorn main:app --reload --log-level debug

# Or check specific log files in logs/
ls -la /home/rodrigo/agentic/logs/
```

### 4. Frontend Console Debugging

**Browser DevTools:**
- Open Chrome DevTools (F12)
- Console tab shows React errors, warnings, WebSocket messages
- Network tab shows API calls and WebSocket frames
- React DevTools extension for component inspection

**Common Debug Points:**
- `api.js` - API client wrapper
- WebSocket connection events in `VoiceAssistant.js`
- Component render issues in browser console

---

## Backend Development

### Core Modules

#### 1. `main.py` - FastAPI Application

**Purpose:** Main HTTP and WebSocket server

**Key Endpoints:**

```python
# REST API
GET    /api/agents                    # List all agents
GET    /api/agents/{agent_name}       # Get agent config
POST   /api/agents                    # Create/update agent
DELETE /api/agents/{agent_name}       # Delete agent
GET    /api/tools                     # List tools
POST   /api/tools                     # Upload tool

# WebSocket endpoints
WS     /api/runs/ClaudeCode           # Claude Code controller
WS     /api/runs/{agent_name}         # Generic agent runner
WS     /api/realtime-voice            # Voice assistant
```

**Adding New Endpoints:**

```python
@app.get("/api/my-endpoint")
async def my_endpoint():
    """Always add docstrings"""
    return {"status": "ok"}

@app.websocket("/api/ws/my-stream")
async def my_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # Handle data
            await websocket.send_json({"response": "data"})
    except WebSocketDisconnect:
        logger.info("Client disconnected")
```

#### 2. `core/runner.py` - Agent Execution Engine

**Location:** `/home/rodrigo/agentic/backend/core/runner.py`

**Purpose:** Runs agents and streams events via WebSocket

**Key Functions:**
- `run_agent_ws(agent_config, tools, websocket)` - Main execution loop
- Event streaming to frontend
- Tool execution monitoring

**Imports:**
```python
from config.schemas import AgentConfig
from utils.context import get_current_agent
from core.agent_factory import create_agent_from_config
```

#### 3. `core/agent_factory.py` - Agent Instantiation

**Location:** `/home/rodrigo/agentic/backend/core/agent_factory.py`

**Purpose:** Creates agent instances from JSON configurations

**Agent Types:**
- `looping` - Single agent with tool call loop
- `nested_team` - Multiple coordinated agents
- `code_executor` - Agent with code execution capability

**Imports:**
```python
from config.schemas import AgentConfig
from core.looping_agent import LoopingAgent
from core.looping_code_executor_agent import LoopingCodeExecutorAgent
from core.nested_agent import NestedTeamAgent
```

#### 4. `api/claude_code_controller.py` - Claude Code Integration

**Location:** `/home/rodrigo/agentic/backend/api/claude_code_controller.py`

**Purpose:** Manages Claude Code CLI subprocess for self-editing

**Classes:**
- `ClaudeCodeProcess` - Subprocess manager
- `ClaudeCodeSession` - High-level session wrapper

**Event Flow:**
```python
# User sends message via WebSocket
{"type": "user_message", "data": "Add a new feature"}

# Claude Code CLI receives
{"type": "user", "message": {"role": "user", "content": "Add a new feature"}}

# Claude Code streams back events
{"type": "assistant", "message": {...}}
{"type": "tool_use", ...}
{"type": "tool_result", ...}
{"type": "result", ...}

# Frontend receives normalized events
{"type": "TextMessage", "data": {...}, "source": "claude_code"}
{"type": "ToolCallRequestEvent", "data": {"name": "Bash", ...}}
```

#### 5. `utils/voice_conversation_store.py` - SQLite Storage

**Location:** `/home/rodrigo/agentic/backend/utils/voice_conversation_store.py`

**Purpose:** Persist voice conversation data

**Schema:**
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    voice_model TEXT,
    metadata TEXT
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,
    timestamp TIMESTAMP,
    source TEXT,
    type TEXT,
    payload TEXT,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

**Usage:**
```python
from utils.voice_conversation_store import ConversationStore

store = ConversationStore()
conv_id = store.create_conversation("MyConversation")
store.add_event(conv_id, "claude_code", "ToolCallRequestEvent", {...})
events = store.list_events(conv_id)
```

#### 6. `config/schemas.py` - Data Models

**Location:** `/home/rodrigo/agentic/backend/config/schemas.py`

**Purpose:** Pydantic models for agent configuration and data validation

**Key Models:**
- `AgentConfig` - Agent configuration structure
- `LLMConfig` - LLM provider settings
- `PromptConfig` - System/user prompt configuration

#### 7. `config/config_loader.py` - Configuration Loading

**Location:** `/home/rodrigo/agentic/backend/config/config_loader.py`

**Purpose:** Load agent configurations and tools from disk

**Key Functions:**
- `load_agent_config(name)` - Load agent JSON
- `load_tools()` - Dynamically load all tools from tools/

---

## Frontend Development

### Architecture Overview

The frontend uses a **feature-based architecture** where components and pages are organized by domain rather than by type. This promotes better code organization, scalability, and maintainability.

**Structure:**
```
frontend/src/
├── api.js                    # API client
├── App.js                    # Main app component
├── features/                 # Feature-based organization
│   ├── agents/              # Agent management feature
│   ├── tools/               # Tool management feature
│   └── voice/               # Voice assistant feature
└── shared/                   # Shared components
```

### Features

#### 1. Agents Feature (`features/agents/`)

**Purpose:** Agent configuration, editing, and execution

**Pages:**
- `pages/AgentDashboard.js` - Main agent management interface

**Components:**
- `components/AgentEditor.js` - Form for creating/editing agent configurations
- `components/RunConsole.js` - Live agent execution console with WebSocket
- `components/LogMessageDisplay.js` - Formatted log message rendering

**Location:** `/home/rodrigo/agentic/frontend/src/features/agents/`

#### 2. Tools Feature (`features/tools/`)

**Purpose:** Custom tool management and editing

**Pages:**
- `pages/ToolsDashboard.js` - Tool listing and management

**Components:**
- `components/ToolEditor.js` - Tool code editor interface
- `components/CodeEditor.js` - Monaco-based code editing component

**Location:** `/home/rodrigo/agentic/frontend/src/features/tools/`

#### 3. Voice Feature (`features/voice/`)

**Purpose:** Voice assistant interface and conversation management

**Pages:**
- `pages/VoiceAssistant.js` - Main voice interface with real-time communication
- `pages/VoiceDashboard.js` - Voice conversation listing and management

**Components:**
- `components/VoiceSessionControls.js` - Voice session start/stop controls
- `components/AudioVisualizer.js` - Real-time audio visualization
- `components/ConversationHistory.js` - Message history display
- `components/NestedAgentInsights.js` - Nested team agent activity visualization
- `components/ClaudeCodeInsights.js` - Claude Code tool usage visualization

**Location:** `/home/rodrigo/agentic/frontend/src/features/voice/`

### Key Components Detail

#### `VoiceAssistant.js` - Main Voice Interface

**Location:** `frontend/src/features/voice/pages/VoiceAssistant.js`

**Key Features:**
- OpenAI Realtime API integration (WebRTC)
- Nested team WebSocket connection
- Claude Code WebSocket connection
- Audio streaming and playback
- Real-time event display

**State Management:**
```javascript
const [isRunning, setIsRunning] = useState(false);
const [isMuted, setIsMuted] = useState(false);
const [messages, setMessages] = useState([]);
const nestedWsRef = useRef(null);
const claudeCodeWsRef = useRef(null);
```

**Imports:**
```javascript
import RunConsole from '../../agents/components/RunConsole';
import ConversationHistory from '../components/ConversationHistory';
import NestedAgentInsights from '../components/NestedAgentInsights';
import ClaudeCodeInsights from '../components/ClaudeCodeInsights';
import VoiceSessionControls from '../components/VoiceSessionControls';
```

#### `ClaudeCodeInsights.js` - Claude Code Event Visualizer

**Location:** `frontend/src/features/voice/components/ClaudeCodeInsights.js`

**Purpose:** Display Claude Code tool usage, outputs, and messages

**Data Structure:**
```javascript
// Message structure from backend
{
  id: 123,
  timestamp: "2025-10-10T05:12:41.853041Z",
  source: "claude_code",
  type: "ToolCallRequestEvent",
  data: {
    type: "ToolCallRequestEvent",
    data: {
      name: "Bash",          // Tool name
      arguments: {...},      // Tool arguments
      result: "...",         // Tool result (for execution events)
      content: "..."         // Assistant message content
    }
  }
}
```

**Extraction Pattern:**
```javascript
const msgData = msg?.data || msg?.payload || msg;
const data = msgData?.data || msgData;  // Double nesting!

// For tool calls
const toolName = data.name;           // "Bash", "Read", "Edit", etc.
const args = data.arguments;          // {command: "ls -la", ...}

// For tool results
const result = data.result;           // String result (may have \n)

// For text messages
const content = data.content;         // Assistant message text
```

#### `NestedAgentInsights.js` - Nested Team Visualizer

**Location:** `frontend/src/features/voice/components/NestedAgentInsights.js`

**Purpose:** Visualize nested team agent activities and message flow

#### `RunConsole.js` - Agent Execution Console

**Location:** `frontend/src/features/agents/components/RunConsole.js`

**Purpose:** Generic agent console with WebSocket for real-time agent execution

#### `AudioVisualizer.js` - Voice Activity Visualization

**Location:** `frontend/src/features/voice/components/AudioVisualizer.js`

**Purpose:** Real-time audio waveform visualization during voice sessions

#### `ConversationHistory.js` - Message Display

**Location:** `frontend/src/features/voice/components/ConversationHistory.js`

**Purpose:** Display conversation message history with formatting

### API Client (`frontend/src/api.js`)

**Location:** `/home/rodrigo/agentic/frontend/src/api.js`

**Purpose:** Centralized backend communication

**Example Usage:**
```javascript
// From any feature
import {
  listAgents,
  getAgent,
  runAgentWebSocket,
  connectVoiceConversationStream
} from '../../../api'; // Adjust path based on nesting level

// REST
const agents = await listAgents();
const agent = await getAgent('MainConversation');

// WebSocket
const ws = runAgentWebSocket('MainConversation');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle events
};
```

### Import Patterns

The feature-based architecture uses relative imports:

**From Pages to Components (Same Feature):**
```javascript
// In features/agents/pages/AgentDashboard.js
import AgentEditor from '../components/AgentEditor';
import RunConsole from '../components/RunConsole';
```

**From Pages to Components (Different Feature):**
```javascript
// In features/voice/pages/VoiceAssistant.js
import RunConsole from '../../agents/components/RunConsole';
```

**To API Client:**
```javascript
// From any feature component/page
import api from '../../../api';  // 3 levels up from features/*/components/
import api from '../../api';     // 2 levels up from features/*/pages/
```

---

## Creating New Agents

### Agent JSON Structure

**Location:** `/home/rodrigo/agentic/backend/agents/{AgentName}.json`

### Agent Types

#### 1. Looping Agent (Single Agent with Tools)

**Example:** `Researcher.json`

```json
{
  "name": "MyResearcher",
  "agent_type": "looping",
  "tools": [
    "web_search",
    "fetch_web_content"
  ],
  "llm": {
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "temperature": 0.0,
    "max_tokens": null
  },
  "prompt": {
    "system": "You are a researcher. Use tools to gather info. Say TERMINATE when done.",
    "user": "Research the topic provided by the user."
  },
  "code_executor": null,
  "model_client_stream": false,
  "sources": null,
  "description": "Research agent",
  "system_message": null,
  "max_consecutive_auto_reply": 20,
  "reflect_on_tool_use": true,
  "terminate_on_text": false,
  "tool_call_loop": true,
  "sub_agents": null,
  "mode": null,
  "orchestrator_prompt": null,
  "include_inner_dialog": true
}
```

**Key Fields:**
- `agent_type: "looping"` - Single agent with tool loop
- `tool_call_loop: true` - Continue calling tools until TERMINATE
- `reflect_on_tool_use: true` - Agent reflects on tool results before proceeding

#### 2. Nested Team Agent (Multi-Agent Coordination)

**Example:** `MainConversation.json`

```json
{
  "name": "MyTeam",
  "agent_type": "nested_team",
  "tools": [],
  "llm": {
    "provider": "openai",
    "model": "gpt-4-turbo-2024-04-09",
    "temperature": 0.0,
    "max_tokens": null
  },
  "prompt": {
    "system": "",
    "user": ""
  },
  "code_executor": {"type": ""},
  "model_client_stream": false,
  "sources": [],
  "description": "Coordinated team",
  "system_message": "",
  "max_consecutive_auto_reply": 20,
  "reflect_on_tool_use": true,
  "terminate_on_text": false,
  "tool_call_loop": false,
  "sub_agents": [
    "Manager",
    "Researcher",
    "Developer"
  ],
  "mode": "selector",
  "orchestrator_prompt": "__function__",
  "include_inner_dialog": true
}
```

**Key Fields:**
- `agent_type: "nested_team"` - Multi-agent coordinator
- `sub_agents: [...]` - List of agent names to coordinate
- `mode: "selector"` - Orchestrator selects which agent responds
- `orchestrator_prompt: "__function__"` - Uses built-in orchestration logic

#### 3. Multimodal Tools Looping Agent (Vision-Capable Agent)

**Example:** `MultimodalVisionAgent.json`

**Added:** 2025-10-11

```json
{
  "name": "MyVisionAgent",
  "agent_type": "multimodal_tools_looping",
  "tools": [
    "take_screenshot",
    "generate_test_image",
    "get_sample_image"
  ],
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.0,
    "max_tokens": null
  },
  "prompt": {
    "system": "You are an AI assistant with vision capabilities. When you use tools that return images, you will automatically be able to see and analyze those images directly. Describe what you see in detail. Say TERMINATE when done.",
    "user": "Generate a test image and describe what you see."
  },
  "code_executor": null,
  "model_client_stream": false,
  "sources": null,
  "description": "An agent that can interpret images from tool responses",
  "system_message": null,
  "max_consecutive_auto_reply": 15,
  "reflect_on_tool_use": true,
  "terminate_on_text": false,
  "tool_call_loop": true,
  "sub_agents": null,
  "mode": null,
  "orchestrator_prompt": null,
  "include_inner_dialog": true
}
```

**Key Features:**
- `agent_type: "multimodal_tools_looping"` - Looping agent with vision capabilities
- **Automatic image detection** - Detects images in tool responses (file paths, base64)
- **MultiModalMessage creation** - Converts images to multimodal messages for the LLM
- **Vision model required** - Must use vision-capable models (gpt-4o, gpt-4o-mini, etc.)
- **Seamless integration** - Works like regular looping agent, but can "see" images

**How It Works:**

1. Tool returns text with image reference: `"Screenshot saved to /path/image.png"`
2. Agent automatically detects the image path or base64 data
3. Agent converts to `MultiModalMessage` containing text + image
4. LLM receives and can "see" the image directly
5. LLM describes/analyzes the image content

**Supported Image Formats:**
- File paths: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`
- Base64 encoded: `data:image/png;base64,...`
- Absolute or relative paths

**Example Tools for Multimodal Agents:**
- `take_screenshot` - Capture screen images
- `generate_test_image` - Create test images with PIL
- `get_sample_image` - Generate charts, diagrams, photos
- Any tool that returns image file paths

**Testing:**
```bash
# Run unit tests
cd backend
source venv/bin/activate
pytest tests/test_image_tools.py -v

# Run integration tests
python3 tests/integration/test_multimodal_integration.py
python3 tests/integration/test_multimodal_api.py
```

**Documentation:**
- See `backend/docs/MULTIMODAL_AGENT_GUIDE.md` for complete usage guide
- See `backend/docs/MULTIMODAL_AGENT_IMPLEMENTATION_SUMMARY.md` for implementation details

### Creating a New Agent

**Step 1:** Create JSON configuration

```bash
cat > /home/rodrigo/agentic/backend/agents/MyNewAgent.json << 'EOF'
{
  "name": "MyNewAgent",
  "agent_type": "looping",
  "tools": ["web_search"],
  "llm": {
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "temperature": 0.0,
    "max_tokens": null
  },
  "prompt": {
    "system": "Your system prompt here",
    "user": "Your example task"
  },
  "code_executor": null,
  "model_client_stream": false,
  "sources": null,
  "description": "Description of agent",
  "system_message": null,
  "max_consecutive_auto_reply": 20,
  "reflect_on_tool_use": true,
  "terminate_on_text": false,
  "tool_call_loop": true,
  "sub_agents": null,
  "mode": null,
  "orchestrator_prompt": null,
  "include_inner_dialog": true
}
EOF
```

**Step 2:** Reload backend (auto-reloads if using uvicorn)

**Step 3:** Test via frontend at `http://localhost:3000/agents/MyNewAgent`

### Agent Configuration Reference

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Agent name (must match filename) |
| `agent_type` | string | "looping", "multimodal_tools_looping", or "nested_team" |
| `tools` | array | List of tool names to provide |
| `llm.provider` | string | "openai", "anthropic", "google" |
| `llm.model` | string | Model identifier (use gpt-4o for multimodal) |
| `llm.temperature` | float | 0.0-2.0, controls randomness |
| `prompt.system` | string | System prompt for agent |
| `tool_call_loop` | bool | Continue calling tools in loop |
| `reflect_on_tool_use` | bool | Reflect on tool results |
| `sub_agents` | array | Child agents (nested team only) |
| `mode` | string | "selector" (nested team only) |
| `orchestrator_prompt` | string | "__function__" for built-in orchestration |
| `include_inner_dialog` | bool | Show agent-to-agent messages |

---

## Creating New Tools

### Tool Structure

**Location:** `/home/rodrigo/agentic/backend/tools/{toolname}.py`

### Tool Implementation Pattern

**Example:** Simple tool

```python
# tools/my_tool.py

from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 1. Define input schema using Pydantic
class MyToolInput(BaseModel):
    query: str = Field(..., description="The search query")
    max_results: Optional[int] = Field(5, description="Maximum results to return")

# 2. Implement tool function
def my_tool(query: str, max_results: int = 5) -> str:
    """
    Brief description of what the tool does.

    This docstring becomes part of the tool's description for the LLM.
    Be clear and concise about what the tool does and when to use it.

    Args:
        query: The search query
        max_results: Maximum number of results

    Returns:
        String with results
    """
    try:
        # Tool logic here
        results = perform_search(query, max_results)
        return f"Found {len(results)} results:\n" + "\n".join(results)
    except Exception as e:
        logger.error(f"Error in my_tool: {e}")
        return f"Error: {str(e)}"

# 3. Create FunctionTool instance
my_tool_func = FunctionTool(
    func=my_tool,
    name="my_tool",
    description="Search for information using my custom tool"
)

# 4. Export as list (required by config_loader.py)
tools = [my_tool_func]
```

### Advanced Tool with Agent Context

**Example:** Memory tool (from `tools/memory.py`)

```python
from utils.context import get_current_agent
from autogen_core.tools import FunctionTool

def save_to_short_term_memory(content: str) -> str:
    """Save content to short-term memory and refresh agent's context."""
    try:
        # Get current agent from execution context
        agent = get_current_agent()

        # Save to file
        with open(SHORT_TERM_MEMORY_FILE, 'w') as f:
            f.write(content)

        # Update agent's system message with new memory
        if agent and agent._system_messages:
            updated_msg = agent._system_messages[0].content.replace(
                "{{SHORT_TERM_MEMORY}}",
                content
            )
            agent._system_messages[0].content = updated_msg

        return f"Saved to short-term memory: {len(content)} characters"
    except Exception as e:
        return f"Error: {str(e)}"

save_memory_tool = FunctionTool(
    func=save_to_short_term_memory,
    name="save_to_short_term_memory",
    description="Save important information to short-term memory for later recall"
)

tools = [save_memory_tool, ...]
```

### Tool Best Practices

1. **Clear Documentation:**
   - Docstring should explain when to use the tool
   - Describe parameters clearly
   - Include examples if complex

2. **Error Handling:**
   - Always wrap in try/except
   - Return helpful error messages
   - Log errors for debugging

3. **Type Safety:**
   - Use Pydantic models for validation
   - Specify Field descriptions for LLM context

4. **Return Format:**
   - Return strings or structured data
   - Format output for readability
   - Include relevant context in response

### Registering Tools

Tools are automatically loaded from `/backend/tools/` by `config/config_loader.py`.

**Verification:**

```python
# Check loaded tools
GET /api/tools

# Response:
{
  "tools": [
    {"name": "my_tool", "file": "my_tool.py"},
    ...
  ]
}
```

---

## Voice Assistant System

### Architecture

```
User Speech
    ↓
Microphone (WebRTC)
    ↓
OpenAI Realtime API (WebSocket)
    ↓
Voice Controller (backend/api/realtime_voice.py)
    ├─→ Nested Team WebSocket
    ├─→ Claude Code WebSocket
    └─→ Tool Execution (send_to_nested, send_to_claude_code)
    ↓
Audio Response
    ↓
Speaker Playback (WebRTC)
```

### Key Components

**Backend:** `api/realtime_voice.py`

**Frontend:** `pages/VoiceAssistant.js`

### Voice Tools

The voice model has access to special tools:

```javascript
{
  name: "send_to_nested",
  description: "Send task to nested team",
  parameters: {text: string}
}

{
  name: "send_to_claude_code",
  description: "Send self-editing instruction to Claude Code",
  parameters: {text: string}
}

{
  name: "pause",
  description: "Pause nested team execution"
}

{
  name: "reset",
  description: "Reset nested team state"
}
```

### Voice System Prompt

Located in `api/realtime_voice.py`:

```python
VOICE_SYSTEM_PROMPT = (
    "You are Archie, the realtime voice interface for a multi-agent team "
    "and self-editing Claude Code instance..."
)
```

**Key Behaviors:**
- Narrate team activities concisely
- Only speak after meaningful milestones
- Wait for [RUN_FINISHED] before final summary
- Use tools to delegate work, not execute directly

---

## Claude Code Self-Editor

### Purpose

Allows the voice assistant to instruct Claude Code CLI to modify the codebase in real-time.

### Architecture

```
Voice Command: "Add a new feature"
    ↓
Voice Model calls: send_to_claude_code({text: "Add a new feature"})
    ↓
Frontend sends to: ws://localhost:8000/api/runs/ClaudeCode
    ↓
ClaudeCodeSession spawns: claude --permission-mode=bypassPermissions --input-format=stream-json --output-format=stream-json
    ↓
Events stream back:
    - SystemEvent (init)
    - TextMessage (assistant thoughts)
    - ToolCallRequestEvent (tool usage)
    - ToolCallExecutionEvent (results)
    - TaskResult (completion)
    ↓
Frontend displays in ClaudeCodeInsights component
    ↓
Voice narrates significant changes
```

### Permission Handling

**Key Configuration:**

The voice assistant requires **automatic permission approval** since users cannot interactively approve Claude Code's tool usage during voice sessions.

**Implementation:**

```python
# backend/api/claude_code_controller.py

class ClaudeCodeProcess:
    # Claude CLI path - VSCode extension binary
    CLAUDE_CLI_PATH = "/home/rodrigo/.vscode/extensions/anthropic.claude-code-2.0.14-linux-x64/resources/native-binary/claude"

    def __init__(
        self,
        working_dir: str = "/home/rodrigo/agentic",
        model: str = "claude-sonnet-4-5-20250929",
        permission_mode: str = "bypassPermissions",  # ← Key setting
    ):
        ...

# backend/main.py - WebSocket endpoint
@app.websocket("/api/runs/ClaudeCode")
async def run_claude_code_ws(websocket: WebSocket):
    session = ClaudeCodeSession(
        working_dir=working_dir,
        model="claude-sonnet-4-5-20250929",
        permission_mode="bypassPermissions",  # ← Bypass for voice assistant
    )
```

**Available Permission Modes:**

- `bypassPermissions` - **Used for voice assistant** - Executes all tools without prompts
- `acceptEdits` - Auto-accepts file edits only, still prompts for other tools
- `default` - Normal interactive permission prompts (not suitable for voice)
- `plan` - Plan mode, doesn't execute tools

**Testing:**

```bash
# Test permission-free execution
cd /home/rodrigo/agentic/backend
python3 test_claude_code_permissions.py
```

**Security Note:**

The `bypassPermissions` mode is safe in this context because:
1. The voice assistant is already trusted to execute arbitrary code
2. Claude Code operates in the same working directory as the voice assistant
3. The system is designed for self-modification capabilities

For production deployments or untrusted environments, consider implementing:
- Allowlisted tools: `--allowed-tools "Bash(git:*) Edit Read"`
- Directory restrictions: `--add-dir /safe/path`
- Tool approval workflows in the voice interface

### Event Types

**From Claude Code:**

```javascript
// System initialization
{
  type: "SystemEvent",
  data: {
    message: "init",
    details: {
      cwd: "/home/rodrigo/agentic",
      tools: [...],
      model: "claude-sonnet-4-5-20250929"
    }
  }
}

// Assistant message
{
  type: "TextMessage",
  data: {
    content: "I'll add the feature now...",
    source: "ClaudeCode"
  }
}

// Tool request
{
  type: "ToolCallRequestEvent",
  data: {
    name: "Bash",
    arguments: {
      command: "ls -la",
      description: "List files"
    },
    id: "toolu_xxx"
  }
}

// Tool result
{
  type: "ToolCallExecutionEvent",
  data: {
    name: "tool",
    result: "total 48\ndrwxr-xr-x ...",
    is_error: false,
    id: "toolu_xxx"
  }
}

// Final result
{
  type: "TaskResult",
  data: {
    outcome: "success",
    message: "Feature added successfully",
    duration_ms: 5420,
    usage: {...},
    models_usage: {...}
  }
}
```

### Adding Claude Code Narration

In `api/realtime_voice.py`, Claude Code events are forwarded to voice:

```python
# Tool use narration
if type === "ToolCallRequestEvent":
    tool_name = data.get("name")
    forwardToVoice("system", f"[CODE ClaudeCode] Using {tool_name}")

# Completion narration
if type === "TaskResult":
    message = data.get("message")
    forwardToVoice("system", f"[CODE RESULT] {message}")
```

---

## Best Practices

### General Development

1. **Always Use TodoWrite:**
   - Track multi-step tasks
   - Mark tasks in_progress before starting
   - Complete tasks immediately after finishing

2. **Read Before Write:**
   - Always Read files before editing
   - Understand context before making changes

3. **Test Changes:**
   - Take screenshots for UI changes
   - Export database for backend debugging
   - Check logs for errors

### UI Development Workflow

```bash
# 1. Screenshot before
node /home/rodrigo/agentic/debug/screenshot.js http://localhost:3000/voice \
  /home/rodrigo/agentic/debug/screenshots/before.png 2000

# 2. Read screenshot

# 3. Edit React component

# 4. Wait for hot reload
sleep 3

# 5. Screenshot after
node /home/rodrigo/agentic/debug/screenshot.js http://localhost:3000/voice \
  /home/rodrigo/agentic/debug/screenshots/after.png 3000

# 6. Read and verify
```

### Agent Development Workflow

1. **Design agent purpose** - What specific task?
2. **Choose agent type** - Looping or nested team?
3. **Select tools** - What capabilities needed?
4. **Write system prompt** - Clear instructions + examples
5. **Test iteratively** - Start simple, add complexity
6. **Export conversations** - Debug with database exports

### Debugging Workflow

**For Voice System Issues:**

```bash
# 1. Export conversations
cd /home/rodrigo/agentic
python3 debug/export_voice_conversations.py

# 2. Find problematic conversation
ls debug/db_exports/voice_conversations/

# 3. Analyze events
jq '.events[] | select(.type == "Error")' debug/db_exports/voice_conversations/{id}.json
```

**For UI Issues:**

```bash
# 1. Take screenshot
node debug/screenshot.js http://localhost:3000/path debug/screenshots/debug.png

# 2. Read screenshot

# 3. Check browser console (if running locally)

# 4. Check React component state
```

**For Agent Issues:**

```bash
# 1. Check agent configuration
curl http://localhost:8000/api/agents/AgentName

# 2. Check available tools
curl http://localhost:8000/api/tools

# 3. Test agent via API
# (Use frontend or WebSocket client)

# 4. Check backend logs
```

### Code Style

**Python:**
- Use type hints
- Add docstrings to all functions
- Handle exceptions gracefully
- Log important events

**JavaScript/React:**
- Use functional components with hooks
- Extract reusable logic to custom hooks
- PropTypes for component props
- Descriptive variable names

### Git Workflow

**Commit Messages:**

```bash
# Good
git commit -m "Add Claude Code integration for voice assistant

- Created claude_code_controller.py for subprocess management
- Added ClaudeCodeInsights.js component for visualization
- Integrated with voice assistant tools

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Bad
git commit -m "Fixed stuff"
```

---

## Quick Reference

### Common Commands

```bash
# Start backend
cd /home/rodrigo/agentic/backend
uvicorn main:app --reload

# Start frontend
cd /home/rodrigo/agentic/frontend
npm start

# Take screenshot
node /home/rodrigo/agentic/debug/screenshot.js http://localhost:3000

# Export voice conversations
cd /home/rodrigo/agentic
python3 debug/export_voice_conversations.py

# List agents
curl http://localhost:8000/api/agents

# List tools
curl http://localhost:8000/api/tools
```

### File Locations Reference

| Purpose | Location |
|---------|----------|
| **Backend** | |
| Main FastAPI app | `/home/rodrigo/agentic/backend/main.py` |
| Agent configs | `/home/rodrigo/agentic/backend/agents/*.json` |
| Tool implementations | `/home/rodrigo/agentic/backend/tools/*.py` |
| Configuration & schemas | `/home/rodrigo/agentic/backend/config/` |
| Core agent logic | `/home/rodrigo/agentic/backend/core/` |
| API modules (voice, claude) | `/home/rodrigo/agentic/backend/api/` |
| Utility modules | `/home/rodrigo/agentic/backend/utils/` |
| **Frontend** | |
| API client | `/home/rodrigo/agentic/frontend/src/api.js` |
| Agents feature | `/home/rodrigo/agentic/frontend/src/features/agents/` |
| Tools feature | `/home/rodrigo/agentic/frontend/src/features/tools/` |
| Voice feature | `/home/rodrigo/agentic/frontend/src/features/voice/` |
| Shared components | `/home/rodrigo/agentic/frontend/src/shared/` |
| **Debug & Tools** | |
| Screenshot tool | `/home/rodrigo/agentic/debug/screenshot.js` |
| Screenshots | `/home/rodrigo/agentic/debug/screenshots/` |
| Export script | `/home/rodrigo/agentic/debug/export_voice_conversations.py` |
| Voice DB exports | `/home/rodrigo/agentic/debug/db_exports/voice_conversations/` |
| Voice database | `/home/rodrigo/agentic/backend/voice_conversations.db` |
| **Tests** | |
| Test suite directory | `/home/rodrigo/agentic/backend/tests/` |
| Image tools tests | `/home/rodrigo/agentic/backend/tests/test_image_tools.py` |
| Unit tests | `/home/rodrigo/agentic/backend/tests/unit/` |
| Integration tests | `/home/rodrigo/agentic/backend/tests/integration/` |
| **Scripts** | |
| Scripts directory | `/home/rodrigo/agentic/backend/scripts/` |
| X11 fix & test | `/home/rodrigo/agentic/backend/scripts/fix_x11_and_test.sh` |
| GNOME screenshot fix | `/home/rodrigo/agentic/backend/scripts/fix_gnome_screenshot.sh` |
| **Documentation** | |
| Main guide (this file) | `/home/rodrigo/agentic/CLAUDE.md` |
| Root documentation | `/home/rodrigo/agentic/docs/` |
| Backend docs | `/home/rodrigo/agentic/backend/docs/` |
| Screenshot guides | `/home/rodrigo/agentic/backend/docs/SCREENSHOT_*.md` |
| Multimodal guides | `/home/rodrigo/agentic/backend/docs/MULTIMODAL_*.md` |
| Backend refactoring | `/home/rodrigo/agentic/docs/REFACTORING_SUMMARY.md` |
| Frontend refactoring | `/home/rodrigo/agentic/docs/FRONTEND_REFACTORING.md` |

---

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python3 --version  # Should be 3.9+

# Install dependencies
cd /home/rodrigo/agentic/backend
pip install -r requirements.txt

# Check for port conflicts
lsof -i :8000
```

### Frontend won't start

```bash
# Check Node version
node --version  # Should be 16+

# Install dependencies
cd /home/rodrigo/agentic/frontend
npm install

# Check for port conflicts
lsof -i :3000
```

### WebSocket not connecting

```bash
# Verify backend is running
curl http://localhost:8000/api/agents

# Check browser console for errors

# Verify WebSocket URL in frontend
# Should be ws://localhost:8000 (or wss:// for production)
```

### Screenshot tool fails

```bash
# Install Puppeteer dependencies
cd /home/rodrigo/agentic/debug
npm install

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install -y chromium-browser
```

### Claude Code integration fails

```bash
# Verify claude command exists
which claude

# Test claude CLI
echo '{"type":"user","message":{"role":"user","content":"test"}}' | \
  claude -p --input-format=stream-json --output-format=stream-json

# Check permissions
ls -la ~/.claude/
```

---

## Future Enhancements

**Potential Improvements:**

1. **Agent Memory:**
   - Persistent memory across sessions
   - Memory search and retrieval
   - Memory cleanup/summarization

2. **Voice Features:**
   - Custom wake word
   - Voice activity detection tuning
   - Multi-language support

3. **Claude Code:**
   - Permission management UI
   - Code review before applying changes
   - Change history and rollback

4. **Debugging:**
   - Real-time log streaming to frontend
   - Agent execution replay
   - Performance monitoring dashboard

5. **Testing:**
   - Automated E2E tests
   - Agent behavior tests
   - Voice interaction tests

---

---

## Recent Changes

### Multimodal Vision Agent (2025-10-11)

A new agent type has been added that can automatically interpret images and visual content from tool responses.

**What's New:**
- **New Agent Type:** `multimodal_tools_looping` - Looping agent with vision capabilities
- **Automatic Image Detection:** Detects images in tool responses (file paths, base64)
- **MultiModalMessage Creation:** Converts images to multimodal messages for vision-capable LLMs
- **Test Coverage:** 8/8 unit tests + integration tests passing

**New Files:**
- `backend/core/multimodal_tools_looping_agent.py` - Core implementation
- `backend/tools/image_tools.py` - Sample image generation tools
- `backend/agents/MultimodalVisionAgent.json` - Example configuration
- `backend/tests/test_multimodal_agent_e2e.py` - Comprehensive test suite
- `backend/MULTIMODAL_AGENT_GUIDE.md` - Complete documentation
- `backend/MULTIMODAL_AGENT_IMPLEMENTATION_SUMMARY.md` - Implementation details

**How It Works:**
1. Tool returns: `"Screenshot saved to /path/image.png"`
2. Agent detects image reference automatically
3. Converts to MultiModalMessage with text + image
4. Vision LLM (gpt-4o) "sees" and describes the image

**Example Use Cases:**
- Screenshot analysis and UI testing
- Chart interpretation and data extraction
- Image description for accessibility
- Visual debugging and verification

**Testing:**
```bash
cd backend && source venv/bin/activate
pytest tests/test_multimodal_agent_e2e.py -v  # Unit tests
python3 test_multimodal_integration.py        # Integration test
python3 test_multimodal_api.py                # Full stack test
```

### Backend Reorganization (2025-10-10)

The backend has been reorganized into a modular structure for better maintainability:

**New Structure:**
- `config/` - Configuration and data models (schemas.py, config_loader.py)
- `utils/` - Utility functions (context.py, voice_conversation_store.py)
- `core/` - Core agent logic (agent_factory.py, runner.py, agent implementations)
- `api/` - API-specific modules (realtime_voice.py, claude_code_controller.py)

**Import Pattern:**
All imports now use the new module structure:
```python
from config.schemas import AgentConfig
from utils.context import get_current_agent
from core.agent_factory import create_agent_from_config
from api.realtime_voice import router
```

**Deleted Files:**
The following legacy/unused files were removed:
- Backend: agent_client.py, list_openai_models.py, list_google_models.py, voice_controller.py
- Frontend: AgentList.js, NestedInsights.js, ToolList.js, VoiceConversationsList.js, VoiceConversationPanel.js, VoiceControls.js

See [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) for complete details.

### Frontend Reorganization

The frontend has been reorganized into a feature-based architecture:

**New Structure:**
- `features/agents/` - Agent management feature (components + pages)
- `features/tools/` - Tool management feature (components + pages)
- `features/voice/` - Voice assistant feature (components + pages)
- `shared/` - Shared components (for future use)

**Import Pattern:**
Components are now imported from feature folders:
```javascript
// In App.js
import AgentDashboard from './features/agents/pages/AgentDashboard';
import VoiceAssistant from './features/voice/pages/VoiceAssistant';

// Cross-feature imports
import RunConsole from '../../agents/components/RunConsole';
```

**Benefits:**
- Feature isolation - Each feature is self-contained
- Better scalability - Easy to add new features
- Clearer organization - Components grouped by domain
- Improved maintainability - Feature-specific changes are isolated

See [FRONTEND_REFACTORING.md](FRONTEND_REFACTORING.md) for complete details.

---

**End of CLAUDE.md**

This document should be updated whenever significant architectural changes are made.

**Last updated:** 2025-10-11
**Changes:**
- 2025-10-11: Added multimodal vision agent (`multimodal_tools_looping`) with automatic image detection and interpretation
- 2025-10-10: Refactored backend into modular structure (config, utils, core, api) + Refactored frontend into feature-based architecture (agents, tools, voice)
