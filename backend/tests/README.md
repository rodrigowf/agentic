# Backend Tests

This directory contains all test files for the backend codebase.

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_dynamic_init_agent.py       # Dynamic initialization agent tests
│   ├── test_screenshot.py               # Screenshot function unit tests
│   └── test_working_image_tools.py      # Image tools functionality tests
│
├── integration/             # Integration tests for system components
│   ├── test_claude_code_permissions.py  # Claude Code permission testing
│   ├── test_dynamic_init_integration.py # Dynamic init agent integration tests
│   ├── test_multimodal_api.py           # Multimodal agent API tests
│   ├── test_multimodal_integration.py   # Multimodal agent integration tests
│   ├── test_real_screenshot.py          # Real screenshot capture tests
│   ├── test_system_message_update.py    # System message update tests
│   └── test_voice_claude_integration.py # Voice + Claude Code integration tests
│
├── e2e_dynamic_init_test.py # End-to-end dynamic init agent tests
└── test_image_tools.py      # Image tools test suite (in parent tests/ dir)
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

### Specific Test File
```bash
pytest tests/unit/test_screenshot.py -v
```

## Test Categories

### Unit Tests
- **test_dynamic_init_agent.py** - Tests dynamic initialization agent functionality (11 tests)
- **test_screenshot.py** - Tests the take_screenshot function with various backends
- **test_working_image_tools.py** - Tests generate_test_image and get_sample_image functions

### Integration Tests
- **test_claude_code_permissions.py** - Tests Claude Code CLI with different permission modes
- **test_dynamic_init_integration.py** - Tests dynamic init agent with factory and config (4 tests)
- **test_multimodal_api.py** - Full-stack API test for multimodal vision agent
- **test_multimodal_integration.py** - Tests multimodal agent with tool interactions
- **test_real_screenshot.py** - End-to-end screenshot capture test with agent
- **test_system_message_update.py** - Tests dynamic system message updates
- **test_voice_claude_integration.py** - Tests voice assistant with Claude Code integration

### End-to-End Tests
- **e2e_dynamic_init_test.py** - Full-stack dynamic initialization agent tests (3 tests)

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

1. **Unit tests** - Place in `tests/unit/`
   - Test individual functions/classes
   - Mock external dependencies
   - Fast execution

2. **Integration tests** - Place in `tests/integration/`
   - Test multiple components together
   - May require external services
   - Slower execution

3. **Naming convention**: `test_<component>_<feature>.py`

4. **Use pytest fixtures** for common setup/teardown

## CI/CD

Tests can be run in CI/CD pipelines:
```yaml
- name: Run Tests
  run: |
    source venv/bin/activate
    pytest tests/ -v --tb=short
```

## Recent Test Additions

### Dynamic Initialization Agent Tests (2025-11-08)

Added comprehensive test coverage for the new dynamic initialization agent:

- **11 unit tests** in `test_dynamic_init_agent.py`:
  - Agent creation with/without initialization
  - Invalid function format handling
  - Module/function not found handling
  - Successful initialization execution
  - Agent modification via initialization

- **4 integration tests** in `test_dynamic_init_integration.py`:
  - Agent factory creation
  - Memory config loading
  - Memory initialization function execution
  - Memory agent with auto-initialization

- **3 end-to-end tests** in `e2e_dynamic_init_test.py`:
  - API configuration verification
  - Agent creation with initialization
  - Backend integration

**Total: 18 tests passing**

Run all dynamic init tests:
```bash
cd backend && source venv/bin/activate
pytest tests/unit/test_dynamic_init_agent.py -v
python3 tests/integration/test_dynamic_init_integration.py
python3 tests/e2e_dynamic_init_test.py
```

---

**Last updated:** 2025-11-08
