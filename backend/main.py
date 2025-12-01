from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File, Body, Path
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import re
import inspect  # Added inspect
import asyncio  # Added asyncio
import google.generativeai as genai
from openai import OpenAI
# Updated imports: Use ToolInfo for API, FunctionTool internally
from config.schemas import AgentConfig, ToolInfo, GenerateToolRequest, VoiceConfig
# Updated imports: load_tools now returns List[Tuple[FunctionTool, str]]
# Add get_tool_infos helper and voice configuration functions
from config.config_loader import (
    load_tools, load_agents, save_agent, save_tool, get_tool_infos, _get_tool_schema,
    load_voice_configs, load_voice_config, save_voice_config, delete_voice_config,
    load_voice_prompts, load_voice_prompt, save_voice_prompt, delete_voice_prompt
)
from core.runner import run_agent_ws
from autogen_core.tools import FunctionTool  # Import FunctionTool
import logging  # Add logging import
from starlette.websockets import WebSocketState, WebSocketDisconnect  # Import WebSocketState and WebSocketDisconnect
from datetime import datetime  # Import datetime
import anthropic  # Import Anthropic client
from api.claude_code_controller import ClaudeCodeSession  # Import Claude Code controller
from api.webrtc_signaling import handle_webrtc_signaling  # Import WebRTC signaling handler

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found in environment. Tool generation will not work.")

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS to allow local development and mobile access
# Dynamically allow network IP for mobile devices on same network
cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
]

# Allow any 192.168.x.x network addresses (common home networks)
# This enables mobile devices on the same WiFi to connect
import socket
try:
    # Get local network IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    if local_ip and local_ip.startswith("192.168."):
        cors_origins.append(f"http://{local_ip}:3000")
        logger.info(f"Added CORS origin for network IP: http://{local_ip}:3000")
except Exception as e:
    logger.warning(f"Could not detect local IP for CORS: {e}")

# Also allow pattern-based origins for flexibility
# Support both HTTP and HTTPS (HTTPS required for mobile getUserMedia)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}):300[0-9]",  # Allow HTTP/HTTPS, ports 3000-3009
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount realtime voice router under /api/realtime
try:
    # Prefer relative import when running as package (uvicorn backend.main:app)
    from .api.realtime_voice import router as realtime_router  # type: ignore
except Exception:
    try:
        # Fallback to absolute if executed differently
        from api.realtime_voice import router as realtime_router  # type: ignore
    except Exception as e:
        realtime_router = None
        logger.warning(f"Failed to import realtime voice router: {e}")

if realtime_router is not None:
    app.include_router(realtime_router, prefix="/api/realtime")
    logger.info("Realtime voice router mounted at /api/realtime")

# Startup cache
TOOLS_DIR = "tools"
AGENTS_DIR = "agents"
VOICE_CONFIGS_DIR = "voice_configs"
VOICE_PROMPTS_DIR = "voice_prompts"

# Ensure directories exist at startup
os.makedirs(TOOLS_DIR, exist_ok=True)
os.makedirs(AGENTS_DIR, exist_ok=True)
os.makedirs(VOICE_CONFIGS_DIR, exist_ok=True)
os.makedirs(VOICE_PROMPTS_DIR, exist_ok=True)

# Load tools returns (FunctionTool, filename) tuples
LOADED_TOOLS_WITH_FILENAMES = load_tools(TOOLS_DIR)
AGENTS = load_agents(AGENTS_DIR)

# --- Model Endpoints ---

@app.get("/api/models/{provider}")
def get_models_by_provider(provider: str):
    """Fetch available models from the specified provider."""
    try:
        if provider.lower() == "openai":
            # Get OpenAI models
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                raise HTTPException(status_code=400, detail="OPENAI_API_KEY not configured")
            client = OpenAI()
            models = [model.id for model in client.models.list()]
            return {"models": models}
            
        elif provider.lower() == "gemini":
            # Get Google Gemini models
            gemini_key = os.getenv('GEMINI_API_KEY')
            if not gemini_key:
                raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured")
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # Clean up model names (remove prefix)
            models = [m.split('/')[-1] for m in models]
            return {"models": models}
            
        elif provider.lower() == "anthropic":
            # Get Anthropic models
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if not anthropic_key:
                raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not configured")
            
            # Anthropic doesn't provide a list API, so return the known models
            models = ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
            return {"models": models}
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}")

# --- Tool Endpoints ---

@app.get("/api/tools", response_model=list[ToolInfo])
def list_all_tools():
    # Reload from disk and convert to ToolInfo for the API response
    global LOADED_TOOLS_WITH_FILENAMES
    LOADED_TOOLS_WITH_FILENAMES = load_tools(TOOLS_DIR)
    return get_tool_infos(LOADED_TOOLS_WITH_FILENAMES)

# GET /api/tools/{filename} - Keep for fetching raw file content
@app.get("/api/tools/content/{filename}", response_class=PlainTextResponse)
async def get_tool_file_content(filename: str):
    if not re.fullmatch(r"[a-zA-Z0-9_]+\.py", filename) or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    filepath = os.path.join(TOOLS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Tool file not found")
    try:
        with open(filepath, "r") as f:
            content = f.read()
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

# PUT /api/tools/{filename} - Keep for saving raw file content
@app.put("/api/tools/content/{filename}", status_code=204)
async def save_tool_file_content(filename: str, content: str = Body(...)):
    if not re.fullmatch(r"[a-zA-Z0-9_]+\.py", filename) or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    try:
        save_tool(TOOLS_DIR, filename, content.encode('utf-8'))
        # Reload tools cache after saving
        global LOADED_TOOLS_WITH_FILENAMES
        LOADED_TOOLS_WITH_FILENAMES = load_tools(TOOLS_DIR)
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

@app.post("/api/tools/upload", response_model=list[ToolInfo])
async def upload_tool(file: UploadFile = File(...)):
    filename = file.filename
    if not filename or not filename.endswith(".py") or not re.fullmatch(r"[a-zA-Z0-9_]+\.py", filename) or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid or disallowed filename")

    content = await file.read()
    try:
        save_tool(TOOLS_DIR, filename, content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving uploaded file: {e}")

    # Reload all tools
    global LOADED_TOOLS_WITH_FILENAMES
    LOADED_TOOLS_WITH_FILENAMES = load_tools(TOOLS_DIR)

    # Find ToolInfo originating from the newly uploaded file
    newly_loaded_tool_infos = [
        ToolInfo(name=t.name, description=t.description, parameters=_get_tool_schema(t), filename=f)
        for t, f in LOADED_TOOLS_WITH_FILENAMES if f == filename
    ]

    if not newly_loaded_tool_infos:
        print(f"Warning: Uploaded file '{filename}' saved but no FunctionTool instances were loaded from it.")

    return newly_loaded_tool_infos

@app.post("/api/tools/generate", response_class=PlainTextResponse)
async def generate_tool_code(request: GenerateToolRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured on the server.")

    model_name = "gemini-1.5-pro-latest"  # Use a capable model
    print(f"Generating tool code using model: {model_name} for prompt: '{request.prompt[:50]}...'")

    # Updated Prompt Instructions for FunctionTool
    generation_prompt = f"""
    Generate Python code for an AutoGen v0.5.3+ compatible tool file based on the following request.
    The file can contain one or more tool definitions using FunctionTool.

    Request: "{request.prompt}"

    The generated Python code MUST:
    1. Be a single, complete Python script.
    2. Import necessary libraries (e.g., `typing`, `pydantic` for input models if needed).
    3. Import `FunctionTool` from `autogen_core.tools`.
    4. Define the tool logic within one or more Python functions.
    5. Each tool function MUST have:
        - Type annotations for ALL arguments.
        - A type annotation for the return value.
        - A clear docstring explaining what the function does, its arguments, and what it returns. This description is used by the LLM.
    6. For EACH tool function defined, create an instance of `FunctionTool` like this:
       ```python
       my_tool_instance = FunctionTool(
           func=my_tool_function,
           description="A concise description of what the tool does and when to use it."
           # The 'name' will default to the function name ('my_tool_function')
           # The parameter schema is automatically generated from type hints and docstring.
       )
       ```
    7. If a tool function requires complex input parameters, define a Pydantic `BaseModel` for those inputs and use it as the type hint for the corresponding argument in the function signature. `FunctionTool` will use this model to generate the schema.
       Example:
       ```python
       from pydantic import BaseModel, Field

       class MyInputModel(BaseModel):
           param1: str = Field(description="Description of param1")
           param2: int = Field(default=0, description="Description of param2")

       def my_tool_function_with_model(inputs: MyInputModel) -> str:
           # Docstring here...
           # ... function logic using inputs.param1, inputs.param2 ...
           return "result"

       my_tool_instance = FunctionTool(func=my_tool_function_with_model, description="...")
       ```
    8. You can define multiple functions and multiple `FunctionTool` instances in the same file. Make sure each instance is assigned to a variable so it can be discovered.
    9. Only output the raw Python code, without any introductory text, explanations, or markdown formatting like ```python ... ```.
    """

    try:
        model = genai.GenerativeModel(model_name)
        safety_settings = {
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
        }
        response = await model.generate_content_async(
            generation_prompt,
            safety_settings=safety_settings
        )

        if not response.parts:
            print("Warning: Gemini response was empty or blocked.")
            block_reason = response.prompt_feedback.block_reason if response.prompt_feedback else 'Unknown'
            raise HTTPException(status_code=400, detail=f"Generation failed. The response was empty or blocked (Reason: {block_reason}). Try rephrasing your prompt.")

        generated_code = response.text
        generated_code = re.sub(r"^```python\n?", "", generated_code, flags=re.MULTILINE)
        generated_code = re.sub(r"\n?```$", "", generated_code, flags=re.MULTILINE)

        print(f"Successfully generated code snippet starting with: {generated_code[:100]}...")
        return generated_code.strip()

    except Exception as e:
        print(f"Error generating tool code with Gemini: {e}")
        error_detail = str(e)
        status_code = 500
        if "API key" in error_detail:
            status_code = 401
        elif "quota" in error_detail.lower():
            status_code = 429
        raise HTTPException(status_code=status_code, detail=f"Failed to generate tool code: {error_detail}")

# --- Agent Endpoints ---

@app.get("/api/agents", response_model=list[AgentConfig])
def list_agents():
    # Reload agents from disk
    global AGENTS
    AGENTS = load_agents(AGENTS_DIR)
    return AGENTS

@app.post("/api/agents", response_model=AgentConfig)
def create_agent(cfg: AgentConfig):
    # Reload agents to prevent race condition if multiple requests happen
    global AGENTS
    AGENTS = load_agents(AGENTS_DIR)
    if any(a.name == cfg.name for a in AGENTS):
        raise HTTPException(400, "Agent with this name already exists")
    AGENTS.append(cfg)
    save_agent(cfg, AGENTS_DIR)
    return cfg

@app.put("/api/agents/{agent_name}", response_model=AgentConfig)
def update_agent(agent_name: str, cfg: AgentConfig):
    # Reload agents to ensure we have the latest list
    global AGENTS
    AGENTS = load_agents(AGENTS_DIR)
    found = False
    for i, a in enumerate(AGENTS):
        if a.name == agent_name:
            # Ensure the name in the path matches the name in the body
            if cfg.name != agent_name:
                raise HTTPException(status_code=400, detail=f"Agent name in path ({agent_name}) does not match name in body ({cfg.name})")
            AGENTS[i] = cfg
            save_agent(cfg, AGENTS_DIR)
            found = True
            break
    if not found:
        raise HTTPException(404, "Agent not found")
    return cfg

# --- Voice Configuration Endpoints ---

@app.get("/api/voice-configs", response_model=list[VoiceConfig])
def list_voice_configs():
    """List all voice configurations."""
    return load_voice_configs(VOICE_CONFIGS_DIR)

@app.get("/api/voice-configs/{config_name}", response_model=VoiceConfig)
def get_voice_config(config_name: str):
    """Get a specific voice configuration."""
    config = load_voice_config(VOICE_CONFIGS_DIR, config_name)
    if not config:
        raise HTTPException(404, f"Voice configuration '{config_name}' not found")
    return config

@app.post("/api/voice-configs", response_model=VoiceConfig)
def create_voice_config(cfg: VoiceConfig):
    """Create or update a voice configuration."""
    save_voice_config(cfg, VOICE_CONFIGS_DIR)
    return cfg

@app.put("/api/voice-configs/{config_name}", response_model=VoiceConfig)
def update_voice_config(config_name: str, cfg: VoiceConfig):
    """Update a voice configuration."""
    if cfg.name != config_name:
        raise HTTPException(400, f"Config name in path ({config_name}) does not match name in body ({cfg.name})")
    save_voice_config(cfg, VOICE_CONFIGS_DIR)
    return cfg

@app.delete("/api/voice-configs/{config_name}")
def delete_voice_config_endpoint(config_name: str):
    """Delete a voice configuration."""
    if config_name == "default":
        raise HTTPException(400, "Cannot delete the default configuration")
    success = delete_voice_config(VOICE_CONFIGS_DIR, config_name)
    if not success:
        raise HTTPException(404, f"Voice configuration '{config_name}' not found")
    return {"message": f"Voice configuration '{config_name}' deleted"}

@app.get("/api/voice-prompts")
def list_voice_prompt_files():
    """List all available voice prompt files."""
    files = load_voice_prompts(VOICE_PROMPTS_DIR)
    return {"prompts": files}

@app.get("/api/voice-prompts/{filename}", response_class=PlainTextResponse)
def get_voice_prompt(filename: str):
    """Get the content of a voice prompt file."""
    content = load_voice_prompt(VOICE_PROMPTS_DIR, filename)
    if content is None:
        raise HTTPException(404, f"Voice prompt '{filename}' not found")
    return content

@app.post("/api/voice-prompts/{filename}")
def save_voice_prompt_endpoint(filename: str, content: str = Body(..., media_type="text/plain")):
    """Save a voice prompt file."""
    save_voice_prompt(VOICE_PROMPTS_DIR, filename, content)
    return {"message": f"Voice prompt '{filename}' saved"}

@app.delete("/api/voice-prompts/{filename}")
def delete_voice_prompt_endpoint(filename: str):
    """Delete a voice prompt file."""
    if filename == "default.txt":
        raise HTTPException(400, "Cannot delete the default prompt")
    success = delete_voice_prompt(VOICE_PROMPTS_DIR, filename)
    if not success:
        raise HTTPException(404, f"Voice prompt '{filename}' not found")
    return {"message": f"Voice prompt '{filename}' deleted"}

# --- WebSocket Helper Function ---
async def send_event_to_websocket(websocket: WebSocket, event_type: str, data: dict):
    if websocket.client_state == WebSocketState.CONNECTED:
        try:
            payload = {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            await websocket.send_json(payload)
        except Exception as e:
            logger.error(f"Failed to send event '{event_type}' via WebSocket: {e}")
    else:
        logger.warning(f"Attempted to send event '{event_type}' but WebSocket was not connected.")

@app.websocket("/api/runs/ClaudeCode")
async def run_claude_code_ws(websocket: WebSocket):
    """WebSocket endpoint for Claude Code self-editor."""
    await websocket.accept()
    logger.info("Claude Code WebSocket connection accepted")

    session: ClaudeCodeSession | None = None

    try:
        # Initialize Claude Code session
        working_dir = os.path.abspath(os.path.dirname(__file__) + "/..")  # Project root
        session = ClaudeCodeSession(
            working_dir=working_dir,
            model="claude-sonnet-4-5-20250929",
            permission_mode="bypassPermissions",  # Bypass permissions for voice assistant
        )
        await session.start()

        # Send initial connection event
        await send_event_to_websocket(websocket, "system", {
            "message": "Claude Code session initialized",
            "working_dir": working_dir,
        })

        # Background task for streaming Claude Code events
        async def stream_claude_events():
            try:
                async for event in session.stream_events():
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(event)
                    else:
                        break
            except Exception as e:
                logger.error(f"Error streaming Claude Code events: {e}")
                if websocket.client_state == WebSocketState.CONNECTED:
                    await send_event_to_websocket(websocket, "error", {
                        "message": f"Claude Code stream error: {str(e)}"
                    })

        stream_task = asyncio.create_task(stream_claude_events())

        # Listen for commands from the client
        while websocket.client_state == WebSocketState.CONNECTED:
            try:
                cmd = await websocket.receive_json()
                cmd_type = (cmd.get("type") or "").lower()

                if cmd_type == "user_message":
                    message = (cmd.get("data") or "").strip()
                    if message:
                        await session.send_message(message)
                        await send_event_to_websocket(websocket, "system", {
                            "message": f"Sent message to Claude Code: {message[:100]}..."
                        })
                    else:
                        await send_event_to_websocket(websocket, "system", {
                            "message": "Ignored empty user_message."
                        })

                elif cmd_type == "cancel":
                    await session.cancel()
                    await send_event_to_websocket(websocket, "system", {
                        "message": "Cancellation signal sent to Claude Code"
                    })

                else:
                    await send_event_to_websocket(websocket, "error", {
                        "message": f"Unknown command type: {cmd_type}"
                    })

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing Claude Code command: {e}")
                await send_event_to_websocket(websocket, "error", {
                    "message": f"Error: {str(e)}"
                })

        # Wait for stream task to complete
        if not stream_task.done():
            stream_task.cancel()
            try:
                await stream_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info("Claude Code WebSocket disconnected by client")
    except Exception as e:
        logger.exception(f"Error in Claude Code WebSocket handler: {e}")
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await send_event_to_websocket(websocket, "error", {
                    "message": f"Claude Code session error: {str(e)}"
                })
        except Exception:
            pass
    finally:
        if session:
            await session.stop()
        logger.info("Claude Code WebSocket connection closing")
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
        except Exception as e:
            logger.warning(f"Error closing Claude Code WebSocket: {e}")

@app.websocket("/api/runs/{agent_name}")
async def run_ws(websocket: WebSocket, agent_name: str = Path(...)):
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for agent: {agent_name}")
    try:
        # Reload agents and tools for the specific run to ensure freshness
        logger.info("Reloading agents and tools for the run...")
        current_agents = load_agents(AGENTS_DIR)
        current_tools_with_filenames = load_tools(TOOLS_DIR)
        current_tools: list[FunctionTool] = [t for t, f in current_tools_with_filenames]
        logger.info(f"Found {len(current_tools)} tools.")

        agent_config = next((a for a in current_agents if a.name == agent_name), None)

        if not agent_config:
            logger.error(f"Agent '{agent_name}' configuration not found.")
            await send_event_to_websocket(websocket, "error", {"message": f"Agent '{agent_name}' configuration not found."})
            await websocket.close(code=1003)
            return

        logger.info(f"Found agent config for '{agent_name}'. Starting agent run...")
        await run_agent_ws(agent_config, current_tools, websocket)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client for agent: {agent_name}")
    except Exception as e:
        logger.exception(f"Unhandled exception during WebSocket run for agent '{agent_name}': {e}")
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await send_event_to_websocket(websocket, "error", {"message": f"Server error during agent run: {str(e)}"})
        except Exception as send_err:
            logger.error(f"Failed to send error details over WebSocket: {send_err}")
    finally:
        logger.info(f"WebSocket connection closing or closed for agent: {agent_name}")
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
                logger.info(f"WebSocket connection explicitly closed for agent: {agent_name}")
        except RuntimeError as re:
            if "WebSocket is not connected" not in str(re) and "Cannot call 'close'" not in str(re):
                logger.warning(f"Error closing WebSocket (might be already closed): {re}")
        except Exception as e:
            logger.warning(f"Unexpected error closing WebSocket: {e}")

@app.websocket("/api/webrtc-signal/{conversation_id}")
async def webrtc_signaling_ws(websocket: WebSocket, conversation_id: str):
    """
    WebRTC signaling WebSocket endpoint for peer-to-peer audio connections

    Handles:
    - Peer registration
    - SDP offer/answer exchange
    - ICE candidate exchange
    """
    await handle_webrtc_signaling(websocket, conversation_id)

# --- Server Management Endpoints ---

@app.post("/api/server/refresh")
async def refresh_service():
    """
    Refresh the agentic service by:
    1. Pulling latest changes from git
    2. Building the frontend
    3. Restarting the systemd service
    """
    try:
        import subprocess

        # Get the project root directory
        project_root = os.path.abspath(os.path.dirname(__file__) + "/..")

        logger.info("Starting service refresh...")

        # Step 1: Pull latest changes
        logger.info("Pulling latest git changes...")
        pull_result = subprocess.run(
            ["git", "pull"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if pull_result.returncode != 0:
            logger.error(f"Git pull failed: {pull_result.stderr}")
            return {
                "success": False,
                "error": f"Git pull failed: {pull_result.stderr}",
                "step": "git_pull"
            }

        # Step 2: Build frontend
        logger.info("Building frontend...")
        frontend_dir = os.path.join(project_root, "frontend")
        build_result = subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout for build
        )

        if build_result.returncode != 0:
            logger.error(f"Frontend build failed: {build_result.stderr}")
            return {
                "success": False,
                "error": f"Frontend build failed: {build_result.stderr}",
                "step": "frontend_build"
            }

        # Step 3: Restart systemd service (if running as service)
        logger.info("Restarting agentic-backend service...")
        restart_result = subprocess.run(
            ["sudo", "systemctl", "restart", "agentic-backend"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if restart_result.returncode != 0:
            logger.warning(f"Service restart failed (may not be running as systemd service): {restart_result.stderr}")
            # Don't fail the whole operation if service restart fails
            # The service might not be running via systemd

        logger.info("Service refresh completed successfully")
        return {
            "success": True,
            "message": "Service refreshed successfully",
            "git_output": pull_result.stdout,
            "build_output": build_result.stdout[:500] + "..." if len(build_result.stdout) > 500 else build_result.stdout
        }

    except subprocess.TimeoutExpired as e:
        logger.error(f"Operation timed out: {e}")
        return {
            "success": False,
            "error": f"Operation timed out: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Error refreshing service: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/server/push")
async def push_changes():
    """
    Push local changes to git repository:
    1. Stage all changes
    2. Commit with timestamp
    3. Push to remote
    """
    try:
        import subprocess
        from datetime import datetime

        # Get the project root directory
        project_root = os.path.abspath(os.path.dirname(__file__) + "/..")

        logger.info("Starting git push operation...")

        # Step 1: Stage all changes
        logger.info("Staging all changes...")
        add_result = subprocess.run(
            ["git", "add", "-A"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if add_result.returncode != 0:
            logger.error(f"Git add failed: {add_result.stderr}")
            return {
                "success": False,
                "error": f"Git add failed: {add_result.stderr}",
                "step": "git_add"
            }

        # Step 2: Check if there are changes to commit
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if not status_result.stdout.strip():
            logger.info("No changes to commit")
            return {
                "success": True,
                "message": "No changes to commit",
                "pushed": False
            }

        # Step 3: Commit changes with timestamp
        commit_message = f"Auto-commit from server: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        logger.info(f"Committing changes: {commit_message}")
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if commit_result.returncode != 0:
            logger.error(f"Git commit failed: {commit_result.stderr}")
            return {
                "success": False,
                "error": f"Git commit failed: {commit_result.stderr}",
                "step": "git_commit"
            }

        # Step 4: Push to remote
        logger.info("Pushing to remote...")
        push_result = subprocess.run(
            ["git", "push"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )

        if push_result.returncode != 0:
            logger.error(f"Git push failed: {push_result.stderr}")
            return {
                "success": False,
                "error": f"Git push failed: {push_result.stderr}",
                "step": "git_push"
            }

        logger.info("Git push completed successfully")
        return {
            "success": True,
            "message": "Changes pushed successfully",
            "pushed": True,
            "commit_message": commit_message,
            "push_output": push_result.stdout
        }

    except subprocess.TimeoutExpired as e:
        logger.error(f"Operation timed out: {e}")
        return {
            "success": False,
            "error": f"Operation timed out: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Error pushing changes: {e}")
        return {
            "success": False,
            "error": str(e)
        }