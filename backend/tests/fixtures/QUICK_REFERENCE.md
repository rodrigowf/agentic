# Test Fixtures Quick Reference

## Import Patterns

```python
# Import everything
from tests.fixtures import *

# Import specific items
from tests.fixtures import (
    MOCK_LOOPING_AGENT,
    MOCK_WEB_SEARCH_RESPONSE,
    create_mock_tool_call_event
)

# Import from specific module
from tests.fixtures.agent_configs import MOCK_MULTIMODAL_AGENT
from tests.fixtures.tool_responses import create_mock_image_base64
```

## Quick Access

### Agents
```python
MOCK_LOOPING_AGENT           # Basic looping agent
MOCK_NESTED_AGENT            # Nested team with sub-agents
MOCK_MULTIMODAL_AGENT        # Vision-capable agent
MOCK_CODE_EXECUTOR_AGENT     # Code execution agent
MOCK_RESEARCHER_AGENT        # Research specialist
MOCK_MEMORY_AGENT            # Memory management

# Create custom
create_mock_agent_config(name="MyAgent", tools=["tool1"])
```

### Tool Responses
```python
# Research
MOCK_WEB_SEARCH_RESPONSE
MOCK_ARXIV_SEARCH_RESPONSE
MOCK_WIKIPEDIA_SEARCH_RESPONSE

# Memory
MOCK_MEMORY_SAVE_RESPONSE
MOCK_MEMORY_GET_RESPONSE

# Images
MOCK_SCREENSHOT_RESPONSE
MOCK_BASE64_IMAGE
create_mock_image_base64(width=400, height=300, text="TEST")

# Code execution
MOCK_BASH_EXECUTION_RESPONSE
MOCK_GIT_STATUS_RESPONSE

# Errors
MOCK_TOOL_ERROR_RESPONSE
MOCK_API_ERROR_RESPONSE
```

### WebSocket Events
```python
# System
MOCK_WS_CONNECT_EVENT
MOCK_WS_INIT_EVENT

# Messages
MOCK_WS_MESSAGE_EVENT
MOCK_WS_USER_MESSAGE_EVENT

# Tools
MOCK_WS_TOOL_CALL_EVENT
MOCK_WS_TOOL_RESULT_EVENT

# Claude Code
MOCK_CLAUDE_CODE_INIT_EVENT
MOCK_CLAUDE_CODE_TOOL_CALL_EVENT
MOCK_CLAUDE_CODE_COMPLETE_EVENT

# Sequences
MOCK_WS_COMPLETE_CONVERSATION_SEQUENCE
MOCK_CLAUDE_CODE_CONVERSATION_SEQUENCE

# Create custom
create_mock_tool_call_event("web_search", {"query": "test"})
create_mock_tool_result_event("web_search", "Results", "tool_id")
```

### Voice Data
```python
# Conversations
MOCK_VOICE_CONVERSATION
MOCK_VOICE_CONVERSATION_LIST

# Events
MOCK_VOICE_SESSION_CREATED
MOCK_VOICE_TRANSCRIPTION
MOCK_VOICE_FUNCTION_CALL

# Complete data
MOCK_VOICE_EVENTS
MOCK_COMPLETE_VOICE_CONVERSATION

# Helpers
filter_events_by_source(events, "voice")
get_event_sequence_by_type(events, ["ToolCallRequestEvent"])
```

## Common Snippets

### Test Agent Config
```python
def test_agent():
    agent = MOCK_LOOPING_AGENT
    assert agent.name == "TestLoopingAgent"
    assert agent.tool_call_loop == True
```

### Test Tool Response
```python
def test_search():
    response = MOCK_WEB_SEARCH_RESPONSE
    assert "Web Search Results" in response
```

### Test WebSocket Flow
```python
def test_tool_flow():
    call = create_mock_tool_call_event("web_search", {"query": "test"})
    result = create_mock_tool_result_event(
        "web_search",
        "Found results",
        call["data"]["data"]["id"]
    )
    assert result["data"]["data"]["is_error"] == False
```

### Test Voice Events
```python
def test_voice():
    voice_events = filter_events_by_source(MOCK_VOICE_EVENTS, "voice")
    assert len(voice_events) > 0
    assert all(e["source"] == "voice" for e in voice_events)
```

### Create Custom Agent
```python
def test_custom():
    agent = create_mock_agent_config(
        name="Custom",
        tools=["tool1", "tool2"],
        max_consecutive_auto_reply=15
    )
    assert len(agent.tools) == 2
```

## File Locations

| Module | Path |
|--------|------|
| Agent configs | `tests/fixtures/agent_configs.py` |
| Tool responses | `tests/fixtures/tool_responses.py` |
| WebSocket events | `tests/fixtures/websocket_events.py` |
| Voice data | `tests/fixtures/voice_data.py` |
| Main export | `tests/fixtures/__init__.py` |
| Documentation | `tests/fixtures/README.md` |

## Testing

```bash
# Import test
python3 -c "from tests.fixtures import *; print('✓ OK')"

# Run example tests
pytest tests/test_fixtures_example.py -v

# Use in your tests
pytest tests/your_test.py -v
```

## Tips

1. **Use pre-defined fixtures** for standard tests
2. **Use helper functions** for custom scenarios
3. **Combine fixtures** for integration tests
4. **Check README.md** for detailed examples
5. **Look at test_fixtures_example.py** for patterns

---

See `README.md` for comprehensive documentation.
