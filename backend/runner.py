import os
import importlib
from fastapi import WebSocket
from schemas import AgentConfig, ToolDefinition

# Assuming autogen v0.5.3 structure might differ, adjust imports if needed
# Placeholder imports, replace with actual AutoGen v0.5.3+ imports
# from autogen import Agent, ConversableAgent # Example
# from autogen.llm import ... # Example

# Mock AutoGen classes/functions for structure - REPLACE WITH ACTUAL AUTOGEN IMPORTS
class MockLLM:
  def __init__(self, api_key, model):
    self.api_key = api_key
    self.model = model

class MockAgent:
  def __init__(self, name, llm, tools, system_message, human_message, max_turns):
    self.name = name
    self.llm = llm
    self.tools = tools
    self.system_message = system_message
    self.human_message = human_message
    self.max_turns = max_turns
    print(f"MockAgent '{self.name}' initialized.")

  async def stream(self):
    print(f"Streaming mock events for agent '{self.name}'...")
    for i in range(self.max_turns):
      yield {"event_type": "mock_turn", "turn": i + 1, "message": f"Mock message {i + 1}"}
    yield {"event_type": "mock_end", "message": "Mock run finished."}

def create_openai_llm(api_key, model):
  print(f"Creating mock OpenAI LLM (model: {model})")
  return MockLLM(api_key=api_key, model=model)

def create_anthropic_llm(api_key, model):
  print(f"Creating mock Anthropic LLM (model: {model})")
  return MockLLM(api_key=api_key, model=model)

def create_gemini_llm(api_key, model):
  # Assuming gemini-sdk provides a similar function
  print(f"Creating mock Gemini LLM (model: {model})")
  return MockLLM(api_key=api_key, model=model)

async def run_agent_ws(agent_cfg: AgentConfig, tools: list[ToolDefinition], websocket: WebSocket):
  # Build tool instances
  tool_funcs = {}
  for t in tools:
    if t.name in agent_cfg.tools:
      try:
        # Dynamically import the tool function
        module = importlib.import_module(f"tools.{t.name}")
        tool_funcs[t.name] = getattr(module, t.name)
        print(f"Loaded tool: {t.name}")
      except (ModuleNotFoundError, AttributeError) as e:
        print(f"Warning: Could not load tool '{t.name}': {e}")
        await websocket.send_json({"error": f"Could not load tool '{t.name}'"})
        # Decide if you want to proceed without the tool or close
        # await websocket.close(code=1011) # Internal Error
        # return

  # Select LLM
  key = None
  llm = None
  prov = agent_cfg.llm.provider.lower()
  try:
    if prov == 'openai':
      key = os.getenv('OPENAI_API_KEY')
      if not key:
        raise ValueError("OPENAI_API_KEY not set in environment")
      llm = create_openai_llm(api_key=key, model=agent_cfg.llm.model)
    elif prov == 'anthropic':
      key = os.getenv('ANTHROPIC_API_KEY')
      if not key:
        raise ValueError("ANTHROPIC_API_KEY not set in environment")
      llm = create_anthropic_llm(api_key=key, model=agent_cfg.llm.model)
    elif prov == 'gemini':
      key = os.getenv('GEMINI_API_KEY')
      if not key:
        raise ValueError("GEMINI_API_KEY not set in environment")
      # Ensure the gemini-sdk provides create_gemini_llm or similar
      llm = create_gemini_llm(api_key=key, model=agent_cfg.llm.model)
    else:
      raise ValueError(f"Unsupported LLM provider: {prov}")
  except Exception as e:
    print(f"Error creating LLM: {e}")
    await websocket.send_json({"error": f"LLM configuration error: {e}"})
    await websocket.close(code=1011)
    return

  if not llm:
    print("LLM could not be initialized.")
    await websocket.send_json({"error": "LLM could not be initialized."})
    await websocket.close(code=1011)
    return

  # Instantiate agent (Using MockAgent - REPLACE WITH ACTUAL AUTOGEN AGENT)
  try:
    # Replace MockAgent with the actual AutoGen agent class
    agent = MockAgent(
      name=agent_cfg.name,
      llm=llm,
      tools=list(tool_funcs.values()),  # Pass loaded functions
      system_message=agent_cfg.prompt.system,
      human_message=agent_cfg.prompt.user,  # Check if AutoGen uses this directly
      max_turns=agent_cfg.max_turns
    )
  except Exception as e:
    print(f"Error instantiating agent: {e}")
    await websocket.send_json({"error": f"Agent instantiation error: {e}"})
    await websocket.close(code=1011)
    return

  # Stream events
  try:
    async for evt in agent.stream():
      # Assuming evt has a to_dict() method or is directly serializable
      if hasattr(evt, 'to_dict'):
        await websocket.send_json(evt.to_dict())
      else:
        await websocket.send_json(evt)  # Send the mock dict directly
  except Exception as e:
    print(f"Error during agent run: {e}")
    try:
      await websocket.send_json({"error": f"Runtime error: {e}"})
    except Exception:
      pass  # Websocket might already be closed
  finally:
    # Ensure websocket is closed if not already
    try:
      await websocket.close()
      print(f"Websocket closed for agent run '{agent_cfg.name}'")
    except Exception:
      pass  # Ignore if already closed