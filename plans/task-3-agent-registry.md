# Task 3: Generalize Agent List Loading (Agent Registry System)

**Status:** Pending
**Priority:** High
**Assigned to:** TBD
**Estimated Effort:** 12-16 hours

---

## Overview

Create a centralized agent registry system that automatically loads agent metadata from JSON files, eliminating hard-coded agent lists throughout the codebase. This enables runtime agent discovery for Manager and Planner agents, and provides a foundation for dynamic team composition.

**📋 Complete Analysis:** See `docs/AGENT_SELECTION_ANALYSIS.md` for detailed analysis of current system and proposed architecture.

---

## Problem Statement

### Current Issues

**Manager Agent Hard-Coded List** (`backend/agents/Manager.json:12`):
```
The agents involved in this conversation besides you are:
- Researcher: It runs multiple turns interacting with the web...
- Developer: This agent can solve any task within the system...
```

**Problems:**
1. ❌ Agent descriptions manually typed and duplicated
2. ❌ No runtime discovery - Manager can't learn about new agents
3. ❌ Adding agents requires updating multiple files
4. ❌ Information can become stale if agent configs change
5. ❌ Planner agent (Task #4) can't assess team capabilities
6. ❌ Frontend has hard-coded agent references

---

## Objectives

- Eliminate all hard-coded agent lists
- Enable runtime agent discovery for Manager
- Provide foundation for Planner agent (Task #4)
- Auto-update Manager prompt when agents change
- Dynamic frontend rendering based on available agents
- Single source of truth (agent JSON files)

---

## Proposed Solution: Agent Registry System

### Architecture

```
┌─────────────────────────────────────────┐
│         Agent Registry                   │
│   (backend/config/agent_registry.py)    │
│   - Scans agents/ directory             │
│   - Caches metadata                     │
│   - Thread-safe access                  │
└──────────────┬──────────────────────────┘
               │
               ├──→ Agent Discovery Tools
               │    (tools/agent_discovery.py)
               │    - get_available_agents()
               │    - get_agent_info(name)
               │    - find_agents_for_task()
               │
               ├──→ API Endpoint
               │    GET /api/agents/metadata
               │
               └──→ Dynamic Manager Init
                    initialize_manager_with_team()
```

---

## Implementation Plan

### Phase 1: Backend Foundation (4-5 hours)

#### 1.1 Create Agent Registry Module

**File:** `backend/config/agent_registry.py`

**Classes:**

```python
@dataclass
class AgentMetadata:
    """Lightweight agent metadata for discovery."""
    name: str
    description: str
    agent_type: str
    tools: List[str]
    capabilities_summary: str
    is_orchestrator: bool
    sub_agents: List[str] | None = None

class AgentRegistry:
    """Centralized agent metadata management."""

    def __init__(self, agents_dir: str):
        self._agents: Dict[str, AgentMetadata] = {}
        self._agents_dir = agents_dir
        self._lock = threading.RLock()
        self._load_all_agents()

    def get_all_agents(self) -> List[AgentMetadata]:
        """Get all registered agents."""

    def get_agent(self, name: str) -> AgentMetadata | None:
        """Get specific agent metadata."""

    def get_agents_by_tool(self, tool_name: str) -> List[AgentMetadata]:
        """Find agents that have a specific tool."""

    def refresh(self):
        """Reload agents from disk."""

    def _load_all_agents(self):
        """Scan agents directory and load metadata."""

    def _extract_metadata(self, agent_config: AgentConfig) -> AgentMetadata:
        """Extract metadata from AgentConfig."""
```

**Key Features:**
- Thread-safe with RLock
- Lazy loading with caching
- Auto-refresh capability (dev mode)
- Capability summary generation

**Capability Summary Logic:**
```python
def _generate_capabilities_summary(agent_config: AgentConfig) -> str:
    """Generate human-readable capabilities summary."""
    summary_parts = []

    # Add description
    if agent_config.description:
        summary_parts.append(agent_config.description)

    # Add tool count
    if agent_config.tools:
        summary_parts.append(f"Has {len(agent_config.tools)} tools")

    # Add agent type info
    if agent_config.agent_type == "nested_team":
        summary_parts.append("Orchestrates team of sub-agents")
    elif agent_config.agent_type == "looping_code_executor":
        summary_parts.append("Can execute code")

    return ". ".join(summary_parts)
```

#### 1.2 Create Agent Discovery Tools

**File:** `backend/tools/agent_discovery.py`

**Tools:**

```python
def get_available_agents() -> str:
    """
    Get a list of all available agents and their capabilities.

    Returns a formatted string describing each agent:
    - Name
    - Description
    - Agent type
    - Available tools
    - Capabilities summary

    Use this to understand what agents are available for delegation.
    """
    registry = get_agent_registry()
    agents = registry.get_all_agents()

    output = "Available Agents:\n\n"
    for agent in agents:
        output += f"## {agent.name}\n"
        output += f"Type: {agent.agent_type}\n"
        output += f"Description: {agent.description}\n"

        # Show first 5 tools
        if agent.tools:
            tools_display = agent.tools[:5]
            if len(agent.tools) > 5:
                tools_display.append(f"... and {len(agent.tools) - 5} more")
            output += f"Tools: {', '.join(tools_display)}\n"

        output += f"Capabilities: {agent.capabilities_summary}\n\n"

    return output


def get_agent_info(agent_name: str) -> str:
    """
    Get detailed information about a specific agent.

    Args:
        agent_name: Name of the agent to query

    Returns detailed agent information or error message.
    """
    registry = get_agent_registry()
    agent = registry.get_agent(agent_name)

    if not agent:
        return f"Agent '{agent_name}' not found"

    output = f"Agent: {agent.name}\n"
    output += f"Type: {agent.agent_type}\n"
    output += f"Description: {agent.description}\n"
    output += f"\nTools ({len(agent.tools)}):\n"
    for tool in agent.tools:
        output += f"  - {tool}\n"
    output += f"\nCapabilities: {agent.capabilities_summary}\n"

    if agent.is_orchestrator and agent.sub_agents:
        output += f"\nSub-agents: {', '.join(agent.sub_agents)}\n"

    return output


def find_agents_for_task(task_description: str) -> str:
    """
    Find agents suitable for a given task based on their capabilities.

    Args:
        task_description: Description of the task to perform

    Returns list of recommended agents with reasoning.

    Uses basic keyword matching and tool availability to suggest agents.
    """
    registry = get_agent_registry()
    agents = registry.get_all_agents()

    # Simple keyword matching for MVP
    task_lower = task_description.lower()
    matches = []

    for agent in agents:
        score = 0
        reasons = []

        # Match against description
        if agent.description and any(
            word in agent.description.lower()
            for word in task_lower.split()
        ):
            score += 2
            reasons.append("Description matches task")

        # Match against tool names
        matching_tools = [
            tool for tool in agent.tools
            if any(word in tool.lower() for word in task_lower.split())
        ]
        if matching_tools:
            score += len(matching_tools)
            reasons.append(f"Has relevant tools: {', '.join(matching_tools[:3])}")

        if score > 0:
            matches.append((agent, score, reasons))

    # Sort by score
    matches.sort(key=lambda x: x[1], reverse=True)

    if not matches:
        return "No agents found matching the task description."

    output = f"Recommended agents for: '{task_description}'\n\n"
    for agent, score, reasons in matches[:5]:  # Top 5
        output += f"**{agent.name}** (score: {score})\n"
        output += f"  - {agent.description}\n"
        for reason in reasons:
            output += f"  - {reason}\n"
        output += "\n"

    return output


def initialize_manager_with_team():
    """
    Initialize Manager agent with current team roster.

    Called automatically when Manager agent starts up.
    Replaces {{AGENT_ROSTER}} placeholder in system prompt
    with current list of available agents.
    """
    from utils.context import get_current_agent

    agent = get_current_agent()
    registry = get_agent_registry()

    # Get all agents except Manager itself
    agents = [a for a in registry.get_all_agents() if a.name != "Manager"]

    # Build roster text
    roster = "Current Team:\n\n"
    for agent_meta in agents:
        roster += f"**{agent_meta.name}**\n"
        roster += f"  - Description: {agent_meta.description}\n"
        roster += f"  - Type: {agent_meta.agent_type}\n"

        # Show key tools
        if agent_meta.tools:
            key_tools = agent_meta.tools[:5]
            if len(agent_meta.tools) > 5:
                key_tools_str = ', '.join(key_tools) + f' (and {len(agent_meta.tools) - 5} more)'
            else:
                key_tools_str = ', '.join(key_tools)
            roster += f"  - Key Tools: {key_tools_str}\n"

        roster += "\n"

    roster += "You can query available agents anytime using get_available_agents()."

    # Replace placeholder in system message
    if agent and agent._system_messages:
        current_content = agent._system_messages[0].content
        updated_content = current_content.replace("{{AGENT_ROSTER}}", roster)
        agent._system_messages[0].content = updated_content

    return f"Manager initialized with {len(agents)} team members"


# Create FunctionTool instances
get_available_agents_tool = FunctionTool(
    func=get_available_agents,
    name="get_available_agents",
    description="Get list of all available agents and their capabilities"
)

get_agent_info_tool = FunctionTool(
    func=get_agent_info,
    name="get_agent_info",
    description="Get detailed information about a specific agent"
)

find_agents_for_task_tool = FunctionTool(
    func=find_agents_for_task,
    name="find_agents_for_task",
    description="Find agents suitable for a given task based on capabilities"
)

# Export for config_loader
tools = [
    get_available_agents_tool,
    get_agent_info_tool,
    find_agents_for_task_tool
]
```

#### 1.3 Add API Endpoint

**File:** `backend/main.py`

```python
from config.agent_registry import get_agent_registry

@app.get("/api/agents/metadata")
def get_agents_metadata():
    """
    Get lightweight agent metadata for UI rendering.

    Returns list of agent metadata without full configuration details.
    """
    registry = get_agent_registry()
    agents = registry.get_all_agents()

    return [
        {
            "name": a.name,
            "description": a.description,
            "agent_type": a.agent_type,
            "tools": a.tools,
            "is_orchestrator": a.is_orchestrator,
            "capabilities_summary": a.capabilities_summary,
            "sub_agents": a.sub_agents
        }
        for a in agents
    ]

@app.post("/api/agents/refresh")
def refresh_agent_registry():
    """
    Manually refresh agent registry (reload from disk).

    Useful in development when agents are modified.
    """
    registry = get_agent_registry()
    registry.refresh()
    return {"status": "refreshed", "count": len(registry.get_all_agents())}
```

#### 1.4 Global Registry Instance

**File:** `backend/config/agent_registry.py`

```python
# Singleton instance
_registry_instance: AgentRegistry | None = None
_registry_lock = threading.Lock()

def get_agent_registry() -> AgentRegistry:
    """Get global agent registry instance (singleton)."""
    global _registry_instance
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                agents_dir = os.getenv("AGENTS_DIR", "agents")
                _registry_instance = AgentRegistry(agents_dir)
    return _registry_instance
```

---

### Phase 2: Manager Integration (3-4 hours)

#### 2.1 Update Manager Configuration

**File:** `backend/agents/Manager.json`

**Before:**
```json
{
  "name": "Manager",
  "agent_type": "assistant",
  "tools": [],
  "prompt": {
    "system": "You are the Manager...\nThe agents involved are:\n- Researcher: ...\n- Developer: ..."
  }
}
```

**After:**
```json
{
  "name": "Manager",
  "agent_type": "dynamic_init_looping",
  "initialization_function": "agent_discovery.initialize_manager_with_team",
  "tools": [
    "get_available_agents",
    "get_agent_info",
    "find_agents_for_task"
  ],
  "llm": {
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "temperature": 0.0,
    "max_tokens": null
  },
  "prompt": {
    "system": "You are the Manager, the task coordinator for an agent team.\n\n{{AGENT_ROSTER}}\n\nYour role is to:\n1. Understand the user's request\n2. Select the most appropriate agent from the team\n3. Delegate the task with clear instructions\n\nYou can query available agents anytime using get_available_agents().\n\nWhen the task is complete, respond to the user with normal text and finish with TERMINATE.\n\nIn all other cases you must output in the format:\nTASK: <Their task>\nNEXT AGENT: <Agent_name>",
    "user": ""
  },
  "code_executor": null,
  "model_client_stream": false,
  "sources": null,
  "description": "Task coordinator who delegates work to team agents",
  "system_message": null,
  "max_consecutive_auto_reply": null,
  "reflect_on_tool_use": true,
  "terminate_on_text": false,
  "tool_call_loop": true,
  "sub_agents": null,
  "mode": null,
  "orchestrator_prompt": null,
  "include_inner_dialog": true
}
```

**Key Changes:**
1. ✅ `agent_type: "dynamic_init_looping"`
2. ✅ `initialization_function: "agent_discovery.initialize_manager_with_team"`
3. ✅ Added discovery tools
4. ✅ `tool_call_loop: true` (can use tools in loop)
5. ✅ `{{AGENT_ROSTER}}` placeholder in prompt

#### 2.2 Test Manager Integration

**Test Script:** `backend/tests/test_agent_registry_manager.py`

```python
import pytest
from config.agent_registry import get_agent_registry
from config.config_loader import load_agents
from core.agent_factory import create_agent_from_config

def test_manager_initialization():
    """Test Manager initializes with team roster."""
    # Load Manager config
    agents = load_agents("agents")
    manager_cfg = next(a for a in agents if a.name == "Manager")

    # Create Manager agent
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from config.config_loader import load_tools

    model_client = OpenAIChatCompletionClient(...)
    tools = load_tools("tools")
    all_tools = [t for t, _ in tools]

    manager = create_agent_from_config(manager_cfg, all_tools, model_client)

    # Check initialization ran
    assert manager._system_messages
    content = manager._system_messages[0].content

    # Should NOT contain placeholder
    assert "{{AGENT_ROSTER}}" not in content

    # Should contain team members
    assert "Researcher" in content or "Developer" in content

def test_get_available_agents():
    """Test get_available_agents tool."""
    registry = get_agent_registry()
    agents = registry.get_all_agents()

    assert len(agents) > 0
    assert any(a.name == "Researcher" for a in agents)
    assert any(a.name == "Developer" for a in agents)
```

---

### Phase 3: Frontend Integration (3-4 hours)

#### 3.1 Create Agent Context

**File:** `frontend/src/contexts/AgentContext.js`

```javascript
import { createContext, useContext, useState, useEffect } from 'react';
import { getAgentsMetadata } from '../api';

const AgentContext = createContext();

export function AgentProvider({ children }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAgents = async () => {
    try {
      setLoading(true);
      const metadata = await getAgentsMetadata();
      setAgents(metadata);
      setError(null);
    } catch (err) {
      console.error('Failed to load agents:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();

    // Auto-refresh every 30 seconds
    const interval = setInterval(loadAgents, 30000);
    return () => clearInterval(interval);
  }, []);

  const refreshAgents = () => {
    loadAgents();
  };

  return (
    <AgentContext.Provider value={{ agents, loading, error, refreshAgents }}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgents() {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgents must be used within AgentProvider');
  }
  return context;
}
```

#### 3.2 Update API Client

**File:** `frontend/src/api.js`

```javascript
export async function getAgentsMetadata() {
  const response = await fetch(`${backendBase}/api/agents/metadata`);
  if (!response.ok) {
    throw new Error(`Failed to fetch agents metadata: ${response.statusText}`);
  }
  return response.json();
}

export async function refreshAgentRegistry() {
  const response = await fetch(`${backendBase}/api/agents/refresh`, {
    method: 'POST'
  });
  if (!response.ok) {
    throw new Error(`Failed to refresh registry: ${response.statusText}`);
  }
  return response.json();
}
```

#### 3.3 Update App.js

**File:** `frontend/src/App.js`

```javascript
import { AgentProvider } from './contexts/AgentContext';

function App() {
  return (
    <AgentProvider>
      <Router>
        {/* existing routes */}
      </Router>
    </AgentProvider>
  );
}
```

#### 3.4 Update AgentEditor (Dynamic Sub-Agents)

**File:** `frontend/src/features/agents/components/AgentEditor.js`

```javascript
import { useAgents } from '../../../contexts/AgentContext';

function AgentEditor({ /* props */ }) {
  const { agents, loading } = useAgents();

  // Filter agents suitable as sub-agents
  const availableSubAgents = agents.filter(a => !a.is_orchestrator);

  return (
    <FormControl fullWidth>
      <InputLabel>Sub-Agents</InputLabel>
      <Select
        multiple
        value={config.sub_agents || []}
        onChange={handleSubAgentsChange}
        disabled={loading}
      >
        {loading ? (
          <MenuItem disabled>Loading agents...</MenuItem>
        ) : (
          availableSubAgents.map(agent => (
            <MenuItem key={agent.name} value={agent.name}>
              {agent.name} - {agent.description}
            </MenuItem>
          ))
        )}
      </Select>
    </FormControl>
  );
}
```

---

### Phase 4: Testing & Documentation (2-3 hours)

#### 4.1 Unit Tests

**File:** `backend/tests/unit/test_agent_registry.py`

```python
def test_agent_registry_loads_agents()
def test_agent_registry_caching()
def test_agent_registry_refresh()
def test_get_agents_by_tool()
def test_capability_summary_generation()
```

#### 4.2 Integration Tests

**File:** `backend/tests/integration/test_agent_registry_integration.py`

```python
def test_manager_uses_discovery_tools()
def test_api_endpoint_returns_metadata()
def test_frontend_context_loads_agents()
def test_dynamic_initialization()
```

#### 4.3 Documentation Updates

Update `CLAUDE.md`:
- Add Agent Registry section
- Document discovery tools
- Update Manager agent documentation
- Add examples of using registry

---

## Files to Create

| File | Lines | Priority |
|------|-------|----------|
| `backend/config/agent_registry.py` | ~300 | Required |
| `backend/tools/agent_discovery.py` | ~200 | Required |
| `frontend/src/contexts/AgentContext.js` | ~60 | Required |
| `backend/tests/unit/test_agent_registry.py` | ~150 | Recommended |
| `backend/tests/integration/test_agent_registry_integration.py` | ~100 | Recommended |

---

## Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `backend/agents/Manager.json` | Convert to dynamic_init_looping | Required |
| `backend/main.py` | Add metadata endpoint | Required |
| `frontend/src/api.js` | Add getAgentsMetadata() | Required |
| `frontend/src/App.js` | Wrap with AgentProvider | Required |
| `frontend/src/features/agents/components/AgentEditor.js` | Use dynamic agents | Required |
| `CLAUDE.md` | Document registry system | Recommended |

---

## Success Criteria

- ✅ AgentRegistry loads all agents from JSON files
- ✅ Manager prompt auto-updates with team roster
- ✅ Manager can call `get_available_agents()` at runtime
- ✅ API endpoint returns agent metadata
- ✅ Frontend AgentContext provides agent list
- ✅ AgentEditor shows dynamic sub-agent dropdown
- ✅ Adding new agent JSON automatically appears in system
- ✅ All tests pass
- ✅ No hard-coded agent lists remain
- ✅ Backward compatible (existing agents work)

---

## Migration Strategy

### Backward Compatibility

During migration, support both approaches:

1. If Manager has `{{AGENT_ROSTER}}` → use dynamic initialization
2. If Manager has hard-coded list → continue using it
3. Gradual migration of agents one at a time

### Testing Approach

1. Test registry in isolation
2. Test Manager with new system
3. Compare behavior with old system
4. Ensure all existing workflows still work

---

## Dependencies

**Required for this task:**
- Dynamic initialization system (already exists)
- Agent loading infrastructure (already exists)

**Enables these tasks:**
- Task #4 (Planner Agent) - Can now query team capabilities

---

## Performance Considerations

- Registry caching reduces file I/O
- Thread-safe for concurrent access
- Metadata extraction is lightweight
- API endpoint returns only necessary data

---

## Security Considerations

- Registry only reads agent configs (no execution)
- Path validation for agent directory
- No user input in registry operations
- Metadata exposure limited to safe fields

---

## Rollback Plan

If issues arise:

1. Revert Manager.json to previous version
2. Keep registry code (no harm)
3. Remove API endpoint calls from frontend
4. System returns to hard-coded state

---

## Next Steps After Completion

1. ✅ Test with existing agents
2. → Implement Task #4 (Planner Agent)
3. → Add more discovery features (search by capability, etc.)
4. → Consider agent recommendation system
5. → Add agent usage analytics

---

**Last Updated:** 2025-11-29
