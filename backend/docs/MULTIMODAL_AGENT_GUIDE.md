# Multimodal Tools Looping Agent Guide

## Overview

The **MultimodalToolsLoopingAgent** is an advanced agent type that can automatically interpret images and audio returned by tools using the multimodal capabilities of LLMs like GPT-4 Vision (GPT-4o, GPT-4o-mini, etc.).

### Key Features

- **Automatic Image Detection**: Detects images in tool responses (file paths, base64 encoded)
- **Multimodal Message Creation**: Converts detected images to `MultiModalMessage` objects
- **Vision-Enabled Analysis**: LLM can directly "see" and analyze images from tool outputs
- **Seamless Integration**: Works like a regular looping agent but with vision capabilities
- **Robust Error Handling**: Gracefully handles missing files, corrupted data, etc.

---

## How It Works

### 1. Tool Returns Image Reference

When a tool returns text containing an image reference:

```python
def take_screenshot():
    """Take a screenshot and save it."""
    screenshot_path = "/workspace/screenshot.png"
    # ... save screenshot ...
    return f"Screenshot saved to {screenshot_path}"
```

### 2. Agent Detects Image

The agent automatically detects image references using pattern matching:

- **File paths**: `/path/to/image.png`, `./workspace/chart.jpg`
- **Base64 encoded**: `data:image/png;base64,iVBORw0KGgo...`

### 3. Agent Creates MultiModalMessage

The agent converts the text + image to a `MultiModalMessage`:

```python
MultiModalMessage(
    content=[
        "Screenshot saved to /workspace/screenshot.png",  # Original text
        AGImage.from_file("/workspace/screenshot.png")    # Image object
    ],
    source="tools"
)
```

### 4. LLM Sees the Image

The LLM receives the image directly and can:
- Describe what's in the image
- Answer questions about the image
- Extract text from the image
- Analyze charts, diagrams, photos, etc.

---

## Supported Image Formats

### File Extensions
- `.png`
- `.jpg` / `.jpeg`
- `.gif`
- `.bmp`
- `.webp`

### Input Methods
1. **File Path**: `/home/user/image.png`
2. **Relative Path**: `./workspace/chart.jpg`
3. **Base64 Data URI**: `data:image/png;base64,...`

---

## Usage

### Agent Configuration

Create a JSON configuration file in `/backend/agents/`:

```json
{
  "name": "MyVisionAgent",
  "agent_type": "multimodal_tools_looping",
  "tools": [
    "take_screenshot",
    "generate_test_image",
    "get_sample_image"
  ],
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.0,
    "max_tokens": null
  },
  "prompt": {
    "system": "You are a helpful assistant with vision. Use tools to get images and describe what you see. Say TERMINATE when done.",
    "user": "Take a screenshot and tell me what you see."
  },
  "max_consecutive_auto_reply": 15,
  "reflect_on_tool_use": true
}
```

### Key Configuration Fields

- **agent_type**: Must be `"multimodal_tools_looping"`
- **model**: Must support vision (e.g., `gpt-4o`, `gpt-4o-mini`)
- **tools**: List of tools that may return images
- **max_consecutive_auto_reply**: Safety limit for iteration count

---

## Creating Vision-Compatible Tools

### Example 1: Screenshot Tool

```python
from autogen_core.tools import FunctionTool
from pathlib import Path

def take_screenshot(description: str) -> str:
    """Take a screenshot of the current screen."""
    # Use pyautogui, playwright, etc.
    screenshot_path = Path("workspace/screenshot.png")
    # ... capture screenshot ...

    return f"Screenshot saved to {screenshot_path}"

screenshot_tool = FunctionTool(
    func=take_screenshot,
    name="take_screenshot",
    description="Take a screenshot and save it to a file"
)
```

### Example 2: Chart Generator

```python
from PIL import Image, ImageDraw
from autogen_core.tools import FunctionTool

def generate_bar_chart(data: list[int]) -> str:
    """Generate a bar chart from data."""
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)

    # Draw bars
    for i, value in enumerate(data):
        x = 50 + i * 80
        y = 250 - value
        draw.rectangle([x, y, x + 60, 250], fill='blue')

    chart_path = Path("workspace/chart.png")
    img.save(chart_path)

    return f"Chart saved to {chart_path}"

chart_tool = FunctionTool(
    func=generate_bar_chart,
    name="generate_bar_chart",
    description="Generate a bar chart image from numeric data"
)
```

### Example 3: Base64 Image Tool

```python
import base64
from io import BytesIO
from PIL import Image

def get_base64_image() -> str:
    """Get an image as base64."""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return f"Image data: data:image/png;base64,{b64_data}"
```

---

## API Integration

### Running via WebSocket

```python
import asyncio
from config.config_loader import load_agent_config, load_tools
from core.agent_factory import create_agent_from_config

async def run_vision_agent():
    # Load agent config
    agent_cfg = load_agent_config("MyVisionAgent")

    # Load tools
    all_tools = load_tools()

    # Create model client
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
        api_key="your-api-key"
    )

    # Create agent
    agent = create_agent_from_config(agent_cfg, all_tools, model_client)

    # Run
    async for event in agent.run_stream("Take a screenshot and describe it"):
        print(event)

asyncio.run(run_vision_agent())
```

### Event Types

You'll receive these event types:

```python
# Tool call
{
    "type": "ToolCallRequestEvent",
    "data": {"name": "take_screenshot", ...}
}

# Tool result with image (MultiModalMessage)
{
    "type": "MultiModalMessage",
    "content": ["Screenshot saved to...", <Image>],
    "source": "tools"
}

# Assistant response (after seeing image)
{
    "type": "TextMessage",
    "content": "I can see a desktop with...",
    "source": "MyVisionAgent"
}
```

---

## Testing

### Unit Tests

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
pytest tests/test_multimodal_agent_e2e.py -v
```

### Integration Test

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
python3 test_multimodal_integration.py
```

---

## Architecture

### Class Hierarchy

```
BaseChatAgent
    └── AssistantAgent
            └── LoopingAssistantAgent
                    └── MultimodalToolsLoopingAgent
```

### Key Methods

#### `_detect_and_convert_images(content: str) -> List[AGImage]`
Scans text for image references and converts them to `AGImage` objects.

#### `_create_multimodal_message_from_tool_result(content: str) -> BaseChatMessage`
Creates `MultiModalMessage` if images found, otherwise `TextMessage`.

#### `run_stream(task: str) -> AsyncIterator`
Main execution loop that handles tool calls and multimodal message creation.

---

## Comparison with Regular Looping Agent

| Feature | LoopingAssistantAgent | MultimodalToolsLoopingAgent |
|---------|----------------------|----------------------------|
| Tool calling | ✓ | ✓ |
| Text responses | ✓ | ✓ |
| Image interpretation | ✗ | ✓ |
| Base64 image handling | ✗ | ✓ |
| Automatic image detection | ✗ | ✓ |
| MultiModalMessage support | ✗ | ✓ |

---

## Best Practices

### 1. Use Vision-Capable Models

Always use models that support vision:
- ✓ `gpt-4o`
- ✓ `gpt-4o-mini`
- ✗ `gpt-3.5-turbo` (no vision)
- ✗ `gpt-4-turbo` (older, limited vision)

### 2. Clear System Prompts

Guide the agent to use tools and describe images:

```json
{
  "system": "You are a vision-capable assistant. When you use tools that return images, describe what you see in detail. Always say TERMINATE when done."
}
```

### 3. Tool Return Format

Ensure tools return clear image references:

```python
# ✓ Good
return f"Screenshot saved to {path}"

# ✓ Also good
return f"Image: {path}"

# ✗ Bad (unclear)
return "Done!"
```

### 4. Error Handling

The agent gracefully handles:
- Missing files
- Corrupted base64 data
- Invalid paths
- Non-image files

### 5. Workspace Organization

Keep images in a dedicated workspace:

```python
workspace = Path("workspace") / "images"
workspace.mkdir(parents=True, exist_ok=True)
```

---

## Limitations

1. **Image Size**: Very large images may hit token limits
2. **Audio**: Audio support is experimental (not fully documented in AutoGen)
3. **Video**: Video is not yet supported (would need frame extraction)
4. **Model Requirement**: Requires vision-capable models (GPT-4o, etc.)

---

## Troubleshooting

### Issue: Images not detected

**Solution**: Check that tool returns contain valid file paths or base64:

```python
# Debug: Print tool result
print(f"Tool result: {result}")

# Check pattern match
import re
pattern = r'(?:^|[\s\'\"])((?:[\/~])?(?:[\w\-\.]+\/)*[\w\-\.]+\.(?:png|jpg|jpeg|gif|bmp|webp))'
matches = re.findall(pattern, result, re.IGNORECASE | re.MULTILINE)
print(f"Matches: {matches}")
```

### Issue: PIL import error

**Solution**: Install Pillow:

```bash
pip install Pillow
```

### Issue: Agent doesn't describe image

**Solution**:
1. Verify model supports vision (`gpt-4o` or similar)
2. Check system prompt guides agent to describe images
3. Verify image is valid (check file exists)

### Issue: MultiModalMessage not in events

**Solution**: Verify image was detected:

```python
# Check agent logs
import logging
logging.basicConfig(level=logging.INFO)
```

---

## Example Workflows

### 1. Screenshot Analysis

```json
{
  "system": "Use the screenshot tool and describe what applications are open, what's on the screen, etc."
}
```

Task: "Take a screenshot and tell me what's on my desktop"

### 2. Chart Interpretation

```json
{
  "system": "Generate charts from data and analyze them to extract insights."
}
```

Task: "Create a bar chart showing Q1: 100, Q2: 150, Q3: 120, Q4: 180, then tell me which quarter had the highest sales"

### 3. Image Comparison

```json
{
  "system": "Generate multiple images and compare them."
}
```

Task: "Create three sample images (red, green, blue) and tell me what colors you see"

---

## Future Enhancements

Potential improvements for future versions:

1. **Audio Support**: Full audio file interpretation
2. **Video Support**: Extract frames and analyze video content
3. **OCR Integration**: Extract text from images more reliably
4. **Image Caching**: Cache images to reduce re-processing
5. **URL Image Support**: Download and process images from URLs
6. **Image Format Conversion**: Auto-convert unsupported formats

---

## References

- [AutoGen AgentChat Documentation](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/)
- [AutoGen Multimodal Messages](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/messages.html)
- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision)

---

**Last Updated**: 2025-10-11
**Agent Type**: `multimodal_tools_looping`
**File**: `/backend/core/multimodal_tools_looping_agent.py`
