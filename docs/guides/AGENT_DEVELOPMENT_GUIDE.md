# Agent Development Guide

Complete guide to creating and configuring AI agents in the Agentic system.

---

## Agent Configuration Structure

### Location

Agent configurations are JSON files stored in `backend/agents/{AgentName}.json`

### Complete Configuration Example

```json
{
  "name": "ResearchAssistant",
  "agent_type": "looping",
  "description": "A professional web researcher that performs multi-step research using web search, Wikipedia, ArXiv, and content fetching. Validates information across multiple sources. Best for: current events, fact verification, academic research.",
  "tools": [
    "web_search",
    "fetch_web_content",
    "save_to_long_term_memory"
  ],
  "llm": {
    "provider": "openai",
    "model": "gpt-4-turbo",
    "temperature": 0.7,
    "max_tokens": 4000
  },
  "prompt": {
    "system": "You are a research assistant. When given a topic:\n1. Use web_search to find sources\n2. Use fetch_web_content to read articles\n3. Analyze and synthesize information\n4. Save key findings to memory\n\nWhen complete, respond with TERMINATE.",
    "user": "Research the latest developments in AI agent architectures"
  },
  "code_executor": null,
  "model_client_stream": false,
  "sources": null,
  "system_message": null,
  "max_consecutive_auto_reply": 20,
  "reflect_on_tool_use": true,
  "terminate_on_text": false,
  "tool_call_loop": true,
  "sub_agents": null,
  "mode": null,
  "orchestrator_prompt": null,
  "include_inner_dialog": true,
  "initialization_function": null
}
```

---

## Agent Types

### 1. Looping Agent

**Use When:**
- Single-purpose agent (research, code execution, data processing)
- Simple tool usage patterns
- No need for team coordination

**Configuration:**
```json
{
  "agent_type": "looping",
  "tool_call_loop": true,
  "reflect_on_tool_use": true,
  "max_consecutive_auto_reply": 20
}
```

**Example Use Cases:**
- Web research with multiple searches
- Code execution with iterative debugging
- Data processing pipelines

---

### 2. Multimodal Tools Looping Agent

**Use When:**
- Agent needs to "see" and interpret images
- Working with screenshots, charts, diagrams
- Image analysis or generation tasks

**Requirements:**
- Vision-capable model (gpt-4o, gpt-4o-mini, claude-3-opus, etc.)
- Tools that return image paths or base64 data

**Configuration:**
```json
{
  "agent_type": "multimodal_tools_looping",
  "tools": ["take_screenshot", "generate_chart"],
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.0
  }
}
```

**How It Works:**
1. Tool returns: `"Screenshot saved to /path/image.png"`
2. Agent automatically detects image reference
3. Converts to MultiModalMessage with text + image
4. Vision LLM "sees" and analyzes the image

**Supported Image Formats:**
- File paths: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`
- Base64 encoded: `data:image/png;base64,...`

**See:** [MULTIMODAL_AGENT_GUIDE.md](MULTIMODAL_AGENT_GUIDE.md)

---

### 3. Dynamic Initialization Looping Agent

**Use When:**
- Agent needs custom initialization logic
- System prompt contains placeholders requiring runtime values
- Need to load data, connect to DB, verify resources on startup

**Configuration:**
```json
{
  "agent_type": "dynamic_init_looping",
  "initialization_function": "memory.initialize_memory_agent",
  "prompt": {
    "system": "You are a memory agent.\n\n{{SHORT_TERM_MEMORY}}\n\nUse memory tools..."
  }
}
```

**Initialization Function Example:**
```python
# tools/memory.py

from utils.context import get_current_agent
import logging

logger = logging.getLogger(__name__)

def initialize_memory_agent():
    """Load memory from file and inject into system prompt"""
    try:
        agent = get_current_agent()

        # Load memory content
        with open('backend/data/memory/short_term_memory.txt', 'r') as f:
            memory = f.read()

        # Replace placeholder in system prompt
        if agent and agent._system_messages:
            agent._system_messages[0].content = agent._system_messages[0].content.replace(
                "{{SHORT_TERM_MEMORY}}",
                memory
            )

        return f"Memory initialized: {len(memory)} characters"
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return f"Error: {e}"
```

**See:** [DYNAMIC_INIT_AGENT_IMPLEMENTATION.md](DYNAMIC_INIT_AGENT_IMPLEMENTATION.md)

---

### 4. Nested Team Agent

**Use When:**
- Complex multi-step workflows requiring specialization
- Need different agents for different capabilities
- Want orchestrator to coordinate work between sub-agents

**Configuration:**
```json
{
  "agent_type": "nested_team",
  "sub_agents": ["Manager", "Researcher", "Engineer", "Memory"],
  "mode": "selector",
  "orchestrator_prompt": "__function__",
  "tool_call_loop": false
}
```

**Orchestrator Agent (Manager.json):**
```json
{
  "name": "Manager",
  "agent_type": "looping",
  "tools": [],
  "prompt": {
    "system": "You are the Manager coordinating a team.\n\n{{AVAILABLE_AGENTS}}\n\nDelegate tasks using: NEXT AGENT: <Name>"
  }
}
```

**At runtime**, `{{AVAILABLE_AGENTS}}` is automatically replaced with:
```
The agents involved in this conversation besides you are:
- Memory: An agent that manages short-term memory and persistent memory banks...
- Researcher: A professional web researcher and fact-checker...
- Engineer: A software engineer that writes and executes Python or Bash code...
```

**Orchestration Modes:**
- `selector` - Orchestrator chooses ONE agent per turn (most common)
- `broadcast` - All agents receive message simultaneously

**See:** [DYNAMIC_AGENT_DESCRIPTION_INJECTION.md](DYNAMIC_AGENT_DESCRIPTION_INJECTION.md)

---

## Agent Description Best Practices

The `description` field is **critical** for nested team orchestration. The orchestrator uses descriptions to make intelligent routing decisions.

### Good Description Structure

```
[Role] that [key capability]. [Tool/approach details]. Capable of: [specific capabilities list]. Best for: [use cases]. Avoid: [anti-patterns].
```

### Examples

**✅ Good - Comprehensive:**
```json
{
  "name": "Researcher",
  "description": "A professional web researcher and fact-checker that performs multi-step research using web search, Wikipedia, ArXiv, and content fetching. Validates information across multiple sources, fact-checks sensitive topics, and runs in a loop until complete information is gathered. Best for: current events, fact verification, academic research, general knowledge queries, and any task requiring up-to-date web information."
}
```

**✅ Good - Clear Capabilities:**
```json
{
  "name": "Engineer",
  "description": "A software engineer that writes and executes Python or Bash code in an isolated workspace (./workspace directory). Can provide code snippets, create executable scripts, run code iteratively to debug errors, and save outputs to workspace files. Capable of: data processing, file manipulation, system operations, calculations, API integrations, automation scripts, testing, and any task solvable through code. All executed code and generated files are saved in backend/workspace/. Avoid using for web research - use Researcher instead."
}
```

**❌ Bad - Too Vague:**
```json
{
  "description": "An agent that does research"
}
```

**❌ Bad - Missing Use Cases:**
```json
{
  "description": "Writes and executes code"
}
```

### Description Checklist

- [ ] Defines the agent's role clearly
- [ ] Lists specific tools or approaches used
- [ ] Enumerates concrete capabilities
- [ ] Provides use case examples ("Best for:")
- [ ] Includes anti-patterns ("Avoid using for:")
- [ ] Written from orchestrator's perspective
- [ ] Concise but comprehensive (1-3 sentences)

---

## LLM Configuration

### Provider Options

**OpenAI:**
- `gpt-4o` - Latest multimodal model (vision + audio)
- `gpt-4o-mini` - Faster, cheaper multimodal model
- `gpt-4-turbo` - Large context, good for complex tasks
- `gpt-4` - Stable, reliable
- `gpt-3.5-turbo` - Fast, economical

**Anthropic:**
- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced
- `claude-3-haiku-20240307` - Fast, economical

**Google:**
- `gemini-1.5-pro` - Large context (2M tokens)
- `gemini-pro` - General purpose

### Temperature Guidelines

- `0.0` - Deterministic, consistent (code generation, data extraction)
- `0.3-0.5` - Slightly creative (technical writing)
- `0.7-0.9` - Creative (brainstorming, content creation)
- `1.0+` - Highly creative (experimental)

### Token Limits

- Set `max_tokens: null` for unlimited (model default)
- Set specific limit to control costs
- Consider context window size when setting limits

---

## Prompt Engineering

### System Prompt Structure

```
[Role definition]

[Available tools and when to use them]

[Step-by-step workflow]

[Output format expectations]

[Termination criteria]
```

### Example System Prompt

```
You are a research assistant that finds, analyzes, and remembers information.

Available tools:
- web_search: Find relevant sources
- fetch_web_content: Read full articles
- save_to_long_term_memory: Store key findings

When given a research topic:
1. Use web_search to find relevant sources
2. Use fetch_web_content to read full articles
3. Analyze and synthesize the information
4. Save key findings to long-term memory with descriptive tags
5. Provide a comprehensive summary with sources

Always cite your sources and tag memories appropriately.

When complete, respond with TERMINATE.
```

### Placeholder Variables

**For nested_team orchestrators:**
- `{{AVAILABLE_AGENTS}}` - Auto-populated with sub-agent descriptions

**For dynamic_init_looping:**
- Any custom placeholder (e.g., `{{SHORT_TERM_MEMORY}}`, `{{DATABASE_SCHEMA}}`)
- Replaced by initialization function

---

## Tool Selection

### Best Practices

1. **Only include tools the agent actually needs**
   - Too many tools confuse the LLM
   - Group related functionality

2. **Tool naming matters**
   - Use descriptive names
   - Follow verb_noun pattern (e.g., `save_to_memory`, `fetch_web_content`)

3. **Consider tool dependencies**
   - Some tools work together (e.g., `web_search` + `fetch_web_content`)
   - Order doesn't matter (auto-loaded alphabetically)

### Available Tools

Check current tools:
```bash
curl http://localhost:8000/api/tools
```

Common tools:
- `web_search` - Search the web (DuckDuckGo)
- `fetch_web_content` - Retrieve webpage content
- `save_to_short_term_memory` / `get_short_term_memory` - In-conversation memory
- `save_to_long_term_memory` / `retrieve_similar_memories` - Vector-based persistent memory
- `execute_python_code` / `execute_bash_command` - Code execution
- `take_screenshot` - Capture screen images
- `register_api` / `call_api` - HTTP API interactions

---

## Advanced Configuration

### Reflection on Tool Use

```json
{
  "reflect_on_tool_use": true
}
```

When enabled, agent thinks about tool results before deciding next action. Improves reasoning quality but increases tokens.

### Max Consecutive Auto-Reply

```json
{
  "max_consecutive_auto_reply": 20
}
```

Prevents infinite loops. Agent terminates after N turns without user input.

### Model Client Stream

```json
{
  "model_client_stream": false
}
```

Enable streaming for real-time token-by-token output (not yet fully implemented).

### Include Inner Dialog

```json
{
  "include_inner_dialog": true
}
```

For nested teams, shows agent-to-agent messages in output.

---

## Testing Agents

### Via API

```bash
# Get agent config
curl http://localhost:8000/api/agents/ResearchAssistant

# Test via WebSocket (use frontend or WebSocket client)
```

### Via Frontend

1. Navigate to `http://localhost:3000/agentic/agents`
2. Select agent from left panel
3. Click "Run Agent" button
4. Monitor execution in right panel console

### Via Voice Assistant

1. Navigate to `http://localhost:3000/agentic/voice`
2. Start session
3. Say: "Ask the Researcher to find information about quantum computing"

---

## Common Patterns

### Research Agent

```json
{
  "agent_type": "looping",
  "tools": ["web_search", "fetch_web_content", "save_to_long_term_memory"],
  "llm": {"provider": "openai", "model": "gpt-4-turbo", "temperature": 0.7},
  "tool_call_loop": true,
  "reflect_on_tool_use": true
}
```

### Code Execution Agent

```json
{
  "agent_type": "looping",
  "tools": ["execute_python_code", "execute_bash_command"],
  "llm": {"provider": "openai", "model": "gpt-4-turbo", "temperature": 0.0},
  "tool_call_loop": true
}
```

### Vision Agent

```json
{
  "agent_type": "multimodal_tools_looping",
  "tools": ["take_screenshot", "analyze_image"],
  "llm": {"provider": "openai", "model": "gpt-4o", "temperature": 0.0}
}
```

### Memory Agent

```json
{
  "agent_type": "dynamic_init_looping",
  "initialization_function": "memory.initialize_memory_agent",
  "tools": ["save_to_short_term_memory", "save_to_long_term_memory"]
}
```

### Team Coordinator

```json
{
  "agent_type": "nested_team",
  "sub_agents": ["Manager", "Researcher", "Engineer"],
  "mode": "selector"
}
```

---

## Troubleshooting

### Agent Not Loading

```bash
# Check agent file exists
ls backend/agents/AgentName.json

# Validate JSON syntax
python3 -m json.tool < backend/agents/AgentName.json

# Check backend logs
tail -f logs/backend.log | grep AgentName
```

### Agent Not Using Tools

- Check `tool_call_loop: true` is set
- Verify tools exist: `curl http://localhost:8000/api/tools`
- Check system prompt mentions tools explicitly
- Review max_consecutive_auto_reply limit

### Agent Terminates Too Early

- Increase `max_consecutive_auto_reply`
- Remove "TERMINATE" from system prompt examples
- Check `terminate_on_text: false`

### Nested Team Not Delegating

- Verify orchestrator has `{{AVAILABLE_AGENTS}}` in system prompt
- Check sub-agent descriptions are comprehensive
- Review orchestrator prompt for delegation syntax
- Ensure `mode: "selector"` is set

---

## See Also

- [MULTIMODAL_AGENT_GUIDE.md](MULTIMODAL_AGENT_GUIDE.md) - Vision-capable agents
- [DYNAMIC_INIT_AGENT_IMPLEMENTATION.md](DYNAMIC_INIT_AGENT_IMPLEMENTATION.md) - Custom initialization
- [DYNAMIC_AGENT_DESCRIPTION_INJECTION.md](DYNAMIC_AGENT_DESCRIPTION_INJECTION.md) - Orchestrator setup
- [DATABASE_AGENT_GUIDE.md](DATABASE_AGENT_GUIDE.md) - Database agent example
- [API_AGENT_GUIDE.md](API_AGENT_GUIDE.md) - API agent example
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - System architecture

---

**Last Updated:** 2025-12-01
