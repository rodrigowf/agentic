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

# Start the FastAPI server (with auto-reload)
uvicorn main:app --reload --port 8000
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