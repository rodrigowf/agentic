"""
Audio Chat Handler for disconnected voice mode.

Uses OpenAI Chat Completions API with gpt-4o-audio-preview model
for non-realtime audio input/output conversations.
"""

import os
import json
import logging
from typing import List, Dict, Optional, Tuple, Any
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class AudioChatHandler:
    """Handles non-realtime audio chat using OpenAI Chat Completions API."""

    # Tools available in disconnected mode (same as realtime voice)
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "send_to_nested",
                "description": "Send a user message to the nested agents team (MainConversation) via WebSocket. Use this when the user asks you to do a task that requires the nested team.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The user message to send to the nested team."}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_to_claude_code",
                "description": "Send a self-editing instruction to Claude Code to modify the codebase. Use when the user asks to change, add, or fix code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "The instruction for Claude Code."}
                    },
                    "required": ["text"],
                    "additionalProperties": False
                }
            }
        }
    ]

    def __init__(
        self,
        model: str = "gpt-4o-audio-preview",
        voice: str = "alloy"
    ):
        """
        Initialize the audio chat handler.

        Args:
            model: OpenAI model to use (must support audio modality)
            voice: Voice to use for audio output (alloy, echo, fable, onyx, nova, shimmer)
        """
        self.model = model
        self.voice = voice
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def send_audio_message(
        self,
        audio_base64: str,
        conversation_history: List[Dict],
        system_prompt: str,
        audio_format: str = "wav"
    ) -> Tuple[str, Optional[str], Optional[str], Optional[List[Dict]]]:
        """
        Send audio input and get text + audio output.

        Args:
            audio_base64: Base64-encoded audio data
            conversation_history: List of conversation events from storage
            system_prompt: System prompt for the conversation
            audio_format: Format of input audio (wav, mp3, etc.)

        Returns:
            Tuple of (text_response, audio_base64_response, user_transcript, tool_calls)
        """
        messages = self._build_messages(
            conversation_history,
            system_prompt,
            audio_base64=audio_base64,
            audio_format=audio_format
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            modalities=["text", "audio"],
            audio={"voice": self.voice, "format": "wav"},
            messages=messages,
            tools=self.TOOLS
        )

        choice = response.choices[0]

        # Extract text content
        text = choice.message.content or ""

        # Extract audio response if available
        audio_data = None
        if hasattr(choice.message, 'audio') and choice.message.audio:
            audio_data = choice.message.audio.data

        # Try to get transcript from audio (if model provides it)
        transcript = None
        if hasattr(choice.message, 'audio') and choice.message.audio:
            transcript = getattr(choice.message.audio, 'transcript', None)

        # Extract tool calls if any
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = []
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                })

        return text, audio_data, transcript, tool_calls

    async def send_text_message(
        self,
        text: str,
        conversation_history: List[Dict],
        system_prompt: str,
        include_audio: bool = True
    ) -> Tuple[str, Optional[str], Optional[List[Dict]]]:
        """
        Send text input and get text + optional audio output.

        Args:
            text: Text message from user
            conversation_history: List of conversation events from storage
            system_prompt: System prompt for the conversation
            include_audio: Whether to request audio in the response

        Returns:
            Tuple of (text_response, audio_base64_response, tool_calls)
        """
        messages = self._build_messages(
            conversation_history,
            system_prompt,
            text_input=text
        )

        # Build modalities based on whether audio is requested
        modalities = ["text", "audio"] if include_audio else ["text"]

        kwargs = {
            "model": self.model,
            "modalities": modalities,
            "messages": messages,
            "tools": self.TOOLS
        }

        if include_audio:
            kwargs["audio"] = {"voice": self.voice, "format": "wav"}

        response = await self.client.chat.completions.create(**kwargs)

        choice = response.choices[0]

        # Extract text content
        text_response = choice.message.content or ""

        # Extract audio response if available
        audio_data = None
        if include_audio and hasattr(choice.message, 'audio') and choice.message.audio:
            audio_data = choice.message.audio.data

        # Extract tool calls if any
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = []
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                })

        return text_response, audio_data, tool_calls

    def _build_messages(
        self,
        conversation_history: List[Dict],
        system_prompt: str,
        audio_base64: Optional[str] = None,
        audio_format: str = "wav",
        text_input: Optional[str] = None
    ) -> List[Dict]:
        """
        Build OpenAI messages array from stored conversation events.

        Args:
            conversation_history: List of events from voice_conversation_store
            system_prompt: System prompt content
            audio_base64: Current user audio input (optional)
            audio_format: Format of audio input
            text_input: Current user text input (optional)

        Returns:
            List of messages formatted for OpenAI API
        """
        messages = [{"role": "system", "content": system_prompt}]

        for event in conversation_history:
            event_type = event.get("type", "")
            payload = event.get("payload", {}) or event.get("data", {})

            if not payload:
                continue

            # Handle user messages from realtime voice
            if event_type == "voice_user_message":
                text = payload.get("text") or payload.get("transcript", "")
                if text:
                    messages.append({"role": "user", "content": text})

            # Handle user messages from disconnected mode (audio)
            elif event_type == "disconnected_user_audio":
                transcript = payload.get("transcript", "")
                if transcript:
                    messages.append({"role": "user", "content": transcript})

            # Handle user messages from disconnected mode (text)
            elif event_type == "disconnected_user_text":
                text = payload.get("text", "")
                if text:
                    messages.append({"role": "user", "content": text})

            # Handle assistant messages from realtime voice
            elif event_type == "voice_assistant_message":
                text = payload.get("text", "")
                if text:
                    messages.append({"role": "assistant", "content": text})

            # Handle assistant responses from disconnected mode
            elif event_type == "disconnected_assistant_response":
                text = payload.get("text", "")
                if text:
                    messages.append({"role": "assistant", "content": text})

            # Handle text messages sent via WebRTC bridge
            elif event_type == "voice_text_input":
                text = payload.get("text", "")
                if text:
                    messages.append({"role": "user", "content": text})

            # Handle forwarded voice responses
            elif event_type == "voice_forward":
                text = payload.get("text", "")
                if text:
                    messages.append({"role": "assistant", "content": text})

            # Handle tool calls from disconnected mode
            elif event_type == "disconnected_tool_call":
                # These are informational - the actual tool execution happens separately
                pass

        # Add current input as the latest user message
        if audio_base64:
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_base64,
                            "format": audio_format
                        }
                    }
                ]
            })
        elif text_input:
            messages.append({"role": "user", "content": text_input})

        return messages
