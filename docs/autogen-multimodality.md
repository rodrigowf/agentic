Here’s the shortest path I’ve found to plug **base-64 images (and audio) straight into AutoGen 0.5.5** and have the *same* snippet work with either **GPT-4o** or **Gemini 2.5 Pro**. The new `MultiModalMessage` plus the “OpenAI-compatible” model client makes the trick almost friction-less.

## TL;DR (60 s)

1. **Install**

   ```bash
   pip install -U "autogen-agentchat[openai,gemini]"~=0.5.5
   ```

2. **Create one model-client per provider**

   ```python
   from autogen_ext.models.openai import OpenAIChatCompletionClient
   openai_client = OpenAIChatCompletionClient(model="gpt-4o-mini",
                                              api_key=os.getenv("OPENAI_API_KEY"))

   gemini_client = OpenAIChatCompletionClient(model="gemini-2.5-pro",
                                              api_key=os.getenv("GEMINI_API_KEY"),
                                              base_url="https://generativelanguage.googleapis.com/v1beta")  # Vertex or §
   ```

   The same class works because AutoGen treats “models with OpenAI-API compatibility (e.g., Gemini)” identically ([Microsoft GitHub][1]).

3. **Wrap any file as a `data:` URL**

   ```python
   import base64, mimetypes, pathlib
   def to_data_url(path):
       mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
       b64  = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
       return f"data:{mime};base64,{b64}"
   ```

4. **Send a `MultiModalMessage`**

   ```python
   from autogen_agentchat.messages import MultiModalMessage
   data_url = to_data_url("cat.png")               # works for .wav too
   msg = MultiModalMessage(
          content=["What’s in this picture?", data_url],
          source="user")

   # pick the model you want at runtime
   assistant = AssistantAgent("vision", model_client=openai_client)
   print(await assistant.run(task=[msg]).content)
   ```

That’s enough for GPT-4o *and* Gemini: AutoGen converts the data-URI back into the provider-specific JSON behind the scenes ([Microsoft GitHub][2], [Microsoft GitHub][3]).

---

## 1 | Why `MultiModalMessage` is your friend

* `MultiModalMessage` was added in 0.5.x and accepts a **list of strings *or* `Image` objects** ([Microsoft GitHub][2]).
* When you hand it a string starting with `data:<mime>;base64,` it just passes that straight through; when you hand it a `PIL.Image` or `autogen_core.Image`, it serialises for you.
* If you later call `to_model_text(image_placeholder=None)` it will spit the raw base-64 back out (handy for tool debugging) ([Microsoft GitHub][4]).

### Minimal pattern

```python
msg = MultiModalMessage(
        content=[
          "Summarise the lecture:", 
          to_data_url("lecture.wav")   # 48 kHz WAV or Opus for GPT-4o realtime
        ],
        source="user")
```

AutoGen handles MIME sniffing for Gemini (which insists on the correct `audio/*` type) and image tokenisation for GPT-4o automatically.

---

## 2 | Model-client setup cheatsheet

| Provider                              | Client class                          | Key env var      | Extra kwargs                                                  |
| ------------------------------------- | ------------------------------------- | ---------------- | ------------------------------------------------------------- |
| **OpenAI GPT-4o**                     | `OpenAIChatCompletionClient`          | `OPENAI_API_KEY` | none                                                          |
| **OpenAI Realtime** (speech ↔ speech) | `OpenAIRealtimeClient` (experimental) | `OPENAI_API_KEY` | `model="gpt-4o-realtime-preview"` ([docs.ag2.ai][5])          |
| **Gemini 2.5 Pro**                    | `OpenAIChatCompletionClient`          | `GEMINI_API_KEY` | `base_url="https://generativelanguage.googleapis.com/v1beta"` |

A single agent can swap the `model_client` at runtime, so you keep the same `MultiModalMessage` logic.

---

## 3 | What works with each model today

| Modality                               | GPT-4o Chat          | GPT-4o Realtime (WS)                                | Gemini 2.5 Pro                                   |
| -------------------------------------- | -------------------- | --------------------------------------------------- | ------------------------------------------------ |
| **Image IN** (`data:image/*;base64,…`) | ✅ (≤10 / req)        | —                                                   | ✅ (≤3 000 / req, <7 MB each) ([Google Cloud][6]) |
| **Audio IN** (`data:audio/*;base64,…`) | ⚠️ Only via Realtime | ✅ stream                                            | ✅ (<8.4 h) ([Google Cloud][6])                   |
| **Image OUT**                          | ✅ (`gpt-image-1`)    | —                                                   | ❌ (text only)                                    |
| **Audio OUT**                          | ✅ (text ↔ speech)    | ✅ speech stream ([OpenAI Platform][7], [OpenAI][8]) | ✅ via Live API                                   |

So for *images* you can stay with Chat completions; for *audio* you’ll usually swap to the Realtime client on GPT-4o or stick with Gemini’s Live API.

---

## 4 | Base-64 helper utilities

```python
def encode_file(path: str) -> str:
    """Return a data-URI for <path> suitable for MultiModalMessage."""
    import base64, mimetypes, pathlib
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    data = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
    return f"data:{mime};base64,{data}"
```

AutoGen will automatically count the tokens (image-pixels or audio-bytes) when the message is converted for the model ([Microsoft GitHub][9]).

---

## 5 | Realtime audio in AutoGen (GPT-4o)

```python
from autogen.agentchat.realtime.experimental.clients.oai import OpenAIRealtimeClient
rt = OpenAIRealtimeClient(model="gpt-4o-realtime-preview",
                          api_key=os.getenv("OPENAI_API_KEY"))
await rt.connect()
await rt.session_update({"modalities": ["text","audio"]})
await rt.send_audio(open("mic_chunk.opus","rb").read())
```

The client wraps the WebSocket protocol announced in the official Realtime docs ([OpenAI Platform][7], [OpenAI][8]) and is available in 0.5.5 under the `experimental` namespace ([docs.ag2.ai][5]). Gemini’s Live API follows the same pattern but is not yet wrapped; you can create a thin subclass if needed.

---

## 6 | Switching models on the fly

```python
async def ask(message, provider="openai"):
    agent.model_client = openai_client if provider=="openai" else gemini_client
    return (await agent.run(task=[message])).content
```

Because both clients conform to `ChatCompletionClient`, the rest of your AutoGen code—including function-calling loops—doesn’t change.

---

### Gotchas & tips

* **Resize before encoding**—vision cost scales with pixel count; down-sample to 512 px max side for “describe” tasks.
* **Gemini quota** counts **bytes**, not tokens; big base-64 audio blobs may hit limit first.
* When debugging, call `msg.to_model_text(image_placeholder=None)` to verify the exact base-64 string AutoGen will send ([Microsoft GitHub][3]).
* GPT-4o Realtime imposes \~30 s continuous-speech limit; chunk or flush periodically ([Microsoft Learn][10]).
* Set `OPENAI_API_BASE_URL` or `AUTOGEN_OPENAI_API_BASE` env vars if you route through a proxy such as *Together* or *Fireworks*.

With these pieces you can juggle images + audio between the two flagship multimodal LLMs without rewriting your agent code—just point AutoGen at a different model client. Happy coding!

[1]: https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/components/model-clients.html?utm_source=chatgpt.com "Model Clients — AutoGen - Microsoft Open Source"
[2]: https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/tutorial/messages.html "Messages — AutoGen"
[3]: https://microsoft.github.io/autogen/dev//_modules/autogen_agentchat/messages.html?utm_source=chatgpt.com "autogen_agentchat.messages — AutoGen - Microsoft Open Source"
[4]: https://microsoft.github.io/autogen/stable//reference/python/autogen_agentchat.messages.html?utm_source=chatgpt.com "autogen_agentchat.messages — AutoGen - Microsoft Open Source"
[5]: https://docs.ag2.ai/latest/docs/api-reference/autogen/agentchat/realtime/experimental/clients/OpenAIRealtimeClient/?utm_source=chatgpt.com "OpenAIRealtimeClient - AG2"
[6]: https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-pro?utm_source=chatgpt.com "Gemini 2.5 Pro | Generative AI on Vertex AI - Google Cloud"
[7]: https://platform.openai.com/docs/guides/realtime?utm_source=chatgpt.com "Realtime API - OpenAI Platform"
[8]: https://openai.com/index/introducing-the-realtime-api/?utm_source=chatgpt.com "Introducing the Realtime API - OpenAI"
[9]: https://microsoft.github.io/autogen/stable/reference/python/autogen_core.tools.html?utm_source=chatgpt.com "autogen_core.tools — AutoGen - Microsoft Open Source"
[10]: https://learn.microsoft.com/en-us/azure/ai-services/openai/whats-new?utm_source=chatgpt.com "What's new in Azure OpenAI Service? - Learn Microsoft"
