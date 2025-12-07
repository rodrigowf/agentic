"""
Unit tests for Pipecat voice controller
Tests the FastAPI endpoints, function handlers, and event recording
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from api.realtime_voice_pipecat import (
    router,
    VoiceFunctionHandler,
    EventRecordingProcessor,
    sessions
)
from pipecat.frames.frames import TranscriptionMessage, TextFrame, FunctionCallFromLLM
from pipecat.processors.frame_processor import FrameDirection


class TestVoiceFunctionHandler:
    """Test VoiceFunctionHandler class"""

    @pytest.fixture
    def handler(self):
        """Create function handler instance"""
        return VoiceFunctionHandler("test-conversation-id")

    @pytest.mark.asyncio
    async def test_send_to_nested(self, handler):
        """Test send_to_nested function"""
        result = await handler.send_to_nested("Test task for nested team")
        assert "Nested team will execute" in result
        assert "Test task for nested team" in result

    @pytest.mark.asyncio
    async def test_send_to_claude_code(self, handler):
        """Test send_to_claude_code function"""
        result = await handler.send_to_claude_code("Fix bug in main.py")
        assert "Claude Code will execute" in result
        assert "Fix bug in main.py" in result

    @pytest.mark.asyncio
    async def test_pause(self, handler):
        """Test pause function"""
        result = await handler.pause()
        assert result == "Nested team paused"

    @pytest.mark.asyncio
    async def test_reset(self, handler):
        """Test reset function"""
        result = await handler.reset()
        assert result == "Nested team reset"

    @pytest.mark.asyncio
    async def test_pause_claude_code(self, handler):
        """Test pause_claude_code function"""
        result = await handler.pause_claude_code()
        assert result == "Claude Code paused"


class TestEventRecordingProcessor:
    """Test EventRecordingProcessor class"""

    @pytest.fixture
    def processor(self):
        """Create event recording processor"""
        return EventRecordingProcessor("test-conversation-id")

    @pytest.mark.asyncio
    async def test_process_transcription_frame(self, processor):
        """Test recording transcription frames"""
        # Create mock transcription frame (correct signature: role, content, user_id, timestamp)
        frame = TranscriptionMessage(
            role="user",
            content="Hello, how are you?",
            user_id="user",
            timestamp="2025-12-03T00:00:00Z"
        )

        # Mock push_frame
        processor.push_frame = AsyncMock()

        # Process frame
        await processor.process_frame(frame, FrameDirection.DOWNSTREAM)

        # Verify frame was pushed through
        processor.push_frame.assert_called_once_with(frame, FrameDirection.DOWNSTREAM)

    @pytest.mark.asyncio
    async def test_process_text_frame(self, processor):
        """Test recording text frames"""
        # Create mock text frame
        frame = TextFrame(text="I'm doing great, thanks!")

        # Mock push_frame
        processor.push_frame = AsyncMock()

        # Process frame
        await processor.process_frame(frame, FrameDirection.DOWNSTREAM)

        # Verify frame was pushed through
        processor.push_frame.assert_called_once_with(frame, FrameDirection.DOWNSTREAM)

    @pytest.mark.asyncio
    async def test_process_function_call_frame(self, processor):
        """Test recording function call frames"""
        # Create mock function call frame (correct signature: function_name, tool_call_id, arguments, context)
        frame = FunctionCallFromLLM(
            function_name="send_to_nested",
            tool_call_id="call_123",
            arguments={"text": "Test task"},
            context=None
        )

        # Mock push_frame
        processor.push_frame = AsyncMock()

        # Process frame
        await processor.process_frame(frame, FrameDirection.DOWNSTREAM)

        # Verify frame was pushed through
        processor.push_frame.assert_called_once_with(frame, FrameDirection.DOWNSTREAM)

    @pytest.mark.asyncio
    async def test_error_handling(self, processor):
        """Test error handling in process_frame"""
        # Create frame that might cause issues
        frame = TextFrame(text="Test")

        # Mock push_frame to raise exception
        processor.push_frame = AsyncMock()

        # Should not raise exception (graceful error handling)
        await processor.process_frame(frame, FrameDirection.DOWNSTREAM)


class TestPipecatAPI:
    """Test Pipecat FastAPI endpoints"""

    @pytest.fixture
    def env_vars(self, monkeypatch):
        """Set up environment variables for testing"""
        monkeypatch.setenv("DAILY_API_KEY", "test-daily-api-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-api-key")

    @pytest.mark.asyncio
    async def test_create_session_missing_conversation_id(self, env_vars):
        """Test session creation with missing conversation_id"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/realtime/pipecat/session", json={})
            assert response.status_code == 400
            assert "conversation_id is required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_session_missing_daily_key(self, monkeypatch):
        """Test session creation with missing DAILY_API_KEY"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-api-key")
        # Don't set DAILY_API_KEY

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/realtime/pipecat/session", json={
                "conversation_id": "test-123"
            })
            assert response.status_code == 500
            assert "DAILY_API_KEY not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_session_missing_openai_key(self, monkeypatch):
        """Test session creation with missing OPENAI_API_KEY"""
        monkeypatch.setenv("DAILY_API_KEY", "test-daily-api-key")
        # Don't set OPENAI_API_KEY

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/realtime/pipecat/session", json={
                "conversation_id": "test-123"
            })
            assert response.status_code == 500
            assert "OPENAI_API_KEY not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_close_session_not_found(self):
        """Test closing non-existent session"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/realtime/pipecat/session/non-existent-id")
            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self):
        """Test listing sessions when none exist"""
        # Clear sessions
        sessions.clear()

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/realtime/pipecat/sessions")
            assert response.status_code == 200
            data = response.json()
            assert "sessions" in data
            assert len(data["sessions"]) == 0

    @pytest.mark.asyncio
    async def test_list_sessions_with_mock_session(self):
        """Test listing sessions with a mock session"""
        # Add mock session
        sessions["test-session-id"] = {
            "conversation_id": "test-conv-id",
            "room_url": "https://test.daily.co/room",
            "task": MagicMock(),
            "runner": MagicMock()
        }

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/realtime/pipecat/sessions")
            assert response.status_code == 200
            data = response.json()
            assert len(data["sessions"]) == 1
            assert data["sessions"][0]["session_id"] == "test-session-id"
            assert data["sessions"][0]["conversation_id"] == "test-conv-id"

        # Clean up
        sessions.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
