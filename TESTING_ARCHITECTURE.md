# Testing Architecture

**Last Updated:** 2025-10-11

## Overview

This document describes the comprehensive testing strategy for the Agentic AI system, covering both backend (Python/FastAPI) and frontend (React) components.

## Testing Levels

### 1. Unit Tests
- **Purpose:** Test individual functions, classes, and modules in isolation
- **Coverage Target:** 80%+ for core business logic
- **Location:**
  - Backend: `backend/tests/unit/`
  - Frontend: `frontend/src/**/__tests__/unit/`

### 2. Integration Tests
- **Purpose:** Test interactions between components, modules, and external services
- **Coverage Target:** 70%+ for critical paths
- **Location:**
  - Backend: `backend/tests/integration/`
  - Frontend: `frontend/src/**/__tests__/integration/`

### 3. End-to-End (E2E) Tests
- **Purpose:** Test complete user workflows from UI to database
- **Coverage Target:** Key user journeys and critical features
- **Location:**
  - Backend: `backend/tests/e2e/`
  - Frontend: `frontend/e2e/`

## Backend Testing Stack

### Technologies
- **pytest** - Test runner and framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking utilities
- **httpx** - HTTP client for FastAPI testing
- **fakeredis** - Redis mocking (if needed)
- **freezegun** - Time mocking
- **factory-boy** - Test data factories

### Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py                    # Shared pytest fixtures
├── pytest.ini                     # Pytest configuration
├── fixtures/                      # Test data and mocks
│   ├── __init__.py
│   ├── agent_configs.py          # Sample agent configurations
│   ├── tool_responses.py         # Mock tool responses
│   ├── websocket_events.py       # WebSocket event fixtures
│   └── voice_data.py             # Voice conversation fixtures
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── test_config_loader.py     # Config loading tests
│   ├── test_schemas.py           # Pydantic model tests
│   ├── test_agent_factory.py     # Agent creation tests
│   ├── test_looping_agent.py     # Looping agent tests
│   ├── test_nested_agent.py      # Nested team tests
│   ├── test_multimodal_agent.py  # Multimodal agent tests
│   ├── test_runner.py            # Agent runner tests
│   ├── test_voice_store.py       # Voice storage tests
│   ├── test_context.py           # Context management tests
│   ├── test_tools_memory.py      # Memory tool tests
│   ├── test_tools_research.py    # Research tool tests
│   └── test_tools_image.py       # Image tool tests
├── integration/                   # Integration tests
│   ├── __init__.py
│   ├── test_api_agents.py        # Agent API endpoints
│   ├── test_api_tools.py         # Tool API endpoints
│   ├── test_api_voice.py         # Voice API endpoints
│   ├── test_websocket_agents.py  # Agent WebSocket integration
│   ├── test_websocket_voice.py   # Voice WebSocket integration
│   ├── test_claude_code.py       # Claude Code integration
│   ├── test_agent_tool_execution.py  # Agent + Tool integration
│   └── test_database_operations.py   # Database operations
└── e2e/                           # End-to-end tests
    ├── __init__.py
    ├── test_agent_workflow.py    # Complete agent execution
    ├── test_voice_workflow.py    # Voice assistant workflow
    ├── test_tool_upload.py       # Tool upload and execution
    └── test_multimodal_workflow.py  # Multimodal agent workflow
```

## Frontend Testing Stack

### Technologies
- **Jest** - Test runner and framework
- **React Testing Library** - Component testing
- **@testing-library/user-event** - User interaction simulation
- **MSW (Mock Service Worker)** - API mocking
- **Playwright** - E2E testing
- **@testing-library/jest-dom** - DOM matchers
- **jest-websocket-mock** - WebSocket mocking

### Test Structure

```
frontend/
├── src/
│   ├── __tests__/
│   │   ├── setup.js                 # Test setup and global mocks
│   │   └── utils.js                 # Test utilities
│   ├── features/
│   │   ├── agents/
│   │   │   ├── components/
│   │   │   │   ├── __tests__/
│   │   │   │   │   ├── AgentEditor.test.js
│   │   │   │   │   ├── RunConsole.test.js
│   │   │   │   │   └── LogMessageDisplay.test.js
│   │   │   └── pages/
│   │   │       └── __tests__/
│   │   │           └── AgentDashboard.test.js
│   │   ├── tools/
│   │   │   ├── components/
│   │   │   │   └── __tests__/
│   │   │   │       ├── CodeEditor.test.js
│   │   │   │       └── ToolEditor.test.js
│   │   │   └── pages/
│   │   │       └── __tests__/
│   │   │           └── ToolsDashboard.test.js
│   │   └── voice/
│   │       ├── components/
│   │       │   └── __tests__/
│   │       │       ├── AudioVisualizer.test.js
│   │       │       ├── ClaudeCodeInsights.test.js
│   │       │       ├── ConversationHistory.test.js
│   │       │       ├── NestedAgentInsights.test.js
│   │       │       └── VoiceSessionControls.test.js
│   │       └── pages/
│   │           └── __tests__/
│   │               ├── VoiceAssistant.test.js
│   │               └── VoiceDashboard.test.js
│   └── __tests__/
│       ├── api.test.js              # API client tests
│       └── App.test.js              # App component tests
└── e2e/                             # Playwright E2E tests
    ├── playwright.config.js
    ├── fixtures/                    # E2E fixtures
    │   ├── agents.js
    │   └── mockData.js
    └── tests/
        ├── agent-workflow.spec.js
        ├── voice-workflow.spec.js
        └── tool-management.spec.js
```

## Test Coverage Goals

### Backend
- **Unit Tests:** 85%+ coverage
  - Core modules: 90%+
  - API endpoints: 80%+
  - Tools: 85%+
  - Utils: 90%+

- **Integration Tests:** 75%+ coverage
  - API routes: 90%+
  - WebSocket connections: 80%+
  - Database operations: 85%+

- **E2E Tests:** Critical paths
  - Agent execution workflows
  - Voice assistant flows
  - Tool management

### Frontend
- **Unit Tests:** 80%+ coverage
  - Components: 85%+
  - API client: 90%+
  - Utilities: 90%+

- **Integration Tests:** 70%+ coverage
  - Feature workflows
  - API integration
  - State management

- **E2E Tests:** Critical user journeys
  - Agent creation and execution
  - Voice conversations
  - Tool upload and management

## Testing Patterns

### Backend Patterns

#### 1. Async Test Pattern
```python
@pytest.mark.asyncio
async def test_websocket_connection():
    async with AsyncClient(app=app) as client:
        async with client.websocket_connect("/api/runs/TestAgent") as ws:
            data = await ws.receive_json()
            assert data["type"] == "connected"
```

#### 2. Fixture Pattern
```python
@pytest.fixture
def sample_agent_config():
    return AgentConfig(
        name="TestAgent",
        agent_type="looping",
        tools=["test_tool"],
        llm=LLMConfig(provider="openai", model="gpt-4")
    )
```

#### 3. Mock Pattern
```python
def test_agent_execution(mocker):
    mock_llm = mocker.patch("core.agent_factory.ChatCompletionClient")
    mock_llm.return_value.create.return_value = mock_response
    agent = create_agent_from_config(config)
    result = agent.run()
    assert result.status == "success"
```

### Frontend Patterns

#### 1. Component Test Pattern
```javascript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('renders agent editor', async () => {
  render(<AgentEditor />);
  const input = screen.getByLabelText('Agent Name');
  await userEvent.type(input, 'TestAgent');
  expect(input).toHaveValue('TestAgent');
});
```

#### 2. API Mock Pattern (MSW)
```javascript
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/agents', (req, res, ctx) => {
    return res(ctx.json({ agents: mockAgents }));
  })
);
```

#### 3. WebSocket Mock Pattern
```javascript
import WS from 'jest-websocket-mock';

test('websocket connection', async () => {
  const server = new WS('ws://localhost:8000/api/runs/Agent');
  render(<RunConsole agentName="Agent" />);
  await server.connected;
  server.send(JSON.stringify({ type: 'message', data: 'test' }));
});
```

## Running Tests

### Backend

```bash
# Run all tests
cd backend
source venv/bin/activate
pytest

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_agent_factory.py

# Run specific test
pytest tests/unit/test_agent_factory.py::test_create_looping_agent

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/integration/

# Run fast tests only (skip slow)
pytest -m "not slow"
```

### Frontend

```bash
# Run all tests
cd frontend
npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test AgentEditor.test.js

# Run E2E tests
npm run test:e2e

# Run E2E tests in headed mode
npm run test:e2e:headed

# Update snapshots
npm test -- -u
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch
- Nightly builds

### CI Pipeline
1. **Lint** - Code quality checks
2. **Unit Tests** - Fast isolated tests
3. **Integration Tests** - Component interaction tests
4. **E2E Tests** - Full workflow tests
5. **Coverage Report** - Upload to coverage service

## Test Data Management

### Fixtures
- Store in `tests/fixtures/`
- Use factory pattern for complex objects
- Keep fixtures minimal and focused

### Mocks
- Mock external services (OpenAI, Anthropic APIs)
- Mock file system operations
- Mock network requests
- Use real implementations for internal code when possible

### Database
- Use in-memory SQLite for tests
- Reset database between tests
- Use transactions for isolation

## Best Practices

1. **Test Naming:** Use descriptive names that explain what is being tested
   - ✅ `test_agent_factory_creates_looping_agent_with_valid_config`
   - ❌ `test_agent_1`

2. **Arrange-Act-Assert:** Structure tests clearly
   ```python
   def test_example():
       # Arrange
       config = create_test_config()

       # Act
       result = function_under_test(config)

       # Assert
       assert result.success is True
   ```

3. **One Assertion Per Test:** Focus tests on single behaviors
4. **Fast Tests:** Keep unit tests under 100ms
5. **Isolated Tests:** Tests should not depend on each other
6. **Clean Mocks:** Reset mocks between tests
7. **Readable Tests:** Tests are documentation
8. **Test Edge Cases:** Don't just test happy paths

## Troubleshooting

### Common Issues

**Issue: Tests pass locally but fail in CI**
- Solution: Check for timing issues, use proper async/await, ensure clean state

**Issue: Flaky tests**
- Solution: Add proper waits, use deterministic test data, avoid time-based assertions

**Issue: Slow tests**
- Solution: Mock external services, use in-memory databases, parallelize tests

**Issue: Low coverage**
- Solution: Identify uncovered code with coverage reports, add targeted tests

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright Documentation](https://playwright.dev/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Testing Best Practices](https://testingjavascript.com/)

---

**Next Steps:**
1. Review and approve testing architecture
2. Install testing dependencies
3. Create test configuration files
4. Implement test suites following this structure
5. Set up CI/CD pipeline
6. Achieve target coverage
