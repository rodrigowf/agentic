"""
Example test file demonstrating fixture usage.

This file shows how to use the comprehensive test fixtures
for testing agents, tools, WebSocket events, and voice conversations.
"""

import pytest
from tests.fixtures import (
    # Agent configs
    MOCK_LOOPING_AGENT,
    MOCK_NESTED_AGENT,
    MOCK_MULTIMODAL_AGENT,
    create_mock_agent_config,

    # Tool responses
    MOCK_WEB_SEARCH_RESPONSE,
    MOCK_MEMORY_SAVE_RESPONSE,
    MOCK_SCREENSHOT_RESPONSE,
    create_mock_tool_response,

    # WebSocket events
    MOCK_WS_TOOL_CALL_EVENT,
    MOCK_WS_TOOL_RESULT_EVENT,
    MOCK_CLAUDE_CODE_CONVERSATION_SEQUENCE,
    create_mock_tool_call_event,
    create_mock_tool_result_event,

    # Voice data
    MOCK_VOICE_CONVERSATION,
    MOCK_VOICE_EVENTS,
    filter_events_by_source,
    get_event_sequence_by_type,
)


# ============================================================================
# Agent Configuration Tests
# ============================================================================

def test_mock_looping_agent():
    """Test that MOCK_LOOPING_AGENT has expected properties."""
    agent = MOCK_LOOPING_AGENT

    assert agent.name == "TestLoopingAgent"
    assert agent.agent_type == "looping"
    assert agent.tool_call_loop == True
    assert "web_search" in agent.tools
    assert agent.llm.provider == "openai"
    assert agent.max_consecutive_auto_reply == 10


def test_mock_nested_agent():
    """Test that MOCK_NESTED_AGENT has sub-agents."""
    agent = MOCK_NESTED_AGENT

    assert agent.name == "TestNestedTeam"
    assert agent.agent_type == "nested_team"
    assert agent.mode == "selector"
    assert len(agent.sub_agents) == 3
    assert agent.sub_agents[0].name == "Manager"


def test_create_custom_agent():
    """Test creating a custom agent config."""
    agent = create_mock_agent_config(
        name="CustomAgent",
        agent_type="looping",
        tools=["custom_tool_1", "custom_tool_2"],
        max_consecutive_auto_reply=15
    )

    assert agent.name == "CustomAgent"
    assert len(agent.tools) == 2
    assert agent.max_consecutive_auto_reply == 15


# ============================================================================
# Tool Response Tests
# ============================================================================

def test_web_search_response():
    """Test that web search response has expected format."""
    response = MOCK_WEB_SEARCH_RESPONSE

    assert "Web Search Results" in response
    assert "machine learning" in response.lower()
    assert "URL:" in response


def test_create_tool_response():
    """Test creating a custom tool response."""
    response = create_mock_tool_response(
        tool_name="my_tool",
        success=True,
        result="Tool executed successfully",
        execution_time=0.5
    )

    assert response["tool_name"] == "my_tool"
    assert response["success"] == True
    assert response["result"] == "Tool executed successfully"
    assert response["execution_time"] == 0.5


# ============================================================================
# WebSocket Event Tests
# ============================================================================

def test_tool_call_event_structure():
    """Test that tool call event has correct structure."""
    event = MOCK_WS_TOOL_CALL_EVENT

    assert event["type"] == "ToolCallRequestEvent"
    assert event["source"] == "nested"
    assert "data" in event
    assert event["data"]["data"]["name"] == "web_search"


def test_create_custom_tool_events():
    """Test creating matching tool call and result events."""
    # Create tool call
    call_event = create_mock_tool_call_event(
        tool_name="custom_tool",
        arguments={"param": "value"},
        tool_id="tool_123"
    )

    # Create matching result
    result_event = create_mock_tool_result_event(
        tool_name="custom_tool",
        result="Success",
        tool_id="tool_123",
        is_error=False
    )

    # Verify they match
    assert call_event["data"]["data"]["id"] == result_event["data"]["data"]["id"]
    assert call_event["data"]["data"]["name"] == result_event["data"]["data"]["name"]
    assert result_event["data"]["data"]["is_error"] == False


def test_claude_code_sequence():
    """Test Claude Code conversation sequence."""
    sequence = MOCK_CLAUDE_CODE_CONVERSATION_SEQUENCE

    assert len(sequence) > 0
    assert sequence[0]["type"] == "SystemEvent"
    assert sequence[0]["source"] == "claude_code"

    # Find tool calls
    tool_calls = [e for e in sequence if e["type"] == "ToolCallRequestEvent"]
    assert len(tool_calls) > 0


# ============================================================================
# Voice Conversation Tests
# ============================================================================

def test_voice_conversation_structure():
    """Test that voice conversation has required fields."""
    conv = MOCK_VOICE_CONVERSATION

    assert "id" in conv
    assert "name" in conv
    assert "created_at" in conv
    assert "voice_model" in conv
    assert conv["voice_model"] == "gpt-4o-realtime-preview-2024-10-01"


def test_filter_voice_events():
    """Test filtering events by source."""
    # Filter voice events only
    voice_events = filter_events_by_source(MOCK_VOICE_EVENTS, "voice")

    assert len(voice_events) > 0
    assert all(e["source"] == "voice" for e in voice_events)

    # Filter Claude Code events
    claude_events = filter_events_by_source(MOCK_VOICE_EVENTS, "claude_code")

    assert len(claude_events) > 0
    assert all(e["source"] == "claude_code" for e in claude_events)


def test_get_tool_events():
    """Test extracting tool-related events."""
    tool_events = get_event_sequence_by_type(
        MOCK_VOICE_EVENTS,
        ["ToolCallRequestEvent", "ToolCallExecutionEvent"]
    )

    assert len(tool_events) > 0
    assert all(
        e["type"] in ["ToolCallRequestEvent", "ToolCallExecutionEvent"]
        for e in tool_events
    )


# ============================================================================
# Integration Tests
# ============================================================================

def test_complete_agent_workflow():
    """Test a complete agent workflow using fixtures."""
    # 1. Create agent
    agent = MOCK_LOOPING_AGENT

    # 2. Simulate tool call
    tool_call = create_mock_tool_call_event(
        tool_name="web_search",
        arguments={"query": "test query", "max_results": 5}
    )

    # 3. Simulate tool result
    tool_result = create_mock_tool_result_event(
        tool_name="web_search",
        result=MOCK_WEB_SEARCH_RESPONSE,
        tool_id=tool_call["data"]["data"]["id"],
        is_error=False
    )

    # Verify workflow
    assert agent.tools == ["web_search", "fetch_web_content"]
    assert tool_call["data"]["data"]["name"] in agent.tools
    assert tool_result["data"]["data"]["result"] == MOCK_WEB_SEARCH_RESPONSE


# ============================================================================
# Pytest Markers
# ============================================================================

pytestmark = pytest.mark.unit  # Mark all tests in this file as unit tests


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
