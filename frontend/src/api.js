import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api', // Add fallback
  withCredentials: true, // Important if backend needs cookies/session
});

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000'; // Add fallback

// Tools
export const getTools = () => API.get('/tools'); // Returns [{filename: string, definition: ToolDefinition | null}, ...]
export const getToolContent = (filename) => API.get(`/tools/${filename}`, {
  transformResponse: [(data) => data] // Prevent axios from parsing JSON
}); // Get raw file content
export const saveToolContent = (filename, content) => API.put(`/tools/${filename}`, content, {
  headers: { 'Content-Type': 'text/plain' } // Send as plain text
});
export const uploadTool = (file) => {
  const fd = new FormData(); fd.append('file', file);
  return API.post('/tools/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};
export const generateToolCode = (prompt) => API.post('/tools/generate', { prompt }, {
  transformResponse: [(data) => data] // Prevent axios from parsing JSON
});

// Agents
export const getAgents = () => API.get('/agents');
export const createAgent = (agent) => API.post('/agents', agent);
export const updateAgent = (name, agent) => API.put(`/agents/${name}`, agent);

// Runs
export const runAgent = (name) => {
  // Construct WebSocket URL based on the API base URL, replacing http with ws
  // Assumes API base URL is like 'http://localhost:8000/api'
  const httpBase = API.defaults.baseURL.replace('/api', ''); // Get 'http://localhost:8000'
  const wsBase = httpBase.replace(/^http/, 'ws'); // Replace 'http' with 'ws' -> 'ws://localhost:8000'
  const wsUrl = `${wsBase}/api/runs/${name}`; // Construct the final URL

  console.log("Connecting WebSocket to:", wsUrl); // Log the correct URL
  return new WebSocket(wsUrl);
};

// Models
export const getModelsByProvider = (provider) => API.get(`/models/${provider}`);

// Export API instance and individual functions
export default { API, getTools, getToolContent, saveToolContent, uploadTool, generateToolCode, getAgents, createAgent, updateAgent, runAgent, getModelsByProvider };