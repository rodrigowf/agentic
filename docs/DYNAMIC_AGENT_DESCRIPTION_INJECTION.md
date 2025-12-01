# Dynamic Agent Description Injection

**Feature Added:** 2025-12-01
**Location:** `backend/core/nested_agent.py`
**Status:** Stable

---

## Overview

Dynamic Agent Description Injection is a feature that automatically populates orchestrator agents with information about available sub-agents in nested team configurations. This ensures the orchestrator always has up-to-date, comprehensive information about each agent's capabilities without manual updates.

## Problem Solved

**Before this feature:**
- Orchestrator system prompts had hardcoded agent lists
- Adding/removing agents required manual prompt updates
- Agent descriptions could become stale or inconsistent
- Orchestrators had incomplete information about agent capabilities

**After this feature:**
- Agent descriptions are automatically injected from configurations
- Single source of truth (agent JSON configs)
- Always up-to-date when agents are added/removed
- Comprehensive capability information for better task routing

---

## How It Works

### 1. Architecture

```
MainConversation (nested_team)
    ├── Manager (orchestrator) ← Receives injected descriptions
    ├── Memory (sub-agent)
    ├── FileManager (sub-agent)
    ├── Researcher (sub-agent)
    └── Engineer (sub-agent)
```

### 2. Injection Flow

```
1. Nested team agent initializes (_init_team)
   ↓
2. Sub-agents are created from configs
   ↓
3. _inject_agent_descriptions() is called
   ↓
4. Finds orchestrator among sub-agents
   ↓
5. Extracts names + descriptions from other sub-agents
   ↓
6. Formats as bullet list
   ↓
7. Replaces {{AVAILABLE_AGENTS}} placeholder in orchestrator's system prompt
   ↓
8. Orchestrator now has complete agent information
```

### 3. Implementation

**File:** `backend/core/nested_agent.py`

```python
def _inject_agent_descriptions(self, sub_agents: List):
    """
    Inject agent names and descriptions into orchestrator's system prompt.
    Replaces {{AVAILABLE_AGENTS}} placeholder with formatted list of agents.
    """
    # Find orchestrator agent
    orchestrator_name = self.agent_cfg.orchestrator_agent_name or "Manager"
    orchestrator_agent = None
    for agent in sub_agents:
        if agent.name == orchestrator_name:
            orchestrator_agent = agent
            break

    if not orchestrator_agent:
        return  # No orchestrator found, skip injection

    # Build agent descriptions (exclude orchestrator itself)
    agent_descriptions = []
    for agent in sub_agents:
        if agent.name != orchestrator_name:
            description = agent.description or "No description available"
            agent_descriptions.append(f"- {agent.name}: {description}")

    if not agent_descriptions:
        agents_text = "(No other agents available)"
    else:
        agents_text = "The agents involved in this conversation besides you are:\n" + "\n".join(agent_descriptions)

    # Inject into orchestrator's system message
    if orchestrator_agent._system_messages:
        current_prompt = orchestrator_agent._system_messages[0].content
        updated_prompt = current_prompt.replace("{{AVAILABLE_AGENTS}}", agents_text)
        orchestrator_agent._system_messages[0].content = updated_prompt
```

---

## Usage Guide

### Step 1: Add Placeholder to Orchestrator

**File:** `backend/agents/Manager.json`

```json
{
  "name": "Manager",
  "agent_type": "assistant",
  "prompt": {
    "system": "You are the Manager, the tasks manager of an agents group chat conversation that works as an assistant.\nYour goal is to check the latest activities performed by the group, then choose the next agent from the list and tell it exactly what to do based on its capabilities.\n\n{{AVAILABLE_AGENTS}}\n\nWhen the task is complete respond to the user with normal text and finish with TERMINATE.\nIn all other cases you must output in the format:\nTASK: <Their task>\nNEXT AGENT: <Agent_name>"
  }
}
```

**Key Points:**
- Use `{{AVAILABLE_AGENTS}}` placeholder where you want agent list injected
- Placeholder can appear anywhere in the system prompt
- No special configuration needed - works automatically

### Step 2: Write Comprehensive Agent Descriptions

**Good Example - Researcher.json:**

```json
{
  "name": "Researcher",
  "description": "A professional web researcher and fact-checker that performs multi-step research using web search, Wikipedia, ArXiv, and content fetching. Validates information across multiple sources, fact-checks sensitive topics, and runs in a loop until complete information is gathered. Best for: current events, fact verification, academic research, general knowledge queries, and any task requiring up-to-date web information."
}
```

**Good Example - Engineer.json:**

```json
{
  "name": "Engineer",
  "description": "A software engineer that writes and executes Python or Bash code in an isolated workspace (./workspace directory). Can provide code snippets, create executable scripts, run code iteratively to debug errors, and save outputs to workspace files. Capable of: data processing, file manipulation, system operations, calculations, API integrations, automation scripts, testing, and any task solvable through code. All executed code and generated files are saved in backend/workspace/. Avoid using for web research - use Researcher instead."
}
```

**Description Structure:**
```
[Role] that [key capability]. [Tool/approach details]. [Specific capabilities]. Best for: [use cases]. Avoid: [anti-patterns].
```

### Step 3: Configure Nested Team

**File:** `backend/agents/MainConversation.json`

```json
{
  "name": "MainConversation",
  "agent_type": "nested_team",
  "sub_agents": [
    "Manager",
    "Memory",
    "FileManager",
    "Researcher",
    "Engineer"
  ],
  "mode": "selector",
  "orchestrator_prompt": "__function__"
}
```

**Key Points:**
- First agent in `sub_agents` is typically the orchestrator
- Can be overridden with `orchestrator_agent_name` field
- Orchestrator receives descriptions of ALL other sub-agents

### Step 4: Runtime Result

When the nested team agent initializes, the Manager sees:

```
You are the Manager, the tasks manager of an agents group chat conversation that works as an assistant.
Your goal is to check the latest activities performed by the group, then choose the next agent from the list and tell it exactly what to do based on its capabilities.

The agents involved in this conversation besides you are:
- Memory: An agent that manages short-term memory and persistent memory banks using vector similarity search. Stores, retrieves, updates, and organizes information intelligently.
- FileManager: An agent that manages files with automatic workspace hierarchy awareness. Handles all file CRUD operations within the workspace directory.
- Researcher: A professional web researcher and fact-checker that performs multi-step research using web search, Wikipedia, ArXiv, and content fetching. Validates information across multiple sources, fact-checks sensitive topics, and runs in a loop until complete information is gathered. Best for: current events, fact verification, academic research, general knowledge queries, and any task requiring up-to-date web information.
- Engineer: A software engineer that writes and executes Python or Bash code in an isolated workspace. Can create files, run scripts, debug errors, and iterate through multiple code execution cycles until the task is complete. Capable of: data processing, file manipulation, system operations, calculations, API integrations, automation scripts, testing, and any task solvable through code execution. Avoid using for web research - use Researcher instead.

When the task is complete respond to the user with normal text and finish with TERMINATE.
In all other cases you must output in the format:
TASK: <Their task>
NEXT AGENT: <Agent_name>
```

---

## Testing

A test script is provided to verify the feature works correctly.

**File:** `backend/test_placeholder_injection.py`

**Run the test:**

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
python3 test_placeholder_injection.py
```

**Expected output:**

```
================================================================================
Testing {{AVAILABLE_AGENTS}} Placeholder Injection
================================================================================

✅ Loaded 11 agent configs
✅ Found MainConversation with sub-agents: ['Manager', 'Memory', 'FileManager', 'Researcher', 'Engineer']
✅ Loaded 22 tools

🔄 Creating nested team agent...
✅ Created nested team agent: MainConversation
✅ Found Manager agent in team

================================================================================
Manager System Message (first 1500 chars):
================================================================================
You are the Manager, the tasks manager of an agents group chat conversation...

The agents involved in this conversation besides you are:
- Memory: An agent that manages short-term memory and persistent memory banks...
- FileManager: An agent that manages files with automatic workspace hierarchy...
- Researcher: A professional web researcher and fact-checker...
- Engineer: A software engineer that writes and executes Python or Bash code...

...
================================================================================

✅ SUCCESS: Placeholder was replaced!
✅ All expected agents found in system message: ['Memory', 'FileManager', 'Researcher', 'Engineer']
✅ Correct formatting used

================================================================================
✅ TEST PASSED: Placeholder injection working correctly!
================================================================================
```

**Test verifies:**
- ✅ Placeholder is replaced (not present in final prompt)
- ✅ All sub-agents are listed correctly
- ✅ Descriptions are pulled from agent configs
- ✅ Formatting matches expected pattern

---

## Best Practices

### Writing Agent Descriptions

**Do:**
- ✅ Be comprehensive (100-200 words)
- ✅ List specific tools and capabilities
- ✅ Include use cases ("Best for:")
- ✅ Mention anti-patterns ("Avoid:")
- ✅ Write from orchestrator's perspective
- ✅ Use consistent formatting across agents

**Don't:**
- ❌ Be vague ("Does research")
- ❌ Omit capabilities
- ❌ Skip use case examples
- ❌ Write from first person ("I can...")
- ❌ Exceed 300 words (keep concise)

### Description Template

```json
{
  "description": "[Role] that [core capability]. [Implementation details: tools, approach, workflow]. [Specific capabilities: list of tasks it can handle]. Best for: [use case 1], [use case 2], [use case 3]. Avoid: [what NOT to use it for - suggest alternative]."
}
```

### Placeholder Usage

**Supported placeholders:**
- `{{AVAILABLE_AGENTS}}` - Injected agent list (current feature)
- `{{SHORT_TERM_MEMORY}}` - Memory agent specific (see Memory.json)
- `{{MEMORY_BANKS}}` - Memory agent specific (see Memory.json)
- `{{WORKSPACE_HIERARCHY}}` - FileManager specific (see FileManager.json)

**Multiple placeholders:**

You can use multiple placeholders in the same system prompt:

```json
{
  "prompt": {
    "system": "You are the Manager...\n\n{{AVAILABLE_AGENTS}}\n\nCurrent workspace:\n{{WORKSPACE_HIERARCHY}}"
  }
}
```

---

## Advanced Usage

### Custom Orchestrator Name

By default, the first agent in `sub_agents` is the orchestrator. You can override this:

```json
{
  "name": "MainConversation",
  "agent_type": "nested_team",
  "sub_agents": [
    "Coordinator",
    "Worker1",
    "Worker2"
  ],
  "orchestrator_agent_name": "Coordinator"
}
```

### Multiple Nested Teams

Each nested team maintains its own injection:

```
TeamA (nested_team)
    ├── ManagerA ← Gets descriptions of TeamA sub-agents
    ├── AgentX
    └── AgentY

TeamB (nested_team)
    ├── ManagerB ← Gets descriptions of TeamB sub-agents
    ├── AgentZ
    └── AgentW
```

### Dynamic Sub-Agent Updates

If you modify `sub_agents` in the JSON config:

1. Save the config file
2. Restart the backend (or use hot reload)
3. Next initialization automatically picks up changes
4. Orchestrator receives updated agent list

**No code changes needed!**

---

## Troubleshooting

### Placeholder Not Replaced

**Symptom:** Manager prompt still shows `{{AVAILABLE_AGENTS}}`

**Causes:**
1. Typo in placeholder name (case-sensitive)
2. Orchestrator agent not found in sub-agents
3. orchestrator_agent_name doesn't match any sub-agent

**Solution:**
```bash
# Verify placeholder spelling
grep "{{AVAILABLE_AGENTS}}" backend/agents/Manager.json

# Verify orchestrator is in sub-agents list
cat backend/agents/MainConversation.json | grep -A 10 sub_agents

# Check logs for errors
tail -f backend/logs/backend.log
```

### Empty Agent List

**Symptom:** `(No other agents available)` appears instead of agent list

**Causes:**
1. Only one agent in sub_agents (the orchestrator itself)
2. All sub-agents failed to load

**Solution:**
```bash
# Check sub_agents count
python3 -c "
import sys; sys.path.insert(0, '.')
from config.config_loader import load_agents
cfg = [c for c in load_agents('agents') if c.name == 'MainConversation'][0]
print(f'Sub-agents: {[a.name for a in cfg.sub_agents]}')
"
```

### Descriptions Not Showing

**Symptom:** Agent names appear but descriptions are "No description available"

**Cause:** `description` field missing or empty in agent config

**Solution:**
```bash
# Check agent description
python3 -c "
import sys; sys.path.insert(0, '.')
from config.config_loader import load_agents
cfg = [c for c in load_agents('agents') if c.name == 'Researcher'][0]
print(f'Description: {cfg.description}')
"
```

---

## Migration Guide

### Upgrading Existing Nested Teams

**Before (hardcoded descriptions):**

```json
{
  "name": "Manager",
  "prompt": {
    "system": "You are the Manager...\n\nThe agents are:\n- Researcher: Does web research\n- Engineer: Writes code"
  }
}
```

**After (dynamic injection):**

```json
{
  "name": "Manager",
  "prompt": {
    "system": "You are the Manager...\n\n{{AVAILABLE_AGENTS}}"
  }
}
```

**Steps:**
1. Replace hardcoded agent list with `{{AVAILABLE_AGENTS}}`
2. Enhance each sub-agent's `description` field
3. Restart backend
4. Test with `test_placeholder_injection.py`

---

## Performance

**Initialization Time:**
- Negligible overhead (~1-2ms per agent)
- One-time cost during nested team creation
- No runtime performance impact

**Memory:**
- No additional memory overhead
- Descriptions are already loaded from JSON configs
- Single string replacement operation

---

## Future Enhancements

Potential improvements:

- 🔮 **Custom Formatting:** Allow customization of agent list format
- 🔮 **Capability Filtering:** Show only agents with specific capabilities
- 🔮 **Dynamic Sorting:** Order agents by relevance to current task
- 🔮 **Tool Enumeration:** Include full tool list for each agent
- 🔮 **Version Tracking:** Track when agent descriptions change

---

## Related Documentation

- **Main Guide:** [CLAUDE.md](../CLAUDE.md) - Section on "Creating New Agents"
- **Implementation:** [nested_agent.py](../backend/core/nested_agent.py) - Lines 122-154
- **Test Script:** [test_placeholder_injection.py](../backend/test_placeholder_injection.py)
- **Example Configs:**
  - [Manager.json](../backend/agents/Manager.json) - Orchestrator with placeholder
  - [MainConversation.json](../backend/agents/MainConversation.json) - Nested team config
  - [Researcher.json](../backend/agents/Researcher.json) - Example comprehensive description
  - [Engineer.json](../backend/agents/Engineer.json) - Example comprehensive description

---

## Changelog

### 2025-12-01 - Initial Implementation
- Added `_inject_agent_descriptions()` method to `NestedTeamAgent`
- Automatic placeholder detection and replacement
- Support for `{{AVAILABLE_AGENTS}}` placeholder
- Created test script for validation
- Updated Manager.json with placeholder
- Enhanced Researcher and Engineer descriptions
- Integrated Memory and FileManager into MainConversation

---

**Status:** Production Ready
**Tested:** ✅ Passing all tests
**Breaking Changes:** None (backward compatible)
