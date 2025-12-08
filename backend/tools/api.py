"""
API tools for HTTP requests and documentation management.

This module provides tools for:
1. Making HTTP requests (GET, POST, PUT, DELETE, PATCH)
2. Registering and managing API documentation
3. Maintaining an index of API documentation

API documentation is stored in data/api/docs/ with an index file.
"""

import requests
import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from autogen_core.tools import FunctionTool

logger = logging.getLogger(__name__)

# Configuration - use data/api for all API-related storage
API_DATA_DIR = Path("/home/rodrigo/agentic/backend/data/api")
API_DOCS_DIR = API_DATA_DIR / "docs"
API_INDEX_FILE = API_DATA_DIR / "api_index.json"

# Ensure directories exist
API_DATA_DIR.mkdir(parents=True, exist_ok=True)
API_DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize index file if it doesn't exist
if not API_INDEX_FILE.exists():
    with open(API_INDEX_FILE, 'w') as f:
        json.dump({}, f, indent=2)


def _load_api_index() -> Dict[str, Dict]:
    """Load API index from disk."""
    if API_INDEX_FILE.exists():
        try:
            with open(API_INDEX_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading API index: {e}")
            return {}
    return {}


def _save_api_index(index: Dict[str, Dict]):
    """Save API index to disk."""
    try:
        with open(API_INDEX_FILE, 'w') as f:
            json.dump(index, f, indent=2)
        logger.info(f"Saved API index with {len(index)} APIs")
    except Exception as e:
        logger.error(f"Error saving API index: {e}")


def _get_api_index_summary() -> str:
    """Get a formatted summary of all registered APIs for the agent prompt."""
    index = _load_api_index()

    if not index:
        return "(No APIs registered yet)"

    result = []
    for api_name in sorted(index.keys()):
        api_info = index[api_name]
        base_url = api_info.get('base_url', 'N/A')
        auth_type = api_info.get('auth_type', 'none')
        description = api_info.get('description', 'No description')

        result.append(f"- **{api_name}**: {description}")
        result.append(f"  Base URL: {base_url} | Auth: {auth_type}")

    return "\n".join(result)


# ============================================================================
# Initialization Function
# ============================================================================

def initialize_api_agent(agent):
    """
    Initialize the API agent by injecting the API documentation index
    into its system prompt.

    This function is called automatically when the API agent starts.
    It replaces the {{API_INDEX}} placeholder with the current API index.

    Args:
        agent: The DynamicInitLoopingAgent instance being initialized
    """
    try:
        # Get current API index summary
        api_summary = _get_api_index_summary()

        # Update agent's system message
        if agent._system_messages:
            original = agent._system_messages[0].content
            updated = original.replace("{{API_INDEX}}", api_summary)
            agent._system_messages[0].content = updated
            logger.info("API agent initialized with API documentation index")
            return "API agent initialized successfully"
        else:
            logger.warning("No system messages found for API agent")
            return "Warning: No system messages in agent"

    except Exception as e:
        logger.error(f"Error initializing API agent: {e}")
        return f"Error: {str(e)}"


# ============================================================================
# Tool 1: HTTP Request
# ============================================================================

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
        if method not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            return f"Error: Invalid HTTP method '{method}'. Use GET, POST, PUT, PATCH, or DELETE."

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

        # Add key response headers
        result += "Response Headers:\n"
        for header in ['content-type', 'content-length', 'date', 'x-ratelimit-remaining']:
            if header in response.headers:
                result += f"  {header}: {response.headers[header]}\n"

        result += f"\nBody ({len(response.content)} bytes):\n"

        # Try to parse as JSON for pretty printing
        try:
            json_body = response.json()
            result += json.dumps(json_body, indent=2)
        except:
            # Fall back to text
            text = response.text[:5000]
            result += text
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


# ============================================================================
# Tool 2: Register API Documentation
# ============================================================================

def register_api(
    api_name: str,
    base_url: str,
    auth_type: str = "none",
    description: str = "",
    documentation: str = ""
) -> str:
    """
    Register a new API by saving its documentation and adding it to the index.

    Use this after receiving API documentation from the Researcher.
    Creates a documentation file and updates the central API index.

    Args:
        api_name: Unique identifier for the API (use lowercase_with_underscores)
        base_url: The base URL for API requests (e.g., "https://api.github.com")
        auth_type: Type of authentication: 'none', 'bearer', 'api_key', 'basic', 'oauth2'
        description: Brief description of what the API does
        documentation: Full documentation content including endpoints, params, examples

    Returns:
        Success message with the path to saved documentation, or error message

    Example:
        register_api(
            api_name="github_api",
            base_url="https://api.github.com",
            auth_type="bearer",
            description="GitHub REST API for repos, users, issues",
            documentation="# GitHub API\\n\\n## Endpoints\\n\\n### GET /user/repos\\n..."
        )
    """
    try:
        # Sanitize api_name
        safe_name = api_name.lower().replace(" ", "_").replace("-", "_")

        # Load existing index
        index = _load_api_index()

        # Create documentation file
        doc_file = API_DOCS_DIR / f"{safe_name}.md"

        with open(doc_file, 'w') as f:
            f.write(f"# {api_name} API Documentation\n\n")
            f.write(f"**Base URL**: {base_url}\n")
            f.write(f"**Auth Type**: {auth_type}\n")
            f.write(f"**Description**: {description}\n\n")
            f.write("---\n\n")
            f.write(documentation)

        # Update index
        index[safe_name] = {
            "doc_path": str(doc_file),
            "base_url": base_url,
            "auth_type": auth_type,
            "description": description
        }
        _save_api_index(index)

        logger.info(f"Registered API '{safe_name}' with documentation at {doc_file}")
        return f"Successfully registered API '{safe_name}'.\nDocumentation saved to: {doc_file}\nBase URL: {base_url}\nAuth Type: {auth_type}"

    except Exception as e:
        logger.error(f"Error registering API '{api_name}': {e}")
        return f"Error: {str(e)}"


# ============================================================================
# Tool 3: Get API Documentation
# ============================================================================

def get_api_documentation(api_name: str) -> str:
    """
    Retrieve documentation for a registered API.

    Args:
        api_name: The name of the API to get documentation for

    Returns:
        The full documentation content, or error message if not found
    """
    try:
        safe_name = api_name.lower().replace(" ", "_").replace("-", "_")
        index = _load_api_index()

        if safe_name not in index:
            available = ", ".join(index.keys()) if index else "none"
            return f"Error: API '{api_name}' not found. Available APIs: {available}"

        doc_path = Path(index[safe_name]['doc_path'])

        if not doc_path.exists():
            return f"Error: Documentation file not found at {doc_path}"

        with open(doc_path, 'r') as f:
            content = f.read()

        logger.info(f"Retrieved documentation for API '{safe_name}'")
        return content

    except Exception as e:
        logger.error(f"Error retrieving API documentation for '{api_name}': {e}")
        return f"Error: {str(e)}"


# ============================================================================
# Tool 4: List Registered APIs
# ============================================================================

def list_apis() -> str:
    """
    List all registered APIs with their basic information.

    Returns:
        Formatted list of all APIs with name, base URL, auth type, and description
    """
    try:
        index = _load_api_index()

        if not index:
            return "No APIs registered yet. When you need API documentation, ask the Manager to have the Researcher find it for you."

        result = [f"Registered APIs ({len(index)} total):\n"]
        for api_name in sorted(index.keys()):
            api_info = index[api_name]
            result.append(
                f"- **{api_name}**\n"
                f"  Base URL: {api_info.get('base_url', 'N/A')}\n"
                f"  Auth: {api_info.get('auth_type', 'none')}\n"
                f"  Description: {api_info.get('description', 'No description')}"
            )

        return "\n".join(result)

    except Exception as e:
        logger.error(f"Error listing APIs: {e}")
        return f"Error: {str(e)}"


# ============================================================================
# Tool 5: Delete API Documentation
# ============================================================================

def delete_api(api_name: str) -> str:
    """
    Delete API documentation and remove from index.

    Args:
        api_name: Name of the API to delete

    Returns:
        Success or error message
    """
    try:
        safe_name = api_name.lower().replace(" ", "_").replace("-", "_")
        index = _load_api_index()

        if safe_name not in index:
            return f"Error: API '{api_name}' not found in index."

        # Remove documentation file
        doc_path = Path(index[safe_name].get('doc_path', ''))
        if doc_path.exists():
            doc_path.unlink()

        # Remove from index
        del index[safe_name]
        _save_api_index(index)

        logger.info(f"Deleted API docs: {safe_name}")
        return f"API documentation for '{api_name}' has been deleted."

    except Exception as e:
        logger.error(f"Error deleting API docs: {e}")
        return f"Error: {str(e)}"


# ============================================================================
# Create FunctionTool instances
# ============================================================================

http_request_tool = FunctionTool(
    func=http_request,
    name="http_request",
    description="Make HTTP requests (GET, POST, PUT, DELETE, PATCH) to any API endpoint with headers, params, and body"
)

register_api_tool = FunctionTool(
    func=register_api,
    name="register_api",
    description="Register a new API by saving its documentation (base URL, auth type, endpoints) to the index for future use"
)

get_api_documentation_tool = FunctionTool(
    func=get_api_documentation,
    name="get_api_documentation",
    description="Retrieve the full documentation for a registered API including endpoints, parameters, and examples"
)

list_apis_tool = FunctionTool(
    func=list_apis,
    name="list_apis",
    description="List all registered APIs with their basic information (name, base URL, auth type, description)"
)

delete_api_tool = FunctionTool(
    func=delete_api,
    name="delete_api",
    description="Delete API documentation and remove it from the index"
)


# Export tools
tools = [
    http_request_tool,
    register_api_tool,
    get_api_documentation_tool,
    list_apis_tool,
    delete_api_tool
]
