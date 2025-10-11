"""
claude_code_controller.py
==========================

This module manages Claude Code CLI instances for self-editing capabilities.
It spawns `claude` processes, manages JSON streaming I/O, and provides a
WebSocket interface for real-time communication.

The architecture mirrors the nested team agent pattern:
- ClaudeCodeProcess: Manages the subprocess lifecycle
- ClaudeCodeSession: Handles JSON stream parsing and event forwarding
- WebSocket handler: Streams events to frontend in real-time

Example usage:
    async def handle_claude_code(websocket: WebSocket):
        session = ClaudeCodeSession(working_dir="/home/rodrigo/agentic")
        await session.start()
        await session.send_message("Add a new feature to the voice assistant")
        async for event in session.stream_events():
            await websocket.send_json(event)
"""

import asyncio
import json
import logging
import os
from typing import Optional, AsyncIterator, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class ClaudeCodeProcess:
    """Manages a Claude Code CLI subprocess with JSON streaming."""

    # Claude CLI path - VSCode extension binary
    CLAUDE_CLI_PATH = "/home/rodrigo/.vscode/extensions/anthropic.claude-code-2.0.14-linux-x64/resources/native-binary/claude"

    def __init__(
        self,
        working_dir: str = "/home/rodrigo/agentic",
        model: str = "claude-sonnet-4-5-20250929",
        permission_mode: str = "bypassPermissions",
    ):
        self.working_dir = Path(working_dir)
        self.model = model
        self.permission_mode = permission_mode
        self.process: Optional[asyncio.subprocess.Process] = None
        self._stdout_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def start(self) -> None:
        """Start the Claude Code process with JSON streaming."""
        if self.process is not None:
            raise RuntimeError("Process already started")

        # Build command: claude --print --verbose --input-format=stream-json --output-format=stream-json
        cmd = [
            self.CLAUDE_CLI_PATH,
            "--print",
            "--verbose",
            "--input-format=stream-json",
            "--output-format=stream-json",
            "--replay-user-messages",
            f"--model={self.model}",
            f"--permission-mode={self.permission_mode}",
        ]

        logger.info(f"Starting Claude Code in {self.working_dir}: {' '.join(cmd)}")

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.working_dir),
        )

        self._running = True
        # Start background tasks for reading stdout and stderr
        asyncio.create_task(self._read_stdout())
        asyncio.create_task(self._read_stderr())

    async def _read_stdout(self) -> None:
        """Read stdout line by line and queue JSON events."""
        if not self.process or not self.process.stdout:
            return

        try:
            while self._running:
                line = await self.process.stdout.readline()
                if not line:
                    break

                try:
                    event = json.loads(line.decode().strip())
                    await self._stdout_queue.put(event)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from Claude Code stdout: {e}")
                    # Queue as raw text event
                    await self._stdout_queue.put({
                        "type": "raw_stdout",
                        "data": line.decode().strip(),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception as e:
            logger.error(f"Error reading Claude Code stdout: {e}")
        finally:
            await self._stdout_queue.put(None)  # Signal end of stream

    async def _read_stderr(self) -> None:
        """Read stderr and log errors."""
        if not self.process or not self.process.stderr:
            return

        try:
            while self._running:
                line = await self.process.stderr.readline()
                if not line:
                    break
                error_msg = line.decode().strip()
                if error_msg:
                    logger.warning(f"Claude Code stderr: {error_msg}")
                    # Queue as error event
                    await self._stdout_queue.put({
                        "type": "error",
                        "data": {"message": error_msg, "source": "claude_stderr"},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception as e:
            logger.error(f"Error reading Claude Code stderr: {e}")

    async def send_message(self, message: str) -> None:
        """Send a user message to Claude Code via stdin."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Process not started")

        event = {
            "type": "user",
            "message": {
                "role": "user",
                "content": message,
            },
        }
        json_line = json.dumps(event) + "\n"
        self.process.stdin.write(json_line.encode())
        await self.process.stdin.drain()
        logger.debug(f"Sent message to Claude Code: {message[:100]}...")

    async def cancel(self) -> None:
        """Send cancellation signal to Claude Code."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Process not started")

        # Claude Code uses Ctrl+C signal - send SIGINT
        try:
            self.process.send_signal(2)  # SIGINT
            logger.info("Sent cancellation signal to Claude Code")
        except Exception as e:
            logger.error(f"Error sending cancellation to Claude Code: {e}")

    async def get_event(self) -> Optional[Dict[str, Any]]:
        """Get next event from Claude Code stdout queue."""
        return await self._stdout_queue.get()

    async def stop(self) -> None:
        """Stop the Claude Code process gracefully."""
        self._running = False
        if self.process:
            if self.process.stdin:
                self.process.stdin.close()
                await self.process.stdin.wait_closed()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Claude Code process did not stop gracefully, terminating...")
                self.process.terminate()
                await self.process.wait()
            self.process = None
            logger.info("Claude Code process stopped")


class ClaudeCodeSession:
    """High-level session manager for Claude Code interactions."""

    def __init__(
        self,
        working_dir: str = "/home/rodrigo/agentic",
        model: str = "claude-sonnet-4-5-20250929",
        permission_mode: str = "bypassPermissions",
    ):
        self.working_dir = working_dir
        self.model = model
        self.permission_mode = permission_mode
        self.process: Optional[ClaudeCodeProcess] = None
        self._session_id: Optional[str] = None

    async def start(self) -> None:
        """Start the Claude Code session."""
        self.process = ClaudeCodeProcess(
            working_dir=self.working_dir,
            model=self.model,
            permission_mode=self.permission_mode,
        )
        await self.process.start()
        logger.info("Claude Code session started")

    async def send_message(self, message: str) -> None:
        """Send a user message to Claude Code."""
        if not self.process:
            raise RuntimeError("Session not started")
        await self.process.send_message(message)

    async def cancel(self) -> None:
        """Cancel the current Claude Code task."""
        if not self.process:
            raise RuntimeError("Session not started")
        await self.process.cancel()

    async def stream_events(self) -> AsyncIterator[Dict[str, Any]]:
        """Stream events from Claude Code."""
        if not self.process:
            raise RuntimeError("Session not started")

        while True:
            event = await self.process.get_event()
            if event is None:
                break

            # Extract session_id from init event
            if event.get("type") == "system" and event.get("subtype") == "init":
                self._session_id = event.get("session_id")

            # Normalize event structure for frontend
            normalized = self._normalize_event(event)
            yield normalized

    def _normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Claude Code events to match frontend expectations."""
        event_type = event.get("type", "unknown")

        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Normalize structure based on event type
        if event_type == "system":
            return {
                "type": "SystemEvent",
                "data": {
                    "message": event.get("subtype", "system"),
                    "details": event,
                },
                "timestamp": event["timestamp"],
                "source": "claude_code",
            }
        elif event_type == "assistant":
            # Check if this is a tool use event
            message = event.get("message", {})
            content = message.get("content", [])

            # Check if content contains tool_use
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict) and first_item.get("type") == "tool_use":
                    # This is a tool request
                    return {
                        "type": "ToolCallRequestEvent",
                        "data": {
                            "name": first_item.get("name", "unknown"),
                            "source": "ClaudeCode",
                            "arguments": first_item.get("input", {}),
                            "id": first_item.get("id"),
                        },
                        "timestamp": event["timestamp"],
                        "source": "claude_code",
                    }

            # Regular text message
            return {
                "type": "TextMessage",
                "data": {
                    "content": self._extract_text_from_message(message),
                    "source": "ClaudeCode",
                    "role": "assistant",
                    "raw": event,
                },
                "timestamp": event["timestamp"],
                "source": "claude_code",
            }
        elif event_type == "user":
            # This is typically a tool result
            message = event.get("message", {})
            content = message.get("content", [])

            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict) and first_item.get("type") == "tool_result":
                    # This is a tool result
                    return {
                        "type": "ToolCallExecutionEvent",
                        "data": {
                            "name": "tool",  # Claude doesn't include tool name in result
                            "source": "ClaudeCode",
                            "result": first_item.get("content", ""),
                            "is_error": first_item.get("is_error", False),
                            "id": first_item.get("tool_use_id"),
                        },
                        "timestamp": event["timestamp"],
                        "source": "claude_code",
                    }

            # Unknown user event
            return {
                "type": "user",
                "data": event,
                "timestamp": event["timestamp"],
                "source": "claude_code",
            }
        elif event_type == "result":
            return {
                "type": "TaskResult",
                "data": {
                    "outcome": "success" if not event.get("is_error") else "error",
                    "message": event.get("result", ""),
                    "duration_ms": event.get("duration_ms"),
                    "usage": event.get("usage", {}),
                    "models_usage": event.get("modelUsage", {}),
                },
                "timestamp": event["timestamp"],
                "source": "claude_code",
            }
        elif event_type == "error":
            return {
                "type": "Error",
                "data": {
                    "message": event.get("data", {}).get("message", str(event)),
                    "source": event.get("data", {}).get("source", "claude_code"),
                },
                "timestamp": event["timestamp"],
                "source": "claude_code",
            }
        else:
            # Pass through unknown events
            return {
                "type": event_type,
                "data": event,
                "timestamp": event["timestamp"],
                "source": "claude_code",
            }

    def _extract_text_from_message(self, message: Dict[str, Any]) -> str:
        """Extract text content from Claude API message."""
        content = message.get("content", [])
        if isinstance(content, list):
            text_parts = [
                block.get("text", "")
                for block in content
                if block.get("type") == "text"
            ]
            return "\n".join(text_parts)
        return str(content)

    async def stop(self) -> None:
        """Stop the Claude Code session."""
        if self.process:
            await self.process.stop()
            self.process = None
            logger.info("Claude Code session stopped")
