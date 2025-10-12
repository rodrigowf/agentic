# Backend Tests

This directory contains all test files for the backend codebase.

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_screenshot.py              # Screenshot function unit tests
│   ├── test_working_image_tools.py     # Image tools functionality tests
│   ├── test_config_loader.py           # Config loader unit tests
│   ├── test_schemas.py                 # Pydantic schemas tests
│   ├── test_context.py                 # Agent context tests
│   ├── test_voice_store.py             # Voice store unit tests
│   ├── test_nested_agent.py            # Nested agent tests
│   ├── test_multimodal_agent.py        # Multimodal agent tests
│   ├── test_agent_factory.py           # Agent factory tests
│   ├── test_looping_agent.py           # Looping agent tests
│   ├── test_tools_memory.py            # Memory tools tests
│   ├── test_tools_research.py          # Research tools tests
│   └── test_tools_image.py             # Image tools tests
│
├── integration/             # Integration tests for system components
│   ├── test_claude_code_permissions.py # Claude Code permission testing
│   ├── test_multimodal_api.py          # Multimodal agent API tests
│   ├── test_multimodal_integration.py  # Multimodal agent integration tests
│   ├── test_real_screenshot.py         # Real screenshot capture tests
│   ├── test_system_message_update.py   # System message update tests
│   ├── test_voice_claude_integration.py # Voice + Claude Code integration tests
│   ├── test_api_agents.py              # Agent API endpoint tests
│   ├── test_api_tools.py               # Tool API endpoint tests
│   ├── test_api_voice.py               # Voice API endpoint tests
│   ├── test_websocket_agents.py        # WebSocket agent tests
│   └── test_database_operations.py     # Database operation tests
│
├── e2e/                     # End-to-end workflow tests
│   ├── README.md                       # E2E tests documentation
│   ├── test_agent_workflow.py          # Complete agent workflows
│   ├── test_voice_workflow.py          # Voice assistant workflows
│   ├── test_tool_upload.py             # Tool upload workflows
│   └── test_multimodal_workflow.py     # Multimodal agent workflows
│
├── fixtures/                # Test fixtures and mock data
│   ├── README.md                       # Fixtures documentation
│   ├── __init__.py                     # Fixture exports
│   ├── agent_configs.py                # Mock agent configurations
│   ├── tool_responses.py               # Mock tool responses
│   ├── websocket_events.py             # Mock WebSocket events
│   └── voice_data.py                   # Mock voice conversation data
│
├── conftest.py              # Shared pytest configuration and fixtures
├── test_fixtures_example.py # Example tests using fixtures
└── test_image_tools.py      # Image tools test suite
```

## Running Tests

### All Tests
```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
pytest tests/ -v
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Integration Tests Only
```bash
pytest tests/integration/ -v
```

### E2E Tests Only
```bash
pytest tests/e2e/ -v
```

### Specific Test File
```bash
pytest tests/unit/test_screenshot.py -v
pytest tests/integration/test_api_agents.py -v
pytest tests/e2e/test_agent_workflow.py -v
```

## Test Categories

### Unit Tests (`tests/unit/`)
Individual component tests with full mocking:
- **test_screenshot.py** - Screenshot function with various backends
- **test_working_image_tools.py** - Image generation and sample tools
- **test_config_loader.py** - Configuration loading logic
- **test_schemas.py** - Pydantic model validation
- **test_context.py** - Agent context management
- **test_voice_store.py** - Voice conversation storage
- **test_nested_agent.py** - Nested team agent logic
- **test_multimodal_agent.py** - Multimodal agent logic
- **test_agent_factory.py** - Agent instantiation
- **test_looping_agent.py** - Looping agent behavior
- **test_tools_memory.py** - Memory management tools
- **test_tools_research.py** - Research and web tools
- **test_tools_image.py** - Image manipulation tools

### Integration Tests (`tests/integration/`)
Multi-component tests with partial mocking:
- **test_claude_code_permissions.py** - Claude Code CLI permission modes
- **test_multimodal_api.py** - Multimodal agent API integration
- **test_multimodal_integration.py** - Multimodal agent with tools
- **test_real_screenshot.py** - Screenshot capture with agent
- **test_system_message_update.py** - Dynamic system messages
- **test_voice_claude_integration.py** - Voice + Claude Code
- **test_api_agents.py** - Agent API endpoints
- **test_api_tools.py** - Tool API endpoints
- **test_api_voice.py** - Voice API endpoints
- **test_websocket_agents.py** - WebSocket communication
- **test_database_operations.py** - Database persistence

### E2E Tests (`tests/e2e/`)
Complete workflow tests with minimal mocking:
- **test_agent_workflow.py** - Complete agent execution workflows (50+ tests)
- **test_voice_workflow.py** - Voice assistant integration workflows (50+ tests)
- **test_tool_upload.py** - Tool upload and execution workflows (40+ tests)
- **test_multimodal_workflow.py** - Multimodal vision workflows (40+ tests)

**See [tests/e2e/README.md](e2e/README.md) for detailed E2E documentation.**

### Fixtures (`tests/fixtures/`)
Shared test data and helpers:
- **agent_configs.py** - Mock agent configurations
- **tool_responses.py** - Mock tool responses
- **websocket_events.py** - Mock WebSocket events
- **voice_data.py** - Mock voice conversation data

**See [tests/fixtures/README.md](fixtures/README.md) for fixtures documentation.**

## Test Requirements

Most tests require:
- Python virtual environment activated
- All dependencies installed from requirements.txt
- Backend services not necessarily running (tests are standalone)

Some integration tests may require:
- X11 or Wayland display server access (for screenshot tests)
- Claude Code CLI installed (for permission tests)
- OpenAI API key in .env (for agent tests)

## Adding New Tests

### Test Hierarchy

**Choose the right test type:**

1. **Unit tests** (`tests/unit/`) - For individual functions/classes
   - Test one component in isolation
   - Mock all external dependencies
   - Fast execution (<10ms per test)
   - Example: Testing a single function with mocked inputs

2. **Integration tests** (`tests/integration/`) - For component interactions
   - Test 2-3 components together
   - Mock external APIs (OpenAI, Anthropic)
   - Medium execution (10-100ms per test)
   - Example: Testing API endpoint with database

3. **E2E tests** (`tests/e2e/`) - For complete workflows
   - Test entire user flow end-to-end
   - Minimal mocking (only LLM APIs)
   - Slower execution (100ms-1s per test)
   - Example: Create agent → Upload tool → Execute → Verify results

### Naming Conventions

- **File names**: `test_<component>_<feature>.py`
- **Test classes**: `Test<Component><Feature>`
- **Test functions**: `test_<specific_behavior>`

### Using Fixtures

Use shared fixtures from `conftest.py` and `tests/fixtures/`:

```python
from tests.fixtures import MOCK_LOOPING_AGENT, create_mock_agent_config

def test_my_feature(client, temp_workspace, sample_agent_config):
    # Use fixtures for setup
    ...
```

## CI/CD

Tests can be run in CI/CD pipelines:
```yaml
- name: Run Tests
  run: |
    source venv/bin/activate
    pytest tests/ -v --tb=short
```

## Test Statistics

| Category | Files | Tests | Lines of Code | Coverage |
|----------|-------|-------|---------------|----------|
| Unit Tests | 13 | 150+ | 3,000+ | Individual components |
| Integration Tests | 10 | 100+ | 2,500+ | Component interactions |
| E2E Tests | 4 | 50+ | 2,380+ | Complete workflows |
| Fixtures | 4 | N/A | 1,800+ | Shared test data |
| **TOTAL** | **31** | **300+** | **9,680+** | **Complete system** |

## Quick Reference

**Run all tests:**
```bash
pytest tests/ -v
```

**Run by category:**
```bash
pytest tests/unit/ -v          # Unit tests only
pytest tests/integration/ -v   # Integration tests only
pytest tests/e2e/ -v           # E2E tests only
```

**Run with markers:**
```bash
pytest -m unit -v              # Unit tests (marked)
pytest -m integration -v       # Integration tests (marked)
pytest -m e2e -v               # E2E tests (marked)
```

**Run with coverage:**
```bash
pytest tests/ --cov=backend --cov-report=html
```

**Run specific test:**
```bash
pytest tests/e2e/test_agent_workflow.py::TestLoopingAgentWorkflow::test_complete_looping_agent_lifecycle -v
```

## Documentation

- **[tests/e2e/README.md](e2e/README.md)** - Complete E2E testing guide
- **[tests/fixtures/README.md](fixtures/README.md)** - Fixtures documentation
- **[conftest.py](conftest.py)** - Shared fixtures and configuration
- **[../CLAUDE.md](../CLAUDE.md)** - Complete system documentation

---

**Last updated:** 2025-10-11
**E2E Tests Added:** 2025-10-11
