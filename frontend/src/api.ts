import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  AgentConfig,
  AgentSummary,
  ToolFile,
  VoiceConversation,
  VoiceEvent,
} from './types';

// Create axios instance with default config
const API: AxiosInstance = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  withCredentials: true,
});

const VOICE_BASE = '/realtime';

// ============================================================================
// Tools API
// ============================================================================

export const getTools = (): Promise<AxiosResponse<{ tools: ToolFile[] }>> => {
  return API.get('/tools');
};

export const getToolContent = (filename: string): Promise<AxiosResponse<string>> => {
  return API.get(`/tools/content/${filename}`, {
    transformResponse: [(data) => data], // Prevent axios from parsing JSON
  });
};

export const saveToolContent = (
  filename: string,
  content: string
): Promise<AxiosResponse<{ message: string }>> => {
  return API.put(`/tools/content/${filename}`, content, {
    headers: { 'Content-Type': 'text/plain' },
  });
};

export const uploadTool = (file: File): Promise<AxiosResponse<{ message: string }>> => {
  const fd = new FormData();
  fd.append('file', file);
  return API.post('/tools/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const generateToolCode = (prompt: string): Promise<AxiosResponse<string>> => {
  return API.post(
    '/tools/generate',
    { prompt },
    {
      transformResponse: [(data) => data], // Prevent axios from parsing JSON
    }
  );
};

// ============================================================================
// Agents API
// ============================================================================

export const getAgents = (): Promise<AxiosResponse<{ agents: AgentSummary[] }>> => {
  return API.get('/agents');
};

export const getAgent = (name: string): Promise<AxiosResponse<AgentConfig>> => {
  return API.get(`/agents/${name}`);
};

export const createAgent = (
  agent: AgentConfig
): Promise<AxiosResponse<{ message: string }>> => {
  return API.post('/agents', agent);
};

export const updateAgent = (
  name: string,
  agent: AgentConfig
): Promise<AxiosResponse<{ message: string }>> => {
  return API.put(`/agents/${name}`, agent);
};

export const deleteAgent = (name: string): Promise<AxiosResponse<{ message: string }>> => {
  return API.delete(`/agents/${name}`);
};

// ============================================================================
// Runs API (WebSocket)
// ============================================================================

export const runAgent = (name: string): WebSocket => {
  // Construct WebSocket URL based on the API base URL
  const httpBase = API.defaults.baseURL!.replace('/api', '');
  const wsBase = httpBase.replace(/^http/, 'ws');
  const wsUrl = `${wsBase}/api/runs/${name}`;

  console.log('Connecting WebSocket to:', wsUrl);
  return new WebSocket(wsUrl);
};

// ============================================================================
// Models API
// ============================================================================

export const getModelsByProvider = (
  provider: string
): Promise<AxiosResponse<{ models: string[] }>> => {
  return API.get(`/models/${provider}`);
};

// ============================================================================
// Voice Conversations API
// ============================================================================

export interface CreateConversationPayload {
  name?: string;
  voice_model?: string;
  metadata?: Record<string, unknown>;
}

export interface UpdateConversationPayload {
  name?: string;
  metadata?: Record<string, unknown>;
}

export interface AppendEventPayload {
  source: string;
  type: string;
  data: Record<string, unknown>;
}

export interface GetEventsParams {
  limit?: number;
  offset?: number;
  source?: string;
  type?: string;
}

export const createVoiceConversation = (
  payload: CreateConversationPayload
): Promise<AxiosResponse<VoiceConversation>> => {
  return API.post(`${VOICE_BASE}/conversations`, payload);
};

export const listVoiceConversations = (): Promise<
  AxiosResponse<{ conversations: VoiceConversation[] }>
> => {
  return API.get(`${VOICE_BASE}/conversations`);
};

export const getVoiceConversation = (
  conversationId: string,
  params: Record<string, unknown> = {}
): Promise<AxiosResponse<VoiceConversation>> => {
  return API.get(`${VOICE_BASE}/conversations/${conversationId}`, { params });
};

export const updateVoiceConversation = (
  conversationId: string,
  payload: UpdateConversationPayload
): Promise<AxiosResponse<VoiceConversation>> => {
  return API.put(`${VOICE_BASE}/conversations/${conversationId}`, payload);
};

export const deleteVoiceConversation = (
  conversationId: string
): Promise<AxiosResponse<{ message: string }>> => {
  return API.delete(`${VOICE_BASE}/conversations/${conversationId}`);
};

export const appendVoiceConversationEvent = (
  conversationId: string,
  payload: AppendEventPayload
): Promise<AxiosResponse<VoiceEvent>> => {
  return API.post(`${VOICE_BASE}/conversations/${conversationId}/events`, payload);
};

export const getVoiceConversationEvents = (
  conversationId: string,
  params: GetEventsParams = {}
): Promise<AxiosResponse<{ events: VoiceEvent[] }>> => {
  return API.get(`${VOICE_BASE}/conversations/${conversationId}/events`, { params });
};

export const connectVoiceConversationStream = (
  conversationId: string,
  params: Record<string, unknown> = {}
): WebSocket => {
  const httpBase = API.defaults.baseURL!.replace('/api', '');
  const wsBase = httpBase.replace(/^http/, 'ws');
  const searchParams = new URLSearchParams(params as Record<string, string>);
  const query = searchParams.toString();
  const url = `${wsBase}/api${VOICE_BASE}/conversations/${conversationId}/stream${
    query ? `?${query}` : ''
  }`;
  return new WebSocket(url);
};

// ============================================================================
// Default Export for Backward Compatibility
// ============================================================================

const api = {
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
  deleteAgent,
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

export default api;
