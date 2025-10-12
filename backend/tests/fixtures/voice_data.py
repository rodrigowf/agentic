"""
Mock voice conversation data for testing.

This module provides mock data for voice conversations, including
conversation records and events from the SQLite database.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid


# ============================================================================
# Mock Voice Conversation Records
# ============================================================================

MOCK_VOICE_CONVERSATION = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Test Voice Conversation",
    "created_at": "2025-10-11T10:30:00.000000Z",
    "updated_at": "2025-10-11T10:45:30.000000Z",
    "voice_model": "gpt-4o-realtime-preview-2024-10-01",
    "metadata": {
        "session_duration": 930,  # 15.5 minutes
        "total_turns": 12,
        "tools_used": ["send_to_nested", "send_to_claude_code"],
        "status": "completed"
    }
}

MOCK_VOICE_CONVERSATION_MINIMAL = {
    "id": "660f9511-f3ac-52e5-b827-557766551111",
    "name": "Quick Test",
    "created_at": "2025-10-11T11:00:00.000000Z",
    "updated_at": "2025-10-11T11:02:15.000000Z",
    "voice_model": None,
    "metadata": {}
}

MOCK_VOICE_CONVERSATION_LIST = [
    MOCK_VOICE_CONVERSATION,
    MOCK_VOICE_CONVERSATION_MINIMAL,
    {
        "id": "770fa622-g4bd-63f6-c938-668877662222",
        "name": "Agent Development Session",
        "created_at": "2025-10-10T14:20:00.000000Z",
        "updated_at": "2025-10-10T15:10:00.000000Z",
        "voice_model": "gpt-4o-realtime-preview-2024-10-01",
        "metadata": {
            "session_duration": 3000,
            "total_turns": 45,
            "tools_used": ["send_to_nested", "send_to_claude_code", "pause", "reset"],
            "status": "completed"
        }
    }
]


# ============================================================================
# Mock Voice Events (from OpenAI Realtime API)
# ============================================================================

MOCK_VOICE_SESSION_CREATED = {
    "id": 1,
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-11T10:30:00.000000Z",
    "source": "voice",
    "type": "session.created",
    "payload": {
        "type": "session.created",
        "session": {
            "id": "sess_abc123xyz",
            "object": "realtime.session",
            "model": "gpt-4o-realtime-preview-2024-10-01",
            "modalities": ["text", "audio"],
            "instructions": "You are Archie, the realtime voice interface...",
            "voice": "alloy",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "whisper-1"
            },
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 500
            },
            "tools": [
                {
                    "type": "function",
                    "name": "send_to_nested",
                    "description": "Send task to nested team",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
                    }
                },
                {
                    "type": "function",
                    "name": "send_to_claude_code",
                    "description": "Send instruction to Claude Code",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
                    }
                }
            ],
            "temperature": 0.8,
            "max_response_output_tokens": "inf"
        }
    }
}

MOCK_VOICE_USER_SPEECH_STARTED = {
    "id": 2,
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-11T10:30:15.000000Z",
    "source": "voice",
    "type": "input_audio_buffer.speech_started",
    "payload": {
        "type": "input_audio_buffer.speech_started",
        "audio_start_ms": 1000,
        "item_id": "msg_001"
    }
}

MOCK_VOICE_USER_SPEECH_STOPPED = {
    "id": 3,
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-11T10:30:18.500000Z",
    "source": "voice",
    "type": "input_audio_buffer.speech_stopped",
    "payload": {
        "type": "input_audio_buffer.speech_stopped",
        "audio_end_ms": 4500,
        "item_id": "msg_001"
    }
}

MOCK_VOICE_TRANSCRIPTION = {
    "id": 4,
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-11T10:30:19.000000Z",
    "source": "voice",
    "type": "conversation.item.input_audio_transcription.completed",
    "payload": {
        "type": "conversation.item.input_audio_transcription.completed",
        "item_id": "msg_001",
        "content_index": 0,
        "transcript": "Can you search for the latest research on quantum computing?"
    }
}

MOCK_VOICE_RESPONSE_CREATED = {
    "id": 5,
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-11T10:30:19.200000Z",
    "source": "voice",
    "type": "response.created",
    "payload": {
        "type": "response.created",
        "response": {
            "id": "resp_001",
            "object": "realtime.response",
            "status": "in_progress",
            "output": []
        }
    }
}

MOCK_VOICE_FUNCTION_CALL = {
    "id": 6,
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-11T10:30:19.800000Z",
    "source": "voice",
    "type": "response.function_call_arguments.done",
    "payload": {
        "type": "response.function_call_arguments.done",
        "response_id": "resp_001",
        "item_id": "fc_001",
        "output_index": 0,
        "call_id": "call_abc123",
        "name": "send_to_nested",
        "arguments": "{\"text\": \"Search for latest research on quantum computing using arxiv_search\"}"
    }
}

MOCK_VOICE_AUDIO_DELTA = {
    "id": 7,
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-11T10:30:20.100000Z",
    "source": "voice",
    "type": "response.audio.delta",
    "payload": {
        "type": "response.audio.delta",
        "response_id": "resp_001",
        "item_id": "msg_002",
        "output_index": 0,
        "content_index": 0,
        "delta": "base64_encoded_audio_chunk..."  # Abbreviated for readability
    }
}

MOCK_VOICE_RESPONSE_DONE = {
    "id": 8,
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-10-11T10:30:22.000000Z",
    "source": "voice",
    "type": "response.done",
    "payload": {
        "type": "response.done",
        "response": {
            "id": "resp_001",
            "object": "realtime.response",
            "status": "completed",
            "status_details": None,
            "output": [
                {
                    "id": "msg_002",
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "audio",
                            "transcript": "I'll search for the latest research on quantum computing for you."
                        }
                    ]
                }
            ],
            "usage": {
                "total_tokens": 145,
                "input_tokens": 120,
                "output_tokens": 25
            }
        }
    }
}


# ============================================================================
# Mock Nested Agent Events (during voice session)
# ============================================================================

MOCK_NESTED_AGENT_EVENTS = [
    {
        "id": 10,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:30:19.900000Z",
        "source": "nested",
        "type": "SystemEvent",
        "payload": {
            "message": "Nested team started",
            "orchestrator": "Manager",
            "sub_agents": ["Researcher", "Developer"]
        }
    },
    {
        "id": 11,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:30:20.000000Z",
        "source": "nested",
        "type": "TextMessage",
        "payload": {
            "content": "NEXT AGENT: Researcher",
            "source": "Manager"
        }
    },
    {
        "id": 12,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:30:20.500000Z",
        "source": "nested",
        "type": "ToolCallRequestEvent",
        "payload": {
            "type": "ToolCallRequestEvent",
            "data": {
                "name": "arxiv_search",
                "arguments": {
                    "query": "quantum computing",
                    "max_results": 5
                },
                "id": "toolu_nest_001"
            }
        }
    },
    {
        "id": 13,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:30:21.800000Z",
        "source": "nested",
        "type": "ToolCallExecutionEvent",
        "payload": {
            "type": "ToolCallExecutionEvent",
            "data": {
                "name": "arxiv_search",
                "result": "ArXiv Search Results for 'quantum computing' (Top 5):\n1. Title: Quantum Computing: A Gentle Introduction...",
                "is_error": False,
                "id": "toolu_nest_001"
            }
        }
    },
    {
        "id": 14,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:30:23.000000Z",
        "source": "nested",
        "type": "TextMessage",
        "payload": {
            "content": "I found 5 recent papers on quantum computing from ArXiv. TERMINATE",
            "source": "Researcher"
        }
    },
    {
        "id": 15,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:30:23.200000Z",
        "source": "nested",
        "type": "TaskResult",
        "payload": {
            "outcome": "success",
            "message": "Task completed by nested team",
            "final_agent": "Researcher",
            "total_turns": 3
        }
    }
]


# ============================================================================
# Mock Claude Code Events (during voice session)
# ============================================================================

MOCK_CLAUDE_CODE_EVENTS = [
    {
        "id": 20,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:32:00.000000Z",
        "source": "claude_code",
        "type": "SystemEvent",
        "payload": {
            "message": "init",
            "details": {
                "cwd": "/home/rodrigo/agentic",
                "tools": ["Bash", "Read", "Edit", "Write", "Glob", "Grep"],
                "model": "claude-sonnet-4-5-20250929",
                "permission_mode": "bypassPermissions"
            }
        }
    },
    {
        "id": 21,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:32:00.500000Z",
        "source": "claude_code",
        "type": "TextMessage",
        "payload": {
            "content": "I'll create a new research tool for ArXiv searches.",
            "source": "ClaudeCode"
        }
    },
    {
        "id": 22,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:32:01.000000Z",
        "source": "claude_code",
        "type": "ToolCallRequestEvent",
        "payload": {
            "name": "Read",
            "arguments": {
                "file_path": "/home/rodrigo/agentic/backend/tools/research.py"
            },
            "id": "toolu_cc_001"
        }
    },
    {
        "id": 23,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:32:01.200000Z",
        "source": "claude_code",
        "type": "ToolCallExecutionEvent",
        "payload": {
            "name": "Read",
            "result": "# researcher_tools.py\n\nimport logging\nimport requests\nimport arxiv...",
            "is_error": False,
            "id": "toolu_cc_001"
        }
    },
    {
        "id": 24,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:32:02.000000Z",
        "source": "claude_code",
        "type": "ToolCallRequestEvent",
        "payload": {
            "name": "Edit",
            "arguments": {
                "file_path": "/home/rodrigo/agentic/backend/tools/research.py",
                "old_string": "max_results: int = 5",
                "new_string": "max_results: int = 10"
            },
            "id": "toolu_cc_002"
        }
    },
    {
        "id": 25,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:32:02.300000Z",
        "source": "claude_code",
        "type": "ToolCallExecutionEvent",
        "payload": {
            "name": "Edit",
            "result": "File edited successfully",
            "is_error": False,
            "id": "toolu_cc_002"
        }
    },
    {
        "id": 26,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:32:03.000000Z",
        "source": "claude_code",
        "type": "TaskResult",
        "payload": {
            "outcome": "success",
            "message": "Updated ArXiv search tool to return 10 results by default",
            "duration_ms": 3000,
            "usage": {
                "input_tokens": 1500,
                "output_tokens": 300
            }
        }
    }
]


# ============================================================================
# Mock Controller Events
# ============================================================================

MOCK_CONTROLLER_EVENTS = [
    {
        "id": 30,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:30:00.000000Z",
        "source": "controller",
        "type": "system",
        "payload": {
            "message": "Voice session started",
            "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    },
    {
        "id": 31,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:30:19.850000Z",
        "source": "controller",
        "type": "tool_call",
        "payload": {
            "message": "Calling nested team with task",
            "tool": "send_to_nested",
            "task": "Search for latest research on quantum computing using arxiv_search"
        }
    },
    {
        "id": 32,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:32:00.000000Z",
        "source": "controller",
        "type": "tool_call",
        "payload": {
            "message": "Calling Claude Code with instruction",
            "tool": "send_to_claude_code",
            "instruction": "Update the ArXiv search tool"
        }
    },
    {
        "id": 33,
        "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-10-11T10:45:30.000000Z",
        "source": "controller",
        "type": "system",
        "payload": {
            "message": "Voice session ended",
            "duration": 930
        }
    }
]


# ============================================================================
# Complete Voice Conversation with All Events
# ============================================================================

MOCK_VOICE_EVENTS = [
    MOCK_VOICE_SESSION_CREATED,
    MOCK_VOICE_USER_SPEECH_STARTED,
    MOCK_VOICE_USER_SPEECH_STOPPED,
    MOCK_VOICE_TRANSCRIPTION,
    MOCK_VOICE_RESPONSE_CREATED,
    MOCK_VOICE_FUNCTION_CALL,
    MOCK_VOICE_AUDIO_DELTA,
    MOCK_VOICE_RESPONSE_DONE,
    *MOCK_NESTED_AGENT_EVENTS,
    *MOCK_CLAUDE_CODE_EVENTS,
    *MOCK_CONTROLLER_EVENTS
]

MOCK_COMPLETE_VOICE_CONVERSATION = {
    "conversation": MOCK_VOICE_CONVERSATION,
    "events": MOCK_VOICE_EVENTS
}


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_voice_conversation(
    name: str = "Test Conversation",
    conversation_id: Optional[str] = None,
    voice_model: Optional[str] = "gpt-4o-realtime-preview-2024-10-01",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a mock voice conversation record.

    Args:
        name: Conversation name
        conversation_id: UUID for conversation (auto-generated if not provided)
        voice_model: Voice model identifier
        metadata: Additional metadata

    Returns:
        Voice conversation record dictionary

    Example:
        >>> conv = create_mock_voice_conversation("My Test")
        >>> assert conv["name"] == "My Test"
    """
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    now = datetime.now(timezone.utc).isoformat()

    return {
        "id": conversation_id,
        "name": name,
        "created_at": now,
        "updated_at": now,
        "voice_model": voice_model,
        "metadata": metadata or {}
    }


def create_mock_voice_event(
    conversation_id: str,
    source: str,
    event_type: str,
    payload: Dict[str, Any],
    event_id: Optional[int] = None,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a mock voice event record.

    Args:
        conversation_id: Conversation UUID
        source: Event source (voice, nested, claude_code, controller)
        event_type: Event type
        payload: Event payload data
        event_id: Event ID (auto-incremented in real DB)
        timestamp: Event timestamp (auto-generated if not provided)

    Returns:
        Voice event record dictionary

    Example:
        >>> event = create_mock_voice_event(
        ...     "conv-123",
        ...     "voice",
        ...     "session.created",
        ...     {"session": {"id": "sess_123"}}
        ... )
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "id": event_id,
        "conversation_id": conversation_id,
        "timestamp": timestamp,
        "source": source,
        "type": event_type,
        "payload": payload
    }


def filter_events_by_source(
    events: List[Dict[str, Any]],
    source: str
) -> List[Dict[str, Any]]:
    """
    Filter events by source.

    Args:
        events: List of event records
        source: Source to filter by

    Returns:
        Filtered list of events

    Example:
        >>> voice_events = filter_events_by_source(MOCK_VOICE_EVENTS, "voice")
        >>> assert all(e["source"] == "voice" for e in voice_events)
    """
    return [e for e in events if e.get("source") == source]


def get_event_sequence_by_type(
    events: List[Dict[str, Any]],
    event_types: List[str]
) -> List[Dict[str, Any]]:
    """
    Get events matching specific types in order.

    Args:
        events: List of event records
        event_types: List of event types to include

    Returns:
        Filtered and ordered list of events

    Example:
        >>> tool_events = get_event_sequence_by_type(
        ...     MOCK_VOICE_EVENTS,
        ...     ["ToolCallRequestEvent", "ToolCallExecutionEvent"]
        ... )
    """
    return [e for e in events if e.get("type") in event_types]


# ============================================================================
# Export All
# ============================================================================

__all__ = [
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
