# Backend Tests

This directory contains all test files for the backend codebase.

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_screenshot.py              # Screenshot function unit tests
│   └── test_working_image_tools.py     # Image tools functionality tests
│
├── integration/             # Integration tests for system components
│   ├── test_claude_code_permissions.py # Claude Code permission testing
│   ├── test_multimodal_api.py          # Multimodal agent API tests
│   ├── test_multimodal_integration.py  # Multimodal agent integration tests
│   ├── test_real_screenshot.py         # Real screenshot capture tests
│   ├── test_system_message_update.py   # System message update tests
│   └── test_voice_claude_integration.py # Voice + Claude Code integration tests
│
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
- **test_screenshot.py** - Tests the take_screenshot function with various backends
- **test_working_image_tools.py** - Tests generate_test_image and get_sample_image functions

### Integration Tests
- **test_claude_code_permissions.py** - Tests Claude Code CLI with different permission modes
- **test_multimodal_api.py** - Full-stack API test for multimodal vision agent
- **test_multimodal_integration.py** - Tests multimodal agent with tool interactions
- **test_real_screenshot.py** - End-to-end screenshot capture test with agent
- **test_system_message_update.py** - Tests dynamic system message updates
- **test_voice_claude_integration.py** - Tests voice assistant with Claude Code integration

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

---

**Last updated:** 2025-10-11
