# Frontend Testing Guide

**Last Updated:** 2025-10-12

Comprehensive testing strategy for the agentic frontend application.

---

## Overview

This project uses a multi-layered testing approach:

- **Unit Tests:** Test individual components in isolation
- **Integration Tests:** Test API client and feature workflows with mocked HTTP/WebSocket
- **E2E Tests:** Test complete user workflows in real browsers

**Test Stack:**
- Jest + React Testing Library (unit/integration)
- Mock Service Worker (MSW) for API mocking
- Playwright for E2E browser automation
- jest-websocket-mock for WebSocket testing

---

## Test Scripts

| Command | Description |
|---------|-------------|
| `npm test` | Run unit tests in watch mode |
| `npm run test:unit` | Run only unit tests |
| `npm run test:integration` | Run integration tests |
| `npm run test:coverage` | Run tests with coverage |
| `npm run test:ci` | Run tests in CI mode |
| `npm run test:e2e` | Run E2E tests |
| `npm run test:e2e:ui` | Run E2E tests in interactive UI mode |
| `npm run test:all` | Run all tests |

---

## Quick Start

```bash
# Install dependencies
cd /home/rodrigo/agentic/frontend
npm install

# Install Playwright browsers
npx playwright install

# Run all tests
npm run test:all
```

---

## Documentation

- **Integration Tests:** See test files in `src/__tests__/integration/`
- **E2E Tests:** See `e2e/README.md` for detailed guide
- **Test Setup:** See `src/setupTests.js` for Jest configuration

---

**Last Updated:** 2025-10-12
