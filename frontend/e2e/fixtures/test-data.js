/**
 * test-data.js - E2E Test Data Fixtures
 *
 * Mock data for E2E tests.
 * This data is used to seed tests and verify expected outcomes.
 */

/**
 * Test Agent Configurations
 */
const testAgents = {
  looping: {
    name: 'E2E_Looping_Agent',
    agent_type: 'looping',
    description: 'E2E test looping agent',
    tools: ['web_search'],
    llm: {
      provider: 'openai',
      model: 'gpt-4o-mini',
      temperature: 0.0,
      max_tokens: null,
    },
    prompt: {
      system: 'You are a test agent.',
      user: 'Perform test task.',
    },
    tool_call_loop: true,
    reflect_on_tool_use: true,
    max_consecutive_auto_reply: 5,
  },

  nestedTeam: {
    name: 'E2E_Team_Agent',
    agent_type: 'nested_team',
    description: 'E2E test team agent',
    sub_agents: ['Researcher', 'Developer'],
    mode: 'selector',
    llm: {
      provider: 'openai',
      model: 'gpt-4-turbo-2024-04-09',
      temperature: 0.0,
      max_tokens: null,
    },
    orchestrator_prompt: '__function__',
    include_inner_dialog: true,
  },

  multimodal: {
    name: 'E2E_Vision_Agent',
    agent_type: 'multimodal_tools_looping',
    description: 'E2E test vision agent',
    tools: ['take_screenshot'],
    llm: {
      provider: 'openai',
      model: 'gpt-4o',
      temperature: 0.0,
      max_tokens: null,
    },
    prompt: {
      system: 'You are a vision agent that can see images.',
      user: 'Analyze the image.',
    },
    tool_call_loop: true,
    reflect_on_tool_use: true,
  },
};

/**
 * Test Tool Code
 */
const testToolCode = `from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
import logging

logger = logging.getLogger(__name__)

class E2ETestToolInput(BaseModel):
    message: str = Field(..., description="Test message")

def e2e_test_tool(message: str) -> str:
    """
    E2E test tool for integration testing.

    Args:
        message: Test message to echo

    Returns:
        Echoed message
    """
    logger.info(f"E2E test tool called with: {message}")
    return f"Echo: {message}"

e2e_test_tool_func = FunctionTool(
    func=e2e_test_tool,
    name="e2e_test_tool",
    description="E2E test tool that echoes messages"
)

tools = [e2e_test_tool_func]
`;

/**
 * Test Voice Conversation Data
 */
const testConversations = {
  basic: {
    name: 'E2E Test Session',
    voice_model: 'gpt-4o-realtime-preview',
    metadata: {
      test: true,
      created_by: 'e2e-test',
    },
  },
};

/**
 * Mock WebSocket Messages
 */
const mockMessages = {
  nested: {
    textMessage: {
      type: 'TextMessage',
      source: 'nested',
      data: {
        content: 'Test message from nested agent',
        source: 'Researcher',
      },
    },
    toolCall: {
      type: 'ToolCallRequestEvent',
      source: 'nested',
      data: {
        name: 'web_search',
        arguments: { query: 'test query' },
        id: 'tool_call_test_1',
        agent: 'Researcher',
      },
    },
    toolResult: {
      type: 'ToolCallExecutionEvent',
      source: 'nested',
      data: {
        name: 'web_search',
        result: 'Test search results',
        is_error: false,
        id: 'tool_call_test_1',
      },
    },
  },

  claudeCode: {
    init: {
      type: 'SystemEvent',
      source: 'claude_code',
      data: {
        type: 'SystemEvent',
        data: {
          message: 'init',
          details: {
            cwd: '/test/path',
            model: 'claude-sonnet-4-5-20250929',
            tools: ['Bash', 'Read', 'Edit', 'Write'],
          },
        },
      },
    },
    textMessage: {
      type: 'TextMessage',
      source: 'claude_code',
      data: {
        type: 'TextMessage',
        data: {
          content: 'I will help you with the code...',
        },
      },
    },
    toolCall: {
      type: 'ToolCallRequestEvent',
      source: 'claude_code',
      data: {
        type: 'ToolCallRequestEvent',
        data: {
          name: 'Read',
          arguments: { file_path: '/test/file.py' },
          id: 'toolu_test_1',
        },
      },
    },
    toolResult: {
      type: 'ToolCallExecutionEvent',
      source: 'claude_code',
      data: {
        type: 'ToolCallExecutionEvent',
        data: {
          name: 'Read',
          result: 'def test():\n    pass',
          is_error: false,
          id: 'toolu_test_1',
        },
      },
    },
    taskResult: {
      type: 'TaskResult',
      source: 'claude_code',
      data: {
        type: 'TaskResult',
        data: {
          outcome: 'success',
          message: 'Task completed successfully',
          duration_ms: 2500,
        },
      },
    },
  },

  voice: {
    sessionCreated: {
      type: 'session.created',
      source: 'voice',
      data: {
        session: {
          id: 'test_session_123',
          model: 'gpt-4o-realtime-preview',
        },
      },
    },
    userMessage: {
      type: 'conversation.item.created',
      source: 'voice',
      data: {
        item: {
          id: 'item_test_1',
          type: 'message',
          role: 'user',
          content: [{ type: 'input_text', text: 'Hello Archie' }],
        },
      },
    },
    assistantResponse: {
      type: 'response.audio_transcript.delta',
      source: 'voice',
      data: {
        delta: 'Hello! How can I assist you today?',
      },
    },
  },
};

/**
 * Test User Inputs
 */
const testInputs = {
  agentPrompts: [
    'Research machine learning trends',
    'Analyze the data',
    'Create a summary report',
  ],
  voiceCommands: [
    'Hello Archie',
    'Search for information',
    'Create a new file',
    'Show me the results',
  ],
  toolPrompts: [
    'Create a tool that searches the web',
    'Generate a tool for file operations',
    'Build a data processing tool',
  ],
};

/**
 * Expected Results
 */
const expectedResults = {
  agentCreation: {
    successMessage: /created successfully/i,
    listUpdate: /e2e.*agent/i,
  },
  toolUpload: {
    successMessage: /uploaded successfully/i,
    listUpdate: /e2e_test_tool/i,
  },
  voiceSession: {
    activeStatus: /session.*active/i,
    messageReceived: /hello/i,
  },
};

/**
 * Test Timeouts
 */
const timeouts = {
  short: 2000,
  medium: 5000,
  long: 10000,
  veryLong: 30000,
};

/**
 * Test Selectors
 */
const selectors = {
  // Agent Dashboard
  agents: {
    createButton: 'button:has-text("Create Agent")',
    agentList: '[data-testid="agent-list"]',
    agentItem: '[data-testid="agent-item"]',
    editButton: 'button:has-text("Edit")',
    deleteButton: 'button:has-text("Delete")',
    runButton: 'button:has-text("Run")',
  },

  // Agent Editor
  agentEditor: {
    nameInput: 'input[name="name"], input[label*="name" i]',
    typeSelect: 'select[name="agent_type"], select[label*="type" i]',
    descriptionInput: 'textarea[name="description"]',
    saveButton: 'button:has-text("Save")',
    cancelButton: 'button:has-text("Cancel")',
  },

  // Tool Dashboard
  tools: {
    uploadButton: 'button:has-text("Upload")',
    generateButton: 'button:has-text("Generate")',
    toolList: '[data-testid="tool-list"]',
    toolItem: '[data-testid="tool-item"]',
    editButton: 'button:has-text("Edit")',
  },

  // Voice Assistant
  voice: {
    startButton: 'button:has-text("Start")',
    stopButton: 'button:has-text("Stop")',
    muteButton: 'button:has-text("Mute")',
    conversationHistory: '[data-testid="conversation-history"]',
    claudeCodeInsights: '[data-testid="claude-code-insights"]',
    nestedAgentInsights: '[data-testid="nested-agent-insights"]',
    audioVisualizer: '[data-testid="audio-visualizer"]',
  },

  // Common
  common: {
    confirmButton: 'button:has-text("Confirm")',
    cancelButton: 'button:has-text("Cancel")',
    closeButton: 'button:has-text("Close")',
    submitButton: 'button[type="submit"]',
    loadingSpinner: '[role="progressbar"]',
    errorMessage: '[role="alert"]',
    successMessage: '.success-message, .MuiAlert-success',
  },
};

module.exports = {
  testAgents,
  testToolCode,
  testConversations,
  mockMessages,
  testInputs,
  expectedResults,
  timeouts,
  selectors,
};
