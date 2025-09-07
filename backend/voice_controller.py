"""
voice_controller.py
===================

This module defines a ``VoiceControlledNestedAgent`` class which wraps a
``NestedTeamAgent`` and exposes a simple API for driving it with voice
commands.  The goal of this component is to allow a real–time voice agent
to prompt a nested team of AutoGen agents, pause and resume the conversation
flow, and relay both the final response and the internal dialog back to the
user.

The implementation makes minimal assumptions about the underlying audio
infrastructure.  It originally included placeholder methods for speech recognition
(`transcribe_audio`) and speech synthesis (`speak`). But these were removed: audio
is handled directly by the OpenAI Realtime model in the browser. This class
remains a controller/wrapper for nested conversations only.

Example usage::

    import asyncio
    from backend.voice_controller import VoiceControlledNestedAgent

    async def main():
        vcn = VoiceControlledNestedAgent(agent_name="MainConversation")
        # send a text prompt as if it were transcribed from audio
        await vcn.handle_user_text("Find me a good pizza recipe and summarise the steps.")
        # Later, when the user says "pause" you can call vcn.pause()

    asyncio.run(main())

Note that actual audio streaming, microphone handling and network calls to
OpenAI are intentionally left out of this example to keep the focus on the
agent integration.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

try:
    import openai  # Optional: used for speech recognition/synthesis placeholders
except ImportError:
    openai = None  # If openai is not installed, audio functions will raise

from autogen_core import CancellationToken
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import (
    BaseChatMessage,
    ModelClientStreamingChunkEvent,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient

from config_loader import load_agents, load_tools
from schemas import AgentConfig
from agent_factory import create_agent_from_config


logger = logging.getLogger(__name__)


class VoiceControlledNestedAgent:
    """A wrapper around a nested team agent with voice control capabilities.

    This class manages the lifecycle of an underlying ``NestedTeamAgent`` and
    exposes methods for handling user input (text), streaming responses back to
    the caller, and pausing the conversation. It keeps track of conversation
    history so that subsequent calls include previous turns.
    """

    def __init__(
        self,
        agent_name: str,
        agents_dir: str = "agents",
        tools_dir: str = "tools",
        *,
        include_inner_dialog: bool | None = None,
    ) -> None:
        # Load all agent configurations and pick out the requested one
        agents: List[AgentConfig] = load_agents(agents_dir)
        self.agent_cfg: Optional[AgentConfig] = next(
            (cfg for cfg in agents if cfg.name == agent_name), None
        )
        if self.agent_cfg is None:
            raise ValueError(f"Agent configuration for '{agent_name}' not found in '{agents_dir}'.")

        # Optionally override the include_inner_dialog flag
        if include_inner_dialog is not None:
            self.agent_cfg.include_inner_dialog = include_inner_dialog

        # Load tools and store them; tools are necessary even if the agent
        # doesn't explicitly use them, because sub‑agents may require them.
        loaded_tools_with_filenames = load_tools(tools_dir)
        self.all_tools = [tool for tool, _ in loaded_tools_with_filenames]

        # Create the model client for the nested team.  For now we only
        # support OpenAI models, which is consistent with existing code.
        provider = self.agent_cfg.llm.provider.lower() if self.agent_cfg.llm else "openai"
        model_name = self.agent_cfg.llm.model if self.agent_cfg.llm else "gpt-4o"
        if provider != "openai":
            raise ValueError(
                f"VoiceControlledNestedAgent currently only supports 'openai' providers, got '{provider}'."
            )
        api_key = None
        try:
            model_client = OpenAIChatCompletionClient(model=model_name, api_key=api_key)
        except Exception as e:
            raise RuntimeError(f"Failed to initialise OpenAI model client: {e}")

        # Instantiate the nested team agent via the factory.
        self.agent: BaseChatAgent = create_agent_from_config(
            self.agent_cfg, self.all_tools, model_client
        )

        # Conversation state
        self.history: List[BaseChatMessage] = []  # all previous messages
        self._current_cancellation_token: Optional[CancellationToken] = None
        self._conversation_lock = asyncio.Lock()  # ensures only one run_stream at a time

    # Public API --------------------------------------------------------------

    async def handle_user_text(self, text: str) -> None:
        """Append a user text message and stream the nested team response."""
        await self._send_message_to_nested_team(text)

    async def reset(self) -> None:
        """Reset conversation state and inner team."""
        self.history.clear()
        try:
            await self.agent.reset(CancellationToken())
        except Exception:
            # Not all agents may implement reset; ignore
            pass

    def pause(self) -> None:
        """Cancel the current run_stream invocation, if any."""
        if self._current_cancellation_token is not None:
            logger.info("Pausing conversation via cancellation token…")
            self._current_cancellation_token.cancel()
        else:
            logger.warning("pause() called but there is no active conversation.")

    # Internals ---------------------------------------------------------------

    async def _send_message_to_nested_team(self, message_content: str) -> None:
        async with self._conversation_lock:
            user_msg = TextMessage(content=message_content, source="user")
            self.history.append(user_msg)

            cancellation_token = CancellationToken()
            self._current_cancellation_token = cancellation_token

            logger.info(f"Sending user message to nested team: {message_content[:80]}…")

            messages: List[BaseChatMessage] = list(self.history)

            try:
                async for event in self.agent.run_stream(
                    task=messages, cancellation_token=cancellation_token
                ):
                    await self._handle_stream_event(event)
            except asyncio.CancelledError:
                logger.info("Conversation streaming cancelled.")
            except Exception as e:
                logger.error(f"Error while streaming from nested team: {e}")
            finally:
                self._current_cancellation_token = None

    async def _handle_stream_event(self, event: object) -> None:
        if isinstance(event, TextMessage):
            if event.source != "user":
                self.history.append(event)
            logger.info(f"{event.source}: {event.content}")
            return

        if isinstance(event, ModelClientStreamingChunkEvent):
            if event.content:
                logger.debug(f"Model chunk from {event.source}: {event.content}")
            return

        if isinstance(event, ToolCallRequestEvent):
            logger.info(f"Tool call requested by {event.caller}: {event.content}")
            return
        if isinstance(event, ToolCallExecutionEvent):
            logger.info(f"Tool execution results from {event.caller}: {event.content}")
            for result in event.content:
                msg = TextMessage(content=str(result.content), source="tools")
                self.history.append(msg)
                logger.info(f"tools: {msg.content}")
            return

        logger.debug(f"Unhandled event type {type(event)}: {event}")
