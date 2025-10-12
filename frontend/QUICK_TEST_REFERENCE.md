# Quick Test Reference Card

## Run Tests

```bash
# Integration Tests
npm run test:integration

# E2E Tests (install browsers first time)
npx playwright install
npm run test:e2e

# E2E with visible browser
npm run test:e2e:headed

# E2E interactive mode
npm run test:e2e:ui

# All tests
npm run test:all
```

## File Locations

- **Integration Tests:** `src/__tests__/integration/`
- **E2E Tests:** `e2e/tests/`
- **E2E Helpers:** `e2e/fixtures/test-helpers.js`
- **Test Data:** `e2e/fixtures/test-data.js`

## Test Count

- Integration Tests: 110+
- E2E Tests: 67+
- Total: 177+ tests

## Documentation

- **E2E Guide:** `e2e/README.md`
- **Testing Guide:** `TESTING_GUIDE.md`
- **Implementation Summary:** `TEST_IMPLEMENTATION_SUMMARY.md`
