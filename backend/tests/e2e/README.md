# End-to-End (E2E) Tests

**Location:** `/home/rodrigo/agentic/backend/tests/e2e/`
**Created:** 2025-10-11
**Purpose:** Comprehensive end-to-end testing of complete workflows with minimal mocking

---

## Overview

End-to-end tests verify complete system workflows from HTTP request to final response. Unlike unit tests (which test individual functions) and integration tests (which test component interactions), E2E tests validate entire user flows through the system with real HTTP/WebSocket connections and minimal mocking.

**Key Characteristics:**
- Test complete workflows end-to-end
- Use real FastAPI TestClient
- Minimal mocking (only for LLM API calls)
- Verify data persistence and state changes
- Test error handling and recovery
- Validate event sequences and ordering

---

## Test Files

### 1. `test_agent_workflow.py` (580+ lines)

**Purpose:** Complete agent execution workflows

**Test Classes:**
- `TestLoopingAgentWorkflow` - Looping agent lifecycle and execution
- `TestNestedTeamWorkflow` - Nested team coordination and handoffs
- `TestAgentConfigurationWorkflow` - Agent CRUD operations
- `TestAgentValidationWorkflow` - Configuration validation

**Key Tests:**
- ✅ Complete looping agent lifecycle (create → execute → verify)
- ✅ Looping agent with tool execution
- ✅ Looping agent error recovery
- ✅ Nested team creation and execution
- ✅ Nested team handoff workflow
- ✅ Agent CRUD workflow (Create, Read, Update, Delete)
- ✅ Multiple agents management
- ✅ Invalid agent configuration handling
- ✅ Duplicate agent name handling
- ✅ Nested team validation

**Example Test:**
```python
def test_complete_looping_agent_lifecycle(self, client, temp_workspace, simple_test_tool):
    """
    Test complete lifecycle: Create agent → Execute → Verify results.
    """
    # Step 1: Create agent configuration
    agent_config = create_mock_agent_config(...)

    # Step 2: Save agent via API
    response = client.post("/api/agents", json=agent_config.model_dump(mode='json'))
    assert response.status_code == 200

    # Step 3: Verify agent file was created
    agent_file = Path(temp_workspace["agents_dir"]) / "E2ETestAgent.json"
    assert agent_file.exists()

    # Step 4: Execute agent via WebSocket
    with client.websocket_connect(f"/api/runs/E2ETestAgent") as websocket:
        # Receive and verify events
        ...
```

**Coverage:**
- Agent creation via API
- Agent configuration persistence
- Agent execution via WebSocket
- Tool call workflows
- Event streaming
- Error handling and recovery
- Multi-agent coordination

---

### 2. `test_voice_workflow.py` (550+ lines)

**Purpose:** Complete voice assistant workflows

**Test Classes:**
- `TestVoiceConversationLifecycle` - Voice conversation management
- `TestVoiceNestedIntegration` - Voice + Nested team integration
- `TestVoiceClaudeCodeIntegration` - Voice + Claude Code integration
- `TestVoiceWebSocketCommunication` - Voice WebSocket communication
- `TestVoiceToolExecution` - Voice tool execution
- `TestVoiceConversationExport` - Conversation export functionality

**Key Tests:**
- ✅ Complete voice conversation workflow (create → add events → retrieve)
- ✅ Multiple conversations management
- ✅ Conversation event filtering by source
- ✅ Voice sends to nested team workflow
- ✅ Voice pause and resume nested team
- ✅ Voice sends to Claude Code workflow
- ✅ Claude Code permission bypass verification
- ✅ Voice WebSocket connection
- ✅ Voice event streaming
- ✅ Voice tool: send_to_nested
- ✅ Voice tool: send_to_claude_code
- ✅ Voice tool: pause
- ✅ Voice tool: reset
- ✅ Export conversation to JSON

**Example Test:**
```python
def test_voice_sends_to_nested_workflow(self, client, temp_workspace, conversation_store):
    """
    Test complete workflow:
    1. Voice receives user speech
    2. Voice calls send_to_nested tool
    3. Nested team executes task
    4. Events stored in database
    5. Results returned to voice
    """
    # Create nested team agent
    team_config = create_mock_agent_config(...)
    client.post("/api/agents", json=team_config.model_dump(mode='json'))

    # Create conversation
    conv_id = conversation_store.create_conversation("Voice + Nested Test")

    # Simulate voice events
    conversation_store.add_event(conv_id, "voice", "function_call", {...})

    # Simulate nested team execution
    for nested_event in MOCK_NESTED_AGENT_EVENTS:
        conversation_store.add_event(conv_id, "nested", nested_event["type"], {...})

    # Verify event sequence
    events = conversation_store.list_events(conv_id)
    assert "voice" in [e["source"] for e in events]
    assert "nested" in [e["source"] for e in events]
```

**Coverage:**
- Voice conversation lifecycle
- Database event storage and retrieval
- Voice ↔ Nested team integration
- Voice ↔ Claude Code integration
- Voice tool execution
- Permission management
- Event filtering and export

---

### 3. `test_tool_upload.py` (630+ lines)

**Purpose:** Tool upload and execution workflows

**Test Classes:**
- `TestToolUploadWorkflow` - Tool upload via API
- `TestToolExecutionWorkflow` - Tool execution in agents
- `TestToolUpdateWorkflow` - Tool updates and hot-reload
- `TestToolErrorHandling` - Tool error handling
- `TestToolValidation` - Tool code validation

**Key Tests:**
- ✅ Complete tool upload lifecycle
- ✅ Upload multiple tools
- ✅ Upload tool with dependencies
- ✅ Upload invalid tool code
- ✅ Agent uses uploaded tool
- ✅ Multiple tools in single agent
- ✅ Tool update via re-upload
- ✅ Tool hot-reload after update
- ✅ Tool runtime error handling
- ✅ Missing tool handling
- ✅ Tool with valid schema

**Example Test:**
```python
def test_complete_tool_upload_lifecycle(self, client, temp_workspace):
    """
    Test complete tool lifecycle:
    1. Upload tool via API
    2. Verify tool file created
    3. List tools and verify presence
    4. Verify tool can be loaded
    """
    # Step 1: Create tool code
    tool_code = create_simple_tool_code("custom_search", "A custom search tool")

    # Step 2: Upload tool via API
    response = client.post(
        "/api/tools",
        files={"file": ("custom_search.py", tool_code, "text/x-python")}
    )
    assert response.status_code == 200

    # Step 3: Verify tool file created
    tool_file = Path(temp_workspace["tools_dir"]) / "custom_search.py"
    assert tool_file.exists()

    # Step 4: List tools via API
    response = client.get("/api/tools")
    tools = response.json()
    assert "custom_search" in [t["name"] for t in tools]
```

**Coverage:**
- Tool upload via API
- Tool file persistence
- Dynamic tool loading
- Tool execution in agents
- Tool updates and versioning
- Error handling
- Code validation

---

### 4. `test_multimodal_workflow.py` (620+ lines)

**Purpose:** Multimodal vision agent workflows

**Test Classes:**
- `TestMultimodalAgentCreation` - Multimodal agent creation
- `TestMultimodalImageDetection` - Automatic image detection
- `TestMultimodalWorkflow` - Complete multimodal workflows
- `TestMultimodalErrorHandling` - Error handling

**Key Tests:**
- ✅ Create multimodal agent
- ✅ Multimodal agent with vision models
- ✅ Detect image file paths in tool responses
- ✅ Detect base64 encoded images
- ✅ Screenshot analysis workflow
- ✅ Image generation and description workflow
- ✅ Multiple images in sequence
- ✅ Invalid image path handling
- ✅ Corrupted base64 image handling

**Example Test:**
```python
def test_screenshot_analysis_workflow(self, client, temp_workspace, image_tools):
    """
    Test complete workflow:
    1. Agent takes screenshot
    2. Screenshot detected automatically
    3. Agent analyzes screenshot content
    4. Agent describes what it sees
    """
    agent_config = create_mock_agent_config(
        name="ScreenshotAnalyzer",
        agent_type="multimodal_tools_looping",
        tools=image_tools
    )
    client.post("/api/agents", json=agent_config.model_dump(mode='json'))

    # Execute agent with mocked runner
    with patch('core.runner.run_agent_ws') as mock_run:
        # Simulate screenshot → detection → analysis → description
        ...

    # Verify complete workflow
    assert "ToolCallRequestEvent" in event_types
    assert "MultiModalMessage" in event_types
    assert "TextMessage" in event_types
```

**Coverage:**
- Multimodal agent creation
- Automatic image detection (file paths, base64)
- MultiModalMessage creation
- Vision model integration
- Screenshot workflows
- Image generation workflows
- Multiple image processing
- Error handling

---

## Running E2E Tests

### Run All E2E Tests

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
pytest tests/e2e/ -v
```

### Run Specific Test File

```bash
pytest tests/e2e/test_agent_workflow.py -v
pytest tests/e2e/test_voice_workflow.py -v
pytest tests/e2e/test_tool_upload.py -v
pytest tests/e2e/test_multimodal_workflow.py -v
```

### Run Specific Test Class

```bash
pytest tests/e2e/test_agent_workflow.py::TestLoopingAgentWorkflow -v
```

### Run Specific Test

```bash
pytest tests/e2e/test_agent_workflow.py::TestLoopingAgentWorkflow::test_complete_looping_agent_lifecycle -v
```

### Run with Coverage

```bash
pytest tests/e2e/ --cov=backend --cov-report=html -v
```

### Run with Verbose Output

```bash
pytest tests/e2e/ -v -s  # -s shows print statements
```

### Run E2E Tests Only (Skip Unit/Integration)

```bash
pytest -m e2e -v
```

---

## Test Environment

### Fixtures

E2E tests use several key fixtures:

**1. `client`** - FastAPI TestClient for HTTP requests
```python
@pytest.fixture
def client():
    return TestClient(app)
```

**2. `temp_workspace`** - Temporary directories for agents/tools
```python
@pytest.fixture
def temp_workspace(monkeypatch):
    # Creates temp agents_dir and tools_dir
    # Cleans up after test
    ...
```

**3. `conversation_store`** - Temporary database for voice tests
```python
@pytest.fixture
def conversation_store(temp_db):
    return ConversationStore(db_path=temp_db)
```

**4. `image_tools`** - Pre-created image tools for multimodal tests
```python
@pytest.fixture
def image_tools(temp_workspace):
    # Creates image generation/capture tools
    ...
```

### Mocking Strategy

E2E tests use **minimal mocking**:

**What We Mock:**
- ✅ LLM API calls (to avoid API costs and ensure deterministic tests)
- ✅ Agent execution logic (to simulate predictable workflows)
- ✅ Time-consuming operations (to keep tests fast)

**What We DON'T Mock:**
- ❌ HTTP/WebSocket communication (use real TestClient)
- ❌ File system operations (use real temp directories)
- ❌ Database operations (use real SQLite with temp files)
- ❌ Configuration loading (use real config loaders)
- ❌ Event serialization (use real JSON encoding/decoding)

**Example Mocking Pattern:**
```python
with patch('core.runner.run_agent_ws') as mock_run:
    async def mock_agent_runner(config, tools, websocket):
        # Simulate agent behavior with real WebSocket
        await websocket.send_json({...})

    mock_run.side_effect = mock_agent_runner

    # Real WebSocket connection
    with client.websocket_connect("/api/runs/AgentName") as websocket:
        event = websocket.receive_json()
```

---

## Test Data

E2E tests use fixtures from `tests/fixtures/`:

**Agent Configurations:**
```python
from tests.fixtures import (
    MOCK_LOOPING_AGENT,
    MOCK_NESTED_AGENT,
    MOCK_MULTIMODAL_AGENT,
    create_mock_agent_config
)
```

**Tool Responses:**
```python
from tests.fixtures import (
    MOCK_WEB_SEARCH_RESPONSE,
    create_mock_tool_response
)
```

**Voice Data:**
```python
from tests.fixtures import (
    MOCK_VOICE_SESSION_CREATED,
    MOCK_NESTED_AGENT_EVENTS,
    MOCK_CLAUDE_CODE_EVENTS,
    create_mock_voice_event
)
```

**Image Data:**
```python
from tests.fixtures import (
    MOCK_BASE64_IMAGE,
    create_mock_image_base64
)
```

---

## Test Patterns

### Pattern 1: Complete Lifecycle Test

Test the entire lifecycle from creation to execution:

```python
def test_complete_lifecycle(self, client, temp_workspace):
    # 1. Create resource via API
    response = client.post("/api/resource", json={...})
    assert response.status_code == 200

    # 2. Verify persistence
    file_path = Path(temp_workspace["dir"]) / "resource.json"
    assert file_path.exists()

    # 3. List resources
    response = client.get("/api/resources")
    assert len(response.json()) > 0

    # 4. Execute/use resource
    with client.websocket_connect("/api/ws/resource") as ws:
        event = ws.receive_json()
        assert event["type"] == "success"

    # 5. Update resource
    response = client.put("/api/resource/name", json={...})
    assert response.status_code == 200

    # 6. Verify update
    with open(file_path) as f:
        data = json.load(f)
    assert data["updated"] == True
```

### Pattern 2: Event Sequence Verification

Verify the correct sequence of events in a workflow:

```python
def test_event_sequence(self, client, temp_workspace):
    with patch('core.runner.run_agent_ws') as mock_run:
        async def mock_runner(config, tools, websocket):
            # Send events in specific order
            await websocket.send_json({"type": "start"})
            await websocket.send_json({"type": "tool_call"})
            await websocket.send_json({"type": "tool_result"})
            await websocket.send_json({"type": "complete"})

        mock_run.side_effect = mock_runner

        with client.websocket_connect("/api/runs/Agent") as ws:
            events = []
            try:
                while True:
                    event = ws.receive_json(timeout=2)
                    events.append(event)
                    if event["type"] == "complete":
                        break
            except:
                pass

            # Verify sequence
            event_types = [e["type"] for e in events]
            assert event_types == ["start", "tool_call", "tool_result", "complete"]
```

### Pattern 3: Multi-System Integration

Test integration between multiple systems:

```python
def test_voice_nested_claude_integration(self, client, conversation_store):
    # 1. Voice receives command
    conv_id = conversation_store.create_conversation("Integration Test")
    conversation_store.add_event(conv_id, "voice", "user_message", {...})

    # 2. Voice delegates to nested
    conversation_store.add_event(conv_id, "voice", "function_call", {
        "name": "send_to_nested",
        "arguments": {"text": "task"}
    })

    # 3. Nested executes with tools
    conversation_store.add_event(conv_id, "nested", "tool_call", {...})

    # 4. Nested delegates to Claude Code
    conversation_store.add_event(conv_id, "nested", "handoff", {
        "target": "claude_code"
    })

    # 5. Claude Code executes
    conversation_store.add_event(conv_id, "claude_code", "tool_use", {...})

    # 6. Verify complete flow
    events = conversation_store.list_events(conv_id)
    sources = [e["source"] for e in events]
    assert "voice" in sources
    assert "nested" in sources
    assert "claude_code" in sources
```

### Pattern 4: Error Recovery Testing

Test error handling and recovery:

```python
def test_error_recovery(self, client, temp_workspace):
    with patch('core.runner.run_agent_ws') as mock_run:
        async def mock_runner(config, tools, websocket):
            # Simulate error
            await websocket.send_json({
                "type": "tool_execution",
                "data": {"is_error": True, "result": "Tool failed"}
            })

            # Agent recovers
            await websocket.send_json({
                "type": "text_message",
                "data": {"content": "Retrying with different approach"}
            })

            # Retry succeeds
            await websocket.send_json({
                "type": "tool_execution",
                "data": {"is_error": False, "result": "Success"}
            })

            await websocket.send_json({"type": "complete"})

        mock_run.side_effect = mock_runner

        with client.websocket_connect("/api/runs/Agent") as ws:
            events = []
            while True:
                event = ws.receive_json(timeout=2)
                events.append(event)
                if event["type"] == "complete":
                    break

            # Verify error was handled
            tool_events = [e for e in events if e["type"] == "tool_execution"]
            assert tool_events[0]["data"]["is_error"] == True
            assert tool_events[1]["data"]["is_error"] == False
```

---

## Best Practices

### 1. Use Real Resources

Prefer real file systems, databases, and connections over mocks:

```python
# Good: Real temp directory
temp_dir = tempfile.mkdtemp()
agent_file = Path(temp_dir) / "agent.json"
agent_file.write_text(json.dumps(config))

# Avoid: Mocking file system
# mock_open.return_value = MagicMock()
```

### 2. Test Complete Workflows

Test end-to-end workflows, not individual steps:

```python
# Good: Complete workflow
def test_agent_workflow(self):
    # Create → Save → Load → Execute → Verify
    ...

# Avoid: Testing individual steps in isolation
# def test_create_agent(self): ...
# def test_save_agent(self): ...
# def test_load_agent(self): ...
```

### 3. Verify Side Effects

Check that operations have the expected side effects:

```python
def test_agent_creation(self, client, temp_workspace):
    # Create agent
    response = client.post("/api/agents", json={...})

    # Verify side effects
    agent_file = Path(temp_workspace["agents_dir"]) / "Agent.json"
    assert agent_file.exists()  # File created

    with open(agent_file) as f:
        saved = json.load(f)
    assert saved["name"] == "Agent"  # Correct content
```

### 4. Use Meaningful Assertions

Assert on meaningful outcomes, not implementation details:

```python
# Good: Assert on outcome
assert "tool_call" in [e["type"] for e in events]
assert tool_result["is_error"] == False

# Avoid: Assert on implementation
# assert mock_function.call_count == 3
# assert mock_object.method.called
```

### 5. Clean Up Resources

Always clean up temporary resources:

```python
@pytest.fixture
def temp_workspace(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    # ... setup ...

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)  # Always runs
```

### 6. Handle Timeouts

WebSocket operations should have reasonable timeouts:

```python
try:
    while True:
        event = websocket.receive_json(timeout=2)  # 2 second timeout
        events.append(event)
        if event["type"] == "complete":
            break
except Exception:
    # Timeout or disconnection - acceptable
    pass
```

---

## Troubleshooting

### Tests Hanging

If tests hang, check for:
- Missing timeout on WebSocket `receive_json()`
- Infinite loops waiting for events
- Background processes not terminating

**Solution:**
```python
# Add timeout
event = websocket.receive_json(timeout=2)

# Add loop limit
for _ in range(100):  # Max 100 iterations
    event = websocket.receive_json(timeout=1)
    if event["type"] == "complete":
        break
```

### Temp Files Not Cleaned Up

If temp files persist after tests:
- Check that fixtures yield before cleanup
- Ensure `shutil.rmtree()` runs even on failure

**Solution:**
```python
@pytest.fixture
def temp_workspace():
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
```

### WebSocket Connection Fails

If WebSocket connection fails:
- Verify FastAPI app is properly initialized
- Check that routes are registered
- Verify TestClient is used correctly

**Solution:**
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
with client.websocket_connect("/api/runs/Agent") as ws:
    # Connection should work
    ...
```

### Database Locks

If SQLite database locks occur:
- Use separate databases for each test
- Close connections properly
- Use `tmp_path` fixture

**Solution:**
```python
@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / f"test_{uuid.uuid4()}.db"
    return str(db_path)
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run E2E tests
      run: |
        cd backend
        pytest tests/e2e/ -v --tb=short
      env:
        TESTING: 1
```

### Test Coverage Reporting

```bash
# Run with coverage
pytest tests/e2e/ --cov=backend --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

---

## Statistics

| File | Lines | Classes | Tests | Coverage |
|------|-------|---------|-------|----------|
| test_agent_workflow.py | 580+ | 4 | 11 | Agent workflows |
| test_voice_workflow.py | 550+ | 6 | 15 | Voice workflows |
| test_tool_upload.py | 630+ | 5 | 13 | Tool workflows |
| test_multimodal_workflow.py | 620+ | 4 | 11 | Multimodal workflows |
| **TOTAL** | **2,380+** | **19** | **50** | **Complete system** |

---

## Future Enhancements

Potential additions to E2E test suite:

1. **Performance Tests**
   - Response time measurements
   - Concurrent user handling
   - Load testing scenarios

2. **Security Tests**
   - Authentication/authorization flows
   - Input validation
   - SQL injection prevention

3. **Browser E2E Tests**
   - Selenium/Playwright integration
   - Full frontend + backend workflows
   - Screenshot-based testing

4. **API Contract Tests**
   - Schema validation
   - Breaking change detection
   - Version compatibility

5. **Chaos Engineering**
   - Network failure simulation
   - Database connection loss
   - Service degradation scenarios

---

## Contributing

When adding new E2E tests:

1. **Follow existing patterns** - Use similar structure to existing tests
2. **Test complete workflows** - Don't just test individual steps
3. **Use minimal mocking** - Only mock LLM API calls
4. **Verify side effects** - Check files, database, state changes
5. **Add documentation** - Update this README with new test descriptions
6. **Run all tests** - Ensure new tests don't break existing ones

**Checklist for New E2E Test:**
- [ ] Tests complete workflow end-to-end
- [ ] Uses real HTTP/WebSocket connections
- [ ] Minimal mocking (only LLM APIs)
- [ ] Verifies persistence (files, database)
- [ ] Checks event sequences
- [ ] Handles errors and timeouts
- [ ] Cleans up resources
- [ ] Documented in README
- [ ] All existing tests still pass

---

## References

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [TestClient Documentation](https://www.starlette.io/testclient/)
- [Backend Tests README](../README.md)
- [CLAUDE.md](../../../CLAUDE.md) - Complete system documentation

---

**Last Updated:** 2025-10-11
**Maintainer:** Backend Development Team
**Questions:** See [../README.md](../README.md) for general testing info
