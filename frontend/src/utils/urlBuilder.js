/**
 * Centralized URL builder for all frontend-backend communication
 *
 * Handles three scenarios:
 * 1. Local HTTP: http://localhost:3000 -> backend at localhost:8000
 * 2. Remote HTTP: http://192.168.0.25:3000 -> backend at 192.168.0.25:8000
 * 3. HTTPS via nginx: https://192.168.0.25 -> backend proxied through nginx
 */

/**
 * Detect the current environment and return base URLs
 * @returns {Object} Environment configuration
 */
function detectEnvironment() {
  const protocol = window.location.protocol; // 'http:' or 'https:'
  const hostname = window.location.hostname; // 'localhost' or IP address
  const port = window.location.port; // '3000', '443', or ''

  // Check for environment variable override
  if (process.env.REACT_APP_BACKEND_URL) {
    const backendUrl = process.env.REACT_APP_BACKEND_URL;
    try {
      const url = new URL(backendUrl);
      const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      return {
        type: 'env-override',
        httpBase: `${url.protocol}//${url.host}`,
        wsBase: `${wsProtocol}//${url.host}`,
        apiPath: '/api'
      };
    } catch (e) {
      console.warn('Invalid REACT_APP_BACKEND_URL, falling back to auto-detection');
    }
  }

  // Scenario 3: HTTPS via nginx (production-like)
  // When accessing via https://, we're behind nginx which proxies to backend
  if (protocol === 'https:') {
    const host = window.location.host; // includes port if non-standard
    return {
      type: 'nginx-https',
      httpBase: `https://${host}`,
      wsBase: `wss://${host}`,
      apiPath: '/api'
    };
  }

  // Check if we're accessing through nginx on HTTP (port 80 or no port in production build)
  // Development uses port 3000, production build served by nginx uses port 80 or no port
  const isNginxHttp = port === '80' || port === '' || !port;

  if (isNginxHttp) {
    // HTTP via nginx - backend is proxied
    const host = window.location.host;
    return {
      type: 'nginx-http',
      httpBase: `http://${host}`,
      wsBase: `ws://${host}`,
      apiPath: '/api'
    };
  }

  // Scenarios 1 & 2: HTTP direct to backend (development on port 3000)
  // Frontend on port 3000, backend on port 8000
  return {
    type: 'direct-http',
    httpBase: `http://${hostname}:8000`,
    wsBase: `ws://${hostname}:8000`,
    apiPath: '/api'
  };
}

/**
 * Get the full HTTP/HTTPS URL for a REST API endpoint
 * @param {string} path - API path (e.g., '/agents' or '/realtime/conversations')
 * @returns {string} Full URL
 */
export function getApiUrl(path) {
  const env = detectEnvironment();
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${env.httpBase}${env.apiPath}${normalizedPath}`;
}

/**
 * Get the base URL for HTTP/HTTPS requests (without /api)
 * Used for special endpoints like /api/realtime/token/openai
 * @returns {string} Base URL
 */
export function getHttpBase() {
  const env = detectEnvironment();
  return env.httpBase;
}

/**
 * Get the full WebSocket URL for a WS/WSS endpoint
 * @param {string} path - WebSocket path (e.g., '/runs/MainConversation')
 * @returns {string} Full WebSocket URL
 */
export function getWsUrl(path) {
  const env = detectEnvironment();
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${env.wsBase}${env.apiPath}${normalizedPath}`;
}

/**
 * Get environment info for debugging
 * @returns {Object} Environment details
 */
export function getEnvironmentInfo() {
  const env = detectEnvironment();
  return {
    ...env,
    currentUrl: window.location.href,
    protocol: window.location.protocol,
    hostname: window.location.hostname,
    port: window.location.port,
    host: window.location.host
  };
}

/**
 * Get the full HTTP/HTTPS URL for an API endpoint (alias for getApiUrl)
 * @param {string} path - API path
 * @returns {string} Full URL
 */
export function getFullApiUrl(path) {
  return getApiUrl(path);
}

// Default export for convenience
export default {
  getApiUrl,
  getWsUrl,
  getHttpBase,
  getEnvironmentInfo,
  getFullApiUrl
};
