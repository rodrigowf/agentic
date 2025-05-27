# Agentic Developer Guide

This guide provides an in-depth overview of Agentic's architecture, components, and extension points for developers.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Schemas](#schemas)
- [Backend Components](#backend-components)
  - [Agent Factory (`agent_factory.py`)](#agent-factory-agent_factorypy)
  - [Runner (`runner.py`)](#runner-runnerpy)
  - [Nested Team Agent (`nested_agent.py`)](#nested-team-agent-nested_agentpy)
  - [Looping Assistant Agent (`looping_agent.py`)](#looping-assistant-agent-looping_agentpy)
  - [Config Loader (`config_loader.py`)](#config-loader-config_loaderpy)
  - [Schemas Definition (`schemas.py`)](#schemas-definition-schemaspy)
  - [Tool Modules (`tools/`)](#tool-modules-tools)

- [Frontend Components (`src/components/`)](#frontend-components-srccomponents)
  - [AgentList](#agentlist)
  - [AgentEditor](#agenteditor)
  - [AgentDashboard](#agentdashboard)
  - [RunConsole](#runconsole)
  - [ToolList](#toollist)
  - [ToolEditor](#tooleditor)
  - [CodeEditor](#codeeditor)
  - [LogMessageDisplay](#logmessagedisplay)

- [Extending Agent Types](#extending-agent-types)
- [Adding New Tools](#adding-new-tools)
- [API Endpoints](#api-endpoints)

---

## Architecture Overview

Agentic is a full-stack platform for creating and running generative AI agents. It consists of:

- **Backend**: FastAPI-based server managing configurations, instantiating agents, and running them over WebSockets.
- **Frontend**: React + MUI dashboard for listing, editing, and running agents.
- **Tools**: User-defined function tools loaded dynamically and exposed to agents.

Messages between frontend and backend occur via REST APIs and WebSockets for real-time agent interactions.

---

## Schemas

Defined in `backend/schemas.py` using Pydantic v2:

- **AgentConfig**: Captures agent settings including:
  - `name`: Unique agent identifier.
  - `agent_type`: `assistant`, `looping`, `code_executor`, or `nested_team`.
  - `tools`: List of tool names to attach.
  - `llm`: Model provider config (`provider`, `model`, `temperature`, `max_tokens`).
  - `prompt`: System and user messages for a standard assistant.
  - Code executor fields: `code_executor`, `system_message`, `description`, `sources`, `model_client_stream`.
  - Looping options: `tool_call_loop`, `max_consecutive_auto_reply`.
  - Nested team: `sub_agents`, `mode`, `orchestrator_prompt`.

- **ToolInfo**: Metadata exposed via `/api/tools` including `name`, `description`, `parameters`, and optional `filename`.

---

## Backend Components

### Agent Factory (`agent_factory.py`)

Centralized instantiation of all agent types:

- Filters global tools by agent-specific tool list.
- Branches on `agent_cfg.agent_type`:
  - `assistant`: Returns `AssistantAgent` with prompt and tools.
  - `looping`: Returns `LoopingAssistantAgent` wrapping base assistant logic.
  - `code_executor`: Constructs `CodeExecutorAgent` with configured code executor backend (local CLI by default).
  - `nested_team`: Builds `NestedTeamAgent` which orchestrates multiple sub-agents.

Docstrings in this module explain parameter usage and extension.

### Runner (`runner.py`)

Handles WebSocket connections and agent execution:

- Receives `AgentConfig` and list of `FunctionTool` from config loader.
- Builds an `OpenAIChatCompletionClient` (or other provider) based on `agent_cfg.llm`.
- Instantiates agent via factory, then streams events back to client using `agent.run_stream`.
- Serializes events recursively into JSON-friendly payloads.

### Nested Team Agent (`nested_agent.py`)

Implements a composite agent coordinating multiple sub-agents:

- Reads `sub_agents` configs and creates each via the factory.
- Configures a `RoundRobinGroupChat` or `SelectorGroupChat` based on `mode`.
- Uses `MaxMessageTermination` for graceful shutdown.

### Looping Assistant Agent (`looping_agent.py`)

Extends `AssistantAgent` to re-invoke the model until `TERMINATE` is detected or a safety iteration limit is reached.

- Overrides `run_stream` to manage iteration count and combine tool events.

### Config Loader (`config_loader.py`)

Serves as the bridge between FS storage and runtime:

- **load_tools**: Scans `tools/` directory, imports each `.py`, and enumerates `FunctionTool` instances.
- **load_agents** / **save_agent**: Serialize / deserialize `AgentConfig` JSON files in `agents/`.
- **get_tool_infos**: Prepares `ToolInfo` list for API by extracting schemas from each tool.

### Tool Modules (`tools/`)

Each `.py` in `backend/tools/` defines one or more `FunctionTool` objects that agents can invoke.

- Example: `research.py` includes web search, ArXiv search, and Wikipedia tools.

---

## Frontend Components (`src/components/`)

Components are built with React and MUI:

#### AgentList

Shows existing agents with edit and delete links.

#### AgentEditor

Form to create or edit an agent:
- Dropdown for `agent_type`.
- Dynamically shows fields for prompts, code executor config, nested sub-agents selection, looping options, and LLM settings.

#### AgentDashboard

Top-level page combining `AgentEditor` and `RunConsole` side by side.

#### RunConsole

WebSocket-based console to run tasks against an agent:
- Input field for user prompt.
- Live-stream logs of messages, tool calls, and responses.
- Buttons to connect/disconnect and clear logs.

#### ToolList

Displays tools grouped by source file.

#### ToolEditor

Code editor to create or modify a tool file.

#### CodeEditor

Monaco-based code editor wrapper with theme integration and read-only mode.

#### LogMessageDisplay

Renders logs from agent runs with icons, collapsible data views, and message parsing.

---

## Extending Agent Types

1. Update `schemas.AgentConfig` with new config fields.
2. Add case in `agent_factory.create_agent_from_config` returning a new subclass of `BaseChatAgent`.
3. Implement agent logic in a new module, following patterns in `looping_agent.py` or `nested_agent.py`.
4. Update frontend `AgentEditor` to surface new config options.

---

## Adding New Tools

1. Create or update a `.py` file in `backend/tools/`.
2. Define functions and corresponding Pydantic input models.
3. Instantiate `FunctionTool` for each function.
4. Tools automatically load on server start; refresh frontend to see updated list.

---

## API Endpoints

- `GET /api/tools` – List available tools.
- `GET /api/tools/content/{filename}` – Raw tool code.
- `PUT /api/tools/content/{filename}` – Save tool code.
- `POST /api/tools/upload` – Upload new tool files.
- `GET /api/agents` – List agent configs.
- `POST/PUT /api/agents` – Create/update agent configs.
- `WebSocket /api/runs/{agent_name}` – Run an agent in real time.

---

For more details, refer to in-code docstrings and the `docs/` folder.
