import os, importlib.util, json, inspect
from typing import List, Tuple, Dict, Any
from schemas import AgentConfig, ToolInfo
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
    agents = []
    os.makedirs(agents_dir, exist_ok=True)
    for fname in os.listdir(agents_dir):
        if fname.endswith('.json'):
            try: # Add error handling for invalid JSON
                with open(os.path.join(agents_dir, fname)) as f:
                    data = json.load(f)
                    agents.append(AgentConfig(**data))
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {fname}")
            except Exception as e:
                 print(f"Warning: Could not load agent from {fname}: {e}")
    return agents

def save_agent(cfg: AgentConfig, agents_dir: str):
    os.makedirs(agents_dir, exist_ok=True)
    path = os.path.join(agents_dir, f"{cfg.name}.json")
    with open(path, 'w') as f:
        f.write(cfg.model_dump_json(indent=2)) # Use model_dump_json for Pydantic v2+

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