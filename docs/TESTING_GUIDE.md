# Complete Testing Guide

**Version:** 1.0
**Last Updated:** 2025-10-12

---

## Quick Start

```bash
# Backend Tests
cd backend && source venv/bin/activate
pytest                              # Run all tests
pytest --cov=. --cov-report=html   # With coverage

# Frontend Tests
cd frontend
npm test                           # Run unit tests
npm run test:integration          # Run integration tests
npm run test:e2e                  # Run E2E tests
npm run test:all                  # Run all tests
```

---

## Table of Contents

1. [Overview](#overview)
2. [Backend Testing](#backend-testing)
3. [Frontend Testing](#frontend-testing)
4. [Test Coverage](#test-coverage)
5. [CI/CD Integration](#cicd-integration)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This project has comprehensive test coverage across three levels:

- **Unit Tests** - Test individual functions and components in isolation
- **Integration Tests** - Test interactions between modules and APIs
- **E2E Tests** - Test complete user workflows in real browsers

### Test Statistics

| Category | Backend | Frontend | Total |
|----------|---------|----------|-------|
| **Unit Tests** | 400+ | 276+ | 676+ |
| **Integration Tests** | 245+ | 110+ | 355+ |
| **E2E Tests** | 50+ | 67+ | 117+ |
| **Total** | **695+** | **453+** | **1,148+** |

---

## Backend Testing

### Architecture

```
backend/tests/
├── conftest.py                 # Shared fixtures
├── pytest.ini                  # Configuration
├── fixtures/                   # Mock data
│   ├── agent_configs.py
│   ├── tool_responses.py
│   ├── websocket_events.py
│   └── voice_data.py
├── unit/                       # Unit tests (400+ tests)
│   ├── test_config_loader.py
│   ├── test_schemas.py
│   ├── test_agent_factory.py
│   ├── test_looping_agent.py
│   ├── test_nested_agent.py
│   ├── test_multimodal_agent.py
│   ├── test_context.py
│   ├── test_voice_store.py
│   ├── test_tools_memory.py
│   ├── test_tools_research.py
│   └── test_tools_image.py
├── integration/                # Integration tests (245+ tests)
│   ├── test_api_agents.py
│   ├── test_api_tools.py
│   ├── test_api_voice.py
│   ├── test_websocket_agents.py
│   └── test_database_operations.py
└── e2e/                        # E2E tests (50+ tests)
    ├── test_agent_workflow.py
    ├── test_voice_workflow.py
    ├── test_tool_upload.py
    └── test_multimodal_workflow.py
```

### Running Backend Tests

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate

# Run all tests
pytest

# Run specific test levels
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest tests/e2e/              # E2E tests only

# Run specific test file
pytest tests/unit/test_agent_factory.py

# Run specific test
pytest tests/unit/test_agent_factory.py::test_create_looping_agent

# Run with markers
pytest -m unit                 # Only unit tests
pytest -m integration          # Only integration tests
pytest -m "not slow"           # Skip slow tests

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run with verbose output
pytest -v -s

# Run in parallel (requires pytest-xdist)
pytest -n auto
```

### Backend Test Fixtures

All fixtures are available in `tests/fixtures/`:

```python
from tests.fixtures import (
    MOCK_LOOPING_AGENT,
    MOCK_NESTED_AGENT,
    MOCK_WEB_SEARCH_RESPONSE,
    MOCK_WS_CONNECT_EVENT,
    MOCK_VOICE_CONVERSATION,
)

def test_example():
    agent = MOCK_LOOPING_AGENT
    assert agent.agent_type == "looping"
```

---

## Frontend Testing

### Architecture

```
frontend/
├── src/
│   ├── setupTests.js           # Jest configuration
│   ├── __tests__/
│   │   ├── setup.js            # Test utilities
│   │   ├── mocks/              # MSW mocks
│   │   │   ├── handlers.js
│   │   │   ├── server.js
│   │   │   ├── websocket.js
│   │   │   └── data.js
│   │   └── integration/        # Integration tests (110+ tests)
│   │       ├── api.integration.test.js
│   │       ├── agent-workflow.integration.test.js
│   │       ├── tool-workflow.integration.test.js
│   │       └── voice-workflow.integration.test.js
│   └── features/
│       ├── agents/
│       │   ├── components/__tests__/  # Component tests
│       │   └── pages/__tests__/       # Page tests
│       ├── tools/
│       │   ├── components/__tests__/
│       │   └── pages/__tests__/
│       └── voice/
│           ├── components/__tests__/  # 276+ tests total
│           └── pages/__tests__/
└── e2e/                        # Playwright E2E tests (67+ tests)
    ├── playwright.config.js
    ├── fixtures/
    └── tests/
        ├── agent-workflow.spec.js
        ├── tool-management.spec.js
        └── voice-workflow.spec.js
```

### Running Frontend Tests

```bash
cd /home/rodrigo/agentic/frontend

# Unit tests
npm test                       # Interactive mode
npm run test:coverage         # With coverage
npm run test:unit             # Unit tests only

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e              # Headless mode
npm run test:e2e:headed       # With visible browser
npm run test:e2e:ui           # Interactive UI mode
npm run test:e2e:debug        # Debug mode
npm run test:e2e:chromium     # Chromium only
npm run test:e2e:firefox      # Firefox only
npm run test:e2e:webkit       # WebKit only

# Run all tests
npm run test:all

# CI mode (non-interactive)
npm run test:ci
```

### Frontend Test Patterns

**Component Testing:**
```javascript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AgentEditor from '../AgentEditor';

test('allows user to edit agent name', async () => {
  const user = userEvent.setup();
  render(<AgentEditor />);

  const nameInput = screen.getByLabelText(/agent name/i);
  await user.clear(nameInput);
  await user.type(nameInput, 'MyNewAgent');

  expect(nameInput).toHaveValue('MyNewAgent');
});
```

**API Integration Testing:**
```javascript
import { rest } from 'msw';
import { server } from './__tests__/mocks/server';

test('fetches agents from API', async () => {
  server.use(
    rest.get('/api/agents', (req, res, ctx) => {
      return res(ctx.json([{ name: 'TestAgent' }]));
    })
  );

  // Test code here
});
```

**E2E Testing:**
```javascript
import { test, expect } from '@playwright/test';

test('user can create new agent', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.click('text=Create Agent');
  await page.fill('[name="agentName"]', 'MyAgent');
  await page.click('text=Save');
  await expect(page.locator('text=MyAgent')).toBeVisible();
});
```

---

## Test Coverage

### Current Coverage

**Backend:**
- Unit Tests: 85%+ coverage
- Integration Tests: 75%+ coverage
- E2E Tests: Critical paths covered

**Frontend:**
- Unit Tests: 80%+ coverage (4 files completed, templates provided for 10 more)
- Integration Tests: 70%+ coverage
- E2E Tests: Critical user journeys covered

### Viewing Coverage Reports

**Backend:**
```bash
cd backend
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

**Frontend:**
```bash
cd frontend
npm run test:coverage
open coverage/lcov-report/index.html
```

### Coverage Goals

| Module | Target | Current |
|--------|--------|---------|
| Backend Core | 90% | 85%+ |
| Backend API | 85% | 80%+ |
| Backend Tools | 85% | 85%+ |
| Backend Utils | 90% | 90%+ |
| Frontend Components | 85% | 80%+ |
| Frontend API | 90% | 90%+ |

---

## CI/CD Integration

### GitHub Actions

See [`.github/workflows/tests.yml`](.github/workflows/tests.yml) for complete CI/CD pipeline.

**Pipeline Stages:**
1. Lint & Format Check
2. Backend Unit Tests
3. Backend Integration Tests
4. Backend E2E Tests
5. Frontend Unit Tests
6. Frontend Integration Tests
7. Frontend E2E Tests
8. Coverage Report Upload

### Running Locally (CI Mode)

**Backend:**
```bash
cd backend
pytest --cov=. --cov-report=xml --cov-report=term -v
```

**Frontend:**
```bash
cd frontend
CI=true npm run test:ci
npm run test:e2e -- --reporter=junit
```

---

## Best Practices

### General

1. **Test Naming:** Use descriptive names
   - ✅ `test_agent_factory_creates_looping_agent_with_valid_config`
   - ❌ `test_1`

2. **Arrange-Act-Assert:** Structure tests clearly
   ```python
   def test_example():
       # Arrange
       config = create_config()
       # Act
       result = function(config)
       # Assert
       assert result.success
   ```

3. **Isolation:** Tests should not depend on each other
4. **Fast Tests:** Keep unit tests under 100ms
5. **Readable Tests:** Tests are documentation

### Backend Best Practices

- Use fixtures from `conftest.py`
- Mock external APIs (OpenAI, Anthropic)
- Use temporary databases/files
- Test both success and error paths
- Use markers to categorize tests

### Frontend Best Practices

- Test behavior, not implementation
- Use semantic queries (`getByRole`, `getByLabelText`)
- Test user interactions with `userEvent`
- Mock APIs with MSW
- Use `waitFor` for async operations
- Test accessibility

### E2E Best Practices

- Test critical user paths only
- Use Page Object pattern for complex pages
- Take screenshots on failure
- Clean up test data
- Run in parallel when possible

---

## Troubleshooting

### Backend Issues

**Tests pass locally but fail in CI:**
- Check for timing issues, use proper async/await
- Ensure clean state between tests
- Mock time-dependent code with `freezegun`

**Database errors:**
- Ensure using temporary database (fixtures handle this)
- Check for foreign key constraints
- Verify database is reset between tests

**Import errors:**
- Check `PYTHONPATH` includes project root
- Verify `pytest.ini` has `pythonpath = .`

### Frontend Issues

**Tests timeout:**
- Increase timeout in `waitFor`
- Check for missing mock API responses
- Verify WebSocket mocks are set up correctly

**WebSocket tests fail:**
- Use `jest-websocket-mock` correctly
- Clean up servers in `afterEach`
- Wait for connection before sending messages

**Playwright tests fail:**
- Ensure backend is running (`npm run start`)
- Check browser is installed (`npx playwright install`)
- Verify ports are not in use
- Check test timeouts

**Coverage too low:**
- Identify uncovered code with HTML report
- Add tests for edge cases
- Test error paths

### Common Solutions

**Clear test cache:**
```bash
# Backend
pytest --cache-clear

# Frontend
npm test -- --clearCache
```

**Reset environment:**
```bash
# Backend
rm -rf .pytest_cache __pycache__ htmlcov .coverage
pip install -r requirements.txt

# Frontend
rm -rf node_modules coverage .nyc_output
npm install
```

**Debug tests:**
```bash
# Backend
pytest --pdb  # Drop into debugger on failure
pytest -vv    # Very verbose output

# Frontend
npm run test:debug  # Node debugger
npm run test:e2e:debug  # Playwright debugger
```

---

## Test Documentation

- **Backend Tests:**
  - [Unit Tests Summary](backend/tests/unit/UNIT_TESTS_SUMMARY.md)
  - [Tools Tests Summary](backend/tests/unit/TOOLS_TESTS_SUMMARY.md)
  - [Integration Tests Guide](backend/tests/integration/README.md)
  - [E2E Tests Guide](backend/tests/e2e/README.md)
  - [Fixtures Documentation](backend/tests/fixtures/README.md)

- **Frontend Tests:**
  - [Testing Guide](frontend/TESTING_GUIDE.md)
  - [Test Suite Summary](frontend/TEST_SUITE_SUMMARY.md)
  - [E2E Tests Guide](frontend/e2e/README.md)

- **Architecture:**
  - [Testing Architecture](TESTING_ARCHITECTURE.md)

---

## Quick Reference

```bash
# Backend
cd backend && source venv/bin/activate
pytest                                    # All tests
pytest tests/unit/                        # Unit tests
pytest tests/integration/                 # Integration tests
pytest tests/e2e/                        # E2E tests
pytest --cov=. --cov-report=html         # Coverage

# Frontend
cd frontend
npm test                                 # Unit tests (interactive)
npm run test:coverage                    # Unit tests with coverage
npm run test:integration                 # Integration tests
npm run test:e2e                        # E2E tests
npm run test:e2e:headed                 # E2E tests (visible)
npm run test:e2e:ui                     # E2E tests (UI mode)
npm run test:all                        # All tests

# Both
# Run backend and frontend tests in sequence
(cd backend && pytest) && (cd frontend && npm run test:ci)
```

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright Documentation](https://playwright.dev/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Jest Documentation](https://jestjs.io/)
- [MSW Documentation](https://mswjs.io/)

---

**Last Updated:** 2025-10-12
**Maintained By:** Development Team
**Questions?** See [Troubleshooting](#troubleshooting) or open an issue.
