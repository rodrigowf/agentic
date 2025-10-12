# Integration Tests

This directory contains comprehensive integration tests for the backend API.

## Test Files

### 1. test_api_agents.py
Tests for agent management API endpoints.

**Endpoints tested:**
- `GET /api/agents` - List all agents
- `POST /api/agents` - Create new agent
- `PUT /api/agents/{name}` - Update existing agent

**Test coverage:**
- Empty agent list
- Creating agents with various configurations
- Duplicate name handling
- Input validation
- Updating agent configurations
- Name mismatch validation
- Nested team agents
- Different LLM providers
- Edge cases (special characters, empty tools, etc.)

**Run:**
```bash
cd /home/rodrigo/agentic/backend
pytest tests/integration/test_api_agents.py -v
```

### 2. test_api_tools.py
Tests for tool management API endpoints.

**Endpoints tested:**
- `GET /api/tools` - List all tools
- `GET /api/tools/content/{filename}` - Get tool file content
- `PUT /api/tools/content/{filename}` - Save tool file content
- `POST /api/tools/upload` - Upload tool file
- `POST /api/tools/generate` - Generate tool code with AI

**Test coverage:**
- Tool listing and discovery
- File content reading/writing
- File upload handling
- Path traversal prevention
- Invalid filename validation
- Tool code generation (mocked)
- Syntax error handling
- Unicode support
- Tool reloading after modifications

**Run:**
```bash
cd /home/rodrigo/agentic/backend
pytest tests/integration/test_api_tools.py -v
```

### 3. test_api_voice.py
Tests for voice conversation API endpoints.

**Endpoints tested:**
- `POST /api/realtime/conversations` - Create conversation
- `GET /api/realtime/conversations` - List conversations
- `GET /api/realtime/conversations/{id}` - Get conversation details
- `PUT /api/realtime/conversations/{id}` - Update conversation
- `DELETE /api/realtime/conversations/{id}` - Delete conversation
- `GET /api/realtime/conversations/{id}/events` - List events
- `POST /api/realtime/conversations/{id}/events` - Append event

**Test coverage:**
- Conversation CRUD operations
- Event storage and retrieval
- Metadata handling
- Timestamp management
- Cascade deletion
- Event ordering
- Multiple event sources
- Complex nested data
- Unicode support
- Complete conversation lifecycle

**Run:**
```bash
cd /home/rodrigo/agentic/backend
pytest tests/integration/test_api_voice.py -v
```

### 4. test_websocket_agents.py
Tests for WebSocket communication with agents.

**Endpoints tested:**
- `WS /api/runs/{agent_name}` - Agent execution WebSocket
- `WS /api/runs/ClaudeCode` - Claude Code WebSocket

**Test coverage:**
- Connection establishment
- Message sending/receiving
- Event streaming
- Tool call events
- Error propagation
- Client disconnection
- Server disconnection
- Multiple simultaneous connections
- Different event types (TextMessage, ToolCall, TaskResult, etc.)
- Claude Code integration
- Performance (rapid events, large messages)

**Run:**
```bash
cd /home/rodrigo/agentic/backend
pytest tests/integration/test_websocket_agents.py -v
```

### 5. test_database_operations.py
Tests for database integrity and operations.

**Database tested:**
- Conversation storage (SQLite)
- Event storage (SQLite)

**Test coverage:**
- Conversation CRUD operations
- Event storage and retrieval
- Foreign key constraints
- Cascade deletion
- Transaction handling
- Concurrent access (multi-threading)
- Data integrity
- Timestamp format
- JSON storage (metadata, event data)
- Database schema verification
- Performance (large events, many events)
- Edge cases (unicode, special characters, empty values)

**Run:**
```bash
cd /home/rodrigo/agentic/backend
pytest tests/integration/test_database_operations.py -v
```

## Running All Tests

Run all integration tests:
```bash
cd /home/rodrigo/agentic/backend
pytest tests/integration/ -v
```

Run with coverage:
```bash
cd /home/rodrigo/agentic/backend
pytest tests/integration/ --cov=. --cov-report=html
```

Run specific test class:
```bash
pytest tests/integration/test_api_agents.py::TestAgentListEndpoint -v
```

Run specific test method:
```bash
pytest tests/integration/test_api_agents.py::TestAgentListEndpoint::test_list_agents_empty -v
```

## Test Structure

All integration tests follow a consistent structure:

### Fixtures
- `client` - TestClient for HTTP requests
- `temp_dirs` - Temporary directories for isolated testing
- `temp_db` - Temporary database for isolated testing
- `sample_data` - Sample configurations and data

### Test Classes
Tests are organized into classes by functionality:
- `Test{Feature}Endpoint` - Tests for specific endpoint
- `Test{Feature}EdgeCases` - Edge cases and error handling
- `Test{Feature}Integration` - Full workflow tests

### Naming Convention
- `test_{action}_{scenario}` - Descriptive test names
- Examples:
  - `test_create_agent_success`
  - `test_list_tools_empty`
  - `test_websocket_connect_nonexistent_agent`

## Dependencies

Required packages:
- `pytest` - Test framework
- `fastapi` - For TestClient
- `python-multipart` - For file upload tests
- `sqlite3` - Built-in, for database tests

Install:
```bash
pip install pytest pytest-cov
```

## Mocking

External dependencies are mocked:
- **Gemini API** - Tool generation is mocked
- **Agent execution** - Long-running agents are mocked
- **Claude Code** - Subprocess is mocked

This ensures:
- Fast test execution
- No external API calls
- Consistent test results
- No API key requirements (for most tests)

## Best Practices

1. **Isolation**: Each test uses temporary directories/databases
2. **Cleanup**: Fixtures handle cleanup automatically
3. **Independence**: Tests don't depend on each other
4. **Assertions**: Clear, specific assertions
5. **Coverage**: Success paths + error paths + edge cases

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run integration tests
  run: |
    cd backend
    pytest tests/integration/ -v --cov=. --cov-report=xml
```

## Troubleshooting

### Tests fail due to missing dependencies
```bash
cd /home/rodrigo/agentic/backend
pip install -r requirements.txt
pip install pytest pytest-cov
```

### Database lock errors
- Ensure no other processes are using the database
- Tests use temporary databases to avoid conflicts

### WebSocket timeout errors
- Increase timeout in test if needed
- Check that FastAPI app is properly configured

### Import errors
- Ensure you're running tests from the backend directory
- Check that `sys.path` is correctly set in test files

## Future Enhancements

Potential additions:
- Performance benchmarks
- Load testing
- Security testing (SQL injection, etc.)
- API versioning tests
- Rate limiting tests
- Authentication/authorization tests

## Related Documentation

- [Backend Architecture](../../docs/REFACTORING_SUMMARY.md)
- [API Documentation](../../main.py)
- [Database Schema](../../utils/voice_conversation_store.py)
- [Test README](../README.md)
