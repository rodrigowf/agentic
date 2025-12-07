import axios from 'axios';
import { getHttpBase, getWsUrl } from './utils/urlBuilder';

// Create Axios instance with centralized URL builder
const API = axios.create({
  baseURL: `${getHttpBase()}/api`,
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
export const getAgent = (name) => API.get(`/agents/${name}`);
export const createAgent = (agent) => API.post('/agents', agent);
export const updateAgent = (name, agent) => API.put(`/agents/${name}`, agent);

// Runs
export const runAgent = (name) => {
  const wsUrl = getWsUrl(`/runs/${name}`);
  console.log("Connecting WebSocket to:", wsUrl);
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
export const cleanupInactiveConversations = (inactiveMinutes = 30) => API.post(`${VOICE_BASE}/conversations/cleanup?inactive_minutes=${inactiveMinutes}`);
export const appendVoiceConversationEvent = (conversationId, payload) => API.post(`${VOICE_BASE}/conversations/${conversationId}/events`, payload);
export const getVoiceConversationEvents = (conversationId, params = {}) => API.get(`${VOICE_BASE}/conversations/${conversationId}/events`, { params });
export const connectVoiceConversationStream = (conversationId, params = {}) => {
  const searchParams = new URLSearchParams(params);
  const query = searchParams.toString();
  const wsUrl = getWsUrl(`${VOICE_BASE}/conversations/${conversationId}/stream${query ? `?${query}` : ''}`);
  return new WebSocket(wsUrl);
};
export const startVoiceWebRTCBridge = (payload) => API.post(`${VOICE_BASE}/webrtc/bridge`, payload);
export const stopVoiceWebRTCBridge = (conversationId) => API.delete(`${VOICE_BASE}/webrtc/bridge/${conversationId}`);
export const disconnectVoiceWebRTC = (connectionId) => API.post(`${VOICE_BASE}/webrtc/disconnect`, { connection_id: connectionId });
export const sendVoiceWebRTCText = (conversationId, payload) => API.post(`${VOICE_BASE}/webrtc/bridge/${conversationId}/text`, payload);

// Voice configurations
export const listVoiceConfigs = () => API.get('/voice-configs');
export const getVoiceConfig = (configName) => API.get(`/voice-configs/${configName}`);
export const createVoiceConfig = (config) => API.post('/voice-configs', config);
export const updateVoiceConfig = (configName, config) => API.put(`/voice-configs/${configName}`, config);
export const deleteVoiceConfig = (configName) => API.delete(`/voice-configs/${configName}`);

// Voice prompts
export const listVoicePrompts = () => API.get('/voice-prompts');
export const getVoicePrompt = (filename) => API.get(`/voice-prompts/${filename}`, {
  transformResponse: [(data) => data] // Get raw text
});
export const saveVoicePrompt = (filename, content) => API.post(`/voice-prompts/${filename}`, content, {
  headers: { 'Content-Type': 'text/plain' }
});
export const deleteVoicePrompt = (filename) => API.delete(`/voice-prompts/${filename}`);

// Server management
export const refreshService = () => API.post('/server/refresh');
export const pushChanges = () => API.post('/server/push');

// Export API instance and individual functions
export default {
  API,
  getTools,
  getToolContent,
  saveToolContent,
  uploadTool,
  generateToolCode,
  getAgents,
  getAgent,
  createAgent,
  updateAgent,
  runAgent,
  getModelsByProvider,
  createVoiceConversation,
  listVoiceConversations,
  getVoiceConversation,
  updateVoiceConversation,
  deleteVoiceConversation,
  cleanupInactiveConversations,
  appendVoiceConversationEvent,
  getVoiceConversationEvents,
  connectVoiceConversationStream,
  startVoiceWebRTCBridge,
  stopVoiceWebRTCBridge,
  disconnectVoiceWebRTC,
  sendVoiceWebRTCText,
  listVoiceConfigs,
  getVoiceConfig,
  createVoiceConfig,
  updateVoiceConfig,
  deleteVoiceConfig,
  listVoicePrompts,
  getVoicePrompt,
  saveVoicePrompt,
  deleteVoicePrompt,
  refreshService,
  pushChanges,
};
