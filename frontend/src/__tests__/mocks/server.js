/**
 * server.js - Mock Service Worker Server Setup
 *
 * Configures the MSW server for Node.js environment (Jest tests)
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Create MSW server with default handlers
export const server = setupServer(...handlers);
