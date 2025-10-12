/**
 * types/index.ts - Comprehensive TypeScript Type Definitions
 *
 * This file contains all type definitions for the application, mirroring
 * the backend Pydantic models and API responses.
 */

// ============================================================================
// LLM Configuration
// ============================================================================

export interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'google' | 'gemini';
  model: string;
  temperature: number;
  max_tokens: number | null;
}

// ============================================================================
// Prompt Configuration
// ============================================================================

export interface PromptConfig {
  system: string;
  user: string;
}

// ============================================================================
// Code Executor Configuration
// ============================================================================

export interface CodeExecutorConfig {
  type: string;
  work_dir?: string;
  [key: string]: unknown;
}

// ============================================================================
// Agent Configuration
// ============================================================================

export type AgentType =
  | 'assistant'
  | 'looping'
  | 'code_executor'
  | 'looping_code_executor'
  | 'nested_team'
  | 'multimodal_tools_looping';

export interface AgentConfig {
  name: string;
  agent_type: AgentType;
  tools: string[];
  llm: LLMConfig;
  prompt: PromptConfig;
  code_executor: CodeExecutorConfig | null;
  model_client_stream: boolean;
  sources: string[] | null;
  description: string;
  system_message: string | null;
  max_consecutive_auto_reply: number | null;
  reflect_on_tool_use: boolean;
  terminate_on_text: boolean;
  tool_call_loop: boolean;
  sub_agents: (AgentConfig | string)[] | null;
  mode: string | null;
  orchestrator_prompt: string | null;
  include_inner_dialog: boolean;
}

// Partial agent for listings (may not include all fields)
export interface AgentSummary {
  name: string;
  agent_type: AgentType;
  description: string;
  tools?: string[];
  sub_agents?: string[];
  llm?: LLMConfig;
}

// ============================================================================
// Tool Definitions
// ============================================================================

export interface ToolDefinition {
  name: string;
  description: string;
  file: string;
  parameters?: Record<string, unknown>;
}

export interface ToolFile {
  filename: string;
  name?: string;
  description?: string;
  definition: ToolDefinition | null;
}

// ============================================================================
// WebSocket Message Types
// ============================================================================

export type MessageSource = 'voice' | 'nested' | 'claude_code' | 'controller';

export interface BaseMessage {
  id?: number | string;
  timestamp?: string;
  source?: MessageSource;
  type: string;
  data?: unknown;
  payload?: unknown;
}

// Text message
export interface TextMessage extends BaseMessage {
  type: 'TextMessage' | 'text';
  data: {
    content: string;
    source?: string;
    role?: 'user' | 'assistant' | 'system';
  };
}

// Tool call request
export interface ToolCallRequestEvent extends BaseMessage {
  type: 'ToolCallRequestEvent' | 'tool_use';
  data: {
    name: string;
    arguments: Record<string, unknown>;
    id: string;
    agent?: string;
  };
}

// Tool call execution
export interface ToolCallExecutionEvent extends BaseMessage {
  type: 'ToolCallExecutionEvent' | 'tool_result';
  data: {
    name: string;
    result: string;
    is_error: boolean;
    id: string;
  };
}

// System events
export interface SystemEvent extends BaseMessage {
  type: 'SystemEvent' | 'system';
  data: {
    message: string;
    details?: Record<string, unknown>;
  };
}

// Agent initialization
export interface AgentInitEvent extends BaseMessage {
  type: 'AgentInitEvent';
  data: {
    agent_name: string;
    sub_agents?: string[];
  };
}

// Task result
export interface TaskResult extends BaseMessage {
  type: 'TaskResult' | 'result';
  data: {
    outcome: 'success' | 'error' | 'cancelled';
    message: string;
    duration_ms?: number;
    usage?: Record<string, unknown>;
    models_usage?: Record<string, unknown>;
  };
}

// Error event
export interface ErrorEvent extends BaseMessage {
  type: 'Error' | 'error';
  data: {
    message: string;
    details?: string;
    stack?: string;
  };
}

// Run finished event
export interface RunFinishedEvent extends BaseMessage {
  type: 'RUN_FINISHED';
  data?: {
    message?: string;
  };
}

// Union type for all message types
export type AgentMessage =
  | TextMessage
  | ToolCallRequestEvent
  | ToolCallExecutionEvent
  | SystemEvent
  | AgentInitEvent
  | TaskResult
  | ErrorEvent
  | RunFinishedEvent
  | BaseMessage;

// ============================================================================
// Voice Conversation Types
// ============================================================================

export interface VoiceConversation {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  voice_model: string | null;
  metadata: Record<string, unknown>;
}

export interface VoiceEvent {
  id: number;
  conversation_id: string;
  timestamp: string;
  source: MessageSource;
  type: string;
  data: Record<string, unknown>;
  payload?: Record<string, unknown>;
}

// OpenAI Realtime API specific types
export interface RealtimeSession {
  id: string;
  model: string;
  modalities?: string[];
  instructions?: string;
  voice?: string;
  input_audio_format?: string;
  output_audio_format?: string;
  input_audio_transcription?: {
    model: string;
  };
  turn_detection?: {
    type: string;
    threshold?: number;
    prefix_padding_ms?: number;
    silence_duration_ms?: number;
  };
  tools?: Array<{
    type: string;
    name: string;
    description: string;
    parameters: Record<string, unknown>;
  }>;
  tool_choice?: string;
  temperature?: number;
  max_response_output_tokens?: number | 'inf';
}

export interface RealtimeConversationItem {
  id: string;
  object: string;
  type: 'message' | 'function_call' | 'function_call_output';
  status?: string;
  role?: 'user' | 'assistant' | 'system';
  content?: Array<{
    type: string;
    text?: string;
    audio?: string;
    transcript?: string;
  }>;
  call_id?: string;
  name?: string;
  arguments?: string;
  output?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T = unknown> {
  data?: T;
  error?: string;
  message?: string;
}

export interface AgentsListResponse {
  agents: AgentSummary[];
}

export interface ToolsListResponse {
  tools: ToolFile[];
}

export interface ModelsListResponse {
  models: string[];
}

export interface ConversationsListResponse {
  conversations: VoiceConversation[];
}

export interface EventsListResponse {
  events: VoiceEvent[];
  total?: number;
  limit?: number;
  offset?: number;
}

// ============================================================================
// Component Props Types
// ============================================================================

export interface AgentEditorProps {
  agentName?: string;
  onSave?: (agent: AgentConfig) => void;
  onCancel?: () => void;
}

export interface RunConsoleProps {
  agentName: string;
  onClose?: () => void;
}

export interface LogMessageDisplayProps {
  message: AgentMessage;
  index?: number;
}

export interface ToolEditorProps {
  toolName?: string;
  onSave?: (filename: string, content: string) => void;
  onCancel?: () => void;
}

export interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  height?: string;
  readOnly?: boolean;
}

export interface VoiceSessionControlsProps {
  isRunning: boolean;
  isMuted: boolean;
  onStart: () => void;
  onStop: () => void;
  onToggleMute: () => void;
  disabled?: boolean;
}

export interface AudioVisualizerProps {
  isActive: boolean;
  audioLevel?: number;
}

export interface ConversationHistoryProps {
  messages: AgentMessage[];
  conversationId?: string;
}

export interface NestedAgentInsightsProps {
  messages: AgentMessage[];
}

export interface ClaudeCodeInsightsProps {
  messages: AgentMessage[];
}

// ============================================================================
// Utility Types
// ============================================================================

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type Nullable<T> = T | null;

export type Optional<T> = T | undefined;

// ============================================================================
// Export All
// ============================================================================

export default {
  // Re-export for convenience
};
