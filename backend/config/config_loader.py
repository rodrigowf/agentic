import os, importlib.util, json, inspect
from typing import List, Tuple, Dict, Any, Optional
from config.schemas import AgentConfig, ToolInfo, VoiceConfig
from autogen_core.tools import FunctionTool

# Function to extract schema from FunctionTool (simplified)
def _get_tool_schema(tool: FunctionTool) -> Dict[str, Any]:
    # FunctionTool often exposes schema via methods like .openai_schema or similar
    # This is a placeholder, actual method might differ based on autogen-core version
    if hasattr(tool, 'openai_schema'):
        return tool.openai_schema
    # Fallback or simplified representation if schema method isn't available/stable
    # Inspecting the function signature could be an alternative
    return {"parameters": {"type": "object", "properties": {}}} # Basic fallback

def load_tools(tools_dir: str) -> List[Tuple[FunctionTool, str]]:
    """Loads FunctionTool instances and their source filenames."""
    print(f"--- Loading tools from directory: {tools_dir} ---") # LOGGING START
    tools_with_filenames: List[Tuple[FunctionTool, str]] = []
    os.makedirs(tools_dir, exist_ok=True) # Ensure tools dir exists
    try:
        file_list = os.listdir(tools_dir)
        print(f"Found files/dirs: {file_list}") # LOGGING
    except Exception as e:
        print(f"Error listing directory {tools_dir}: {e}")
        return []

    for fname in file_list:
        if fname.endswith('.py') and fname != '__init__.py':
            module_name = fname[:-3]
            file_path = os.path.join(tools_dir, fname)
            print(f"Attempting to load module: {module_name} from {file_path}") # LOGGING
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader: # Check if spec and loader are valid
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    print(f"  Successfully executed module: {module_name}") # LOGGING

                    # Iterate through all members of the loaded module
                    found_tools_in_file = 0 # LOGGING
                    for name, obj in inspect.getmembers(mod):
                        # Look for FunctionTool instances
                        if isinstance(obj, FunctionTool):
                            print(f"    Found FunctionTool instance: '{name}' in {fname}") # LOGGING
                            # FunctionTool already links the function
                            tools_with_filenames.append((obj, fname))
                            found_tools_in_file += 1 # LOGGING
                    if found_tools_in_file == 0:
                         print(f"  No FunctionTool instances found in {fname}") # LOGGING
                else:
                    print(f"Warning: Could not create spec for module '{module_name}' from '{fname}'. Skipping.")

            except Exception as e:
                print(f"Warning: Failed to load tools from '{fname}': {e}")

    if not tools_with_filenames:
         print(f"--- No valid FunctionTool instances found in '{tools_dir}'. ---") # LOGGING
    else:
         tool_names = [t.name for t, f in tools_with_filenames]
         print(f"--- Finished loading tools. Found: {tool_names} ---") # LOGGING
    return tools_with_filenames

def save_tool(tools_dir: str, filename: str, content: bytes):
    os.makedirs(tools_dir, exist_ok=True)
    path = os.path.join(tools_dir, filename)
    with open(path, 'wb') as f:
        f.write(content)

def load_agents(agents_dir: str) -> List[AgentConfig]:
    agents: List[AgentConfig] = []
    os.makedirs(agents_dir, exist_ok=True)
    for fname in os.listdir(agents_dir):
        if not fname.endswith('.json'):
            continue
        try:
            path = os.path.join(agents_dir, fname)
            with open(path) as f:
                data = json.load(f)
            # For nested_team, expand sub_agents list of filenames to full configs
            if data.get('agent_type') == 'nested_team' and isinstance(data.get('sub_agents'), list):
                names = data['sub_agents']
                expanded: List[AgentConfig] = []
                for item in names:
                    if isinstance(item, str):
                        sub_path = os.path.join(agents_dir, f"{item}.json")
                        try:
                            with open(sub_path) as sf:
                                sub_data = json.load(sf)
                            expanded.append(AgentConfig(**sub_data))
                        except Exception as e:
                            print(f"Warning: Could not load sub-agent '{item}': {e}")
                    elif isinstance(item, dict):
                        expanded.append(AgentConfig(**item))
                data['sub_agents'] = expanded
            agents.append(AgentConfig(**data))
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {fname}")
        except Exception as e:
            print(f"Warning: Could not load agent from {fname}: {e}")
    return agents

def save_agent(cfg: AgentConfig, agents_dir: str):
    path = os.path.join(agents_dir, f"{cfg.name}.json")
    if cfg.agent_type == 'nested_team' and cfg.sub_agents:
        # Only save filenames (agent names) for sub_agents to avoid redundancy
        data = cfg.model_dump()
        data['sub_agents'] = [sub.name for sub in cfg.sub_agents]
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        with open(path, 'w') as f:
            f.write(cfg.model_dump_json(indent=2))

def get_tool_infos(loaded_tools: List[Tuple[FunctionTool, str]]) -> List[ToolInfo]:
    """Converts loaded FunctionTools into ToolInfo for API responses."""
    tool_infos = []
    for tool, filename in loaded_tools:
        tool_infos.append(ToolInfo(
            name=tool.name,
            description=tool.description,
            parameters=_get_tool_schema(tool), # Get schema from FunctionTool
            filename=filename
        ))
    return tool_infos

# Voice Configuration Functions

def load_voice_configs(voice_configs_dir: str) -> List[VoiceConfig]:
    """Load all voice configurations from the voice_configs directory."""
    configs: List[VoiceConfig] = []
    os.makedirs(voice_configs_dir, exist_ok=True)
    for fname in os.listdir(voice_configs_dir):
        if not fname.endswith('.json'):
            continue
        try:
            path = os.path.join(voice_configs_dir, fname)
            with open(path) as f:
                data = json.load(f)
            configs.append(VoiceConfig(**data))
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {fname}")
        except Exception as e:
            print(f"Warning: Could not load voice config from {fname}: {e}")
    return configs

def load_voice_config(voice_configs_dir: str, name: str) -> Optional[VoiceConfig]:
    """Load a specific voice configuration by name."""
    path = os.path.join(voice_configs_dir, f"{name}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return VoiceConfig(**data)
    except Exception as e:
        print(f"Error loading voice config '{name}': {e}")
        return None

def save_voice_config(cfg: VoiceConfig, voice_configs_dir: str):
    """Save a voice configuration."""
    os.makedirs(voice_configs_dir, exist_ok=True)
    path = os.path.join(voice_configs_dir, f"{cfg.name}.json")
    with open(path, 'w') as f:
        f.write(cfg.model_dump_json(indent=2))

def delete_voice_config(voice_configs_dir: str, name: str) -> bool:
    """Delete a voice configuration by name."""
    path = os.path.join(voice_configs_dir, f"{name}.json")
    if not os.path.exists(path):
        return False
    try:
        os.remove(path)
        return True
    except Exception as e:
        print(f"Error deleting voice config '{name}': {e}")
        return False

def load_voice_prompts(voice_prompts_dir: str) -> List[str]:
    """List all available voice prompt files."""
    os.makedirs(voice_prompts_dir, exist_ok=True)
    return [fname for fname in os.listdir(voice_prompts_dir) if fname.endswith(('.txt', '.md'))]

def load_voice_prompt(voice_prompts_dir: str, filename: str) -> Optional[str]:
    """Load the content of a voice prompt file."""
    path = os.path.join(voice_prompts_dir, filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading voice prompt '{filename}': {e}")
        return None

def save_voice_prompt(voice_prompts_dir: str, filename: str, content: str):
    """Save a voice prompt file."""
    os.makedirs(voice_prompts_dir, exist_ok=True)
    # Ensure filename ends with .txt or .md
    if not filename.endswith(('.txt', '.md')):
        filename = filename + '.txt'
    path = os.path.join(voice_prompts_dir, filename)
    with open(path, 'w') as f:
        f.write(content)

def delete_voice_prompt(voice_prompts_dir: str, filename: str) -> bool:
    """Delete a voice prompt file."""
    path = os.path.join(voice_prompts_dir, filename)
    if not os.path.exists(path):
        return False
    try:
        os.remove(path)
        return True
    except Exception as e:
        print(f"Error deleting voice prompt '{filename}': {e}")
        return False