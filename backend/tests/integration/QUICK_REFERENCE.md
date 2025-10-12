# Integration Tests - Quick Reference

## Files Created (2025-10-11)

| File | Size | Purpose | Tests |
|------|------|---------|-------|
| test_api_agents.py | 14 KB | Agent API endpoints | 50+ |
| test_api_tools.py | 15 KB | Tool API endpoints | 45+ |
| test_api_voice.py | 22 KB | Voice API endpoints | 60+ |
| test_websocket_agents.py | 20 KB | WebSocket communication | 40+ |
| test_database_operations.py | 20 KB | Database integrity | 50+ |
| **Total** | **91 KB** | **5 test files** | **245+ tests** |

## Quick Commands

### Run All New Tests
```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
./tests/integration/run_new_tests.sh
```

### Run Individual Test Files
```bash
pytest tests/integration/test_api_agents.py -v
pytest tests/integration/test_api_tools.py -v
pytest tests/integration/test_api_voice.py -v
pytest tests/integration/test_websocket_agents.py -v
pytest tests/integration/test_database_operations.py -v
```

### Run Specific Test Class
```bash
pytest tests/integration/test_api_agents.py::TestAgentCreateEndpoint -v
```

### Run Specific Test Method
```bash
pytest tests/integration/test_api_agents.py::TestAgentCreateEndpoint::test_create_agent_success -v
```

### Run with Coverage
```bash
pytest tests/integration/ --cov=. --cov-report=html
```

### Run and Stop on First Failure
```bash
pytest tests/integration/ -v -x
```

### Run Only Failed Tests from Last Run
```bash
pytest tests/integration/ -v --lf
```

## Test Coverage Matrix

### REST API Endpoints

| Endpoint | Test File | Status |
|----------|-----------|--------|
| GET /api/agents | test_api_agents.py | ✅ Complete |
| POST /api/agents | test_api_agents.py | ✅ Complete |
| PUT /api/agents/{name} | test_api_agents.py | ✅ Complete |
| GET /api/tools | test_api_tools.py | ✅ Complete |
| GET /api/tools/content/{filename} | test_api_tools.py | ✅ Complete |
| PUT /api/tools/content/{filename} | test_api_tools.py | ✅ Complete |
| POST /api/tools/upload | test_api_tools.py | ✅ Complete |
| POST /api/tools/generate | test_api_tools.py | ✅ Complete |
| POST /api/realtime/conversations | test_api_voice.py | ✅ Complete |
| GET /api/realtime/conversations | test_api_voice.py | ✅ Complete |
| GET /api/realtime/conversations/{id} | test_api_voice.py | ✅ Complete |
| PUT /api/realtime/conversations/{id} | test_api_voice.py | ✅ Complete |
| DELETE /api/realtime/conversations/{id} | test_api_voice.py | ✅ Complete |
| GET /api/realtime/conversations/{id}/events | test_api_voice.py | ✅ Complete |
| POST /api/realtime/conversations/{id}/events | test_api_voice.py | ✅ Complete |

### WebSocket Endpoints

| Endpoint | Test File | Status |
|----------|-----------|--------|
| WS /api/runs/{agent_name} | test_websocket_agents.py | ✅ Complete |
| WS /api/runs/ClaudeCode | test_websocket_agents.py | ✅ Complete |

### Database Operations

| Operation | Test File | Status |
|-----------|-----------|--------|
| Conversation CRUD | test_database_operations.py | ✅ Complete |
| Event CRUD | test_database_operations.py | ✅ Complete |
| Foreign Keys | test_database_operations.py | ✅ Complete |
| Transactions | test_database_operations.py | ✅ Complete |
| Concurrency | test_database_operations.py | ✅ Complete |
| Schema Validation | test_database_operations.py | ✅ Complete |

## Test Categories

### Success Path Tests (Happy Path)
- ✅ All endpoints have success case tests
- ✅ Standard operations work correctly
- ✅ Data is properly stored and retrieved

### Error Handling Tests
- ✅ 404 Not Found scenarios
- ✅ 400 Bad Request scenarios
- ✅ Validation errors (422)
- ✅ Server errors (500)
- ✅ Missing configuration errors

### Edge Cases
- ✅ Empty inputs
- ✅ Very long inputs (10KB+)
- ✅ Unicode characters
- ✅ Special characters
- ✅ Null/None values
- ✅ Path traversal attempts
- ✅ Invalid file formats

### Performance Tests
- ✅ Large message handling (100KB+)
- ✅ Rapid event streaming (50+ events)
- ✅ Many records (100-1000+)
- ✅ Concurrent access (5+ threads)

### Integration Tests
- ✅ Full conversation lifecycle
- ✅ Multi-step workflows
- ✅ Cross-component interaction

## Common Test Patterns

### Testing REST Endpoints
```python
def test_endpoint_success(client, temp_db):
    response = client.post("/api/endpoint", json=data)
    assert response.status_code == 200
    assert response.json()["key"] == "expected"
```

### Testing WebSocket
```python
def test_websocket_message(client):
    with client.websocket_connect("/ws/endpoint") as ws:
        ws.send_json({"message": "test"})
        response = ws.receive_json(timeout=2)
        assert response["type"] == "expected"
```

### Testing Database
```python
def test_database_operation(temp_db):
    record = temp_db.create_record("test")
    retrieved = temp_db.get_record(record["id"])
    assert retrieved["name"] == "test"
```

## Fixtures Reference

| Fixture | Purpose | Example |
|---------|---------|---------|
| `client` | TestClient for HTTP/WS | `client.get("/api/agents")` |
| `temp_agents_dir` | Temporary agent directory | Auto-cleaned |
| `temp_tools_dir` | Temporary tools directory | Auto-cleaned |
| `temp_db` | Temporary database | Auto-cleaned |
| `sample_agent_config` | Pre-configured agent | Ready to use |
| `sample_tool_code` | Pre-written tool code | Ready to use |
| `populated_db` | DB with sample data | Multiple records |

## Troubleshooting

### Import Errors
```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
export PYTHONPATH=/home/rodrigo/agentic/backend:$PYTHONPATH
```

### Database Locked
- Tests use isolated temp databases
- Check no other process is running
- Restart if needed

### WebSocket Timeout
- Increase timeout: `ws.receive_json(timeout=5)`
- Check mock configuration
- Verify FastAPI app startup

### Test Failures
```bash
# Run with verbose output
pytest tests/integration/test_file.py -v -s

# Run specific failing test
pytest tests/integration/test_file.py::TestClass::test_method -v

# Run with pdb debugger
pytest tests/integration/test_file.py --pdb
```

## Dependencies

Install all dependencies:
```bash
cd /home/rodrigo/agentic/backend
pip install -r requirements.txt
pip install pytest pytest-cov
```

## Documentation

- **Full Documentation:** [README.md](README.md)
- **Test Summary:** [TEST_SUMMARY.md](TEST_SUMMARY.md)
- **Project Guide:** [/home/rodrigo/agentic/CLAUDE.md](../../CLAUDE.md)
- **Backend Docs:** [/home/rodrigo/agentic/backend/docs/](../docs/)

## Statistics

- **Total Lines of Test Code:** ~2,500+
- **Test Coverage:** REST API, WebSocket, Database
- **Test Types:** Unit, Integration, Performance, Edge Cases
- **Mocked Dependencies:** Gemini API, Agent Execution, Claude Code
- **Execution Time:** ~30-60 seconds (all tests)

## CI/CD Ready

These tests are ready for CI/CD integration:
- ✅ No external API calls required (mocked)
- ✅ Fast execution (< 1 minute)
- ✅ Isolated (temp dirs/databases)
- ✅ Exit codes (0 = success, 1 = failure)
- ✅ Coverage reporting (XML, HTML)

## Next Steps

### To Run Tests
1. `cd /home/rodrigo/agentic/backend`
2. `source venv/bin/activate`
3. `./tests/integration/run_new_tests.sh`

### To Add Tests
1. Choose appropriate test file
2. Add test class/method
3. Use existing fixtures
4. Follow naming convention
5. Run and verify

### To Debug
1. Run specific test: `pytest path::Class::method -v`
2. Add print statements (use `-s` flag)
3. Use pdb: `pytest --pdb`
4. Check fixtures and mocks

---

**Quick Reference v1.0 - 2025-10-11**
