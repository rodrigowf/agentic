import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api', // Add fallback
  withCredentials: true, // Important if backend needs cookies/session
});

const VOICE_BASE = '/realtime';

// Tools
export const getTools = () => API.get('/tools'); // Returns [{filename: string, definition: ToolDefinition | null}, ...]
export const getToolContent = (filename) => API.get(`/tools/content/${filename}`, {
  transformResponse: [(data) => data] // Prevent axios from parsing JSON
}); // Get raw file content
export const saveToolContent = (filename, content) => API.put(`/tools/content/${filename}`, content, {
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

// Voice conversations
export const createVoiceConversation = (payload) => API.post(`${VOICE_BASE}/conversations`, payload);
export const listVoiceConversations = () => API.get(`${VOICE_BASE}/conversations`);
export const getVoiceConversation = (conversationId, params = {}) => API.get(`${VOICE_BASE}/conversations/${conversationId}`, { params });
export const updateVoiceConversation = (conversationId, payload) => API.put(`${VOICE_BASE}/conversations/${conversationId}`, payload);
export const deleteVoiceConversation = (conversationId) => API.delete(`${VOICE_BASE}/conversations/${conversationId}`);
export const appendVoiceConversationEvent = (conversationId, payload) => API.post(`${VOICE_BASE}/conversations/${conversationId}/events`, payload);
export const getVoiceConversationEvents = (conversationId, params = {}) => API.get(`${VOICE_BASE}/conversations/${conversationId}/events`, { params });
export const connectVoiceConversationStream = (conversationId, params = {}) => {
  const httpBase = API.defaults.baseURL.replace('/api', '');
  const wsBase = httpBase.replace(/^http/, 'ws');
  const searchParams = new URLSearchParams(params);
  const query = searchParams.toString();
  const url = `${wsBase}/api${VOICE_BASE}/conversations/${conversationId}/stream${query ? `?${query}` : ''}`;
  return new WebSocket(url);
};

// Export API instance and individual functions
export default {
  API,
  getTools,
  getToolContent,
  saveToolContent,
  uploadTool,
  generateToolCode,
  getAgents,
  createAgent,
  updateAgent,
  runAgent,
  getModelsByProvider,
  createVoiceConversation,
  listVoiceConversations,
  getVoiceConversation,
  updateVoiceConversation,
  deleteVoiceConversation,
  appendVoiceConversationEvent,
  getVoiceConversationEvents,
  connectVoiceConversationStream,
};