# Task 4: Create Planner Agent

**Status:** Pending
**Priority:** High
**Assigned to:** TBD
**Estimated Effort:** 8-12 hours

**⚠️ Dependencies:** Task #3 (Agent Registry) must be completed first

---

## Overview

Create a strategic planning agent that is aware of all available agents and their capabilities, and can create detailed execution plans before delegating work to the appropriate agents.

---

## Objectives

- Build agent that can assess full team capabilities
- Create detailed execution plans with agent assignments
- Match subtasks to appropriate agents based on tools/capabilities
- Provide structured output for Manager to execute
- Handle complex multi-agent workflows
- Remember successful planning patterns

---

## Architecture

### Planner + Manager Workflow

```
User Request
    ↓
Voice/MainConversation
    ↓
Planner Agent
    ├─→ get_available_agents()  (query team)
    ├─→ Analyze request
    ├─→ Break into subtasks
    ├─→ Match tasks to agents
    └─→ Create execution plan
    ↓
Manager Agent
    ├─→ Read plan
    ├─→ Delegate to agents sequentially
    └─→ Coordinate execution
    ↓
Team Agents (Researcher, Developer, etc.)
    ↓
Results
```

---

## Agent Specification

### Basic Configuration

**Agent Name:** `Planner`

**Agent Type:** `dynamic_init_looping`

**Initialization Function:** `agent_discovery.initialize_planner` (optional)

**LLM:** GPT-4 or Claude Opus (strong reasoning needed)

**Description:** "Strategic planning agent that analyzes tasks, assesses team capabilities, and creates detailed execution plans."

### System Prompt

```
You are the Planner, a strategic planning agent for a multi-agent team.

Your role is to:
1. Understand complex user requests
2. Query available team agents and their capabilities
3. Break down requests into clear subtasks
4. Match each subtask to the most appropriate agent
5. Create detailed, structured execution plans
6. Consider dependencies and optimal task ordering

You should NOT execute tasks directly - only plan them.

Available Tools:
- get_available_agents(): See all team agents and their capabilities
- get_agent_info(name): Get detailed info about a specific agent
- find_agents_for_task(description): Find agents suited for a task
- create_execution_plan(plan_data): Generate structured plan document
- save_plan_to_file(filename, content): Save plan for reference

When creating plans:
- Start by querying available agents
- Identify required capabilities for the task
- Match subtasks to agents with appropriate tools
- Consider task dependencies (what must happen first)
- Provide clear instructions for each step
- Estimate complexity/duration if possible
- Include verification/testing steps

Output Format:
Your plan should be a structured markdown document with:
- Executive Summary
- Required Agents
- Step-by-step breakdown with agent assignments
- Dependencies and ordering
- Success criteria

After creating the plan, say TERMINATE.
```

---

## Tools to Implement

### Planning Tools

**File:** `backend/tools/planning.py`

#### `create_execution_plan(plan_data: dict) -> str`
```python
"""
Create a structured execution plan from plan data.

Args:
    plan_data: Dictionary with keys:
        - summary: str (executive summary)
        - agents_needed: List[str] (agent names)
        - steps: List[dict] (step details)
        - dependencies: dict (step dependencies)
        - success_criteria: List[str]

Returns:
    Formatted markdown plan
"""
```

#### `save_plan_to_file(filename: str, content: str, directory: str = "plans") -> str`
```python
"""
Save execution plan to file for reference.

Args:
    filename: Name for the plan file
    content: Plan content (markdown)
    directory: Directory to save in (default: workspace/plans/)

Returns:
    Success message with file path
"""
```

#### `load_plan_from_file(filename: str) -> str`
```python
"""
Load a previously saved plan.

Args:
    filename: Name of the plan file

Returns:
    Plan content or error
"""
```

#### `list_saved_plans() -> str`
```python
"""
List all saved execution plans.

Returns:
    Formatted list of plans with metadata
"""
```

#### `analyze_task_complexity(task_description: str) -> str`
```python
"""
Analyze task complexity and provide estimates.

Args:
    task_description: Description of the task

Returns:
    Complexity analysis:
    - Difficulty level (simple/moderate/complex/very complex)
    - Estimated agent-hours
    - Required capabilities
    - Potential challenges
"""
```

#### `suggest_agent_team(task_description: str) -> str`
```python
"""
Suggest which agents should be involved in a task.

Args:
    task_description: Description of the task

Returns:
    Recommended team composition with reasoning
"""
```

### Discovery Tools (from Task #3)

Planner uses these tools from `agent_discovery.py`:
- `get_available_agents()` - List all agents
- `get_agent_info(name)` - Get agent details
- `find_agents_for_task(description)` - Find suitable agents

---

## Example Planning Workflow

### User Request
```
"Build a web scraper that stores results in a database and sends email notifications"
```

### Planner Process

**Step 1: Query Team**
```python
# Planner calls: get_available_agents()
# Returns: Researcher, Developer, FileManager, Memory, etc.
```

**Step 2: Analyze Task**
```
Required capabilities:
- Web scraping → Researcher (web tools)
- Code development → Developer (code execution)
- Database → FileManager (file storage) or Developer (code)
- Email → Developer (code)
- Testing → Developer (code execution)
```

**Step 3: Create Plan**
```markdown
# Execution Plan: Web Scraper with Notifications

## Executive Summary
Build a web scraping application with database storage and email notifications.
Estimated complexity: Moderate
Estimated time: 4-6 agent-hours

## Required Agents
- Researcher: Investigate target website structure
- Developer: Write code, integrate components, test
- FileManager: Set up database storage

## Execution Steps

### Step 1: Website Investigation
**Agent:** Researcher
**Task:** Analyze target website structure, identify data patterns, find API endpoints if available
**Success Criteria:** Documentation of website structure and data extraction points

### Step 2: Scraper Development
**Agent:** Developer
**Task:** Write Python scraper using requests/BeautifulSoup based on Researcher's findings
**Dependencies:** Step 1
**Success Criteria:** Working scraper that extracts target data

### Step 3: Database Setup
**Agent:** FileManager
**Task:** Create database schema for storing scraped data
**Dependencies:** Step 2 (know what data structure is needed)
**Success Criteria:** Database created with appropriate schema

### Step 4: Database Integration
**Agent:** Developer
**Task:** Integrate scraper with database storage
**Dependencies:** Step 2, Step 3
**Success Criteria:** Scraper successfully saves data to database

### Step 5: Email Notifications
**Agent:** Developer
**Task:** Implement email notification system (SMTP)
**Dependencies:** Step 4
**Success Criteria:** Emails sent on scraping events

### Step 6: Testing
**Agent:** Developer
**Task:** Write tests for scraper, database, and notifications
**Dependencies:** Steps 2-5
**Success Criteria:** All tests pass

### Step 7: Integration Verification
**Agent:** Manager
**Task:** Verify all components work together end-to-end
**Dependencies:** All previous steps
**Success Criteria:** Full workflow executes successfully

## Dependencies
- Step 2 depends on Step 1
- Step 3 depends on Step 2 (need data structure)
- Step 4 depends on Steps 2 & 3
- Step 5 depends on Step 4
- Step 6 depends on Steps 2-5
- Step 7 depends on all steps

## Success Criteria
- ✅ Scraper extracts data successfully
- ✅ Data stored in database correctly
- ✅ Email notifications sent on events
- ✅ All tests pass
- ✅ End-to-end workflow verified

## Estimated Timeline
- Step 1: 30 min
- Step 2: 1 hour
- Step 3: 30 min
- Step 4: 1 hour
- Step 5: 1 hour
- Step 6: 1 hour
- Step 7: 30 min
**Total:** ~5.5 hours
```

**Step 4: Save Plan**
```python
# Planner calls: save_plan_to_file("web_scraper_plan.md", plan_content)
```

**Step 5: Handoff to Manager**
```
Plan created and saved. Manager can now execute the plan step by step.
TERMINATE
```

---

## Integration with Manager

### Manager Updates (Optional)

**File:** `backend/agents/Manager.json`

Add to system prompt:
```
You can also request planning assistance from the Planner agent for complex tasks.
Simply delegate to Planner with a description of what needs to be planned.
Planner will create a detailed execution plan that you can then follow.
```

### Manager Execution Pattern

When Manager receives a plan:

1. Read the plan document
2. Execute steps sequentially
3. Respect dependencies
4. Verify success criteria for each step
5. Report progress to user

---

## Agent Configuration File

**File:** `backend/agents/Planner.json`

```json
{
  "name": "Planner",
  "agent_type": "dynamic_init_looping",
  "initialization_function": "planning.initialize_planner",
  "tools": [
    "get_available_agents",
    "get_agent_info",
    "find_agents_for_task",
    "create_execution_plan",
    "save_plan_to_file",
    "load_plan_from_file",
    "list_saved_plans",
    "analyze_task_complexity",
    "suggest_agent_team"
  ],
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.0,
    "max_tokens": null
  },
  "prompt": {
    "system": "You are the Planner, a strategic planning agent...",
    "user": "Create a plan for the user's request."
  },
  "code_executor": null,
  "model_client_stream": false,
  "sources": null,
  "description": "Strategic planning agent that creates detailed execution plans by analyzing team capabilities",
  "system_message": null,
  "max_consecutive_auto_reply": 20,
  "reflect_on_tool_use": true,
  "terminate_on_text": false,
  "tool_call_loop": true,
  "sub_agents": null,
  "mode": null,
  "orchestrator_prompt": null,
  "include_inner_dialog": true
}
```

---

## Files to Create

| File | Purpose | Lines | Priority |
|------|---------|-------|----------|
| `backend/agents/Planner.json` | Agent configuration | ~50 | Required |
| `backend/tools/planning.py` | Planning tools | ~300 | Required |
| `backend/tests/test_planner.py` | Unit tests | ~200 | Recommended |
| `backend/docs/PLANNER_AGENT_GUIDE.md` | Usage guide | ~150 | Recommended |

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `backend/agents/MainConversation.json` | Add Planner to sub_agents | Optional |
| `backend/agents/Manager.json` | Add Planner awareness | Optional |
| `backend/api/realtime_voice.py` | Mention Planner in voice prompt | Optional |

---

## Testing Plan

### Unit Tests

**File:** `backend/tests/test_planner.py`

```python
def test_create_execution_plan():
    """Test plan creation from structured data."""

def test_save_and_load_plan():
    """Test plan persistence."""

def test_analyze_task_complexity():
    """Test complexity analysis."""

def test_suggest_agent_team():
    """Test team suggestion logic."""

def test_planner_agent_integration():
    """Test Planner agent with discovery tools."""
```

### Integration Tests

**Test Scenarios:**

1. **Simple Task Planning:**
   - Request: "Search for Python tutorials"
   - Expected: Plan with Researcher agent

2. **Medium Task Planning:**
   - Request: "Create a data visualization dashboard"
   - Expected: Plan with Developer, maybe Researcher

3. **Complex Task Planning:**
   - Request: "Build a web scraper with database and notifications"
   - Expected: Multi-step plan with Researcher, Developer, FileManager

4. **Planner + Manager Workflow:**
   - Planner creates plan
   - Manager reads and executes plan
   - Verify steps execute in correct order

---

## Success Criteria

- ✅ Planner can query agent registry successfully
- ✅ Creates structured execution plans in markdown
- ✅ Plans correctly match tasks to agent capabilities
- ✅ Handles complex multi-agent workflows
- ✅ Can save and load plans
- ✅ Works standalone and in nested teams
- ✅ Manager can consume and execute Planner's output
- ✅ Voice assistant can delegate to Planner
- ✅ All tests pass
- ✅ Documentation complete

---

## Advanced Features (Future)

### Plan Optimization
- Identify parallelizable tasks
- Optimize task ordering for efficiency
- Resource allocation (multiple agents working simultaneously)

### Learning from History
- Store successful plans in vector store
- Retrieve similar past plans for reference
- Learn which agent assignments work best

### Interactive Planning
- Ask clarifying questions before planning
- Provide multiple plan options
- Allow user to customize plans

### Plan Execution Monitoring
- Track plan progress
- Detect when plan needs adjustment
- Replan if steps fail

---

## Integration with Other Tasks

### With Memory Agent (Task #1)
- Store successful planning patterns
- Remember user preferences for planning
- Learn from past plans

### With File Manager (Task #2)
- Save plans as structured documents
- Organize plans by project/topic
- Search past plans semantically

### With Agent Registry (Task #3)
- **Required dependency**
- Query team capabilities dynamically
- Adapt to team composition changes

---

## Example Use Cases

### 1. Research Project
```
User: "Research the latest AI trends and create a summary report"

Planner creates:
1. Researcher: Search for AI trends (arxiv, web)
2. Researcher: Gather articles and papers
3. Developer: Create summary document
4. FileManager: Organize and save report
```

### 2. Development Task
```
User: "Add a new feature to the codebase"

Planner creates:
1. Developer: Review existing code
2. Developer: Design feature architecture
3. Developer: Implement feature
4. Developer: Write tests
5. Developer: Integration testing
```

### 3. Multi-Agent Workflow
```
User: "Create a presentation about our product based on web research"

Planner creates:
1. Researcher: Research similar products
2. Researcher: Gather product information
3. Developer: Create presentation slides (code)
4. FileManager: Organize assets
5. Memory: Save key product facts
```

---

## Dependencies

**Required:**
- ✅ Task #3 (Agent Registry) - MUST be completed first
- Agent discovery tools
- Dynamic initialization system

**Optional:**
- Task #1 (Memory) - Enhanced with memory of past plans
- Task #2 (FileManager) - Enhanced plan storage

---

## Rollback Plan

If Planner causes issues:

1. Remove from MainConversation sub_agents
2. Keep Planner.json but don't use
3. Planning tools remain (no harm)
4. Revert to direct Manager delegation

---

## Performance Considerations

- Plan generation may take 10-30 seconds for complex tasks
- LLM should be fast model (gpt-4o, not gpt-4-turbo)
- Cache agent registry to avoid repeated queries
- Save plans to reduce re-planning

---

## Notes

- Planner should NOT execute tasks, only plan them
- Consider temperature=0.0 for consistent planning
- May want to validate plans before saving
- Consider plan version control in future
- Could add plan visualization in frontend

---

**Last Updated:** 2025-11-29
