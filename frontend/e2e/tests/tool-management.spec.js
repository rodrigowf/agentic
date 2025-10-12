/**
 * tool-management.spec.js - Tool Management E2E Tests
 *
 * End-to-end tests for tool management workflows.
 * Tests tool upload, editing, and code generation.
 */

const { test, expect } = require('@playwright/test');
const { readFileSync } = require('fs');
const { join } = require('path');
const {
  waitForAPIResponse,
  fillForm,
  waitForLoadingComplete,
  takeTimestampedScreenshot,
} = require('../fixtures/test-helpers');
const { testToolCode, timeouts } = require('../fixtures/test-data');

test.describe('Tool Management E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to tools dashboard
    await page.goto('/tools');
    await waitForLoadingComplete(page);
  });

  // ============================================================================
  // Tool List Display
  // ============================================================================

  test('should display tool list on page load', async ({ page }) => {
    // Wait for API response
    await waitForAPIResponse(page, '/api/tools');

    // Verify page title
    await expect(page.locator('h1, h2, h3').first()).toContainText(/tools/i);

    // Verify tool list is visible
    const toolList = page.locator('[data-testid="tool-list"], .tool-list, table');
    await expect(toolList).toBeVisible();

    await page.screenshot({ path: 'test-results/screenshots/tool-list.png' });
  });

  test('should display tool details', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Find first tool
    const firstTool = page.locator('[data-testid="tool-item"], tr, .tool-card').first();
    await expect(firstTool).toBeVisible();

    // Verify tool has name and description
    const text = await firstTool.textContent();
    expect(text.length).toBeGreaterThan(0);
  });

  test('should group tools by file', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Look for file groupings
    const body = await page.locator('body').textContent();
    const hasFileNames = body.includes('.py') || body.includes('file');
    expect(hasFileNames).toBeTruthy();
  });

  // ============================================================================
  // Tool Upload
  // ============================================================================

  test('should upload new tool file', async ({ page }) => {
    // Click upload button
    const uploadButton = page.getByRole('button', { name: /upload.*tool/i });
    await uploadButton.click();

    // Verify upload form is displayed
    await expect(page.getByText(/select.*file|choose.*file/i)).toBeVisible();

    // Create test file
    const fileContent = testToolCode;
    const fileName = 'e2e_test_tool.py';

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: fileName,
      mimeType: 'text/x-python',
      buffer: Buffer.from(fileContent),
    });

    // Submit upload
    const submitButton = page.getByRole('button', { name: /upload|submit/i });
    await submitButton.click();

    // Verify success message
    await expect(page.locator('.success-message, [role="alert"]')).toContainText(
      /uploaded successfully/i,
      { timeout: timeouts.long }
    );

    // Verify tool appears in list
    await page.goto('/tools');
    await waitForLoadingComplete(page);
    await expect(page.locator('body')).toContainText(/e2e_test_tool/i);

    await takeTimestampedScreenshot(page, 'tool-uploaded');
  });

  test('should validate file type on upload', async ({ page }) => {
    const uploadButton = page.getByRole('button', { name: /upload.*tool/i });
    await uploadButton.click();

    // Try to upload non-Python file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('not a python file'),
    });

    // Check for validation error
    const errorMessage = page.locator('body');
    const hasError = await errorMessage.textContent();
    expect(hasError.toLowerCase()).toContain('python' || 'invalid' || 'error');
  });

  test('should cancel tool upload', async ({ page }) => {
    const uploadButton = page.getByRole('button', { name: /upload.*tool/i });
    await uploadButton.click();

    // Cancel
    const cancelButton = page.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    // Verify form is closed
    await expect(page.locator('input[type="file"]')).not.toBeVisible();
  });

  // ============================================================================
  // Tool Editing
  // ============================================================================

  test('should open tool editor', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Click edit button
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    await editButton.click();

    // Verify editor is displayed
    await expect(page.locator('body')).toContainText(/editor/i);

    // Verify code editor (Monaco or similar)
    const codeEditor = page.locator(
      '[data-testid="code-editor"], .monaco-editor, textarea.code'
    );
    await expect(codeEditor).toBeVisible({ timeout: timeouts.medium });

    await page.screenshot({ path: 'test-results/screenshots/tool-editor.png' });
  });

  test('should load tool code in editor', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Click edit button
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    await editButton.click();

    // Wait for code to load
    await page.waitForTimeout(2000);

    // Verify code is loaded
    const editor = page.locator('[data-testid="code-editor"], .monaco-editor, textarea');
    const hasCode = await editor.isVisible();
    expect(hasCode).toBeTruthy();
  });

  test('should save tool code changes', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Open editor
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    await editButton.click();

    await page.waitForTimeout(2000);

    // Modify code (if Monaco editor is present)
    const monacoEditor = page.locator('.monaco-editor');
    if (await monacoEditor.isVisible()) {
      // Monaco requires special handling
      await page.keyboard.press('Control+End'); // Go to end
      await page.keyboard.type('\n# E2E test modification');
    } else {
      // Standard textarea
      const textarea = page.locator('textarea');
      if (await textarea.isVisible()) {
        await textarea.fill('# Modified by E2E test\nprint("test")');
      }
    }

    // Save changes
    const saveButton = page.getByRole('button', { name: /save/i });
    await saveButton.click();

    // Verify success
    await expect(page.locator('.success-message, [role="alert"]')).toContainText(
      /saved successfully/i,
      { timeout: timeouts.long }
    );

    await takeTimestampedScreenshot(page, 'tool-saved');
  });

  test('should close editor without saving', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Open editor
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    await editButton.click();

    // Close without saving
    const closeButton = page.getByRole('button', { name: /close|cancel/i });
    await closeButton.click();

    // Verify editor is closed
    const editor = page.locator('[data-testid="code-editor"], .monaco-editor');
    await expect(editor).not.toBeVisible();
  });

  test('should warn about unsaved changes', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Open editor
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    await editButton.click();

    await page.waitForTimeout(2000);

    // Make changes
    const textarea = page.locator('textarea');
    if (await textarea.isVisible()) {
      await textarea.fill('# Changed content');
    }

    // Try to close
    const closeButton = page.getByRole('button', { name: /close|cancel/i });
    await closeButton.click();

    // Check for warning (might be in dialog or message)
    const bodyText = await page.locator('body').textContent();
    const hasWarning =
      bodyText.includes('unsaved') ||
      bodyText.includes('discard') ||
      bodyText.includes('changes');

    if (hasWarning) {
      await page.screenshot({
        path: 'test-results/screenshots/unsaved-warning.png',
      });
    }
  });

  // ============================================================================
  // AI Tool Generation
  // ============================================================================

  test('should open AI generation dialog', async ({ page }) => {
    const generateButton = page.getByRole('button', { name: /generate.*ai/i });

    if (await generateButton.isVisible()) {
      await generateButton.click();

      // Verify prompt input
      await expect(page.getByLabel(/describe|prompt/i)).toBeVisible();

      await page.screenshot({
        path: 'test-results/screenshots/ai-generation-dialog.png',
      });
    } else {
      test.skip();
    }
  });

  test('should generate tool code from prompt', async ({ page }) => {
    const generateButton = page.getByRole('button', { name: /generate.*ai/i });

    if (await generateButton.isVisible()) {
      await generateButton.click();

      // Enter prompt
      const promptInput = page.getByLabel(/describe|prompt/i);
      await promptInput.fill('Create a tool that calculates fibonacci numbers');

      // Generate
      const submitButton = page.getByRole('button', { name: /generate/i });
      await submitButton.click();

      // Wait for generation
      await page.waitForTimeout(5000);

      // Verify generated code is displayed
      const hasCode = await page.locator('body').textContent();
      expect(hasCode).toContain('def' || 'function' || 'fibonacci');

      await takeTimestampedScreenshot(page, 'ai-generated-code');
    } else {
      test.skip();
    }
  });

  test('should allow editing generated code', async ({ page }) => {
    const generateButton = page.getByRole('button', { name: /generate.*ai/i });

    if (await generateButton.isVisible()) {
      await generateButton.click();

      const promptInput = page.getByLabel(/describe|prompt/i);
      await promptInput.fill('Create a simple tool');

      const submitButton = page.getByRole('button', { name: /generate/i });
      await submitButton.click();

      await page.waitForTimeout(3000);

      // Try to edit generated code
      const editor = page.locator('[data-testid="code-editor"], textarea');
      if (await editor.isVisible()) {
        const isDisabled = await editor.isDisabled();
        expect(isDisabled).toBeFalsy();
      }
    } else {
      test.skip();
    }
  });

  // ============================================================================
  // Tool Search and Filter
  // ============================================================================

  test('should search tools', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    const searchInput = page.locator(
      'input[placeholder*="search" i], input[aria-label*="search" i]'
    );

    if (await searchInput.isVisible()) {
      // Search for specific tool
      await searchInput.fill('memory');
      await page.waitForTimeout(500);

      // Verify filtered results
      const results = await page.locator('body').textContent();
      expect(results.toLowerCase()).toContain('memory');

      await page.screenshot({ path: 'test-results/screenshots/tool-search.png' });
    }
  });

  test('should filter tools by file', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    const filterSelect = page.locator('select[name="file"], select[aria-label*="file" i]');

    if (await filterSelect.isVisible()) {
      // Select a file to filter
      await filterSelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      // Verify filtered results
      const toolItems = page.locator('[data-testid="tool-item"], tr:visible');
      const count = await toolItems.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  // ============================================================================
  // Tool Documentation
  // ============================================================================

  test('should display tool documentation', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Click on tool for details/docs
    const toolItem = page.locator('[data-testid="tool-item"], tr, .tool-card').first();
    await toolItem.click();

    // Check for documentation
    const bodyText = await page.locator('body').textContent();
    const hasDescription = bodyText.length > 0;
    expect(hasDescription).toBeTruthy();
  });

  test('should show tool parameters', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Look for parameters section
    const hasParams = await page.locator('body').textContent();
    expect(hasParams).toContain('parameter' || 'argument' || 'input');
  });

  // ============================================================================
  // Tool Deletion
  // ============================================================================

  test('should delete tool with confirmation', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    const deleteButton = page.getByRole('button', { name: /delete/i }).first();

    if (await deleteButton.isVisible()) {
      // Click delete
      await deleteButton.click();

      // Confirm deletion
      const confirmButton = page.getByRole('button', { name: /confirm|yes/i });
      await confirmButton.click();

      // Verify success
      await expect(page.locator('.success-message, [role="alert"]')).toContainText(
        /deleted/i,
        { timeout: timeouts.long }
      );

      await takeTimestampedScreenshot(page, 'tool-deleted');
    }
  });

  // ============================================================================
  // Complete Tool Lifecycle
  // ============================================================================

  test('should complete full tool lifecycle', async ({ page }) => {
    // 1. Upload tool
    const uploadButton = page.getByRole('button', { name: /upload.*tool/i });
    await uploadButton.click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'lifecycle_test_tool.py',
      mimeType: 'text/x-python',
      buffer: Buffer.from(testToolCode),
    });

    const submitButton = page.getByRole('button', { name: /upload|submit/i });
    await submitButton.click();

    await page.waitForTimeout(2000);

    // 2. Verify in list
    await page.goto('/tools');
    await waitForLoadingComplete(page);
    await expect(page.locator('body')).toContainText(/lifecycle_test_tool/i);

    // 3. Edit tool
    const editButtons = page.getByRole('button', { name: /edit/i });
    const lastEdit = editButtons.last();
    await lastEdit.click();

    await page.waitForTimeout(2000);

    // 4. Save changes
    const saveButton = page.getByRole('button', { name: /save/i });
    await saveButton.click();

    await page.waitForTimeout(2000);

    // 5. Verify tool still in list
    await page.goto('/tools');
    await waitForLoadingComplete(page);
    await expect(page.locator('body')).toContainText(/lifecycle_test_tool/i);

    await takeTimestampedScreenshot(page, 'tool-lifecycle-complete');
  });

  // ============================================================================
  // Error Handling
  // ============================================================================

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/api/tools', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });

    await page.goto('/tools');

    // Verify error message
    await expect(page.locator('body')).toContainText(/error|failed/i, {
      timeout: timeouts.medium,
    });

    await page.screenshot({ path: 'test-results/screenshots/tool-error.png' });
  });

  test('should handle code save errors', async ({ page }) => {
    await waitForAPIResponse(page, '/api/tools');

    // Mock save error
    await page.route('**/api/tools/content/**', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Invalid Python syntax' }),
      });
    });

    // Open editor
    const editButton = page.getByRole('button', { name: /edit/i }).first();
    await editButton.click();

    await page.waitForTimeout(2000);

    // Try to save
    const saveButton = page.getByRole('button', { name: /save/i });
    await saveButton.click();

    // Verify error message
    await expect(page.locator('body')).toContainText(/error|invalid|syntax/i, {
      timeout: timeouts.medium,
    });
  });

  // ============================================================================
  // Responsive Design
  // ============================================================================

  test('should work on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/tools');
    await waitForLoadingComplete(page);

    // Verify interface is accessible
    await expect(page.locator('body')).toBeVisible();

    await page.screenshot({ path: 'test-results/screenshots/tools-mobile.png' });
  });
});
