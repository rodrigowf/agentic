"""
Mock WebSocket events for testing.

This module provides mock WebSocket event data that matches the actual
event formats used in the application's WebSocket communication.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


# ============================================================================
# System Events
# ============================================================================

MOCK_WS_CONNECT_EVENT = {
    "type": "system",
    "data": {
        "message": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": "test-session-123"
    }
}

MOCK_WS_INIT_EVENT = {
    "type": "SystemEvent",
    "data": {
        "message": "init",
        "details": {
            "agent_name": "TestAgent",
            "tools_available": ["web_search", "fetch_web_content"],
            "model": "gpt-4o-mini",
            "max_turns": 10
        }
    }
}

MOCK_WS_DISCONNECT_EVENT = {
    "type": "system",
    "data": {
        "message": "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": "client_closed"
    }
}


# ============================================================================
# Message Events
# ============================================================================

MOCK_WS_MESSAGE_EVENT = {
    "type": "TextMessage",
    "data": {
        "content": "I'll help you search for information about machine learning.",
        "source": "TestAgent",
        "models_usage": {
            "gpt-4o-mini": {
                "prompt_tokens": 120,
                "completion_tokens": 25,
                "total_tokens": 145
            }
        },
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn": 1
        }
    }
}

MOCK_WS_USER_MESSAGE_EVENT = {
    "type": "user_message",
    "data": "Search for information about machine learning"
}

MOCK_WS_ASSISTANT_MESSAGE_EVENT = {
    "type": "assistant",
    "message": {
        "role": "assistant",
        "content": "I'll search for information about machine learning using the web_search tool."
    }
}


# ============================================================================
# Tool Call Events
# ============================================================================

MOCK_WS_TOOL_CALL_EVENT = {
    "type": "ToolCallRequestEvent",
    "data": {
        "type": "ToolCallRequestEvent",
        "data": {
            "name": "web_search",
            "arguments": {
                "query": "machine learning fundamentals",
                "max_results": 5
            },
            "id": "toolu_01ABC123xyz"
        }
    },
    "source": "nested"
}

MOCK_WS_TOOL_RESULT_EVENT = {
    "type": "ToolCallExecutionEvent",
    "data": {
        "type": "ToolCallExecutionEvent",
        "data": {
            "name": "web_search",
            "result": "Web Search Results (Google CSE) for 'machine learning fundamentals' (Found 5):\n1. Title: Introduction to Machine Learning...",
            "is_error": False,
            "id": "toolu_01ABC123xyz"
        }
    },
    "source": "nested"
}

MOCK_WS_TOOL_ERROR_EVENT = {
    "type": "ToolCallExecutionEvent",
    "data": {
        "type": "ToolCallExecutionEvent",
        "data": {
            "name": "web_search",
            "result": "Error: Connection timeout while searching. Please try again.",
            "is_error": True,
            "id": "toolu_01ABC123xyz"
        }
    },
    "source": "nested"
}


# ============================================================================
# Claude Code Events
# ============================================================================

MOCK_CLAUDE_CODE_INIT_EVENT = {
    "type": "SystemEvent",
    "data": {
        "message": "init",
        "details": {
            "cwd": "/home/rodrigo/agentic",
            "tools": ["Bash", "Read", "Edit", "Write", "Glob", "Grep"],
            "model": "claude-sonnet-4-5-20250929",
            "permission_mode": "bypassPermissions"
        }
    },
    "source": "claude_code"
}

MOCK_CLAUDE_CODE_TEXT_EVENT = {
    "type": "TextMessage",
    "data": {
        "content": "I'll add the requested feature to the codebase.",
        "source": "ClaudeCode"
    },
    "source": "claude_code"
}

MOCK_CLAUDE_CODE_TOOL_CALL_EVENT = {
    "type": "ToolCallRequestEvent",
    "data": {
        "name": "Bash",
        "arguments": {
            "command": "ls -la backend/",
            "description": "List backend directory contents"
        },
        "id": "toolu_claude_001"
    },
    "source": "claude_code"
}

MOCK_CLAUDE_CODE_TOOL_RESULT_EVENT = {
    "type": "ToolCallExecutionEvent",
    "data": {
        "name": "Bash",
        "result": "total 48\ndrwxrwxr-x 16 rodrigo rodrigo  4096 Oct 11 21:51 .\ndrwxr-xr-x 25 rodrigo rodrigo  4096 Oct 10 15:30 ..\ndrwxrwxr-x 10 rodrigo rodrigo  4096 Oct 11 18:22 backend",
        "is_error": False,
        "id": "toolu_claude_001"
    },
    "source": "claude_code"
}

MOCK_CLAUDE_CODE_COMPLETE_EVENT = {
    "type": "TaskResult",
    "data": {
        "outcome": "success",
        "message": "Feature added successfully. Created new file at backend/tools/new_tool.py",
        "duration_ms": 5420,
        "usage": {
            "input_tokens": 2500,
            "output_tokens": 850,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0
        },
        "models_usage": {
            "claude-sonnet-4-5-20250929": {
                "prompt_tokens": 2500,
                "completion_tokens": 850,
                "total_tokens": 3350
            }
        }
    },
    "source": "claude_code"
}


# ============================================================================
# Nested Agent Events
# ============================================================================

MOCK_NESTED_AGENT_START_EVENT = {
    "type": "system",
    "data": {
        "message": "Nested team started",
        "orchestrator": "Manager",
        "sub_agents": ["Researcher", "Developer"],
        "mode": "selector"
    },
    "source": "nested"
}

MOCK_NESTED_AGENT_SELECTION_EVENT = {
    "type": "TextMessage",
    "data": {
        "content": "NEXT AGENT: Researcher",
        "source": "Manager",
        "metadata": {
            "agent_selection": True,
            "selected_agent": "Researcher"
        }
    },
    "source": "nested"
}

MOCK_NESTED_AGENT_HANDOFF_EVENT = {
    "type": "HandoffMessage",
    "data": {
        "content": "Transferring to Researcher to gather information",
        "source": "Manager",
        "target": "Researcher",
        "metadata": {
            "handoff_reason": "research_required"
        }
    },
    "source": "nested"
}

MOCK_NESTED_AGENT_COMPLETE_EVENT = {
    "type": "TaskResult",
    "data": {
        "outcome": "success",
        "message": "Task completed by nested team",
        "final_agent": "Developer",
        "total_turns": 8,
        "models_usage": {
            "gpt-4o-mini": {
                "prompt_tokens": 5240,
                "completion_tokens": 1250,
                "total_tokens": 6490
            }
        }
    },
    "source": "nested"
}


# ============================================================================
# Error Events
# ============================================================================

MOCK_WS_ERROR_EVENT = {
    "type": "Error",
    "data": {
        "message": "Tool execution failed",
        "error": "Connection timeout while fetching web content",
        "tool": "fetch_web_content",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
}

MOCK_WS_AGENT_ERROR_EVENT = {
    "type": "error",
    "data": {
        "message": "Agent execution failed",
        "error": "Maximum auto-reply limit reached without TERMINATE",
        "agent": "TestAgent",
        "turn": 15
    }
}

MOCK_WS_VALIDATION_ERROR_EVENT = {
    "type": "Error",
    "data": {
        "message": "Invalid message format",
        "error": "Missing required field: 'data'",
        "received": {"type": "user_message"}
    }
}


# ============================================================================
# Complete Event Sequences
# ============================================================================

MOCK_WS_COMPLETE_CONVERSATION_SEQUENCE = [
    MOCK_WS_CONNECT_EVENT,
    MOCK_WS_INIT_EVENT,
    MOCK_WS_USER_MESSAGE_EVENT,
    MOCK_WS_MESSAGE_EVENT,
    MOCK_WS_TOOL_CALL_EVENT,
    MOCK_WS_TOOL_RESULT_EVENT,
    {
        "type": "TextMessage",
        "data": {
            "content": "Based on the search results, machine learning is a subset of AI that enables computers to learn from data. TERMINATE",
            "source": "TestAgent"
        }
    },
    {
        "type": "TaskResult",
        "data": {
            "outcome": "success",
            "message": "Task completed successfully",
            "turns": 3
        }
    }
]

MOCK_CLAUDE_CODE_CONVERSATION_SEQUENCE = [
    MOCK_CLAUDE_CODE_INIT_EVENT,
    {
        "type": "user_message",
        "data": "Add a new tool to the backend"
    },
    MOCK_CLAUDE_CODE_TEXT_EVENT,
    MOCK_CLAUDE_CODE_TOOL_CALL_EVENT,
    MOCK_CLAUDE_CODE_TOOL_RESULT_EVENT,
    {
        "type": "ToolCallRequestEvent",
        "data": {
            "name": "Write",
            "arguments": {
                "file_path": "/home/rodrigo/agentic/backend/tools/new_tool.py",
                "content": "# New tool implementation\n..."
            },
            "id": "toolu_claude_002"
        },
        "source": "claude_code"
    },
    {
        "type": "ToolCallExecutionEvent",
        "data": {
            "name": "Write",
            "result": "File written successfully",
            "is_error": False,
            "id": "toolu_claude_002"
        },
        "source": "claude_code"
    },
    MOCK_CLAUDE_CODE_COMPLETE_EVENT
]


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_ws_event(
    event_type: str,
    data: Any,
    source: str = "nested",
    include_timestamp: bool = True
) -> Dict[str, Any]:
    """
    Create a mock WebSocket event with consistent structure.

    Args:
        event_type: Type of event (e.g., "TextMessage", "ToolCallRequestEvent")
        data: Event data payload
        source: Event source (e.g., "nested", "claude_code", "voice")
        include_timestamp: Whether to add timestamp to metadata

    Returns:
        WebSocket event dictionary

    Example:
        >>> event = create_mock_ws_event("TextMessage", {"content": "Hello"})
        >>> assert event["type"] == "TextMessage"
    """
    event = {
        "type": event_type,
        "data": data,
        "source": source
    }

    if include_timestamp and isinstance(data, dict):
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["timestamp"] = datetime.now(timezone.utc).isoformat()

    return event


def create_mock_tool_call_event(
    tool_name: str,
    arguments: Dict[str, Any],
    tool_id: Optional[str] = None,
    source: str = "nested"
) -> Dict[str, Any]:
    """
    Create a mock tool call request event.

    Args:
        tool_name: Name of the tool being called
        arguments: Tool arguments
        tool_id: Unique tool call ID (auto-generated if not provided)
        source: Event source

    Returns:
        Tool call request event

    Example:
        >>> event = create_mock_tool_call_event("web_search", {"query": "test"})
        >>> assert event["data"]["data"]["name"] == "web_search"
    """
    if tool_id is None:
        import uuid
        tool_id = f"toolu_{uuid.uuid4().hex[:12]}"

    return {
        "type": "ToolCallRequestEvent",
        "data": {
            "type": "ToolCallRequestEvent",
            "data": {
                "name": tool_name,
                "arguments": arguments,
                "id": tool_id
            }
        },
        "source": source
    }


def create_mock_tool_result_event(
    tool_name: str,
    result: str,
    tool_id: str,
    is_error: bool = False,
    source: str = "nested"
) -> Dict[str, Any]:
    """
    Create a mock tool execution result event.

    Args:
        tool_name: Name of the tool
        result: Tool result string
        tool_id: Tool call ID (must match request)
        is_error: Whether this is an error result
        source: Event source

    Returns:
        Tool execution result event

    Example:
        >>> event = create_mock_tool_result_event("web_search", "Found 5 results", "toolu_123")
        >>> assert event["data"]["data"]["is_error"] == False
    """
    return {
        "type": "ToolCallExecutionEvent",
        "data": {
            "type": "ToolCallExecutionEvent",
            "data": {
                "name": tool_name,
                "result": result,
                "is_error": is_error,
                "id": tool_id
            }
        },
        "source": source
    }


def create_mock_text_message_event(
    content: str,
    source: str = "TestAgent",
    models_usage: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a mock text message event.

    Args:
        content: Message content
        source: Message source (agent name)
        models_usage: Optional model usage statistics

    Returns:
        Text message event

    Example:
        >>> event = create_mock_text_message_event("Hello, world!")
        >>> assert event["data"]["content"] == "Hello, world!"
    """
    if models_usage is None:
        models_usage = {
            "gpt-4o-mini": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120
            }
        }

    return {
        "type": "TextMessage",
        "data": {
            "content": content,
            "source": source,
            "models_usage": models_usage,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    }


# ============================================================================
# Export All
# ============================================================================

__all__ = [
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
]
