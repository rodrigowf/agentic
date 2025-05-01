import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api', // Add fallback
});

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000'; // Add fallback

export const getTools    = () => API.get('/tools');
export const uploadTool  = (file) => {
  const fd = new FormData(); fd.append('file', file);
  return API.post('/tools/upload', fd);
};
export const getAgents   = () => API.get('/agents');
export const createAgent = (agent) => API.post('/agents', agent);
export const updateAgent = (name, agent) => API.put(`/agents/${name}`, agent);
// Correct WebSocket URL construction
export const runAgent    = (name) => new WebSocket(`${WS_URL}/api/runs/${name}`);

// Export API instance and individual functions
export default { API, getTools, uploadTool, getAgents, createAgent, updateAgent, runAgent };