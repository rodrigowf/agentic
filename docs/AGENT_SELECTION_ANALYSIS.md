# Agent Selection Analysis

**Date:** 2025-11-29
**Purpose:** Analysis of current agent selection mechanism and proposed generalization

---

## Current Agent Selection Mechanism

### 1. **Hard-Coded Agent List in MainConversation**

**Location:** `backend/agents/MainConversation.json:26-30`

```json
"sub_agents": [
  "Manager",
  "Researcher",
  "Developer"
]
```

**Problem:** Adding new agents requires manual JSON editing.

---

### 2. **Hard-Coded Agent Descriptions in Manager**

**Location:** `backend/agents/Manager.json:12` (system prompt)

```
The agents involved in this conversation besides you are:
- Researcher: It runs multiple turns interacting with the web to find the answer...
- Developer: This agent can solve any task within the system by writing and executing code...
```

**Problems:**
- Agent capabilities are manually listed in Manager's prompt
- No automatic discovery of agent tools or features
- Adding/removing agents requires updating Manager's system prompt
- Information can become stale if agent configs change

---

### 3. **Nested Team Agent Selection Logic**

**Location:** `backend/core/nested_agent.py:74-109`

**How It Works:**
1. `NestedTeamAgent` loads sub-agents from `MainConversation.json`
2. Builds agent list: `_TEAM_AGENT_NAMES = {a.name for a in sub_agents}`
3. Manager uses pattern matching: `NEXT AGENT: <Name>`
4. Custom selector function (`_custom_agent_selector`) validates agent name exists in `_TEAM_AGENT_NAMES`
5. If valid, that agent gets control; if not, returns None

**Key Code:**
```python
# Lines 128-132
_TEAM_AGENT_NAMES = {a.name for a in sub_agents}
_ORCHESTRATOR_NAME = self.agent_cfg.orchestrator_agent_name or "Manager"
_ORCHESTRATOR_PATTERN = self.agent_cfg.orchestrator_pattern or "NEXT AGENT: <Name>"

# Lines 97-102
match = re.search(pattern_regex, content, re.IGNORECASE)
if match:
    agent_name = match.group(1).strip().rstrip('.')
    if agent_name and agent_name.lower() != _ORCHESTRATOR_NAME.lower() and agent_name in _TEAM_AGENT_NAMES:
        return agent_name
```

**Limitation:** Manager must know agent names in advance (from its system prompt).

---

### 4. **Agent Configuration Loading**

**Location:** `backend/config/config_loader.py:70-101`

**Current Process:**
```python
def load_agents(agents_dir: str) -> List[AgentConfig]:
    # 1. Scan agents/ directory for *.json files
    # 2. Load each JSON file into AgentConfig
    # 3. For nested_team agents, expand sub_agents list
    # 4. Return list of AgentConfig objects
```

**What's Loaded:**
- Agent name
- Agent type (looping, nested_team, etc.)
- Tools list
- LLM config
- Prompt config
- Description
- All configuration fields

**Not Currently Exposed to Agents:**
- No runtime tool for agents to query available agents
- No centralized registry with metadata
- Agent capabilities not extracted or summarized

---

### 5. **API Endpoints**

**Location:** `backend/main.py:303-308`

```python
@app.get("/api/agents", response_model=list[AgentConfig])
def list_agents():
    AGENTS = load_agents(AGENTS_DIR)
    return AGENTS
```

**Available to Frontend:**
- Full agent configurations via REST API
- Reloads from disk on each request

**Not Available to Agents:**
- No tool to query this endpoint
- No runtime access to agent registry

---

## Problems with Current Approach

### For Developers:
1. **Maintenance burden** - Must update Manager prompt when adding/removing agents
2. **Error-prone** - Easy to forget to update Manager when agent capabilities change
3. **Redundancy** - Agent info exists in JSON but duplicated in Manager prompt
4. **Scalability** - As team grows, Manager prompt becomes unwieldy

### For Agents:
1. **No discovery** - Manager can't discover new agents at runtime
2. **No capability awareness** - Manager doesn't know what tools agents have
3. **Static planning** - Planner agent can't assess team capabilities dynamically
4. **Limited flexibility** - Can't adapt to changing agent roster

### For Users:
1. **Manual configuration** - Adding agent to team requires multiple file edits
2. **Synchronization** - Easy for Manager prompt to get out of sync with reality
3. **Limited visibility** - Hard to see what agents can do from Manager's perspective

---

## Proposed Solution: Agent Registry System

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Registry System                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent Registry (backend/config/agent_registry.py)   │  │
│  │  - Scans agents/ directory                           │  │
│  │  - Extracts metadata from JSON files                 │  │
│  │  - Caches agent capabilities                         │  │
│  │  - Auto-refreshes on file changes (dev mode)         │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent Discovery Tools (tools/agent_discovery.py)    │  │
│  │  - get_available_agents() → List all agents          │  │
│  │  - get_agent_info(name) → Get specific agent info    │  │
│  │  - get_agents_by_capability(tools) → Filter by tool  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Endpoint (/api/agents/metadata)                 │  │
│  │  - Returns lightweight agent metadata                │  │
│  │  - Used by frontend for dynamic rendering            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
        ┌──────────────────┴──────────────────┐
        ↓                                      ↓
┌───────────────────┐              ┌────────────────────┐
│  Manager Agent    │              │  Planner Agent     │
│  - Queries agents │              │  - Assesses team   │
│  - Delegates work │              │  - Creates plans   │
└───────────────────┘              └────────────────────┘
```

### Components

#### 1. **Agent Registry Module** (`backend/config/agent_registry.py`)

**Purpose:** Centralized agent metadata management

**Features:**
- Scans `agents/` directory for JSON files
- Extracts key metadata:
  - Name
  - Description
  - Agent type
  - Tools available
  - Capabilities summary
- Caches metadata in memory
- Auto-refresh on file changes (development mode)
- Thread-safe access

**Example Structure:**
```python
class AgentMetadata:
    name: str
    description: str
    agent_type: str
    tools: List[str]
    capabilities_summary: str  # Generated from description + tools
    is_orchestrator: bool  # True if nested_team type
    sub_agents: List[str] | None  # For nested teams

class AgentRegistry:
    def __init__(self, agents_dir: str):
        self._agents: Dict[str, AgentMetadata] = {}
        self._load_all_agents()

    def get_all_agents(self) -> List[AgentMetadata]:
        """Get all registered agents"""

    def get_agent(self, name: str) -> AgentMetadata | None:
        """Get specific agent metadata"""

    def get_agents_by_tool(self, tool_name: str) -> List[AgentMetadata]:
        """Find agents that have a specific tool"""

    def refresh(self):
        """Reload agents from disk"""
```

#### 2. **Agent Discovery Tools** (`backend/tools/agent_discovery.py`)

**Purpose:** Tools for agents to query the registry at runtime

**Tools:**

```python
@tool
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
        output += f"Tools: {', '.join(agent.tools)}\n"
        output += f"Capabilities: {agent.capabilities_summary}\n\n"

    return output

@tool
def get_agent_info(agent_name: str) -> str:
    """
    Get detailed information about a specific agent.

    Args:
        agent_name: Name of the agent to query

    Returns detailed agent information or error message.
    """

@tool
def find_agents_for_task(task_description: str) -> str:
    """
    Find agents suitable for a given task based on their capabilities.

    Args:
        task_description: Description of the task to perform

    Returns list of recommended agents with reasoning.

    Uses basic keyword matching and tool availability to suggest agents.
    """
```

#### 3. **Dynamic Manager Initialization** (`backend/agents/Manager.json`)

**Current (Hard-Coded):**
```json
{
  "name": "Manager",
  "agent_type": "looping",
  "tools": [],
  "prompt": {
    "system": "You are the Manager...\nThe agents involved are:\n- Researcher: ...\n- Developer: ..."
  }
}
```

**Proposed (Dynamic):**
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
  "prompt": {
    "system": "You are the Manager, the task coordinator for an agent team.\n\n{{AGENT_ROSTER}}\n\nYou can query available agents anytime using get_available_agents().\nWhen the task is complete, respond with TERMINATE.\nOtherwise output:\nTASK: <description>\nNEXT AGENT: <name>"
  }
}
```

**Initialization Function:**
```python
# tools/agent_discovery.py

def initialize_manager_with_team():
    """Initialize Manager agent with current team roster."""
    agent = get_current_agent()
    registry = get_agent_registry()

    # Get all agents (excluding Manager itself)
    agents = [a for a in registry.get_all_agents() if a.name != "Manager"]

    # Build roster text
    roster = "Current Team:\n"
    for agent_meta in agents:
        roster += f"- {agent_meta.name}: {agent_meta.description}\n"
        roster += f"  Tools: {', '.join(agent_meta.tools[:5])}{'...' if len(agent_meta.tools) > 5 else ''}\n"

    # Replace placeholder in system message
    if agent and agent._system_messages:
        agent._system_messages[0].content = agent._system_messages[0].content.replace(
            "{{AGENT_ROSTER}}",
            roster
        )

    return "Manager initialized with team roster"
```

#### 4. **API Endpoint for Metadata** (`backend/main.py`)

```python
@app.get("/api/agents/metadata")
def get_agents_metadata():
    """
    Get lightweight agent metadata for UI rendering.

    Returns list of:
    - name
    - description
    - agent_type
    - tools (list of tool names)
    - is_orchestrator
    """
    registry = get_agent_registry()
    agents = registry.get_all_agents()

    return [
        {
            "name": a.name,
            "description": a.description,
            "agent_type": a.agent_type,
            "tools": a.tools,
            "is_orchestrator": a.is_orchestrator
        }
        for a in agents
    ]
```

#### 5. **Frontend Agent Context** (`frontend/src/contexts/AgentContext.js`)

```javascript
// Global agent configuration context
import { createContext, useContext, useState, useEffect } from 'react';
import { getAgentsMetadata } from '../api';

const AgentContext = createContext();

export function AgentProvider({ children }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadAgents() {
      try {
        const metadata = await getAgentsMetadata();
        setAgents(metadata);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    }
    loadAgents();

    // Refresh every 30 seconds
    const interval = setInterval(loadAgents, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <AgentContext.Provider value={{ agents, loading, error }}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgents() {
  return useContext(AgentContext);
}
```

---

## Benefits of Proposed Solution

### For Developers:
1. **Zero maintenance** - Manager prompt auto-updates when agents change
2. **Single source of truth** - Agent metadata only in JSON files
3. **Scalability** - Add agents by just creating JSON file
4. **Type safety** - AgentMetadata validated at registry level

### For Agents:
1. **Runtime discovery** - Can query available agents anytime
2. **Capability awareness** - Can see what tools each agent has
3. **Dynamic planning** - Planner can adapt to team composition
4. **Intelligent delegation** - Manager can match tasks to agent capabilities

### For Users:
1. **Automatic updates** - UI reflects agent changes immediately
2. **Consistency** - No risk of outdated information
3. **Transparency** - Can see full team capabilities easily

---

## Implementation Sequence

### Phase 1: Backend Foundation
1. Create `AgentRegistry` class
2. Create `agent_discovery.py` tools
3. Add `/api/agents/metadata` endpoint
4. Test registry loading and caching

### Phase 2: Manager Integration
1. Convert Manager to `dynamic_init_looping` type
2. Add `get_available_agents` tool to Manager
3. Update Manager prompt to use `{{AGENT_ROSTER}}` placeholder
4. Test Manager can query and delegate properly

### Phase 3: Frontend Integration
1. Create `AgentContext` provider
2. Update `App.js` to use context
3. Update `AgentEditor.js` for dynamic sub_agents
4. Test UI updates when agents change

### Phase 4: Planner Agent
1. Create Planner agent configuration
2. Add planning tools
3. Integrate with agent discovery
4. Test Planner + Manager coordination

---

## Migration Path

### Backward Compatibility

The system can support **both** approaches during migration:

1. **Fallback mode:** If `{{AGENT_ROSTER}}` not found in Manager prompt, use existing hard-coded text
2. **Gradual migration:** Can migrate agents one at a time
3. **Testing:** Can compare old vs new behavior side-by-side

### Testing Strategy

1. **Unit tests:** Test `AgentRegistry` loading and caching
2. **Integration tests:** Test Manager uses discovery tools correctly
3. **E2E tests:** Test full workflow from user request to delegation
4. **Comparison tests:** Verify new system produces same results as old

---

## Conclusion

The proposed Agent Registry System:
- ✅ Eliminates hard-coded agent lists
- ✅ Enables runtime agent discovery
- ✅ Provides foundation for Planner agent
- ✅ Maintains backward compatibility
- ✅ Improves developer experience
- ✅ Enables dynamic team composition

**Recommended:** Implement in phases to minimize risk and allow for testing at each stage.

---

**Next Steps:**
1. Review and approve proposed architecture
2. Begin Phase 1 implementation (backend foundation)
3. Test thoroughly before proceeding to Phase 2
4. Document new patterns in CLAUDE.md
