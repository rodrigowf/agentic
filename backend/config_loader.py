import os, importlib.util, json
from typing import List
from schemas import ToolDefinition, AgentConfig

def load_tools(tools_dir: str) -> List[ToolDefinition]:
    tools = []
    os.makedirs(tools_dir, exist_ok=True) # Ensure tools dir exists
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