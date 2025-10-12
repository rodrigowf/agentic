/**
 * global-teardown.js - Playwright Global Teardown
 *
 * Runs once after all tests.
 * Use this for:
 * - Stopping external services
 * - Cleaning up test databases
 * - Generating final reports
 */

module.exports = async (config) => {
  console.log('🧹 Starting global E2E test teardown...');

  // Clean up test artifacts if needed
  // Example: Delete temporary files, reset databases, etc.

  console.log('✅ Global E2E test teardown complete');
};
