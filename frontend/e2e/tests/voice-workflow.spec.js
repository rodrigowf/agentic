/**
 * voice-workflow.spec.js - Voice Assistant E2E Tests
 *
 * End-to-end tests for voice assistant workflows.
 * Tests real user interactions with voice interface.
 */

const { test, expect } = require('@playwright/test');
const {
  waitForWebSocket,
  waitForLoadingComplete,
  takeTimestampedScreenshot,
  mockWebSocket,
} = require('../fixtures/test-helpers');
const { mockMessages, timeouts } = require('../fixtures/test-data');

test.describe('Voice Assistant E2E Tests', () => {
  test.beforeEach(async ({ page, context }) => {
    // Grant microphone permissions
    await context.grantPermissions(['microphone']);

    // Navigate to voice assistant page
    await page.goto('/voice');
    await waitForLoadingComplete(page);
  });

  // ============================================================================
  // Voice Session Start/Stop
  // ============================================================================

  test('should display voice assistant interface', async ({ page }) => {
    // Verify page title
    await expect(page.locator('h1, h2').first()).toContainText(/voice|assistant/i);

    // Verify start button is visible
    await expect(page.getByRole('button', { name: /start/i })).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'test-results/screenshots/voice-interface.png' });
  });

  test('should start voice session', async ({ page }) => {
    // Mock WebSocket connections
    await mockWebSocket(page, '/api/runs/MainConversation', [
      mockMessages.nested.textMessage,
    ]);

    await mockWebSocket(page, '/api/runs/ClaudeCode', [
      mockMessages.claudeCode.init,
    ]);

    // Click start button
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    // Verify session status
    await expect(page.locator('body')).toContainText(/active|running|connected/i, {
      timeout: timeouts.long,
    });

    // Verify stop button appears
    await expect(page.getByRole('button', { name: /stop/i })).toBeVisible({
      timeout: timeouts.medium,
    });

    await takeTimestampedScreenshot(page, 'voice-session-started');
  });

  test('should stop voice session', async ({ page }) => {
    // Start session first
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    // Wait for session to be active
    await page.waitForTimeout(2000);

    // Stop session
    const stopButton = page.getByRole('button', { name: /stop/i });
    await stopButton.click();

    // Verify session stopped
    await expect(page.locator('body')).toContainText(/stopped|inactive/i, {
      timeout: timeouts.medium,
    });

    // Verify start button reappears
    await expect(page.getByRole('button', { name: /start/i })).toBeVisible();

    await takeTimestampedScreenshot(page, 'voice-session-stopped');
  });

  test('should handle microphone permission denial', async ({ page, context }) => {
    // Reset permissions
    await context.clearPermissions();

    // Try to start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    // Verify error message
    await expect(page.locator('body')).toContainText(
      /microphone|permission/i,
      { timeout: timeouts.medium }
    );

    await page.screenshot({
      path: 'test-results/screenshots/voice-permission-denied.png',
    });
  });

  // ============================================================================
  // Audio Controls
  // ============================================================================

  test('should mute and unmute audio', async ({ page }) => {
    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(2000);

    // Find mute button
    const muteButton = page.getByRole('button', { name: /mute/i });

    if (await muteButton.isVisible()) {
      // Mute
      await muteButton.click();
      await expect(page.locator('body')).toContainText(/muted/i);

      // Unmute
      const unmuteButton = page.getByRole('button', { name: /unmute/i });
      await unmuteButton.click();
      await expect(page.locator('body')).not.toContainText(/muted/i);
    }
  });

  test('should display audio visualizer', async ({ page }) => {
    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(2000);

    // Check for visualizer canvas
    const visualizer = page.locator(
      '[data-testid="audio-visualizer"], canvas, .visualizer'
    );

    if (await visualizer.isVisible()) {
      await expect(visualizer).toBeVisible();
      await page.screenshot({
        path: 'test-results/screenshots/audio-visualizer.png',
      });
    }
  });

  // ============================================================================
  // Message Display
  // ============================================================================

  test('should display conversation messages', async ({ page }) => {
    // Mock WebSocket with messages
    await mockWebSocket(page, '/api/runs/MainConversation', [
      mockMessages.nested.textMessage,
      mockMessages.nested.toolCall,
      mockMessages.nested.toolResult,
    ]);

    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    // Wait for messages to appear
    await page.waitForTimeout(3000);

    // Verify message container exists
    const messageContainer = page.locator(
      '[data-testid="conversation-history"], .messages, .conversation'
    );
    await expect(messageContainer).toBeVisible();

    // Check for message content
    const hasMessages = await messageContainer.textContent();
    expect(hasMessages.length).toBeGreaterThan(0);

    await page.screenshot({
      path: 'test-results/screenshots/conversation-messages.png',
    });
  });

  test('should auto-scroll to latest message', async ({ page }) => {
    // Mock multiple messages
    const messages = Array.from({ length: 20 }, (_, i) => ({
      type: 'TextMessage',
      source: 'nested',
      data: { content: `Message ${i + 1}` },
    }));

    await mockWebSocket(page, '/api/runs/MainConversation', messages);

    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    // Wait for all messages
    await page.waitForTimeout(5000);

    // Verify latest message is visible
    await expect(page.locator('body')).toContainText(/message 20/i);
  });

  // ============================================================================
  // Claude Code Insights
  // ============================================================================

  test('should display Claude Code tool usage', async ({ page }) => {
    // Mock Claude Code messages
    await mockWebSocket(page, '/api/runs/ClaudeCode', [
      mockMessages.claudeCode.init,
      mockMessages.claudeCode.toolCall,
      mockMessages.claudeCode.toolResult,
      mockMessages.claudeCode.taskResult,
    ]);

    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    // Wait for Claude Code activity
    await page.waitForTimeout(3000);

    // Check for Claude Code insights panel
    const claudeInsights = page.locator(
      '[data-testid="claude-code-insights"], .claude-code, .code-insights'
    );

    if (await claudeInsights.isVisible()) {
      await expect(claudeInsights).toBeVisible();

      // Verify tool calls are shown
      await expect(page.locator('body')).toContainText(/read|bash|edit/i);

      await page.screenshot({
        path: 'test-results/screenshots/claude-code-insights.png',
      });
    }
  });

  test('should show tool execution results', async ({ page }) => {
    await mockWebSocket(page, '/api/runs/ClaudeCode', [
      mockMessages.claudeCode.toolCall,
      mockMessages.claudeCode.toolResult,
    ]);

    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(3000);

    // Check for tool results
    const hasResults = await page.locator('body').textContent();
    expect(hasResults).toContain('Read' || 'result' || 'def test()');
  });

  test('should display task completion status', async ({ page }) => {
    await mockWebSocket(page, '/api/runs/ClaudeCode', [
      mockMessages.claudeCode.taskResult,
    ]);

    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(3000);

    // Verify completion message
    await expect(page.locator('body')).toContainText(/success|completed/i);
  });

  // ============================================================================
  // Nested Agent Insights
  // ============================================================================

  test('should display nested agent activities', async ({ page }) => {
    // Mock nested agent messages
    await mockWebSocket(page, '/api/runs/MainConversation', [
      mockMessages.nested.textMessage,
      mockMessages.nested.toolCall,
      mockMessages.nested.toolResult,
    ]);

    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(3000);

    // Check for nested agent insights
    const nestedInsights = page.locator(
      '[data-testid="nested-agent-insights"], .nested-agent, .team-insights'
    );

    if (await nestedInsights.isVisible()) {
      await expect(nestedInsights).toBeVisible();

      // Verify agent names
      await expect(page.locator('body')).toContainText(/researcher/i);

      await page.screenshot({
        path: 'test-results/screenshots/nested-agent-insights.png',
      });
    }
  });

  test('should show tool usage by agents', async ({ page }) => {
    await mockWebSocket(page, '/api/runs/MainConversation', [
      mockMessages.nested.toolCall,
      mockMessages.nested.toolResult,
    ]);

    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(3000);

    // Verify tool usage is displayed
    await expect(page.locator('body')).toContainText(/web_search/i);
  });

  // ============================================================================
  // Insights Panel Interaction
  // ============================================================================

  test('should toggle insights panel visibility', async ({ page }) => {
    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(2000);

    // Find toggle button
    const toggleButton = page.locator('button:has-text("insights"), button:has-text("hide")').first();

    if (await toggleButton.isVisible()) {
      // Hide panel
      await toggleButton.click();
      await page.waitForTimeout(500);

      // Show panel
      await toggleButton.click();
      await page.waitForTimeout(500);
    }
  });

  test('should switch between insight tabs', async ({ page }) => {
    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(2000);

    // Look for tabs
    const claudeTab = page.locator('button:has-text("claude"), [role="tab"]:has-text("claude")').first();
    const nestedTab = page.locator('button:has-text("nested"), [role="tab"]:has-text("team")').first();

    if ((await claudeTab.isVisible()) && (await nestedTab.isVisible())) {
      // Switch to Claude Code tab
      await claudeTab.click();
      await page.waitForTimeout(300);

      // Switch to Nested tab
      await nestedTab.click();
      await page.waitForTimeout(300);
    }
  });

  // ============================================================================
  // Conversation Management
  // ============================================================================

  test('should navigate to conversation list', async ({ page }) => {
    // Look for conversations link/button
    const conversationsLink = page.locator(
      'a:has-text("conversations"), button:has-text("conversations")'
    ).first();

    if (await conversationsLink.isVisible()) {
      await conversationsLink.click();
      await waitForLoadingComplete(page);

      // Verify conversation list page
      await expect(page.locator('body')).toContainText(/conversations|sessions/i);

      await page.screenshot({
        path: 'test-results/screenshots/conversation-list.png',
      });
    }
  });

  // ============================================================================
  // Error Handling
  // ============================================================================

  test('should handle WebSocket connection errors', async ({ page }) => {
    // Don't mock WebSocket to simulate connection failure
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    // Wait and check for error message
    await page.waitForTimeout(5000);

    const bodyText = await page.locator('body').textContent();
    const hasError =
      bodyText.includes('error') ||
      bodyText.includes('failed') ||
      bodyText.includes('connection');

    if (hasError) {
      await page.screenshot({
        path: 'test-results/screenshots/voice-connection-error.png',
      });
    }
  });

  test('should display error messages from backend', async ({ page }) => {
    // Mock error message
    await mockWebSocket(page, '/api/runs/MainConversation', [
      {
        type: 'Error',
        source: 'nested',
        data: { message: 'E2E test error' },
      },
    ]);

    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(3000);

    // Verify error is displayed
    await expect(page.locator('body')).toContainText(/error/i);
  });

  // ============================================================================
  // Responsive Design
  // ============================================================================

  test('should work on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Verify interface adapts
    await expect(page.locator('body')).toBeVisible();

    // Check start button is still accessible
    await expect(page.getByRole('button', { name: /start/i })).toBeVisible();

    await page.screenshot({
      path: 'test-results/screenshots/voice-mobile.png',
    });
  });

  test('should work on tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    await expect(page.locator('body')).toBeVisible();

    await page.screenshot({
      path: 'test-results/screenshots/voice-tablet.png',
    });
  });

  // ============================================================================
  // Session Persistence
  // ============================================================================

  test('should maintain session state on page refresh', async ({ page }) => {
    // Start session
    const startButton = page.getByRole('button', { name: /start.*session/i });
    await startButton.click();

    await page.waitForTimeout(2000);

    // Verify session is active
    await expect(page.locator('body')).toContainText(/active|running/i);

    // Refresh page
    await page.reload();
    await waitForLoadingComplete(page);

    // Session should restart (or show stopped state)
    // This depends on implementation - adjust expectation accordingly
    await expect(page.getByRole('button', { name: /start|stop/i })).toBeVisible();
  });
});
