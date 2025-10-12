/**
 * agent-workflow.spec.js - Agent Management E2E Tests
 *
 * End-to-end tests for agent management workflows.
 * Tests real user interactions with actual browser automation.
 */

const { test, expect } = require('@playwright/test');
const {
  waitForAPIResponse,
  fillForm,
  waitForLoadingComplete,
  takeTimestampedScreenshot,
} = require('../fixtures/test-helpers');
const { testAgents, selectors, timeouts } = require('../fixtures/test-data');

test.describe('Agent Management E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to agent dashboard
    await page.goto('/agents');
    await waitForLoadingComplete(page);
  });

  // ============================================================================
  // Agent List Display
  // ============================================================================

  test('should display agent list on page load', async ({ page }) => {
    // Wait for API response
    await waitForAPIResponse(page, '/api/agents');

    // Verify page title/heading
    await expect(page.locator('h1, h2, h3').first()).toContainText(/agents/i);

    // Verify agent list is visible
    const agentList = page.locator('[data-testid="agent-list"], .agent-list, table');
    await expect(agentList).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'test-results/screenshots/agent-list.png' });
  });

  test('should display agent details', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Find first agent item
    const firstAgent = page.locator('[data-testid="agent-item"], tr, .agent-card').first();
    await expect(firstAgent).toBeVisible();

    // Verify agent name is displayed
    await expect(firstAgent).toContainText(/\w+/);
  });

  // ============================================================================
  // Agent Creation
  // ============================================================================

  test('should create new looping agent', async ({ page }) => {
    // Click create agent button
    const createButton = page.getByRole('button', { name: /create.*agent/i });
    await createButton.click();

    // Verify form is displayed
    await expect(page.getByLabel(/agent name/i)).toBeVisible();

    // Fill form
    await fillForm(page, {
      'Agent Name': testAgents.looping.name,
      Description: testAgents.looping.description,
    });

    // Select agent type
    const typeSelect = page.getByLabel(/agent type/i);
    await typeSelect.selectOption('looping');

    // Fill LLM config
    const providerSelect = page.getByLabel(/provider/i);
    await providerSelect.selectOption('openai');

    const modelInput = page.getByLabel(/model/i);
    await modelInput.fill('gpt-4o-mini');

    // Submit form
    const submitButton = page.getByRole('button', { name: /create|save/i });
    await submitButton.click();

    // Wait for success message
    await expect(page.locator('.success-message, [role="alert"]')).toContainText(
      /created successfully/i,
      { timeout: timeouts.long }
    );

    // Verify agent appears in list
    await page.goto('/agents');
    await waitForLoadingComplete(page);
    await expect(page.locator('body')).toContainText(testAgents.looping.name);

    // Take screenshot
    await takeTimestampedScreenshot(page, 'agent-created');
  });

  test('should create nested team agent', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /create.*agent/i });
    await createButton.click();

    await fillForm(page, {
      'Agent Name': testAgents.nestedTeam.name,
      Description: testAgents.nestedTeam.description,
    });

    // Select nested_team type
    const typeSelect = page.getByLabel(/agent type/i);
    await typeSelect.selectOption('nested_team');

    // Add sub-agents
    const subAgentsInput = page.getByLabel(/sub.*agents/i);
    await subAgentsInput.fill('Researcher,Developer');

    // Submit
    const submitButton = page.getByRole('button', { name: /create|save/i });
    await submitButton.click();

    // Verify success
    await expect(page.locator('.success-message, [role="alert"]')).toContainText(
      /created successfully/i,
      { timeout: timeouts.long }
    );
  });

  test('should validate required fields', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /create.*agent/i });
    await createButton.click();

    // Try to submit without filling fields
    const submitButton = page.getByRole('button', { name: /create|save/i });
    await submitButton.click();

    // Verify validation error
    await expect(page.locator('body')).toContainText(/required/i);
  });

  // ============================================================================
  // Agent Editing
  // ============================================================================

  test('should edit existing agent', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Find and click edit button for first agent
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    await editButton.click();

    // Wait for form to load
    await expect(page.getByLabel(/agent name/i)).toBeVisible();

    // Modify description
    const descInput = page.getByLabel(/description/i);
    await descInput.fill('Updated E2E test description');

    // Save changes
    const saveButton = page.getByRole('button', { name: /save|update/i });
    await saveButton.click();

    // Verify success
    await expect(page.locator('.success-message, [role="alert"]')).toContainText(
      /updated|saved successfully/i,
      { timeout: timeouts.long }
    );

    await takeTimestampedScreenshot(page, 'agent-edited');
  });

  test('should cancel edit without saving', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Open edit form
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    await editButton.click();

    // Make changes
    const descInput = page.getByLabel(/description/i);
    await descInput.fill('This should not be saved');

    // Cancel
    const cancelButton = page.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    // Verify form is closed
    await expect(page.getByLabel(/agent name/i)).not.toBeVisible();
  });

  // ============================================================================
  // Agent Execution
  // ============================================================================

  test('should open agent run console', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Click run button
    const runButton = page.getByRole('button', { name: /run/i }).first();
    await runButton.click();

    // Verify console is displayed
    await expect(page.locator('body')).toContainText(/console|execution/i);

    // Verify start button is present
    await expect(page.getByRole('button', { name: /start/i })).toBeVisible();

    await page.screenshot({ path: 'test-results/screenshots/run-console.png' });
  });

  test('should start and stop agent execution', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Open console
    const runButton = page.getByRole('button', { name: /run/i }).first();
    await runButton.click();

    // Listen for WebSocket connection
    const wsPromise = page.waitForEvent('websocket', {
      predicate: (ws) => ws.url().includes('/api/runs/'),
      timeout: timeouts.medium,
    });

    // Start execution
    const startButton = page.getByRole('button', { name: /start/i });
    await startButton.click();

    // Verify WebSocket connection
    const ws = await wsPromise;
    expect(ws.url()).toContain('/api/runs/');

    // Wait for some execution
    await page.waitForTimeout(2000);

    // Stop execution
    const stopButton = page.getByRole('button', { name: /stop/i });
    await expect(stopButton).toBeVisible({ timeout: timeouts.short });
    await stopButton.click();

    // Verify stopped
    await expect(page.locator('body')).toContainText(/stopped|completed/i, {
      timeout: timeouts.medium,
    });

    await takeTimestampedScreenshot(page, 'agent-execution');
  });

  test('should display execution messages', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Open console
    const runButton = page.getByRole('button', { name: /run/i }).first();
    await runButton.click();

    // Start execution
    const startButton = page.getByRole('button', { name: /start/i });
    await startButton.click();

    // Wait for messages to appear
    await page.waitForTimeout(3000);

    // Verify message area has content
    const messageArea = page.locator('[data-testid="message-area"], .messages, .console-output');
    const content = await messageArea.textContent();
    expect(content.length).toBeGreaterThan(0);
  });

  // ============================================================================
  // Agent Deletion
  // ============================================================================

  test('should delete agent with confirmation', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Get initial agent count
    const agentItems = page.locator('[data-testid="agent-item"], tr, .agent-card');
    const initialCount = await agentItems.count();

    // Click delete button
    const deleteButton = page.getByRole('button', { name: /delete/i }).first();
    await deleteButton.click();

    // Verify confirmation dialog
    await expect(page.locator('body')).toContainText(/confirm.*delete/i);

    // Confirm deletion
    const confirmButton = page.getByRole('button', { name: /confirm|yes/i });
    await confirmButton.click();

    // Wait for success message
    await expect(page.locator('.success-message, [role="alert"]')).toContainText(
      /deleted successfully/i,
      { timeout: timeouts.long }
    );

    // Verify agent is removed from list
    await page.waitForTimeout(1000);
    const newCount = await agentItems.count();
    expect(newCount).toBeLessThan(initialCount);

    await takeTimestampedScreenshot(page, 'agent-deleted');
  });

  test('should cancel deletion', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Click delete
    const deleteButton = page.getByRole('button', { name: /delete/i }).first();
    await deleteButton.click();

    // Cancel
    const cancelButton = page.getByRole('button', { name: /cancel|no/i });
    await cancelButton.click();

    // Verify dialog is closed
    await expect(page.locator('body')).not.toContainText(/confirm.*delete/i);
  });

  // ============================================================================
  // Search and Filter
  // ============================================================================

  test('should search/filter agents', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Find search input
    const searchInput = page.locator('input[placeholder*="search" i], input[aria-label*="search" i]');

    if (await searchInput.isVisible()) {
      // Enter search term
      await searchInput.fill('Researcher');

      // Wait for filter to apply
      await page.waitForTimeout(500);

      // Verify results are filtered
      const visibleAgents = page.locator('[data-testid="agent-item"]:visible, tr:visible');
      const count = await visibleAgents.count();
      expect(count).toBeGreaterThan(0);

      await page.screenshot({ path: 'test-results/screenshots/agent-search.png' });
    }
  });

  // ============================================================================
  // Navigation
  // ============================================================================

  test('should navigate between agent views', async ({ page }) => {
    await waitForAPIResponse(page, '/api/agents');

    // Navigate to specific agent page (if exists)
    const firstAgentLink = page.locator('a[href*="/agents/"]').first();

    if (await firstAgentLink.isVisible()) {
      await firstAgentLink.click();
      await waitForLoadingComplete(page);

      // Verify agent detail page
      await expect(page.locator('h1, h2')).toBeVisible();

      // Navigate back
      await page.goBack();
      await expect(page.locator('body')).toContainText(/agents/i);
    }
  });

  // ============================================================================
  // Error Handling
  // ============================================================================

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/api/agents', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });

    await page.goto('/agents');

    // Verify error message is displayed
    await expect(page.locator('body')).toContainText(/error|failed/i, {
      timeout: timeouts.medium,
    });

    await page.screenshot({ path: 'test-results/screenshots/agent-error.png' });
  });
});
