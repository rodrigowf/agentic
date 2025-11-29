# Task 1: Integrate Memory Agent into Voice Assistant

**Status:** Pending
**Priority:** High
**Assigned to:** TBD
**Estimated Effort:** 2-4 hours

---

## Overview

Integrate the Memory agent into the MainConversation nested team for the voice assistant, enabling persistent memory management during voice sessions.

---

## Objectives

- Add Memory agent to MainConversation's nested team
- Enable voice assistant to delegate memory tasks
- Ensure memory persists across conversation sessions
- Verify memory tools work correctly in nested team context

---

## Current State

**Memory Agent Exists:**
- Location: `backend/agents/Memory.json`
- Type: `dynamic_init_looping`
- Initialization: `memory.initialize_memory_agent`
- Tools: Memory management tools in `backend/tools/memory.py`

**MainConversation Current Sub-Agents:**
- Manager
- Researcher
- Developer

**Missing:** Memory agent not in MainConversation team

---

## Requirements

### 1. Update MainConversation Configuration

**File:** `backend/agents/MainConversation.json`

**Change:**
```json
"sub_agents": [
  "Manager",
  "Researcher",
  "Developer",
  "Memory"
]
```

### 2. Update Manager System Prompt (Optional)

**File:** `backend/agents/Manager.json`

**Current Prompt:** Lists only Researcher and Developer

**Proposed Addition:**
```
- Memory: Manages persistent memory storage including short-term and long-term memory.
  Can save important information, retrieve memories, and maintain context across sessions.
  Use for remembering user preferences, past conversations, or important facts.
```

**Note:** If Task #3 (Agent Registry) is implemented first, this becomes automatic.

### 3. Update Voice System Prompt (Optional)

**File:** `backend/api/realtime_voice.py`

**Consider adding:** Reference to Memory agent capabilities in voice system prompt so the voice assistant knows it can ask the team to remember things.

### 4. Test Memory Integration

**Test Cases:**
1. Voice command: "Remember that my favorite color is blue"
2. Verify Memory agent is invoked
3. Check memory saved to file/database
4. Voice command: "What's my favorite color?"
5. Verify Memory agent retrieves the information
6. Test across conversation sessions (disconnect/reconnect)

---

## Implementation Steps

### Step 1: Update MainConversation
```bash
# Edit the JSON file
# Add "Memory" to sub_agents array
```

### Step 2: Restart Backend
```bash
cd /home/rodrigo/agentic/backend
# Backend auto-reloads with uvicorn --reload
# Or restart manually if needed
```

### Step 3: Test via Frontend
```bash
# Open http://localhost:3000/voice
# Start voice session
# Test memory commands
```

### Step 4: Verify Memory Persistence
```bash
# Check memory files in backend/workspace/ or configured location
# Test retrieval across sessions
```

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `backend/agents/MainConversation.json` | Add "Memory" to sub_agents | Required |
| `backend/agents/Manager.json` | Add Memory description (if not using registry) | Optional |
| `backend/api/realtime_voice.py` | Update voice prompt (if desired) | Optional |

---

## Success Criteria

- ✅ Memory agent appears in MainConversation nested team
- ✅ Voice assistant can delegate memory tasks to Memory agent
- ✅ Memory persists across conversation sessions
- ✅ Memory tools (save_to_short_term_memory, etc.) work correctly
- ✅ Manager can successfully select Memory agent when needed
- ✅ No errors in backend logs during memory operations

---

## Testing Checklist

- [ ] Memory agent loaded in MainConversation team
- [ ] Voice command "Remember X" triggers Memory agent
- [ ] Memory saved successfully (check files/logs)
- [ ] Voice command "What did I ask you to remember?" retrieves memory
- [ ] Memory persists after disconnecting and reconnecting
- [ ] Manager selects Memory agent appropriately
- [ ] No console errors during memory operations

---

## Potential Issues & Solutions

### Issue 1: Memory Agent Not Selected
**Symptom:** Manager doesn't delegate to Memory agent
**Solution:** Update Manager's system prompt with Memory capabilities, or implement Task #3 for automatic discovery

### Issue 2: Memory Not Persisting
**Symptom:** Memory lost between sessions
**Solution:** Check memory file paths, ensure Memory agent initialization runs correctly

### Issue 3: Nested Team Selection Errors
**Symptom:** "Invalid agent name" errors
**Solution:** Verify "Memory" exactly matches agent name in Memory.json, check nested_agent.py selector logic

---

## Dependencies

**Required:**
- Memory agent (`backend/agents/Memory.json`) - ✅ Exists
- Memory tools (`backend/tools/memory.py`) - ✅ Exists
- MainConversation nested team - ✅ Exists

**Optional:**
- Task #3 (Agent Registry) - Makes Manager update automatic

---

## Rollback Plan

If integration causes issues:

1. Remove "Memory" from MainConversation.json sub_agents
2. Restart backend
3. Voice assistant continues working without memory

---

## Follow-up Tasks

After successful integration:

- Consider adding more memory tools (search memories, delete memories, etc.)
- Integrate Memory with Task #2 (File Manager) for file-based memory
- Add memory analytics/insights to voice dashboard
- Implement memory summarization for long-term storage

---

## Notes

- Memory agent uses dynamic initialization (`initialize_memory_agent`)
- Memory files typically stored in backend workspace
- Consider memory privacy/security for sensitive information
- May want to add user-specific memory namespaces in future

---

**Last Updated:** 2025-11-29
