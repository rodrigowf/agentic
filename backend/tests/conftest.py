"""
Shared pytest fixtures and configuration for all tests.

This file provides common fixtures that can be used across all test files.
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from httpx import AsyncClient
from fastapi import FastAPI

# Import app components
from main import app
from config.schemas import AgentConfig, LLMConfig, PromptConfig
from utils.voice_conversation_store import ConversationStore


# ============================================================================
# Session-level Fixtures (run once per test session)
# ============================================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for the entire test session."""
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "fixtures"


# ============================================================================
# Module-level Fixtures (run once per test module)
# ============================================================================

@pytest.fixture(scope="module")
def test_agent_dir(tmp_path_factory) -> Path:
    """Create temporary directory for test agent configurations."""
    return tmp_path_factory.mktemp("test_agents")


@pytest.fixture(scope="module")
def test_tool_dir(tmp_path_factory) -> Path:
    """Create temporary directory for test tools."""
    return tmp_path_factory.mktemp("test_tools")


# ============================================================================
# Function-level Fixtures (run for each test function)
# ============================================================================

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Create a TestClient for synchronous API testing.

    Example:
        def test_get_agents(client):
            response = client.get("/api/agents")
            assert response.status_code == 200
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an AsyncClient for asynchronous API testing.

    Example:
        @pytest.mark.asyncio
        async def test_websocket(async_client):
            async with async_client.websocket_connect("/ws") as ws:
                data = await ws.receive_json()
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing without API calls."""
    mock = MagicMock()
    mock.create = AsyncMock(return_value={
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "Mocked response"
            }
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
    })
    return mock


@pytest.fixture
def sample_llm_config() -> LLMConfig:
    """Create a sample LLM configuration for testing."""
    return LLMConfig(
        provider="openai",
        model="gpt-4o-mini",
        temperature=0.0,
        max_tokens=None
    )


@pytest.fixture
def sample_prompt_config() -> PromptConfig:
    """Create a sample prompt configuration for testing."""
    return PromptConfig(
        system="You are a helpful assistant.",
        user="Test task"
    )


@pytest.fixture
def sample_looping_agent_config(sample_llm_config, sample_prompt_config) -> AgentConfig:
    """Create a sample looping agent configuration for testing."""
    return AgentConfig(
        name="TestLoopingAgent",
        agent_type="looping",
        tools=["test_tool"],
        llm=sample_llm_config,
        prompt=sample_prompt_config,
        code_executor=None,
        model_client_stream=False,
        sources=None,
        description="Test looping agent",
        system_message=None,
        max_consecutive_auto_reply=5,
        reflect_on_tool_use=True,
        terminate_on_text=False,
        tool_call_loop=True,
        sub_agents=None,
        mode=None,
        orchestrator_prompt=None,
        include_inner_dialog=True
    )


@pytest.fixture
def sample_nested_agent_config(sample_llm_config) -> AgentConfig:
    """Create a sample nested team agent configuration for testing."""
    return AgentConfig(
        name="TestNestedAgent",
        agent_type="nested_team",
        tools=[],
        llm=sample_llm_config,
        prompt=PromptConfig(system="", user=""),
        code_executor={"type": ""},
        model_client_stream=False,
        sources=[],
        description="Test nested team agent",
        system_message="",
        max_consecutive_auto_reply=5,
        reflect_on_tool_use=True,
        terminate_on_text=False,
        tool_call_loop=False,
        sub_agents=["Agent1", "Agent2"],
        mode="selector",
        orchestrator_prompt="__function__",
        include_inner_dialog=True
    )


@pytest.fixture
def sample_multimodal_agent_config(sample_llm_config, sample_prompt_config) -> AgentConfig:
    """Create a sample multimodal agent configuration for testing."""
    return AgentConfig(
        name="TestMultimodalAgent",
        agent_type="multimodal_tools_looping",
        tools=["generate_test_image"],
        llm=LLMConfig(provider="openai", model="gpt-4o", temperature=0.0),
        prompt=sample_prompt_config,
        code_executor=None,
        model_client_stream=False,
        sources=None,
        description="Test multimodal agent",
        system_message=None,
        max_consecutive_auto_reply=5,
        reflect_on_tool_use=True,
        terminate_on_text=False,
        tool_call_loop=True,
        sub_agents=None,
        mode=None,
        orchestrator_prompt=None,
        include_inner_dialog=True
    )


@pytest.fixture
def temp_db(tmp_path) -> Path:
    """Create a temporary SQLite database for testing."""
    db_path = tmp_path / "test_voice_conversations.db"
    return db_path


@pytest.fixture
def conversation_store(temp_db) -> ConversationStore:
    """Create a ConversationStore with temporary database."""
    return ConversationStore(db_path=str(temp_db))


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing."""
    mock = AsyncMock()
    mock.accept = AsyncMock()
    mock.send_json = AsyncMock()
    mock.send_text = AsyncMock()
    mock.receive_json = AsyncMock(return_value={"type": "test", "data": "test"})
    mock.receive_text = AsyncMock(return_value="test")
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_tool_response():
    """Mock tool response for testing."""
    return {
        "name": "test_tool",
        "result": "Tool executed successfully",
        "execution_time": 0.1
    }


@pytest.fixture
def sample_agent_json():
    """Sample agent JSON configuration."""
    return {
        "name": "TestAgent",
        "agent_type": "looping",
        "tools": ["web_search"],
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.0,
            "max_tokens": None
        },
        "prompt": {
            "system": "You are a test agent.",
            "user": "Perform test task."
        },
        "code_executor": None,
        "model_client_stream": False,
        "sources": None,
        "description": "Test agent",
        "system_message": None,
        "max_consecutive_auto_reply": 10,
        "reflect_on_tool_use": True,
        "terminate_on_text": False,
        "tool_call_loop": True,
        "sub_agents": None,
        "mode": None,
        "orchestrator_prompt": None,
        "include_inner_dialog": True
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o-mini",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Test response from assistant"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 25,
            "total_tokens": 75
        }
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client for testing."""
    mock = MagicMock()
    mock.get_or_create_collection = MagicMock(return_value=MagicMock())
    return mock


# ============================================================================
# Helper Functions
# ============================================================================

def assert_valid_agent_config(config: dict):
    """Assert that an agent configuration has all required fields."""
    required_fields = ["name", "agent_type", "tools", "llm", "prompt"]
    for field in required_fields:
        assert field in config, f"Missing required field: {field}"


def assert_valid_llm_config(config: dict):
    """Assert that an LLM configuration has all required fields."""
    required_fields = ["provider", "model"]
    for field in required_fields:
        assert field in config, f"Missing required field: {field}"


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_configure(config):
    """Pytest configuration hook."""
    # Set test environment
    os.environ["TESTING"] = "1"
    os.environ["LOG_LEVEL"] = "DEBUG"

    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")


def pytest_collection_modifyitems(config, items):
    """Modify test items after collection."""
    # Add markers based on file path
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
