"""
API interaction tools for HTTP requests and documentation management.

This module provides tools for:
1. Making HTTP requests (GET, POST, PUT, DELETE, PATCH)
2. Storing and managing API documentation
3. Maintaining an index of API documentation

API documentation is stored in backend/api_docs/ with an index file.
"""

import requests
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from autogen_core.tools import FunctionTool
import logging

logger = logging.getLogger(__name__)

# API documentation directory
API_DOCS_DIR = Path("/home/rodrigo/agentic/backend/api_docs")
API_INDEX_FILE = API_DOCS_DIR / "api_index.json"

# Ensure directory exists
API_DOCS_DIR.mkdir(exist_ok=True)

# Initialize index file if it doesn't exist
if not API_INDEX_FILE.exists():
    with open(API_INDEX_FILE, 'w') as f:
        json.dump({"apis": {}}, f, indent=2)


def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> str:
    """
    Make an HTTP request to any URL.

    Supports GET, POST, PUT, DELETE, PATCH methods.
    Can include headers, query parameters, and request body.

    Args:
        url: The full URL to request
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        headers: Optional dictionary of HTTP headers (e.g., {"Authorization": "Bearer token"})
        params: Optional dictionary of query parameters
        body: Optional dictionary for request body (will be JSON encoded)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        String containing response status, headers, and body

    Examples:
        # Simple GET request
        http_request("https://api.github.com/users/octocat")

        # POST with auth header and body
        http_request(
            "https://api.example.com/data",
            method="POST",
            headers={"Authorization": "Bearer abc123"},
            body={"key": "value"}
        )

        # GET with query parameters
        http_request(
            "https://api.example.com/search",
            params={"q": "query", "limit": 10}
        )
    """
    try:
        method = method.upper()

        # Prepare request kwargs
        request_kwargs = {
            "timeout": timeout,
            "headers": headers or {},
            "params": params or {}
        }

        # Add body for methods that support it
        if method in ["POST", "PUT", "PATCH"] and body:
            request_kwargs["json"] = body

        # Make request
        logger.info(f"Making {method} request to {url}")
        response = requests.request(method, url, **request_kwargs)

        # Format response
        result = f"HTTP {response.status_code} {response.reason}\n\n"
        result += "Headers:\n"
        for key, value in response.headers.items():
            result += f"  {key}: {value}\n"

        result += f"\nBody ({len(response.content)} bytes):\n"

        # Try to parse as JSON for pretty printing
        try:
            json_body = response.json()
            result += json.dumps(json_body, indent=2)
        except:
            # Fall back to text
            result += response.text[:5000]  # Limit to 5000 chars
            if len(response.text) > 5000:
                result += f"\n... (truncated, total {len(response.text)} chars)"

        return result

    except requests.exceptions.Timeout:
        return f"Error: Request timed out after {timeout} seconds"
    except requests.exceptions.ConnectionError as e:
        return f"Error: Connection failed - {str(e)}"
    except Exception as e:
        logger.error(f"Error in http_request: {e}")
        return f"Error: {str(e)}"


def save_api_docs(api_name: str, content: str, description: str) -> str:
    """
    Save API documentation to a markdown file and update the index.

    Documentation is stored in backend/api_docs/{api_name}.md
    The index file (api_index.json) is automatically updated with references.

    Args:
        api_name: Name/identifier for the API (will be filename, use lowercase with underscores)
        content: The documentation content (markdown format recommended)
        description: Short description of what this API does (for the index)

    Returns:
        Success message with file path

    Examples:
        save_api_docs(
            "github_api",
            "# GitHub API\\n\\n## Authentication\\n...",
            "GitHub REST API v3 documentation for user and repo operations"
        )
    """
    try:
        # Sanitize api_name for filename
        safe_name = api_name.lower().replace(" ", "_").replace("/", "_")
        doc_file = API_DOCS_DIR / f"{safe_name}.md"

        # Save documentation content
        with open(doc_file, 'w') as f:
            f.write(content)

        # Update index
        with open(API_INDEX_FILE, 'r') as f:
            index = json.load(f)

        index["apis"][safe_name] = {
            "file": f"{safe_name}.md",
            "description": description,
            "path": str(doc_file)
        }

        with open(API_INDEX_FILE, 'w') as f:
            json.dump(index, f, indent=2)

        logger.info(f"Saved API docs: {safe_name}")
        return f"API documentation saved to {doc_file}\nIndex updated with: {description}"

    except Exception as e:
        logger.error(f"Error in save_api_docs: {e}")
        return f"Error: {str(e)}"


def get_api_index() -> str:
    """
    Get the complete API documentation index.

    Returns a formatted list of all stored API documentation
    with descriptions and file paths.

    Returns:
        Formatted string with all API documentation references
    """
    try:
        with open(API_INDEX_FILE, 'r') as f:
            index = json.load(f)

        if not index.get("apis"):
            return "No API documentation stored yet."

        result = "API Documentation Index:\n\n"
        for api_name, info in index["apis"].items():
            result += f"- **{api_name}**: {info['description']}\n"
            result += f"  File: {info['file']}\n"
            result += f"  Path: {info['path']}\n\n"

        return result

    except Exception as e:
        logger.error(f"Error in get_api_index: {e}")
        return f"Error: {str(e)}"


def read_api_docs(api_name: str) -> str:
    """
    Read stored API documentation by name.

    Args:
        api_name: Name of the API (as stored in the index)

    Returns:
        The full documentation content
    """
    try:
        safe_name = api_name.lower().replace(" ", "_").replace("/", "_")
        doc_file = API_DOCS_DIR / f"{safe_name}.md"

        if not doc_file.exists():
            return f"Error: No documentation found for '{api_name}'. Use get_api_index() to see available docs."

        with open(doc_file, 'r') as f:
            content = f.read()

        return content

    except Exception as e:
        logger.error(f"Error in read_api_docs: {e}")
        return f"Error: {str(e)}"


def delete_api_docs(api_name: str) -> str:
    """
    Delete API documentation and remove from index.

    Args:
        api_name: Name of the API to delete

    Returns:
        Success or error message
    """
    try:
        safe_name = api_name.lower().replace(" ", "_").replace("/", "_")
        doc_file = API_DOCS_DIR / f"{safe_name}.md"

        # Remove file
        if doc_file.exists():
            doc_file.unlink()

        # Update index
        with open(API_INDEX_FILE, 'r') as f:
            index = json.load(f)

        if safe_name in index["apis"]:
            del index["apis"][safe_name]

        with open(API_INDEX_FILE, 'w') as f:
            json.dump(index, f, indent=2)

        logger.info(f"Deleted API docs: {safe_name}")
        return f"API documentation for '{api_name}' has been deleted."

    except Exception as e:
        logger.error(f"Error in delete_api_docs: {e}")
        return f"Error: {str(e)}"


# Create FunctionTool instances
http_request_tool = FunctionTool(
    func=http_request,
    name="http_request",
    description="Make HTTP requests (GET, POST, PUT, DELETE, PATCH) to any API endpoint with headers, params, and body"
)

save_api_docs_tool = FunctionTool(
    func=save_api_docs,
    name="save_api_docs",
    description="Save API documentation to a markdown file and update the index for future reference"
)

get_api_index_tool = FunctionTool(
    func=get_api_index,
    name="get_api_index",
    description="Get a list of all stored API documentation with descriptions and file paths"
)

read_api_docs_tool = FunctionTool(
    func=read_api_docs,
    name="read_api_docs",
    description="Read stored API documentation by name"
)

delete_api_docs_tool = FunctionTool(
    func=delete_api_docs,
    name="delete_api_docs",
    description="Delete API documentation and remove from index"
)

def initialize_api_manager():
    """
    Initialize the APIManager agent by injecting the API documentation index
    into its system prompt.

    This function is called automatically when the APIManager agent starts.
    It replaces the {{API_DOCS_INDEX}} placeholder with the current API index.
    """
    from utils.context import get_current_agent

    try:
        agent = get_current_agent()

        # Get current API index
        api_index = get_api_index()

        # Update agent's system message
        if agent and agent._system_messages:
            original = agent._system_messages[0].content
            updated = original.replace("{{API_DOCS_INDEX}}", api_index)
            agent._system_messages[0].content = updated
            logger.info("APIManager initialized with API documentation index")
            return "APIManager initialized successfully"
        else:
            logger.warning("No agent found in context for initialization")
            return "Warning: No agent in context"

    except Exception as e:
        logger.error(f"Error initializing APIManager: {e}")
        return f"Error: {str(e)}"


# Export tools
tools = [
    http_request_tool,
    save_api_docs_tool,
    get_api_index_tool,
    read_api_docs_tool,
    delete_api_docs_tool
]
