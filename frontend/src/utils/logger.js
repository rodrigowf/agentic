/**
 * Frontend Logger Utility
 *
 * Sends all console logs to backend for debugging in real-time.
 * Also keeps original console behavior.
 *
 * SAFE VERSION: Prevents infinite loops and console recursion
 */

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// Prevent infinite loops: track if we're currently sending a log
let isSending = false;

// Queue logs during send to prevent recursion
const logQueue = [];

// Store original console methods (before any interception)
const originalConsole = {
  log: console.log.bind(console),
  warn: console.warn.bind(console),
  error: console.error.bind(console),
  info: console.info.bind(console),
};

/**
 * Send log to backend (SAFE VERSION - no console calls inside)
 */
const sendToBackend = (level, message, data = null) => {
  // Prevent recursion
  if (isSending) {
    return;
  }

  try {
    isSending = true;

    // Use fetch without any console logging
    const payload = {
      level,
      message: String(message),
      data,
      timestamp: new Date().toISOString(),
      url: window.location.href
    };

    // Fire and forget - no then/catch that could trigger console
    fetch(`${BACKEND_URL}/api/frontend-logs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(() => {
      // Success - do nothing (no console)
    }).catch(() => {
      // Error - do nothing (no console)
    }).finally(() => {
      isSending = false;
    });
  } catch (e) {
    // Ignore errors silently (no console)
    isSending = false;
  }
};

/**
 * Logger class with backend forwarding (SAFE VERSION)
 */
class Logger {
  constructor(context = 'App') {
    this.context = context;
  }

  log(...args) {
    // Use original console to prevent recursion
    originalConsole.log(`[${this.context}]`, ...args);
    sendToBackend('log', `[${this.context}] ${args[0]}`, args.slice(1));
  }

  info(...args) {
    originalConsole.info(`[${this.context}]`, ...args);
    sendToBackend('log', `[${this.context}] ${args[0]}`, args.slice(1));
  }

  warn(...args) {
    originalConsole.warn(`[${this.context}]`, ...args);
    sendToBackend('warn', `[${this.context}] ${args[0]}`, args.slice(1));
  }

  error(...args) {
    originalConsole.error(`[${this.context}]`, ...args);
    sendToBackend('error', `[${this.context}] ${args[0]}`, args.slice(1));
  }

  debug(...args) {
    originalConsole.debug(`[${this.context}]`, ...args);
    // Don't send debug to backend to reduce noise
  }
}

/**
 * Create a logger for a specific component/page
 * @param {string} context - Name of component/page (e.g., 'VoiceAssistant', 'AgentDashboard')
 * @returns {Logger}
 */
export const createLogger = (context) => {
  return new Logger(context);
};

/**
 * Default logger for general use
 */
export const logger = new Logger('Frontend');

/**
 * Override window.console to capture all logs (SAFE VERSION)
 * Call this in index.js to capture ALL console statements automatically
 *
 * SAFETY FEATURES:
 * - Uses originalConsole to prevent recursion
 * - Has isSending flag to prevent loops
 * - Silently fails if backend unreachable
 * - No console calls within sendToBackend
 */
export const interceptConsole = () => {
  // Only intercept once
  if (console._intercepted) {
    return;
  }

  console.log = (...args) => {
    originalConsole.log(...args);
    sendToBackend('log', args[0], args.slice(1));
  };

  console.info = (...args) => {
    originalConsole.info(...args);
    sendToBackend('log', args[0], args.slice(1));
  };

  console.warn = (...args) => {
    originalConsole.warn(...args);
    sendToBackend('warn', args[0], args.slice(1));
  };

  console.error = (...args) => {
    originalConsole.error(...args);
    sendToBackend('error', args[0], args.slice(1));
  };

  // Mark as intercepted
  console._intercepted = true;
};

export default logger;
