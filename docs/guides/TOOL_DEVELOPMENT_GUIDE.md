# Tool Development Guide

Complete guide to creating custom tools for agents in the Agentic system.

---

## Quick Start

### 1. Create Tool File

**Location:** `backend/tools/my_tool.py`

```python
from autogen_core.tools import FunctionTool
import logging

logger = logging.getLogger(__name__)

def my_tool(required_param: str, optional_param: int = 10) -> dict:
    """
    Brief description visible to LLM.

    Args:
        required_param: Description
        optional_param: Description

    Returns:
        Result dictionary
    """
    try:
        # Tool logic here
        result = do_something(required_param, optional_param)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error in my_tool: {e}")
        return {"error": str(e)}

my_tool_func = FunctionTool(
    func=my_tool,
    name="my_tool",
    description="One-line description for tool selection"
)

# Required: export tools list
tools = [my_tool_func]
```

### 2. Restart Backend

Tools are automatically loaded on backend startup:

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

### 3. Verify Tool Loaded

```bash
curl http://localhost:8000/api/tools
# Should include "my_tool"
```

### 4. Use in Agent

Add to agent's `tools` list:

```json
{
  "name": "MyAgent",
  "tools": ["my_tool", "other_tool"]
}
```

---

## Tool Implementation Patterns

### Basic Tool

```python
from autogen_core.tools import FunctionTool

def calculate_sum(numbers: list[float]) -> dict:
    """Calculate the sum of a list of numbers."""
    try:
        total = sum(numbers)
        return {
            "sum": total,
            "count": len(numbers),
            "average": total / len(numbers) if numbers else 0
        }
    except Exception as e:
        return {"error": str(e)}

calculate_sum_tool = FunctionTool(
    func=calculate_sum,
    name="calculate_sum",
    description="Calculate sum, count, and average of numbers"
)

tools = [calculate_sum_tool]
```

---

### Tool with Agent Context

Access the currently executing agent to modify its state or read configuration.

```python
from autogen_core.tools import FunctionTool
from utils.context import get_current_agent
import logging

logger = logging.getLogger(__name__)

def save_to_memory(content: str) -> str:
    """Save content to agent's memory and update system prompt."""
    try:
        # Get current agent from execution context
        agent = get_current_agent()

        # Save to file
        with open('backend/data/memory/short_term_memory.txt', 'w') as f:
            f.write(content)

        # Update agent's system message
        if agent and agent._system_messages:
            updated_msg = agent._system_messages[0].content.replace(
                "{{SHORT_TERM_MEMORY}}",
                content
            )
            agent._system_messages[0].content = updated_msg
            logger.info(f"Updated agent system message with {len(content)} chars")

        return f"Saved to memory: {len(content)} characters"
    except Exception as e:
        logger.error(f"Error saving to memory: {e}")
        return f"Error: {str(e)}"

save_memory_tool = FunctionTool(
    func=save_to_memory,
    name="save_to_short_term_memory",
    description="Save important information to short-term memory"
)

tools = [save_memory_tool]
```

---

### Tool with External API

```python
from autogen_core.tools import FunctionTool
import requests
import os
import logging

logger = logging.getLogger(__name__)

def search_web(query: str, num_results: int = 5) -> dict:
    """
    Search the web using DuckDuckGo API.

    Args:
        query: Search query
        num_results: Number of results to return

    Returns:
        Dictionary with search results
    """
    try:
        # Call external API
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            },
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("RelatedTopics", [])[:num_results]

        return {
            "query": query,
            "count": len(results),
            "results": [
                {
                    "title": r.get("Text", ""),
                    "url": r.get("FirstURL", "")
                }
                for r in results if "Text" in r
            ]
        }
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"error": f"Search failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": str(e)}

web_search_tool = FunctionTool(
    func=search_web,
    name="web_search",
    description="Search the web for information"
)

tools = [web_search_tool]
```

---

### Tool with File Operations

```python
from autogen_core.tools import FunctionTool
import os
import logging

logger = logging.getLogger(__name__)

# Tool data directory
WORKSPACE_DIR = "backend/data/workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)

def save_file(filename: str, content: str) -> dict:
    """
    Save content to a file in the workspace.

    Args:
        filename: Name of file to save
        content: Content to write

    Returns:
        Status and file info
    """
    try:
        # Validate filename (security)
        if ".." in filename or filename.startswith("/"):
            return {"error": "Invalid filename"}

        filepath = os.path.join(WORKSPACE_DIR, filename)

        # Create parent directories if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Write file
        with open(filepath, 'w') as f:
            f.write(content)

        logger.info(f"Saved file: {filepath}")

        return {
            "status": "success",
            "filename": filename,
            "size": len(content),
            "path": filepath
        }
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return {"error": str(e)}

save_file_tool = FunctionTool(
    func=save_file,
    name="save_file",
    description="Save content to a file in the workspace"
)

tools = [save_file_tool]
```

---

### Tool with Database Access

```python
from autogen_core.tools import FunctionTool
from pymongo import MongoClient
import os
import logging

logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["agentic"]

def find_documents(
    collection: str,
    query: dict,
    limit: int = 10
) -> dict:
    """
    Find documents in MongoDB collection.

    Args:
        collection: Collection name
        query: MongoDB query (e.g., {"name": "John"})
        limit: Maximum results to return

    Returns:
        Found documents
    """
    try:
        coll = db[collection]

        # Execute query
        cursor = coll.find(query).limit(limit)
        documents = list(cursor)

        # Convert ObjectId to string
        for doc in documents:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        return {
            "collection": collection,
            "count": len(documents),
            "documents": documents
        }
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return {"error": str(e)}

find_docs_tool = FunctionTool(
    func=find_documents,
    name="find_documents",
    description="Find documents in MongoDB collection"
)

tools = [find_docs_tool]
```

---

### Tool Returning Images (for Multimodal Agents)

```python
from autogen_core.tools import FunctionTool
from PIL import Image, ImageDraw, ImageFont
import os
import logging

logger = logging.getLogger(__name__)

WORKSPACE_DIR = "backend/data/workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)

def generate_chart(
    title: str,
    values: list[float]
) -> str:
    """
    Generate a simple bar chart image.

    Args:
        title: Chart title
        values: List of values to plot

    Returns:
        Path to generated image file
    """
    try:
        # Create image
        width, height = 800, 600
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # Draw title
        draw.text((20, 20), title, fill='black')

        # Draw bars
        bar_width = width // (len(values) + 1)
        max_value = max(values) if values else 1

        for i, value in enumerate(values):
            bar_height = int((value / max_value) * (height - 100))
            x = (i + 1) * bar_width
            y = height - 50 - bar_height
            draw.rectangle(
                [x - 20, y, x + 20, height - 50],
                fill='blue'
            )

        # Save image
        filename = f"chart_{title.replace(' ', '_')}.png"
        filepath = os.path.join(WORKSPACE_DIR, filename)
        img.save(filepath)

        logger.info(f"Generated chart: {filepath}")

        # Return path (multimodal agent will automatically detect and display)
        return f"Chart saved to {filepath}"

    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return f"Error: {str(e)}"

generate_chart_tool = FunctionTool(
    func=generate_chart,
    name="generate_chart",
    description="Generate a bar chart image from values"
)

tools = [generate_chart_tool]
```

**For multimodal agents**, return value containing image path or base64 data. Agent automatically detects and converts to MultiModalMessage.

---

## Tool Data Storage

### Best Practice: One Directory Per Tool

Create tool-specific data directories in `backend/data/`:

```python
import os

# Tool-specific data directory
TOOL_DATA_DIR = "backend/data/my_tool"
os.makedirs(TOOL_DATA_DIR, exist_ok=True)

# Subdirectories
CACHE_DIR = os.path.join(TOOL_DATA_DIR, "cache")
CONFIG_DIR = os.path.join(TOOL_DATA_DIR, "config")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)
```

### Current Data Directories

- `data/memory/` - Memory tool (ChromaDB, memory banks, short-term memory)
- `data/api/` - API tool (documentation, API registry)
- `data/database/` - Database tool (MongoDB schema tracking)
- `data/workspace/` - FileManager workspace (agent-created files)

---

## Type Hints and Validation

### Use Type Hints

```python
from typing import Optional, List, Dict, Union

def my_tool(
    required: str,
    optional: Optional[int] = None,
    items: List[str] = [],
    config: Dict[str, any] = {}
) -> Union[Dict, str]:
    """Tool with proper type hints"""
    pass
```

### Pydantic Models (Advanced)

For complex validation:

```python
from pydantic import BaseModel, Field, validator

class SearchInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=100)

    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v

def web_search(query: str, limit: int = 10) -> dict:
    """Search with validation"""
    # Pydantic validates inputs automatically
    input_data = SearchInput(query=query, limit=limit)
    # ...
```

---

## Error Handling Best Practices

### 1. Always Return Dicts with Error Key

```python
def my_tool(param: str) -> dict:
    try:
        result = do_something(param)
        return {"status": "success", "result": result}
    except SpecificError as e:
        logger.warning(f"Specific error: {e}")
        return {"error": f"Specific issue: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": str(e)}
```

### 2. Use Logging

```python
import logging

logger = logging.getLogger(__name__)

def my_tool(param: str) -> dict:
    logger.info(f"Tool called with param: {param}")
    try:
        # ...
        logger.debug(f"Intermediate result: {result}")
        return {"result": result}
    except Exception as e:
        logger.error(f"Tool failed: {e}", exc_info=True)
        return {"error": str(e)}
```

### 3. Provide Helpful Error Messages

```python
# Bad
return {"error": "Failed"}

# Good
return {"error": "API request failed: Connection timeout after 10s"}
```

---

## Performance Optimization

### 1. Use Caching for Expensive Operations

```python
import functools
from typing import Dict

@functools.lru_cache(maxsize=128)
def expensive_operation(param: str) -> str:
    """Cached expensive operation"""
    # Expensive computation
    return result

def my_tool(param: str) -> dict:
    result = expensive_operation(param)
    return {"result": result}
```

### 2. Implement Timeouts

```python
import requests

def fetch_url(url: str) -> dict:
    try:
        response = requests.get(url, timeout=10)  # 10 second timeout
        return {"content": response.text}
    except requests.Timeout:
        return {"error": "Request timed out"}
```

### 3. Limit Resource Usage

```python
def process_large_file(filename: str, max_size_mb: int = 10) -> dict:
    try:
        file_size = os.path.getsize(filename)
        max_size = max_size_mb * 1024 * 1024

        if file_size > max_size:
            return {"error": f"File too large: {file_size / 1024 / 1024:.1f}MB > {max_size_mb}MB"}

        # Process file
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}
```

---

## Testing Tools

### Unit Tests

Create test file in `backend/tests/unit/test_my_tool.py`:

```python
import pytest
from tools.my_tool import my_tool

def test_my_tool_success():
    result = my_tool("valid input")
    assert result["status"] == "success"
    assert "result" in result

def test_my_tool_error():
    result = my_tool("invalid")
    assert "error" in result

def test_my_tool_validation():
    result = my_tool("")
    assert "error" in result
```

Run tests:

```bash
cd backend
source venv/bin/activate
pytest tests/unit/test_my_tool.py -v
```

### Integration Tests

Test with actual agent:

```python
# backend/tests/integration/test_my_tool_integration.py

import pytest
from config.config_loader import load_agent_config
from core.agent_factory import create_agent_from_config

def test_tool_with_agent():
    # Load agent config
    config = load_agent_config("TestAgent")

    # Create agent
    agent = create_agent_from_config(config, ["my_tool"])

    # Test agent can use tool
    # ...
```

---

## Documentation

### Docstring Format

```python
def my_tool(param1: str, param2: int = 10) -> dict:
    """
    One-line summary (shown to LLM for tool selection).

    Detailed explanation of what the tool does and when to use it.
    This helps agents understand the tool's purpose.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter (default: 10)

    Returns:
        Dictionary with:
            - result: The computation result
            - metadata: Additional information
            - error: Error message if failed

    Example:
        >>> my_tool("example", 20)
        {"result": "processed", "metadata": {...}}

    Note:
        Additional notes about usage, limitations, or edge cases.
    """
    pass
```

### Tool Description

The `description` parameter in `FunctionTool` is what agents see when selecting tools:

```python
# Too vague
description="Process data"

# Good
description="Process CSV data: parse, validate, and transform rows"

# Best
description="Process CSV data by parsing file, validating columns against schema, transforming rows using rules, and returning summary statistics"
```

---

## Security Considerations

### 1. Validate File Paths

```python
import os

def is_safe_path(basedir: str, path: str) -> bool:
    """Check if path is within basedir (prevent directory traversal)"""
    abs_basedir = os.path.abspath(basedir)
    abs_path = os.path.abspath(os.path.join(basedir, path))
    return abs_path.startswith(abs_basedir)

def read_file(filename: str) -> dict:
    workspace = "backend/data/workspace"

    if not is_safe_path(workspace, filename):
        return {"error": "Invalid file path"}

    # Safe to read
    filepath = os.path.join(workspace, filename)
    # ...
```

### 2. Sanitize User Input

```python
import re

def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from filename"""
    # Remove path separators and special chars
    safe = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    return safe

def save_file(filename: str, content: str) -> dict:
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return {"error": "Invalid filename"}
    # ...
```

### 3. Limit Resource Access

```python
# Only allow specific domains
ALLOWED_DOMAINS = ["api.example.com", "data.example.org"]

def fetch_api(url: str) -> dict:
    from urllib.parse import urlparse

    domain = urlparse(url).netloc
    if domain not in ALLOWED_DOMAINS:
        return {"error": f"Domain not allowed: {domain}"}

    # Fetch from allowed domain
    # ...
```

---

## Common Patterns

### Stateful Tool with Initialization

```python
class ToolState:
    """Shared state across tool calls"""
    def __init__(self):
        self.cache = {}
        self.connection = None

state = ToolState()

def initialize_connection() -> dict:
    """Initialize database connection (called once)"""
    if state.connection is None:
        state.connection = connect_to_database()
    return {"status": "connected"}

def query_database(sql: str) -> dict:
    """Query database (uses shared connection)"""
    if state.connection is None:
        return {"error": "Not initialized. Call initialize_connection first"}

    result = state.connection.execute(sql)
    return {"rows": result.fetchall()}

tools = [
    FunctionTool(initialize_connection, "initialize_connection", "Connect to database"),
    FunctionTool(query_database, "query_database", "Execute SQL query")
]
```

### Tool Chain Pattern

```python
# Tools that work together in sequence

def search_products(query: str) -> dict:
    """Step 1: Search for products"""
    results = do_search(query)
    return {"product_ids": [r["id"] for r in results]}

def get_product_details(product_ids: list[str]) -> dict:
    """Step 2: Get details for found products"""
    details = [fetch_product(pid) for pid in product_ids]
    return {"products": details}

def compare_products(products: list[dict]) -> dict:
    """Step 3: Compare products and recommend"""
    comparison = analyze_products(products)
    return {"recommendation": comparison["best"], "analysis": comparison}

tools = [
    FunctionTool(search_products, "search_products", "Search product catalog"),
    FunctionTool(get_product_details, "get_product_details", "Get product details"),
    FunctionTool(compare_products, "compare_products", "Compare and recommend products")
]
```

---

## See Also

- [AGENT_DEVELOPMENT_GUIDE.md](AGENT_DEVELOPMENT_GUIDE.md) - Creating agents
- [MULTIMODAL_AGENT_GUIDE.md](MULTIMODAL_AGENT_GUIDE.md) - Vision tools for multimodal agents
- [DATABASE_AGENT_GUIDE.md](DATABASE_AGENT_GUIDE.md) - Database tools example
- [API_AGENT_GUIDE.md](API_AGENT_GUIDE.md) - API tools example
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - System architecture

---

**Last Updated:** 2025-12-01
