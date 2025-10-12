"""
Test fixtures and mock data for backend tests.

This module provides reusable test data, mock responses, and helper functions
for testing agents, tools, WebSocket communication, and voice conversations.

Usage:
    from tests.fixtures import MOCK_LOOPING_AGENT, MOCK_WEB_SEARCH_RESPONSE
    from tests.fixtures import create_mock_agent_config, create_mock_tool_response

Organization:
    - agent_configs.py: Mock agent configurations (looping, nested, multimodal, etc.)
    - tool_responses.py: Mock tool responses (research, memory, images, etc.)
    - websocket_events.py: Mock WebSocket events (messages, tool calls, etc.)
    - voice_data.py: Mock voice conversation data and events
"""

from .agent_configs import *
from .tool_responses import *
from .websocket_events import *
from .voice_data import *

__all__ = [
    # ============================================================================
    # Agent Configurations (from agent_configs.py)
    # ============================================================================

    # LLM configs
    "MOCK_OPENAI_LLM",
    "MOCK_OPENAI_VISION_LLM",
    "MOCK_ANTHROPIC_LLM",
    "MOCK_GOOGLE_LLM",

    # Prompt configs
    "MOCK_BASIC_PROMPT",
    "MOCK_RESEARCH_PROMPT",
    "MOCK_VISION_PROMPT",
    "MOCK_DEVELOPER_PROMPT",
    "MOCK_MEMORY_PROMPT",

    # Agent configs
    "MOCK_LOOPING_AGENT",
    "MOCK_NESTED_AGENT",
    "MOCK_MULTIMODAL_AGENT",
    "MOCK_CODE_EXECUTOR_AGENT",
    "MOCK_RESEARCHER_AGENT",
    "MOCK_MEMORY_AGENT",

    # Helper functions
    "create_mock_agent_config",
    "agent_config_to_dict",
    "create_minimal_agent_dict",

    # ============================================================================
    # Tool Responses (from tool_responses.py)
    # ============================================================================

    # Research responses
    "MOCK_WEB_SEARCH_RESPONSE",
    "MOCK_ARXIV_SEARCH_RESPONSE",
    "MOCK_WIKIPEDIA_SEARCH_RESPONSE",
    "MOCK_FETCH_WEB_CONTENT_RESPONSE",

    # Memory responses
    "MOCK_MEMORY_SAVE_RESPONSE",
    "MOCK_MEMORY_GET_RESPONSE",
    "MOCK_MEMORY_BANK_CREATE_RESPONSE",
    "MOCK_MEMORY_BANK_ADD_RESPONSE",
    "MOCK_MEMORY_BANK_SEARCH_RESPONSE",
    "MOCK_MEMORY_BANK_LIST_RESPONSE",

    # Image responses
    "MOCK_SCREENSHOT_RESPONSE",
    "MOCK_IMAGE_GENERATION_RESPONSE",
    "MOCK_SAMPLE_IMAGE_RESPONSE",
    "MOCK_BASE64_IMAGE",

    # Code execution responses
    "MOCK_PYTHON_EXECUTION_RESPONSE",
    "MOCK_BASH_EXECUTION_RESPONSE",
    "MOCK_GIT_STATUS_RESPONSE",

    # Error responses
    "MOCK_TOOL_ERROR_RESPONSE",
    "MOCK_API_ERROR_RESPONSE",
    "MOCK_PERMISSION_ERROR_RESPONSE",
    "MOCK_NOT_FOUND_ERROR_RESPONSE",

    # Helper functions
    "create_mock_tool_response",
    "create_mock_web_search_result",
    "create_mock_image_response",
    "create_mock_image_base64",

    # ============================================================================
    # WebSocket Events (from websocket_events.py)
    # ============================================================================

    # System events
    "MOCK_WS_CONNECT_EVENT",
    "MOCK_WS_INIT_EVENT",
    "MOCK_WS_DISCONNECT_EVENT",

    # Message events
    "MOCK_WS_MESSAGE_EVENT",
    "MOCK_WS_USER_MESSAGE_EVENT",
    "MOCK_WS_ASSISTANT_MESSAGE_EVENT",

    # Tool events
    "MOCK_WS_TOOL_CALL_EVENT",
    "MOCK_WS_TOOL_RESULT_EVENT",
    "MOCK_WS_TOOL_ERROR_EVENT",

    # Claude Code events
    "MOCK_CLAUDE_CODE_INIT_EVENT",
    "MOCK_CLAUDE_CODE_TEXT_EVENT",
    "MOCK_CLAUDE_CODE_TOOL_CALL_EVENT",
    "MOCK_CLAUDE_CODE_TOOL_RESULT_EVENT",
    "MOCK_CLAUDE_CODE_COMPLETE_EVENT",

    # Nested agent events
    "MOCK_NESTED_AGENT_START_EVENT",
    "MOCK_NESTED_AGENT_SELECTION_EVENT",
    "MOCK_NESTED_AGENT_HANDOFF_EVENT",
    "MOCK_NESTED_AGENT_COMPLETE_EVENT",

    # Error events
    "MOCK_WS_ERROR_EVENT",
    "MOCK_WS_AGENT_ERROR_EVENT",
    "MOCK_WS_VALIDATION_ERROR_EVENT",

    # Event sequences
    "MOCK_WS_COMPLETE_CONVERSATION_SEQUENCE",
    "MOCK_CLAUDE_CODE_CONVERSATION_SEQUENCE",

    # Helper functions
    "create_mock_ws_event",
    "create_mock_tool_call_event",
    "create_mock_tool_result_event",
    "create_mock_text_message_event",

    # ============================================================================
    # Voice Data (from voice_data.py)
    # ============================================================================

    # Conversation records
    "MOCK_VOICE_CONVERSATION",
    "MOCK_VOICE_CONVERSATION_MINIMAL",
    "MOCK_VOICE_CONVERSATION_LIST",

    # Voice events
    "MOCK_VOICE_SESSION_CREATED",
    "MOCK_VOICE_USER_SPEECH_STARTED",
    "MOCK_VOICE_USER_SPEECH_STOPPED",
    "MOCK_VOICE_TRANSCRIPTION",
    "MOCK_VOICE_RESPONSE_CREATED",
    "MOCK_VOICE_FUNCTION_CALL",
    "MOCK_VOICE_AUDIO_DELTA",
    "MOCK_VOICE_RESPONSE_DONE",

    # Nested agent events
    "MOCK_NESTED_AGENT_EVENTS",

    # Claude Code events
    "MOCK_CLAUDE_CODE_EVENTS",

    # Controller events
    "MOCK_CONTROLLER_EVENTS",

    # Complete data
    "MOCK_VOICE_EVENTS",
    "MOCK_COMPLETE_VOICE_CONVERSATION",

    # Helper functions
    "create_mock_voice_conversation",
    "create_mock_voice_event",
    "filter_events_by_source",
    "get_event_sequence_by_type",
]
