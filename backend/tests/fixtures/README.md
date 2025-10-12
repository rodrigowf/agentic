# Test Fixtures

This directory contains comprehensive mock data and test fixtures for the backend test suite.

## Overview

The fixtures are organized into four main modules:

1. **agent_configs.py** - Mock agent configurations
2. **tool_responses.py** - Mock tool responses
3. **websocket_events.py** - Mock WebSocket events
4. **voice_data.py** - Mock voice conversation data

## Usage

### Basic Import

```python
# Import from main fixtures module
from tests.fixtures import (
    MOCK_LOOPING_AGENT,
    MOCK_WEB_SEARCH_RESPONSE,
    MOCK_WS_TOOL_CALL_EVENT,
    MOCK_VOICE_CONVERSATION
)

# Import from specific modules
from tests.fixtures.agent_configs import create_mock_agent_config
from tests.fixtures.tool_responses import create_mock_tool_response
```

### Using in Tests

```python
import pytest
from tests.fixtures import MOCK_LOOPING_AGENT, MOCK_WEB_SEARCH_RESPONSE

def test_agent_execution(client):
    """Test agent execution with mock data."""
    # Use pre-defined mock agent
    agent_config = MOCK_LOOPING_AGENT

    # Make API call
    response = client.post("/api/agents", json=agent_config.model_dump())
    assert response.status_code == 200


def test_custom_agent():
    """Test with custom mock agent."""
    from tests.fixtures import create_mock_agent_config

    # Create custom agent configuration
    custom_agent = create_mock_agent_config(
        name="CustomTestAgent",
        tools=["custom_tool"],
        max_consecutive_auto_reply=15
    )

    assert custom_agent.name == "CustomTestAgent"
    assert custom_agent.max_consecutive_auto_reply == 15
```

## Module Details

### 1. agent_configs.py

Mock agent configurations matching the `AgentConfig` schema.

**Pre-defined Agents:**
- `MOCK_LOOPING_AGENT` - Basic looping agent with web search tools
- `MOCK_NESTED_AGENT` - Nested team agent with sub-agents
- `MOCK_MULTIMODAL_AGENT` - Vision-capable multimodal agent
- `MOCK_CODE_EXECUTOR_AGENT` - Code execution agent
- `MOCK_RESEARCHER_AGENT` - Research specialist agent
- `MOCK_MEMORY_AGENT` - Memory management agent

**Helper Functions:**
```python
# Create custom agent configuration
agent = create_mock_agent_config(
    name="MyAgent",
    agent_type="looping",
    tools=["web_search"],
    max_consecutive_auto_reply=10
)

# Convert to dictionary
agent_dict = agent_config_to_dict(MOCK_LOOPING_AGENT)

# Create minimal config (for testing defaults)
minimal = create_minimal_agent_dict("MinimalAgent")
```

**LLM Configurations:**
- `MOCK_OPENAI_LLM` - Standard OpenAI config
- `MOCK_OPENAI_VISION_LLM` - Vision model config (gpt-4o)
- `MOCK_ANTHROPIC_LLM` - Claude config
- `MOCK_GOOGLE_LLM` - Gemini config

**Prompt Configurations:**
- `MOCK_BASIC_PROMPT` - Generic assistant prompt
- `MOCK_RESEARCH_PROMPT` - Research-focused prompt
- `MOCK_VISION_PROMPT` - Vision analysis prompt
- `MOCK_DEVELOPER_PROMPT` - Code development prompt
- `MOCK_MEMORY_PROMPT` - Memory management prompt

### 2. tool_responses.py

Realistic mock responses for various tools.

**Research Tool Responses:**
```python
# Web search results
MOCK_WEB_SEARCH_RESPONSE  # 5 Google CSE results
MOCK_ARXIV_SEARCH_RESPONSE  # 3 ArXiv papers
MOCK_WIKIPEDIA_SEARCH_RESPONSE  # 3 Wikipedia articles
MOCK_FETCH_WEB_CONTENT_RESPONSE  # Fetched webpage content

# Create custom search results
custom_results = create_mock_web_search_result(
    query="AI ethics",
    num_results=3,
    use_google=True
)
```

**Memory Tool Responses:**
```python
MOCK_MEMORY_SAVE_RESPONSE
MOCK_MEMORY_GET_RESPONSE
MOCK_MEMORY_BANK_CREATE_RESPONSE
MOCK_MEMORY_BANK_SEARCH_RESPONSE
```

**Image Tool Responses:**
```python
MOCK_SCREENSHOT_RESPONSE  # Screenshot file path
MOCK_IMAGE_GENERATION_RESPONSE  # Generated image path
MOCK_BASE64_IMAGE  # Base64-encoded test image

# Create custom image response
response = create_mock_image_response(
    "/path/to/image.png",
    include_base64=True
)

# Generate test image
base64_img = create_mock_image_base64(
    width=400,
    height=300,
    text="CUSTOM"
)
```

**Code Execution Responses:**
```python
MOCK_PYTHON_EXECUTION_RESPONSE
MOCK_BASH_EXECUTION_RESPONSE
MOCK_GIT_STATUS_RESPONSE
```

**Error Responses:**
```python
MOCK_TOOL_ERROR_RESPONSE
MOCK_API_ERROR_RESPONSE
MOCK_PERMISSION_ERROR_RESPONSE
MOCK_NOT_FOUND_ERROR_RESPONSE
```

### 3. websocket_events.py

Mock WebSocket events for testing real-time communication.

**System Events:**
```python
MOCK_WS_CONNECT_EVENT  # Connection established
MOCK_WS_INIT_EVENT  # Agent initialization
MOCK_WS_DISCONNECT_EVENT  # Connection closed
```

**Message Events:**
```python
MOCK_WS_MESSAGE_EVENT  # Assistant message
MOCK_WS_USER_MESSAGE_EVENT  # User input
MOCK_WS_ASSISTANT_MESSAGE_EVENT  # Assistant response
```

**Tool Events:**
```python
MOCK_WS_TOOL_CALL_EVENT  # Tool call request
MOCK_WS_TOOL_RESULT_EVENT  # Tool execution result
MOCK_WS_TOOL_ERROR_EVENT  # Tool execution error

# Create custom tool events
tool_call = create_mock_tool_call_event(
    tool_name="web_search",
    arguments={"query": "test", "max_results": 5},
    tool_id="toolu_123"
)

tool_result = create_mock_tool_result_event(
    tool_name="web_search",
    result="Found 5 results",
    tool_id="toolu_123",
    is_error=False
)
```

**Claude Code Events:**
```python
MOCK_CLAUDE_CODE_INIT_EVENT
MOCK_CLAUDE_CODE_TEXT_EVENT
MOCK_CLAUDE_CODE_TOOL_CALL_EVENT
MOCK_CLAUDE_CODE_TOOL_RESULT_EVENT
MOCK_CLAUDE_CODE_COMPLETE_EVENT
```

**Nested Agent Events:**
```python
MOCK_NESTED_AGENT_START_EVENT
MOCK_NESTED_AGENT_SELECTION_EVENT
MOCK_NESTED_AGENT_HANDOFF_EVENT
MOCK_NESTED_AGENT_COMPLETE_EVENT
```

**Event Sequences:**
```python
# Complete conversation from start to finish
MOCK_WS_COMPLETE_CONVERSATION_SEQUENCE

# Claude Code workflow
MOCK_CLAUDE_CODE_CONVERSATION_SEQUENCE
```

**Helper Functions:**
```python
# Create custom WebSocket event
event = create_mock_ws_event(
    event_type="TextMessage",
    data={"content": "Hello"},
    source="nested",
    include_timestamp=True
)

# Create text message
msg = create_mock_text_message_event(
    content="Agent response",
    source="TestAgent",
    models_usage={"gpt-4o-mini": {...}}
)
```

### 4. voice_data.py

Mock voice conversation data matching the SQLite database structure.

**Conversation Records:**
```python
MOCK_VOICE_CONVERSATION  # Complete conversation record
MOCK_VOICE_CONVERSATION_MINIMAL  # Minimal conversation
MOCK_VOICE_CONVERSATION_LIST  # List of conversations

# Create custom conversation
conv = create_mock_voice_conversation(
    name="My Test Session",
    voice_model="gpt-4o-realtime-preview-2024-10-01",
    metadata={"duration": 300}
)
```

**Voice Events (OpenAI Realtime API):**
```python
MOCK_VOICE_SESSION_CREATED  # Session initialization
MOCK_VOICE_USER_SPEECH_STARTED  # User starts speaking
MOCK_VOICE_USER_SPEECH_STOPPED  # User stops speaking
MOCK_VOICE_TRANSCRIPTION  # Speech transcription
MOCK_VOICE_RESPONSE_CREATED  # Response generation started
MOCK_VOICE_FUNCTION_CALL  # Tool call from voice model
MOCK_VOICE_AUDIO_DELTA  # Audio streaming chunk
MOCK_VOICE_RESPONSE_DONE  # Response complete
```

**Integration Events:**
```python
MOCK_NESTED_AGENT_EVENTS  # Events from nested team
MOCK_CLAUDE_CODE_EVENTS  # Events from Claude Code
MOCK_CONTROLLER_EVENTS  # Voice controller events
```

**Complete Data:**
```python
# All events from a voice session
MOCK_VOICE_EVENTS  # Combined list of all events

# Complete conversation with metadata + events
MOCK_COMPLETE_VOICE_CONVERSATION
```

**Helper Functions:**
```python
# Create custom voice event
event = create_mock_voice_event(
    conversation_id="conv-123",
    source="voice",
    event_type="session.created",
    payload={"session": {...}}
)

# Filter events by source
voice_only = filter_events_by_source(MOCK_VOICE_EVENTS, "voice")
claude_only = filter_events_by_source(MOCK_VOICE_EVENTS, "claude_code")

# Get specific event types
tool_events = get_event_sequence_by_type(
    MOCK_VOICE_EVENTS,
    ["ToolCallRequestEvent", "ToolCallExecutionEvent"]
)
```

## Best Practices

### 1. Use Pre-defined Fixtures When Possible

```python
# Good - reusable and consistent
from tests.fixtures import MOCK_LOOPING_AGENT

def test_agent(client):
    response = client.post("/api/agents", json=MOCK_LOOPING_AGENT.model_dump())
```

### 2. Create Custom Fixtures for Specific Tests

```python
# Good - flexible for edge cases
from tests.fixtures import create_mock_agent_config

def test_agent_with_many_tools():
    agent = create_mock_agent_config(
        name="ManyToolsAgent",
        tools=[f"tool_{i}" for i in range(20)]
    )
```

### 3. Use Helper Functions for Dynamic Data

```python
# Good - generates fresh data for each test
from tests.fixtures import create_mock_tool_response

def test_tool_execution():
    response = create_mock_tool_response(
        tool_name="custom_tool",
        success=True,
        result="Custom result"
    )
```

### 4. Combine Fixtures for Complex Scenarios

```python
from tests.fixtures import (
    MOCK_LOOPING_AGENT,
    MOCK_WS_TOOL_CALL_EVENT,
    MOCK_WEB_SEARCH_RESPONSE
)

@pytest.mark.asyncio
async def test_agent_websocket_flow():
    # Agent config
    agent = MOCK_LOOPING_AGENT

    # Simulate tool call
    tool_event = MOCK_WS_TOOL_CALL_EVENT

    # Mock tool response
    tool_response = MOCK_WEB_SEARCH_RESPONSE

    # Test the flow...
```

## Adding New Fixtures

When adding new fixtures:

1. **Choose the right module:**
   - Agent configurations → `agent_configs.py`
   - Tool responses → `tool_responses.py`
   - WebSocket events → `websocket_events.py`
   - Voice data → `voice_data.py`

2. **Follow naming conventions:**
   - Constants: `MOCK_[DESCRIPTION]` (e.g., `MOCK_WEB_SEARCH_RESPONSE`)
   - Functions: `create_mock_[item]` (e.g., `create_mock_agent_config`)

3. **Add to `__all__` in both:**
   - The module file
   - `__init__.py`

4. **Include docstrings and examples:**
   ```python
   def create_mock_custom_data(param: str) -> Dict[str, Any]:
       """
       Create custom mock data.

       Args:
           param: Description of parameter

       Returns:
           Mock data dictionary

       Example:
           >>> data = create_mock_custom_data("test")
           >>> assert data["param"] == "test"
       """
       return {"param": param}
   ```

## Testing the Fixtures

Run fixture tests:

```bash
# Test fixture imports
python -c "from tests.fixtures import *; print('All fixtures imported successfully')"

# Test specific module
python -c "from tests.fixtures.agent_configs import *; print('Agent configs OK')"

# Run all tests
cd backend
pytest tests/ -v
```

## Common Patterns

### Pattern 1: Testing Agent Configuration

```python
from tests.fixtures import MOCK_LOOPING_AGENT

def test_agent_config_validation():
    config = MOCK_LOOPING_AGENT
    assert config.agent_type == "looping"
    assert "web_search" in config.tools
    assert config.tool_call_loop == True
```

### Pattern 2: Testing WebSocket Events

```python
from tests.fixtures import create_mock_tool_call_event, create_mock_tool_result_event

@pytest.mark.asyncio
async def test_websocket_tool_flow(mock_websocket):
    # Send tool call
    call_event = create_mock_tool_call_event("web_search", {"query": "test"})
    await mock_websocket.send_json(call_event)

    # Receive result
    result_event = create_mock_tool_result_event(
        "web_search",
        "Found results",
        call_event["data"]["data"]["id"]
    )
    assert result_event["data"]["data"]["is_error"] == False
```

### Pattern 3: Testing Voice Conversations

```python
from tests.fixtures import MOCK_VOICE_CONVERSATION, filter_events_by_source

def test_voice_conversation_structure(conversation_store):
    conv = MOCK_VOICE_CONVERSATION

    # Create conversation
    created = conversation_store.create_conversation(
        name=conv["name"],
        voice_model=conv["voice_model"]
    )

    assert created["name"] == conv["name"]

    # Filter events
    voice_events = filter_events_by_source(MOCK_VOICE_EVENTS, "voice")
    assert all(e["source"] == "voice" for e in voice_events)
```

## Maintenance

### Updating Fixtures

When the codebase schema changes:

1. Update the relevant fixture module
2. Run tests to verify compatibility
3. Update this README if needed

### Version History

- **2025-10-11**: Initial comprehensive fixture suite created
  - agent_configs.py with 6 agent types
  - tool_responses.py with research, memory, image, and code responses
  - websocket_events.py with complete event types
  - voice_data.py with full voice conversation structure

---

**Last Updated:** 2025-10-11
