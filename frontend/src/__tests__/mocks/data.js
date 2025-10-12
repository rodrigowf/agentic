/**
 * data.js - Mock Data for Tests
 *
 * Provides mock data fixtures for use in unit tests.
 * This file contains sample agents, tools, conversations, and other test data.
 */

// ============================================================================
// Mock Agents
// ============================================================================

export const mockAgents = [
  {
    name: 'MainConversation',
    agent_type: 'nested_team',
    description: 'Main conversation coordinator',
    sub_agents: ['Manager', 'Researcher', 'Developer'],
    mode: 'selector',
    llm: {
      provider: 'openai',
      model: 'gpt-4-turbo-2024-04-09',
      temperature: 0.0,
      max_tokens: null,
    },
  },
  {
    name: 'Researcher',
    agent_type: 'looping',
    description: 'Research agent with web search capabilities',
    tools: ['web_search', 'fetch_web_content'],
    llm: {
      provider: 'openai',
      model: 'gpt-4-turbo-2024-04-09',
      temperature: 0.0,
      max_tokens: null,
    },
    prompt: {
      system: 'You are a research assistant. Use tools to gather information.',
      user: 'Research the given topic.',
    },
    tool_call_loop: true,
    reflect_on_tool_use: true,
    max_consecutive_auto_reply: 20,
  },
  {
    name: 'Developer',
    agent_type: 'looping_code_executor',
    description: 'Code executor agent',
    tools: ['python_executor'],
    llm: {
      provider: 'openai',
      model: 'gpt-4-turbo-2024-04-09',
      temperature: 0.0,
      max_tokens: null,
    },
    code_executor: {
      type: 'local',
      work_dir: '/tmp/code',
    },
    system_message: 'You are a code execution agent.',
  },
  {
    name: 'MultimodalVisionAgent',
    agent_type: 'multimodal_tools_looping',
    description: 'Vision agent with screenshot capabilities',
    tools: ['take_screenshot', 'generate_test_image'],
    llm: {
      provider: 'openai',
      model: 'gpt-4o',
      temperature: 0.0,
      max_tokens: null,
    },
    prompt: {
      system: 'You are a vision assistant that can see and analyze images.',
      user: 'Analyze images and describe what you see.',
    },
    tool_call_loop: true,
    reflect_on_tool_use: true,
  },
];

// ============================================================================
// Mock Agent Configuration (Full Detail)
// ============================================================================

export const mockAgentConfig = {
  name: 'Researcher',
  agent_type: 'looping',
  description: 'Research agent with web search capabilities',
  tools: ['web_search', 'fetch_web_content'],
  llm: {
    provider: 'openai',
    model: 'gpt-4-turbo-2024-04-09',
    temperature: 0.0,
    max_tokens: null,
  },
  prompt: {
    system: 'You are a research assistant. Use tools to gather information.',
    user: 'Research the given topic.',
  },
  code_executor: null,
  model_client_stream: false,
  sources: null,
  system_message: null,
  max_consecutive_auto_reply: 20,
  reflect_on_tool_use: true,
  terminate_on_text: false,
  tool_call_loop: true,
  sub_agents: null,
  mode: null,
  orchestrator_prompt: null,
  include_inner_dialog: true,
};

// ============================================================================
// Mock Tools
// ============================================================================

export const mockTools = [
  {
    name: 'web_search',
    description: 'Search the web for information',
    file: 'research.py',
  },
  {
    name: 'fetch_web_content',
    description: 'Fetch content from a URL',
    file: 'research.py',
  },
  {
    name: 'save_to_short_term_memory',
    description: 'Save information to short-term memory',
    file: 'memory.py',
  },
  {
    name: 'take_screenshot',
    description: 'Take a screenshot of the screen',
    file: 'image_tools.py',
  },
  {
    name: 'python_executor',
    description: 'Execute Python code',
    file: 'code_executor.py',
  },
];

// ============================================================================
// Mock Voice Conversations
// ============================================================================

export const mockConversations = [
  {
    id: 'conv-123',
    name: 'Session 2025-01-15',
    created_at: '2025-01-15T10:30:00Z',
    updated_at: '2025-01-15T11:45:00Z',
    voice_model: 'gpt-4o-realtime-preview',
    metadata: {},
  },
  {
    id: 'conv-456',
    name: 'Session 2025-01-16',
    created_at: '2025-01-16T14:00:00Z',
    updated_at: '2025-01-16T15:30:00Z',
    voice_model: 'gpt-4o-realtime-preview',
    metadata: {},
  },
];

// ============================================================================
// Mock Voice Messages/Events
// ============================================================================

export const mockVoiceMessages = [
  {
    id: 1,
    timestamp: '2025-01-15T10:30:05Z',
    source: 'voice',
    type: 'session.created',
    data: {
      session: {
        id: 'session_123',
        model: 'gpt-4o-realtime-preview',
      },
    },
  },
  {
    id: 2,
    timestamp: '2025-01-15T10:30:10Z',
    source: 'voice',
    type: 'conversation.item.created',
    data: {
      item: {
        id: 'item_123',
        type: 'message',
        role: 'user',
        content: [{ type: 'input_text', text: 'Hello Archie' }],
      },
    },
  },
  {
    id: 3,
    timestamp: '2025-01-15T10:30:15Z',
    source: 'voice',
    type: 'response.audio_transcript.delta',
    data: {
      delta: 'Hello! How can I assist you today?',
    },
  },
];

// ============================================================================
// Mock Claude Code Messages
// ============================================================================

export const mockClaudeCodeMessages = [
  {
    id: 1,
    timestamp: '2025-01-15T10:32:00Z',
    source: 'claude_code',
    type: 'SystemEvent',
    data: {
      type: 'SystemEvent',
      data: {
        message: 'init',
        details: {
          cwd: '/home/rodrigo/agentic',
          model: 'claude-sonnet-4-5-20250929',
          tools: ['Bash', 'Read', 'Edit', 'Write'],
        },
      },
    },
  },
  {
    id: 2,
    timestamp: '2025-01-15T10:32:05Z',
    source: 'claude_code',
    type: 'TextMessage',
    data: {
      type: 'TextMessage',
      data: {
        content: 'I will help you modify the code...',
      },
    },
  },
  {
    id: 3,
    timestamp: '2025-01-15T10:32:10Z',
    source: 'claude_code',
    type: 'ToolCallRequestEvent',
    data: {
      type: 'ToolCallRequestEvent',
      data: {
        name: 'Read',
        arguments: {
          file_path: '/home/rodrigo/agentic/backend/main.py',
        },
        id: 'toolu_123',
      },
    },
  },
  {
    id: 4,
    timestamp: '2025-01-15T10:32:15Z',
    source: 'claude_code',
    type: 'ToolCallExecutionEvent',
    data: {
      type: 'ToolCallExecutionEvent',
      data: {
        name: 'Read',
        result: 'import fastapi\nfrom fastapi import FastAPI\n\napp = FastAPI()',
        is_error: false,
        id: 'toolu_123',
      },
    },
  },
  {
    id: 5,
    timestamp: '2025-01-15T10:32:20Z',
    source: 'claude_code',
    type: 'TaskResult',
    data: {
      type: 'TaskResult',
      data: {
        outcome: 'success',
        message: 'Code changes completed',
        duration_ms: 5420,
      },
    },
  },
];

// ============================================================================
// Mock Nested Agent Messages
// ============================================================================

export const mockNestedAgentMessages = [
  {
    id: 1,
    timestamp: '2025-01-15T10:31:00Z',
    source: 'nested',
    type: 'AgentInitEvent',
    data: {
      agent_name: 'MainConversation',
      sub_agents: ['Manager', 'Researcher', 'Developer'],
    },
  },
  {
    id: 2,
    timestamp: '2025-01-15T10:31:05Z',
    source: 'nested',
    type: 'TextMessage',
    data: {
      content: 'Manager: I will coordinate the research task...',
      source: 'Manager',
    },
  },
  {
    id: 3,
    timestamp: '2025-01-15T10:31:10Z',
    source: 'nested',
    type: 'TextMessage',
    data: {
      content: 'Researcher: Starting web search...',
      source: 'Researcher',
    },
  },
  {
    id: 4,
    timestamp: '2025-01-15T10:31:15Z',
    source: 'nested',
    type: 'ToolCallRequestEvent',
    data: {
      name: 'web_search',
      arguments: { query: 'machine learning trends 2025' },
      id: 'tool_call_nested_1',
      agent: 'Researcher',
    },
  },
  {
    id: 5,
    timestamp: '2025-01-15T10:31:20Z',
    source: 'nested',
    type: 'ToolCallExecutionEvent',
    data: {
      name: 'web_search',
      result: 'Found 10 results about ML trends...',
      is_error: false,
      id: 'tool_call_nested_1',
    },
  },
];

// ============================================================================
// Mock Models by Provider
// ============================================================================

export const mockModelsByProvider = {
  openai: [
    'gpt-4-turbo-2024-04-09',
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-4-turbo',
    'gpt-3.5-turbo',
  ],
  anthropic: [
    'claude-sonnet-4-5-20250929',
    'claude-3-5-sonnet-20240620',
    'claude-3-opus-20240229',
    'claude-3-haiku-20240307',
  ],
  gemini: [
    'gemini-1.5-pro',
    'gemini-1.5-flash',
    'gemini-pro',
  ],
};

// ============================================================================
// Mock Tool Code
// ============================================================================

export const mockToolCode = `from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query")
    max_results: Optional[int] = Field(5, description="Maximum results to return")

def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for information.

    Args:
        query: The search query
        max_results: Maximum number of results

    Returns:
        String with search results
    """
    try:
        # Search logic here
        results = perform_search(query, max_results)
        return f"Found {len(results)} results"
    except Exception as e:
        logger.error(f"Error in web_search: {e}")
        return f"Error: {str(e)}"

web_search_tool = FunctionTool(
    func=web_search,
    name="web_search",
    description="Search the web for information"
)

tools = [web_search_tool]
`;

// ============================================================================
// Export All Mocks
// ============================================================================

export default {
  mockAgents,
  mockAgentConfig,
  mockTools,
  mockConversations,
  mockVoiceMessages,
  mockClaudeCodeMessages,
  mockNestedAgentMessages,
  mockModelsByProvider,
  mockToolCode,
};
