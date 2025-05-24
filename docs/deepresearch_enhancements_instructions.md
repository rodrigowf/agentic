Great, I’ll review your Agentic application in the `rodrigowf/agentic` repo and research how to extend it with:

* Optional code execution using Autogen agents,
* Image input/output via `MultiModalMessage`, including tool support,
* Runtime access to the agent instance from within tools (to modify system prompts), and
* Direct audio input/output support via multimodal messaging.

I’ll provide precise steps and code modifications for these features, keeping everything aligned with Autogen 0.5.5 standards and AutogenStudio compatibility.
I’ll update you shortly with the findings.


# Agentic Repository Enhancements

Below are step-by-step instructions and code modifications to implement each enhancement. All changes adhere to Autogen’s JSON message format and maintain compatibility with AutogenStudio’s expectations.

## 1. **Optional Code Execution via Autogen Agents**

To enable code execution, integrate Autogen’s `CodeExecutorAgent` in an optional group-chat setup. This will allow the assistant to generate code which is executed by a paired agent, following Autogen’s recommended pattern:

* **Add a flag in the schema:** In **`backend/schemas.py`**, add a new boolean field to `AgentConfig`. For example:

  ```python
  class AgentConfig(BaseSchema):
      # ... existing fields ...
      tool_call_loop: bool = False
      code_execution: bool = False  # Optional: enable code runner agent
  ```

  This flag (`code_execution`) will trigger the code-execution workflow.

* **Import required classes:** In **`backend/runner.py`**, import Autogen’s code execution components at the top:

  ```python
  from autogen_agentchat.agents import CodeExecutorAgent
  from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
  from autogen_agentchat.teams import RoundRobinGroupChat
  from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
  ```

  These provide the `CodeExecutorAgent` and a local code executor tool, plus the team orchestrator and termination conditions.

* **Instantiate code executor agent:** In `run_agent_ws`, branch before the normal agent instantiation to handle the `code_execution` flag. For example:

  ```python
  assistant = None
  if agent_cfg.code_execution:
      logger.info(f"Enabling code execution for agent: {agent_name}")
      # Create LLM-backed assistant agent (no looping needed here)
      assistant = AssistantAgent(
          name=agent_name,
          system_message=system_message,
          model_client=model_client,
          tools=agent_tools,
          max_consecutive_auto_reply=agent_cfg.max_consecutive_auto_reply
      )
      # Create a code executor agent with local execution capability
      code_agent = CodeExecutorAgent(
          name=f"{agent_name}_codeexec",
          code_executor=LocalCommandLineCodeExecutor(work_dir="code_workspace")
      )
      # Define when to terminate: e.g., on the assistant saying "TERMINATE" or after N messages
      term_condition = TextMentionTermination("TERMINATE") | MaxMessageTermination(agent_cfg.max_consecutive_auto_reply or 10)
      # Group the assistant and code executor in a round-robin conversation
      group_chat = RoundRobinGroupChat([assistant, code_agent], termination_condition=term_condition)
      logger.info("Initialized RoundRobinGroupChat with code executor agent.")
      # Use group_chat for streaming instead of a single agent
      stream = group_chat.run_stream(task=task_message, cancellation_token=cancellation_token)
  elif agent_cfg.tool_call_loop:
      # ... existing LoopingAssistantAgent path ...
  else:
      # ... existing single AssistantAgent path ...
  ```

  **Explanation:** If `code_execution` is true, we create a standard `AssistantAgent` and a `CodeExecutorAgent` that uses a local command-line executor (running code in a sandbox directory). We then wrap them in a `RoundRobinGroupChat` so they alternate turns – the assistant will produce code, then the code agent executes it and returns results, and so on. We set a termination condition to stop when the assistant outputs “TERMINATE” or a max number of exchanges is reached. Finally, call `group_chat.run_stream(...)` instead of `assistant.run_stream`. This ensures the streaming events still flow in JSON format as before (the `BaseAgentEvent` and message model serialization still apply).

* **Adjust WebSocket streaming logic:** The rest of `run_agent_ws` can remain largely the same. The `stream` now may yield events from both agents. The existing logic `await send_event_to_websocket(websocket, event_type, event)` will serialize these events with `model_dump()` as before, ensuring JSON compliance (each event includes a `type` field and content). Autogen’s events (including code execution results) are Pydantic models, so they will serialize to JSON cleanly. For example, a code execution result will appear as a `ToolCallExecutionEvent` with the executed code’s output in the content.

**References:** This design follows Autogen’s recommended approach for code execution by pairing an assistant with a code agent. The JSON structure of the conversation remains compliant with AutogenStudio, as messages and events are still emitted via `model_dump` in the Autogen format (role, content, etc.). The termination condition ensures the chat ends gracefully just as in Autogen examples.

## 2. **Image Input/Output via MultiModalMessage**

Enable the agent and tools to accept and produce images by utilizing Autogen’s `MultiModalMessage`. This involves parsing image data from user input and packaging image results appropriately:

* **Accept image in user input:** Modify how the initial task message is constructed in `run_agent_ws`. If the WebSocket “run” message contains image data (e.g. as a base64 string), create a `MultiModalMessage` instead of plain text. For instance:

  ```python
  initial_data = initial_message_data.get("data")
  if isinstance(initial_data, dict) and initial_data.get("image"):
      # e.g. initial_data = {"text": "Describe this image", "image": "<BASE64_STRING>"}
      from autogen_agentchat.messages import MultiModalMessage
      from autogen_core import Image as AGImage
      img = AGImage.from_base64(initial_data["image"])  # decode base64 to Autogen Image
      content_list = []
      if "text" in initial_data:
          content_list.append(initial_data["text"])
      content_list.append(img)
      task_message = MultiModalMessage(content=content_list, source="user")
      logger.info("Created MultiModalMessage for user image input.")
  else:
      task_message = initial_data or agent_cfg.prompt.user or ""
  ```

  Here we use `Image.from_base64(...)` to convert the provided base64 string into Autogen’s `Image` object. Autogen’s `Image` class wraps a PIL image and can serialize to a data URI for JSON output. We then build a `MultiModalMessage` with the user’s text (if any) and the image. This ensures the assistant receives an actual image input rather than a filename. Autogen’s `MultiModalMessage` is designed for this purpose.

* **Embed image outputs from tools/agent:** When a tool returns an image or when the agent itself needs to send an image, wrap it in a `MultiModalMessage` so that the image is sent as part of the message. Specifically, update the tool execution handling in **`backend/looping_agent.py`** (or wherever tool results are processed) to detect image results. For example:

  ```python
  from autogen_agentchat.messages import MultiModalMessage, TextMessage
  from autogen_core import Image as AGImage
  # ...
  if isinstance(evt, ToolCallExecutionEvent):
      for result in evt.content:  # each FunctionExecutionResult
          output = result.content
          if isinstance(output, AGImage):
              # Tool returned an Autogen Image object
              msg = MultiModalMessage(content=[output], source="tools")
          elif isinstance(output, str) and output.startswith("data:image"):
              # Tool returned an image as a data URI string
              msg = MultiModalMessage(content=[output], source="tools")
          else:
              # Non-image output, handle as text
              msg = TextMessage(content=str(output), source="tools")
          current_iteration_new_history.append(msg)
      # (No longer converting images to text; we keep them as images)
      last_assistant_text_message_content = None
      accumulated_assistant_chunks = ""
  ```

  In this snippet, if a tool’s result is an `Image` object (or an image data URI string), we create a `MultiModalMessage` with that image. Otherwise, we fallback to text. This way, the image is preserved in the conversation history. The assistant will “see” the image in the next iteration (since we append it to `history`), enabling vision-capable models (e.g., GPT-4V or Gemini with vision) to reason about it.

* **Import MultiModalMessage where needed:** Ensure `from autogen_agentchat.messages import MultiModalMessage` is added in modules where you construct these messages (e.g., runner and looping\_agent).

* **JSON serialization of images:** Autogen will include images in the JSON events with a special structure. Each `MultiModalMessage` event, when sent to the WebSocket, will serialize with a list of content items. Text parts appear as `{"type": "text", "text": "..."}`, and images appear as `{"type": "image_url", "image_url": {"url": "data:image/png;base64,...", "detail": "auto"}}`. This format is Autogen’s standard JSON for multimodal content and is understood by AutogenStudio. (Under the hood, `AGImage.to_openai_format()` produces the `image_url` payload.)

* **Model configuration for vision:** The existing code already sets `ModelInfo(vision=True)` for OpenAI GPT-4 and Gemini, so those models are flagged as vision-capable. Ensure that for any model used with images, `vision=True` is set in its ModelInfo (as done for OpenAI and Gemini models in the code). This informs Autogen that the model can handle image inputs.

With these changes, users can provide an image (e.g. uploaded via the UI and sent as a base64 string), and the agent will receive it as part of a `MultiModalMessage`. Likewise, if a tool (or the agent) generates an image (for example, a plotting tool or an image search tool returning an image file), it can be sent back to the front-end in the same manner. AutogenStudio will display such messages with the image content rendered (since the JSON contains a data URI for the image).

**References:** Autogen’s documentation demonstrates using `MultiModalMessage` for image-based interactions. The internal conversion to JSON ensures images are encoded properly with their data URIs. By leveraging these, we keep the image exchanges fully in JSON and Autogen-compliant.

## 3. **Tool Access to Agent Instance (Dynamic Prompt Adjustment)**

Allowing tools to access and modify their parent agent at runtime can be achieved by providing the agent’s context to tool functions. The simplest maintainable approach is to use a **context variable** that stores the current agent, which tool functions can read. This avoids altering Autogen’s core tool-calling mechanism and keeps the design thread-safe:

* **Define a context variable:** At the top of **`backend/runner.py`** (or a new context module), define a context variable for the current agent:

  ```python
  import contextvars
  CURRENT_AGENT = contextvars.ContextVar("CURRENT_AGENT", default=None)
  ```

  This uses Python’s `contextvars` to hold a value specific to the execution context (so concurrent runs won’t clash).

* **Set the context before agent run:** In `run_agent_ws`, after instantiating the agent (and possibly the group chat), set this variable:

  ```python
  CURRENT_AGENT.set(assistant)
  ```

  (If using code execution with a group chat, you can set it to the main assistant agent so that tools refer to the assistant’s instance.) This makes the agent available to any tool calls within this run. It’s wise to reset or clear this after the run finishes (e.g., in the `finally` block, do `CURRENT_AGENT.set(None)`).

* **Expose a helper for tools:** You can create a small helper function that tools can import to get the agent, for convenience. For example, in **`backend/runner.py`**:

  ```python
  def get_current_agent():
      return CURRENT_AGENT.get()
  ```

  Now, in any tool implementation (the Python functions under `backend/tools/`), the tool can import this and retrieve the agent.

* **Using the agent in tools:** Tools can now perform actions on the agent. For instance, a tool could modify the agent’s system prompt or other attributes dynamically. Example usage inside a tool function:

  ```python
  from runner import get_current_agent
  def change_agent_prompt(new_prompt: str) -> str:
      \"\"\"Tool to change the agent's system prompt.\"\"\"
      agent = get_current_agent()
      if agent:
          agent.system_message = new_prompt
          return "System prompt updated."
      else:
          return "Failed to update prompt: no agent context."
  ```

  You would then wrap this function in a `FunctionTool` as usual. When the agent calls `change_agent_prompt`, the tool will fetch the current agent instance and alter its `system_message`. (Autogen’s `AssistantAgent` stores the `system_message` used for its responses, so changing it will affect subsequent model calls.) This dynamic change will take effect immediately for the next turn the assistant speaks. For example, after running this tool, the assistant’s responses will use the new system instruction.

* **Attach agent reference (alternative):** Another approach (less elegant but straightforward) is to assign the agent to each tool object before running. For example, after creating `assistant` and `agent_tools`, do:

  ```python
  for tool in agent_tools:
      tool.agent = assistant  # attach the agent instance
  ```

  Then in tool code, if you have access to the `FunctionTool` instance, you could use `tool.agent`. However, since the tool functions themselves don’t get passed the `FunctionTool` object, using the context variable method is cleaner.

By implementing the context variable pattern, we **respect the Autogen framework** (no need to monkey-patch Autogen internals) and keep changes localized. The JSON output of conversations is unaffected by this change – only the internal behavior of tools is enhanced. This is compatible with AutogenStudio as it doesn’t alter message formats; it simply gives more power to tool functions.

**Note:** Autogen does not natively propagate the agent object into tool calls, so this workaround is necessary. Using `contextvars` ensures even if multiple agents run concurrently, each tool invocation sees the correct agent. This approach keeps the code maintainable and aligns with Python best practices for global context.

## 4. **Direct Audio Input/Output Support**

To handle audio in conversations, we extend the multimodal approach to include audio data. While Autogen’s current `MultiModalMessage` directly supports text and images, we can still include audio by using data URIs or a similar mechanism. (AutoGen’s multimodal support for audio is still evolving, but we can integrate it in a compatible way.)

* **Accept audio from user:** Similar to images, if the user provides an audio file (e.g., via the UI), send it as a base64 data URI string (e.g., WAV or MP3). In `run_agent_ws`, detect an audio payload in the incoming data. For example, if `initial_message_data["data"]` contains `"audio": "<BASE64_AUDIO>"`:

  ```python
  if isinstance(initial_data, dict) and initial_data.get("audio"):
      from autogen_agentchat.messages import MultiModalMessage
      audio_data = initial_data["audio"]  # expect base64 string (possibly with prefix)
      # Ensure it’s in data URI form:
      if not audio_data.startswith("data:audio"):
          audio_uri = f"data:audio/wav;base64,{audio_data}"
      else:
          audio_uri = audio_data
      content_list = []
      if "text" in initial_data:
          content_list.append(initial_data["text"])
      content_list.append(audio_uri)
      task_message = MultiModalMessage(content=content_list, source="user")
      logger.info("Created MultiModalMessage for user audio input.")
  ```

  We wrap the audio bytes as a **data URI** (prefixing with `data:audio/…;base64,`) and include it in the `MultiModalMessage.content` list. We treat the audio as a string content (the Autogen message will accept it as it’s a string, though it represents audio). The assistant will receive this audio data. In practice, most LLMs can’t directly interpret raw audio – you would likely have a tool or a special model to handle it (e.g., a Whisper transcription tool) – but this at least passes the audio through in the JSON, so it’s logged and accessible.

* **Agent or tools outputting audio:** If an agent needs to return audio (e.g., a text-to-speech tool generating a spoken response), use a similar approach:

  * If using a tool for TTS, have the tool return a base64 audio string (with a prefix). The code handling `ToolCallExecutionEvent` can detect this. For example, extend the logic in **`looping_agent.py`**:

    ```python
    elif isinstance(output, str) and output.startswith("data:audio"):
        msg = MultiModalMessage(content=[output], source="tools")
        current_iteration_new_history.append(msg)
    ```

    This will include the audio as part of the conversation events. The front-end or AutogenStudio can then recognize the `data:audio/...` URI and potentially render an audio player for it (or at least provide a download link).
  * If the assistant itself somehow produces audio (less likely without a tool), you could similarly ensure to wrap it in a `MultiModalMessage`. (Typically, the assistant would call a function to produce audio rather than generate binary audio in text.)

* **Front-end considerations:** The UI needs to handle `MultiModalMessage` events that contain audio. In the JSON event, the audio will appear as a content item that is a string starting with `data:audio/...`. This is analogous to how images appear (which start with `data:image/`). AutogenStudio (and a custom front-end) can check the content type and, for audio, render an HTML `<audio>` element or provide playback controls. Since we’re not altering Autogen’s message schema – just including audio as a data URI string – this remains within the JSON message format and doesn’t break compatibility.

* **Optional transcription/synthesis:** While not explicitly asked, it’s worth noting that to make audio truly useful, you might incorporate speech-to-text and text-to-speech tools:

  * For example, a **Whisper transcription tool** could take the audio (from `get_current_agent().history` or from the latest message content) and return text. The assistant could be configured to use it when an audio input is present.
  * Similarly, a **TTS tool** could take the assistant’s text reply and return a `data:audio` URI which we then send as described. These would be added as tools in the agent’s tool list.

Even without those extras, the above changes ensure the infrastructure supports audio. The conversation events remain JSON (with the audio encoded in a string), so AutogenStudio compatibility is maintained. In summary, audio files are transmitted as base64-encoded strings inside `MultiModalMessage` content, leveraging the same mechanisms used for images. This approach will work with future Autogen improvements to multimodal support, since it aligns with the idea of embedding non-text data within the message structure.

**References:** Autogen’s roadmap notes that image/audio/video support is actively being developed. By encoding audio as a data URI, we follow a pattern similar to images (which Autogen already encodes as data URIs in JSON). This ensures our solution will be forward-compatible and in the spirit of Autogen’s multimodal design.

---

Each of these enhancements uses Autogen’s own facilities (AgentChat classes, message types, etc.) to remain compliant with its JSON messaging format. All messages, whether text, image, or audio, are packaged into the Autogen event model (`BaseChatMessage` or `BaseAgentEvent`) and will be serialized via `model_dump()` to JSON before sending. This means the front-end/AutogenStudio will continue to receive structured JSON it can interpret. By cross-referencing Autogen’s patterns and following its best practices, we ensure these features integrate smoothly without breaking the existing agent workflow or the AutogenStudio compatibility.

**Sources:**

1. Autogen AgentChat documentation – Code execution via code executor agent
2. Autogen AgentChat documentation – MultiModalMessage usage for images
3. Autogen migration guide – JSON format for multimodal messages (text/image parts)
4. Autogen blog – Multi-modal support status (image, audio, video)
