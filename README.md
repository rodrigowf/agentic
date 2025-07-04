# Agentic: Your AutoGen Agent Dashboard 🚀

Welcome to **Agentic**, the ultimate dashboard for creating, managing, and observing your [AutoGen](https://microsoft.github.io/autogen/) agents in action! Think of it as your mission control for building sophisticated AI assistants.

This project provides a seamless experience with:

- **Backend**: A robust FastAPI server (powered by AutoGen v0.5.3) that handles agent logic, tool execution, and communication.
- **Frontend**: An intuitive React + Material UI dashboard where you can:
    - Visually create and configure new agents.
    - Define and manage Python tools for your agents.
    - Run agents and watch their thought processes and actions unfold in real-time via a live console.

## ✨ Features

*   **Visual Agent Builder**: No more wrestling with JSON files! Create agents through a user-friendly interface.
*   **Tool Management**: Easily add, edit, or generate Python tools for your agents to use.
*   **Live Run Console**: Observe agent interactions, tool calls, and LLM responses as they happen.
*   **Multi-LLM Support**: Configure agents to use models from OpenAI, Anthropic, or Google Gemini.
*   **Flexible Configuration**: Fine-tune agent parameters like temperature, max_consecutive_auto_reply, system prompts, and more.
*   **Modern Tech Stack**: Built with FastAPI, React, Material UI, and AutoGen.

## 🛠️ Setup & Installation

Get Agentic up and running in a few simple steps.

**Prerequisites:**

*   Python 3.10+
*   Node.js 16+
*   API Keys for your chosen LLM providers (OpenAI, Anthropic, Gemini)

**1. Backend Setup:**

```bash
# Navigate to the backend directory
cd backend

# Create and populate your environment file
cp .env.example .env
# --> Edit .env and add your API keys <--

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server (with auto-reload, except for code generations)
uvicorn main:app --reload --reload-exclude workspace
```

**2. Frontend Setup:**

```bash
# Navigate to the frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the React development server
npm start
```

## 🚀 Usage

1.  **Access the Dashboard**: Open your browser and navigate to `http://localhost:3000` (or the port specified by `npm start`).
2.  **Create Tools**: Go to the "Tools" section. You can create new Python tool files from scratch, edit existing ones, or even generate tool code from a natural language prompt. Ensure your tools define functions and corresponding `ToolDefinition` instances.
3.  **Create Agents**: Go to the "Agents" section (the homepage). Click "New Agent".
    *   Give your agent a unique name.
    *   Write system and user prompts.
    *   Select the LLM provider and model.
    *   Choose the tools you want the agent to have access to.
    *   Configure other parameters as needed.
    *   Save the agent.
4.  **Run Agents**: From the "Agents" list, click the "Run" button (play icon) next to the agent you want to deploy. This will take you to the live console.
5.  **Interact**: In the Run Console, enter the initial task or message for the agent and click "Run Agent". Watch the magic happen!

Enjoy building and experimenting with your AI agents using Agentic!

## Architecture Overview

Agentic consists of two main components:

1. **Backend (FastAPI + AutoGen)**
   - **Agent Runner (`runner.py`)**: WebSocket endpoint to run agents in real-time, streaming messages to the frontend.
   - **Agent Factory (`agent_factory.py`)**: Centralized logic to instantiate LLM, Looping, CodeExecutor, and NestedTeam agents from configuration.
   - **Config Loader (`config_loader.py`)**: Dynamically loads tool definitions (`FunctionTool`) and agent JSON configs at startup.
   - **Schemas (`schemas.py`)**: Pydantic models for `AgentConfig`, `ToolInfo`, and API request/response validation.
   - **NestedTeamAgent (`nested_agent.py`)**: Custom agent class that wraps multiple sub-agents in a round-robin or selector team chat.
   - **LoopingAssistantAgent (`looping_agent.py`)**: Extends the standard assistant to loop tool calls until termination criteria.
   - **CodeExecutorAgent**: Integrates code generation and local execution via Autogen’s code-executor framework.

2. **Frontend (React + Material UI)**
   - **Agent List / Editor (`AgentList`, `AgentEditor`)**: UI to create, edit, and configure agents and their tools.
   - **Tool Editor (`ToolList`, `ToolEditor`)**: View, edit, and generate Python tool code loaded into the system.
   - **Run Console (`RunConsole`)**: Live chat interface to run an agent, view streaming messages, and follow up with multi-turn conversations.

---

## Agent Types

Agentic supports four agent types, selected in the Agent Editor UI:

- **Assistant**: Standard LLM-based agent with system/user prompts and optional tools.
- **Looping Assistant**: Same as Assistant but will automatically call tools in a loop until a termination signal or max iterations.
- **Code Executor**: Agent that generates code snippets and executes them locally, returning results back into the chat.
- **Nested Team**: Orchestrates a group of sub-agents in a round-robin or selector mode, aggregating their responses.

Each type is configured via `AgentConfig` JSON and instantiated by `agent_factory.py`.

---

## Getting Started

1. **Clone & Install**

   ```bash
   git clone https://github.com/your-repo/agentic.git
   cd agentic/backend
   pip install -r requirements.txt
   cd ../frontend
   npm install
   ```

2. **Environment Variables**

   Copy `.env.example` to `.env` in the backend folder and provide API keys for OpenAI, Anthropic, and Gemini.

3. **Run Backend**

   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. **Run Frontend**

   ```bash
   npm start
   ```

5. **Open Dashboard**

   Navigate to `http://localhost:3000` to manage agents, tools, and run live sessions.

---

## Development Notes

- **Adding New Agent Types**: Update `schemas.py` with new config fields, extend `create_agent_from_config`, and add UI options in `AgentEditor.js`.
- **Adding Tools**: Drop new `.py` modules in `backend/tools/`, each exporting `FunctionTool` instances. The system auto-loads them on startup.
- **Extending Nested Teams**: Custom sub-agents can be any supported agent type; modify `nested_agent.py` if adding new team behaviors.
- **Testing**: Use the existing logs (under `logs/`) to trace agent runs. Frontend console logs show loaded tools and agents.

---

We hope this guide helps you quickly onboard and extend Agentic with your own AI workflows! Feel free to explore the `docs/` folder for the scrumbled ammount of prompts and informations I gathered for this project.