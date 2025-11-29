# Project Task List

## Active Tasks

### 1. Integrate Memory Agent into Voice Assistant
**Status:** Pending
**Priority:** High
**Description:** Integrate the Memory agent into the MainConversation nested team for the voice assistant, enabling persistent memory management during voice sessions.

**Requirements:**
- Add Memory agent to MainConversation's `sub_agents` array
- Ensure Memory agent is accessible to voice assistant via nested team orchestration
- Test memory persistence across voice sessions
- Verify memory tools (save_to_short_term_memory, etc.) work correctly
- Update voice system prompt to mention memory capabilities

**Files to Modify:**
- `backend/agents/MainConversation.json` - Add Memory to sub_agents
- `backend/api/realtime_voice.py` - Update voice prompt if needed
- Test with voice assistant to verify integration

**Success Criteria:**
- Voice assistant can delegate memory tasks to Memory agent
- Memory persists across conversation sessions
- Memory agent responds appropriately in nested team context

---

### 2. Create File Manager Agent
**Status:** Pending
**Priority:** High
**Description:** Create a comprehensive file manager agent that can create, read, understand, and manage files using a vector store database for semantic search and content organization.

**Requirements:**
- **Agent Configuration:**
  - Agent type: `looping` or `dynamic_init_looping`
  - LLM: GPT-4 or Claude for understanding capabilities
  - System prompt emphasizing file organization and understanding

- **Tools to Create/Use:**
  - `create_file` - Create new files with content
  - `read_file` - Read file contents
  - `update_file` - Modify existing files
  - `delete_file` - Remove files with confirmation
  - `list_files` - List files in directory with filtering
  - `search_files_semantic` - Vector search across file contents
  - `index_file_to_vectorstore` - Add file to ChromaDB
  - `summarize_file` - Generate file summaries
  - `organize_files` - Auto-organize by content/type

- **Vector Store Integration:**
  - Use ChromaDB for file content embeddings
  - Metadata: filename, path, type, created/modified dates, summary
  - Semantic search capabilities across indexed files
  - Auto-indexing option for new/modified files

**Files to Create:**
- `backend/agents/FileManager.json` - Agent configuration
- `backend/tools/file_management.py` - File operation tools
- `backend/tools/file_vectorstore.py` - Vector store tools for files

**Files to Modify:**
- `backend/config/config_loader.py` - If custom tool loading needed
- `frontend/src/App.js` - Add route for FileManager if UI needed

**Success Criteria:**
- Can create, read, update, delete files via agent
- Vector store successfully indexes file contents
- Semantic search returns relevant files
- Agent can understand file context and suggest organization
- Works both standalone and as sub-agent in nested teams

---

### 3. Generalize Agent List Loading
**Status:** Pending
**Priority:** High
**Description:** Centralize agent configuration loading by creating a global variable or configuration system that automatically loads agent names and descriptions from JSON files, eliminating hard-coded agent lists throughout the codebase. **Critical for Manager and Planner agents** to access available agent capabilities dynamically.

**📋 Analysis:** See `docs/AGENT_SELECTION_ANALYSIS.md` for complete analysis of current system and proposed solution.

**Current Problems:**
- **Manager agent has hard-coded agent list** in system prompt (`backend/agents/Manager.json:12`)
- Agent descriptions manually duplicated (Researcher, Developer capabilities)
- No runtime discovery - Manager can't learn about new agents
- MainConversation's `sub_agents` list must be manually updated
- Frontend has hard-coded agent references in routes and dropdowns

**Proposed Solution: Agent Registry System**

**Phase 1: Backend Foundation**
1. **Create Agent Registry Module** (`backend/config/agent_registry.py`)
   - `AgentMetadata` class: name, description, agent_type, tools, capabilities_summary
   - `AgentRegistry` class: Scans agents/, caches metadata, thread-safe
   - Methods: `get_all_agents()`, `get_agent(name)`, `get_agents_by_tool(tool_name)`, `refresh()`

2. **Create Agent Discovery Tools** (`backend/tools/agent_discovery.py`)
   - `get_available_agents()` - Returns formatted list of all agents with capabilities
   - `get_agent_info(name)` - Returns detailed info about specific agent
   - `find_agents_for_task(description)` - Suggests agents for a task based on keywords/tools
   - `initialize_manager_with_team()` - Dynamic initialization function for Manager

3. **Add API Endpoint** (`backend/main.py`)
   - `GET /api/agents/metadata` - Returns lightweight agent metadata for UI

**Phase 2: Manager Integration**
1. **Convert Manager to dynamic initialization** (`backend/agents/Manager.json`)
   - Change to: `"agent_type": "dynamic_init_looping"`
   - Add: `"initialization_function": "agent_discovery.initialize_manager_with_team"`
   - Add tools: `["get_available_agents", "get_agent_info", "find_agents_for_task"]`
   - Update prompt with placeholder: `{{AGENT_ROSTER}}` (replaced during initialization)

2. **Benefits:**
   - Manager prompt auto-updates when agents are added/removed
   - Can query available agents at runtime
   - Single source of truth (agent JSON files)

**Phase 3: Frontend Integration**
1. **Create Agent Context** (`frontend/src/contexts/AgentContext.js`)
   - Loads agents from `/api/agents/metadata`
   - Auto-refreshes every 30 seconds
   - Provides `useAgents()` hook for components

2. **Update Components:**
   - `App.js` - Use dynamic agent loading for routes
   - `AgentEditor.js` - Dynamic sub_agents dropdown
   - `VoiceAssistant.js` - Dynamic agent references

**Phase 4: Planner Agent** (Depends on Phases 1-3)
- Planner uses `get_available_agents()` to assess team
- Creates plans matching tasks to agent capabilities
- Works seamlessly with Manager for execution

**Files to Create:**
- `backend/config/agent_registry.py` - Agent metadata loader and cache
- `backend/tools/agent_discovery.py` - Discovery tools for agents + Manager init function
- `frontend/src/contexts/AgentContext.js` - Global agent configuration context
- `docs/AGENT_SELECTION_ANALYSIS.md` - ✅ Complete analysis document

**Files to Modify:**
- `backend/main.py` - Add `/api/agents/metadata` endpoint
- `backend/config/config_loader.py` - Integrate with agent registry (if needed)
- `backend/agents/Manager.json` - Convert to dynamic_init_looping + add discovery tools
- `frontend/src/App.js` - Wrap with AgentProvider, use dynamic routes
- `frontend/src/features/agents/components/AgentEditor.js` - Dynamic sub_agents selector
- `frontend/src/features/voice/pages/VoiceAssistant.js` - Dynamic agent references
- `frontend/src/api.js` - Add `getAgentsMetadata()` function

**Implementation Sequence:**
1. ✅ **Analyze current system** - Documented in `docs/AGENT_SELECTION_ANALYSIS.md`
2. **Phase 1** - Backend foundation (registry, tools, API)
3. **Phase 2** - Manager integration (test with existing agents)
4. **Phase 3** - Frontend integration (dynamic UI)
5. **Phase 4** - Planner agent (uses registry for planning)

**Success Criteria:**
- No hard-coded agent names/lists in Manager prompt
- Agent list automatically updates when JSON files added/removed
- Manager can call `get_available_agents()` to see current team
- UI components dynamically render available agents
- Planner agent can assess full team capabilities
- Performance: Agent list cached and efficiently loaded
- Backward compatible during migration
- Documentation updated to reflect new pattern

**Testing Strategy:**
- Unit tests: `AgentRegistry` loading and caching
- Integration tests: Manager uses discovery tools correctly
- E2E tests: Full workflow from user request to delegation
- Comparison tests: Verify new system matches old behavior

---

### 4. Create Planner Agent
**Status:** Pending
**Priority:** High
**Description:** Create a strategic planning agent that is aware of all available agents and their capabilities, and can create detailed execution plans before delegating work to the appropriate agents.

**Requirements:**
- **Agent Configuration:**
  - Agent type: `looping` (for planning) or `dynamic_init_looping` (to load agent registry on startup)
  - LLM: GPT-4 or Claude Opus (strong reasoning needed for planning)
  - System prompt emphasizing strategic thinking, task decomposition, and agent capability matching
  - Should NOT execute tasks directly, only plan and delegate

- **Core Capabilities:**
  - Query available agents and their capabilities using `get_available_agents()` tool
  - Analyze user request and break down into subtasks
  - Match subtasks to appropriate agents based on capabilities
  - Create detailed execution plan with agent assignments
  - Consider dependencies and optimal task ordering
  - Output structured plan in markdown format

- **Tools to Use:**
  - `get_available_agents()` - Query agent registry for capabilities (from Task #3)
  - `create_execution_plan()` - Generate structured plan document
  - `save_plan_to_file()` - Save plan for reference
  - `analyze_task_complexity()` - Assess task difficulty and estimate duration
  - `suggest_agent_team()` - Recommend which agents to involve

- **Integration with Manager Agent:**
  - Planner creates the plan
  - Manager executes the plan by delegating to agents
  - Manager can request replanning if issues arise
  - Both can work together in MainConversation nested team

**Example Workflow:**
```
User: "Build a web scraper that stores results in a database and sends email notifications"

Planner analyzes:
1. Query agent registry
2. Identify required capabilities:
   - Web scraping (Researcher agent?)
   - Database operations (FileManager/Memory agent?)
   - Code development (Developer agent?)
   - Testing (Developer agent?)

3. Create plan:
   - Step 1: Researcher - Investigate target website structure
   - Step 2: Developer - Write scraping code
   - Step 3: FileManager - Set up database schema
   - Step 4: Developer - Integrate database storage
   - Step 5: Developer - Implement email notifications
   - Step 6: Developer - Write tests
   - Step 7: Manager - Coordinate execution and verify results

4. Output plan document
5. Hand off to Manager for execution
```

**Files to Create:**
- `backend/agents/Planner.json` - Agent configuration
- `backend/tools/planning.py` - Planning-specific tools
- `backend/docs/PLANNER_AGENT_GUIDE.md` - Usage documentation

**Files to Modify:**
- `backend/agents/MainConversation.json` - Add Planner to sub_agents (optional, can be standalone)
- `backend/agents/Manager.json` - Add awareness of Planner agent
- `backend/api/realtime_voice.py` - Add voice prompt mentioning Planner capabilities

**Success Criteria:**
- Planner can query and understand all available agents
- Creates detailed, structured execution plans
- Plans correctly match agent capabilities to tasks
- Can handle complex multi-agent workflows
- Works both standalone and integrated with Manager
- Plans are saved and accessible for reference
- Voice assistant can delegate planning tasks to Planner

**Integration Notes:**
- **Depends on Task #3** (agent registry) being completed first
- Should integrate with Memory agent to remember past successful plans
- Could use FileManager to store plan templates
- Manager agent should be updated to consume and execute Planner's output

---

## Completed Tasks

_(None yet)_

---

## Future Enhancements

- Multi-agent file collaboration workflows
- File versioning and change tracking
- Automatic file backup to vector store
- Cross-file reference detection
- File dependency analysis

---

**Last Updated:** 2025-11-29
