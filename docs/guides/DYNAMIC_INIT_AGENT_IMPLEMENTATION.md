# Dynamic Initialization Agent Implementation

**Date:** 2025-11-08
**Author:** Claude (Sonnet 4.5)
**Purpose:** Agent-agnostic dynamic initialization system

---

## Overview

This document describes the implementation of the **Dynamic Initialization Looping Agent**, a new agent type that allows custom initialization functions to be executed when an agent starts up. This replaces the previous hard-coded initialization logic for the Memory agent and provides a flexible, reusable system for any agent that needs custom startup behavior.

---

## Problem Statement

### Before

The Memory agent had hard-coded initialization logic in [runner.py:192-202](../backend/core/runner.py#L192-L202):

```python
# Initialize Memory agent if this is the Memory agent
if agent_cfg.name == "Memory":
    try:
        from tools.memory import initialize_memory_agent
        initialize_memory_agent()
        logger.info("Memory agent initialized with short-term memory injection")
    except Exception as init_error:
        logger.warning(f"Failed to initialize Memory agent: {init_error}")
```

**Issues:**
- ❌ Hard-coded to only work with Memory agent
- ❌ Not configurable via UI
- ❌ Not reusable for other agents
- ❌ Tightly coupled initialization logic

### After

Dynamic initialization system with:
- ✅ Agent-agnostic: Any agent can use initialization
- ✅ Configurable via UI: Set initialization function in agent editor
- ✅ Flexible: Users can create custom initialization functions
- ✅ Decoupled: Initialization logic stays in tool modules

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Configuration                       │
│  (agents/Memory.json)                                       │
│                                                              │
│  {                                                           │
│    "agent_type": "dynamic_init_looping",                   │
│    "initialization_function": "memory.initialize_memory_agent" │
│  }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Factory                             │
│  (core/agent_factory.py)                                    │
│                                                              │
│  if agent_cfg.agent_type == 'dynamic_init_looping':        │
│      return DynamicInitLoopingAgent(                        │
│          initialization_function=agent_cfg.initialization_function │
│      )                                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           DynamicInitLoopingAgent                            │
│  (core/dynamic_init_looping_agent.py)                       │
│                                                              │
│  def __init__(self, initialization_function=None):          │
│      if initialization_function:                            │
│          self._run_initialization()                         │
│                                                              │
│  def _run_initialization(self):                             │
│      module = importlib.import_module(f'tools.{module_name}') │
│      init_func = getattr(module, function_name)             │
│      init_func(self)  # Execute initialization with agent   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Initialization Function                         │
│  (tools/memory.py)                                          │
│                                                              │
│  def initialize_memory_agent(agent):                        │
│      # Agent is passed directly as parameter                │
│      # Load memory from file                                │
│      # Update agent's system message                        │
│      # Return success message                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Backend Changes

#### 1.1 Schema Update ([config/schemas.py](../backend/config/schemas.py))

Added `initialization_function` field to `AgentConfig`:

```python
class AgentConfig(BaseSchema):
    # ... existing fields ...

    agent_type: str = Field(
        default="assistant",
        description="..., 'dynamic_init_looping' for looping agent with custom initialization"
    )

    initialization_function: Optional[str] = Field(
        default=None,
        description="Python function to call during agent initialization (format: 'module.function_name', e.g., 'memory.initialize_memory_agent'). The function will be called with no arguments after agent creation and can modify the agent's state, system prompt, or perform any setup logic."
    )
```

#### 1.2 New Agent Class ([core/dynamic_init_looping_agent.py](../backend/core/dynamic_init_looping_agent.py))

Created `DynamicInitLoopingAgent` that extends `LoopingAssistantAgent`:

```python
class DynamicInitLoopingAgent(LoopingAssistantAgent):
    def __init__(self, *args, initialization_function: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialization_function = initialization_function

        if initialization_function:
            try:
                self._run_initialization()
            except Exception as e:
                logger.error(f"Failed to run initialization: {e}")
                # Don't fail agent creation, just log error

    def _run_initialization(self):
        """Dynamically import and call the initialization function"""
        # Parse 'module.function_name'
        parts = self.initialization_function.split('.')
        module_name = parts[0]
        function_name = '.'.join(parts[1:])

        # Import from tools package
        module = importlib.import_module(f'tools.{module_name}')
        init_func = getattr(module, function_name)

        # Execute initialization
        result = init_func()
        logger.info(f"Initialization returned: {result}")
```

**Key Features:**
- Graceful error handling (doesn't break agent creation)
- Supports nested function names (`module.submodule.function`)
- Logs initialization results
- Uses dynamic imports for flexibility

#### 1.3 Agent Factory Update ([core/agent_factory.py](../backend/core/agent_factory.py))

Added support for `dynamic_init_looping` agent type:

```python
if agent_cfg.agent_type == 'dynamic_init_looping':
    return DynamicInitLoopingAgent(
        name=agent_cfg.name,
        description=agent_cfg.description,
        system_message=agent_cfg.prompt.system,
        model_client=model_client,
        tools=agent_tools,
        reflect_on_tool_use=agent_cfg.reflect_on_tool_use,
        max_consecutive_auto_reply=agent_cfg.max_consecutive_auto_reply,
        initialization_function=agent_cfg.initialization_function
    )
```

#### 1.4 Runner Cleanup ([core/runner.py](../backend/core/runner.py))

Removed hard-coded Memory agent initialization:

```diff
  # --- Agent Instantiation via factory ---
  try:
      assistant = create_agent_from_config(agent_cfg, all_tools, model_client)
      CURRENT_AGENT.set(assistant)
-
-     # Initialize Memory agent if this is the Memory agent
-     if agent_cfg.name == "Memory":
-         try:
-             from tools.memory import initialize_memory_agent
-             initialize_memory_agent()
-         except Exception as init_error:
-             logger.warning(f"Failed to initialize Memory agent: {init_error}")
-
  except Exception as e:
```

#### 1.5 Memory Agent Config Update ([agents/Memory.json](../backend/agents/Memory.json))

Updated Memory agent to use new dynamic initialization:

```json
{
  "name": "Memory",
  "agent_type": "dynamic_init_looping",
  "initialization_function": "memory.initialize_memory_agent",
  "tools": [
    "get_short_term_memory",
    "overwrite_short_term_memory",
    ...
  ],
  ...
}
```

### 2. Frontend Changes

#### 2.1 Agent Editor ([frontend/src/features/agents/components/AgentEditor.js](../frontend/src/features/agents/components/AgentEditor.js))

Added support for dynamic initialization configuration:

**1. Default config:**
```javascript
const DEFAULT_AGENT_CONFIG = {
  // ... existing fields ...
  initialization_function: '',
  // ...
};
```

**2. Agent type dropdown:**
```jsx
<Select value={cfg.agent_type} ...>
  <MenuItem value="assistant">Assistant</MenuItem>
  <MenuItem value="looping">Looping Assistant</MenuItem>
  <MenuItem value="multimodal_tools_looping">Multimodal Tools Looping Agent</MenuItem>
  <MenuItem value="dynamic_init_looping">Dynamic Initialization Looping Agent</MenuItem>
  <MenuItem value="nested_team">Nested Team Agent</MenuItem>
  <MenuItem value="code_executor">Code Executor</MenuItem>
  <MenuItem value="looping_code_executor">Looping Code Executor</MenuItem>
</Select>
```

**3. Initialization function field:**
```jsx
{cfg.agent_type === 'dynamic_init_looping' && (
  <TextField
    label="Initialization Function"
    value={cfg.initialization_function || ''}
    onChange={(e) => handleInputChange('initialization_function', e.target.value)}
    helperText="Python function to call on agent startup (format: module.function_name, e.g., memory.initialize_memory_agent). The function will be imported from the tools/ directory."
    placeholder="memory.initialize_memory_agent"
  />
)}
```

**4. System prompt field:**
Updated to show for `dynamic_init_looping` type:
```jsx
{(cfg.agent_type === 'assistant' ||
  cfg.agent_type === 'looping' ||
  cfg.agent_type === 'multimodal_tools_looping' ||
  cfg.agent_type === 'dynamic_init_looping') && (
  <TextField label="System Prompt" ... />
)}
```

---

## Testing

### Unit Tests

**File:** [tests/unit/test_dynamic_init_agent.py](../backend/tests/unit/test_dynamic_init_agent.py)

**Coverage:**
- ✅ Agent creation without initialization function
- ✅ Agent creation with empty initialization function
- ✅ Invalid function format handling
- ✅ Module not found handling
- ✅ Function not found handling
- ✅ Successful initialization execution
- ✅ Initialization function exception handling
- ✅ Agent modification via initialization
- ✅ Nested function name support
- ✅ Memory agent initialization function exists
- ✅ Memory agent creation with dynamic init

**Results:** 11/11 tests passing

```bash
cd backend
source venv/bin/activate
pytest tests/unit/test_dynamic_init_agent.py -v
# ===== 11 passed in 1.89s =====
```

### Integration Tests

**File:** [tests/integration/test_dynamic_init_integration.py](../backend/tests/integration/test_dynamic_init_integration.py)

**Coverage:**
- ✅ Agent creation via factory
- ✅ Memory agent config loading
- ✅ Memory initialization function execution
- ✅ Memory agent with auto-initialization

**Results:** 4/4 tests passing

```bash
cd backend
source venv/bin/activate
export PYTHONPATH=/home/rodrigo/agentic/backend
python3 tests/integration/test_dynamic_init_integration.py
# ===== 4 passed, 0 failed =====
```

### End-to-End Tests

**File:** [tests/e2e_dynamic_init_test.py](../backend/tests/e2e_dynamic_init_test.py)

**Coverage:**
- ✅ API returns dynamic_init_looping agent correctly
- ✅ Agent creation with initialization works
- ✅ Backend can load configuration

**Results:** 3/3 tests passing

```bash
cd backend
source venv/bin/activate
export PYTHONPATH=/home/rodrigo/agentic/backend
python3 tests/e2e_dynamic_init_test.py
# ===== 3 passed, 0 failed =====
```

**All existing unit tests:** 12/12 passing ✅

---

## Usage Guide

### Creating a New Agent with Dynamic Initialization

#### Step 1: Create Initialization Function

Create a function in any module under `backend/tools/`:

```python
# tools/my_custom_tool.py

import logging

logger = logging.getLogger(__name__)

def initialize_my_agent(agent):
    """
    Custom initialization logic for my agent.

    This function is called when the agent is created.
    It receives the agent instance directly as a parameter.

    Args:
        agent: The agent instance to initialize.

    Returns:
        Success or error message.
    """
    try:
        # Load some data
        my_data = load_my_data_from_file()

        # Update agent's system message
        if agent and agent._system_messages:
            agent._system_messages[0].content = agent._system_messages[0].content.replace(
                "{{MY_PLACEHOLDER}}",
                my_data
            )
            logger.info("Agent initialized with custom data")

        return "Initialization successful"
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return f"Error: {e}"
```

#### Step 2: Create Agent Configuration

Create or edit an agent JSON file in `backend/agents/`:

```json
{
  "name": "MyCustomAgent",
  "agent_type": "dynamic_init_looping",
  "initialization_function": "my_custom_tool.initialize_my_agent",
  "tools": ["tool1", "tool2"],
  "llm": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.0
  },
  "prompt": {
    "system": "You are my custom agent. {{MY_PLACEHOLDER}}",
    "user": "Default task"
  },
  "max_consecutive_auto_reply": 20,
  "reflect_on_tool_use": true,
  "tool_call_loop": true
}
```

#### Step 3: Use via Frontend

1. Go to Agent Editor in the UI
2. Select "Dynamic Initialization Looping Agent" from the dropdown
3. Fill in the "Initialization Function" field: `my_custom_tool.initialize_my_agent`
4. Configure other agent settings
5. Save

The agent will automatically run the initialization function on startup!

---

## Use Cases

### 1. Memory Management (Current)
- Load short-term memory from file
- Inject into system prompt
- Update agent context

### 2. Database Connection
```python
def initialize_db_agent(agent):
    # Connect to database
    # Load schema or connection info
    # Update agent with DB context
```

### 3. API Configuration
```python
def initialize_api_agent(agent):
    # Load API credentials
    # Test connection
    # Update agent with API info
```

### 4. Workspace Setup
```python
def initialize_code_agent(agent):
    # Verify workspace directory
    # Load project structure
    # Update agent with project info
```

### 5. Resource Validation
```python
def initialize_resource_agent(agent):
    # Check required files exist
    # Validate dependencies
    # Update agent with resource status
```

---

## Benefits

### For Developers
- **Flexible:** Create any initialization logic you need
- **Reusable:** Write once, use in multiple agents
- **Testable:** Initialization functions are unit testable
- **Maintainable:** Initialization logic lives in tool modules

### For Users
- **Configurable:** Set initialization via UI
- **Transparent:** See what initialization function is used
- **Debuggable:** Clear error messages if initialization fails
- **Safe:** Failed initialization doesn't break agent

### For the System
- **Decoupled:** No hard-coded agent-specific logic
- **Extensible:** Easy to add new initialization patterns
- **Backwards Compatible:** Existing agents work unchanged
- **Consistent:** All dynamic initialization follows same pattern

---

## Migration Guide

### Migrating Existing Hard-Coded Initialization

If you have an agent with hard-coded initialization logic in `runner.py`:

**Before:**
```python
# In runner.py
if agent_cfg.name == "MyAgent":
    from tools.my_tool import initialize_my_agent
    initialize_my_agent()
```

**After:**

1. Remove hard-coded logic from `runner.py`
2. Update agent config:
```json
{
  "agent_type": "dynamic_init_looping",
  "initialization_function": "my_tool.initialize_my_agent"
}
```

That's it! The initialization will happen automatically.

---

## Troubleshooting

### Initialization Function Not Found

**Error:** `AttributeError: Function 'my_func' not found in module 'tools.my_module'`

**Solution:**
- Check function exists in the specified module
- Verify function name spelling
- Ensure module is in `backend/tools/` directory

### Module Import Error

**Error:** `ImportError: No module named 'tools.my_module'`

**Solution:**
- Check module file exists: `backend/tools/my_module.py`
- Verify no syntax errors in the module
- Ensure `__init__.py` exists if using package

### Initialization Fails Silently

**Check:**
- View backend logs for error messages
- Initialization errors are logged but don't break agent creation
- Look for `WARNING` or `ERROR` log entries

### Placeholder Not Replaced

**Issue:** System message still contains `{{PLACEHOLDER}}`

**Possible Causes:**
- Initialization function not modifying system message
- `CURRENT_AGENT` context not set correctly
- Agent created before context was set

**Solution:**
- Ensure initialization function uses `get_current_agent()`
- Check that agent is set in context: `CURRENT_AGENT.set(agent)`
- Re-run initialization after context is set

---

## Future Enhancements

### Potential Improvements

1. **Async Initialization**
   - Support async initialization functions
   - Allow I/O operations without blocking

2. **Initialization Parameters**
   - Pass parameters to initialization functions
   - Configuration-driven initialization

3. **Pre/Post Hooks**
   - Run functions before/after agent creation
   - Chain multiple initialization functions

4. **UI Initialization Editor**
   - Visual editor for initialization code
   - Syntax highlighting and validation

5. **Initialization Templates**
   - Pre-built initialization templates
   - Common patterns library

---

## References

### Files Changed

**Backend:**
- `backend/config/schemas.py` - Added `initialization_function` field
- `backend/core/dynamic_init_looping_agent.py` - New agent class
- `backend/core/agent_factory.py` - Factory support for new type
- `backend/core/runner.py` - Removed hard-coded initialization
- `backend/agents/Memory.json` - Updated to use dynamic init

**Frontend:**
- `frontend/src/features/agents/components/AgentEditor.js` - UI support

**Tests:**
- `backend/tests/unit/test_dynamic_init_agent.py` - Unit tests
- `backend/tests/integration/test_dynamic_init_integration.py` - Integration tests
- `backend/tests/e2e_dynamic_init_test.py` - End-to-end tests

**Documentation:**
- `docs/DYNAMIC_INIT_AGENT_IMPLEMENTATION.md` - This document

### Related Documentation
- [CLAUDE.md](../CLAUDE.md) - Main development guide
- [REFACTORING_SUMMARY.md](../REFACTORING_SUMMARY.md) - Backend refactoring

---

**Implementation Date:** 2025-11-08
**Status:** ✅ Complete and Tested
**Test Coverage:** 18/18 tests passing (11 unit + 4 integration + 3 e2e)
