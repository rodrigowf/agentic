# api_tools.py - API management tools with HTTP requests and documentation indexing

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
import requests
from utils.context import get_current_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_METADATA_PATH = Path("data/api")
API_METADATA_PATH.mkdir(parents=True, exist_ok=True)
API_INDEX_FILE = API_METADATA_PATH / "api_index.json"
API_DOCS_PATH = API_METADATA_PATH / "docs"
API_DOCS_PATH.mkdir(parents=True, exist_ok=True)

# --- API Index Management ---

def _load_api_index() -> Dict[str, Dict]:
    """
    Load API index from disk.

    Returns:
        Dictionary mapping API names to their metadata (doc_path, base_url, auth_type, etc.)
    """
    if API_INDEX_FILE.exists():
        try:
            with open(API_INDEX_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading API index: {e}")
            return {}
    return {}

def _save_api_index(index: Dict[str, Dict]):
    """
    Save API index to disk.

    Args:
        index: Dictionary mapping API names to their metadata
    """
    try:
        with open(API_INDEX_FILE, 'w') as f:
            json.dump(index, f, indent=2)
        logger.info(f"Saved API index with {len(index)} APIs")
    except Exception as e:
        logger.error(f"Error saving API index: {e}")

def _get_api_index_summary() -> str:
    """
    Get a formatted summary of all registered APIs.

    Returns:
        Formatted string listing all APIs with their details.
    """
    index = _load_api_index()

    if not index:
        return "(No APIs registered yet)"

    result = []
    for api_name in sorted(index.keys()):
        api_info = index[api_name]
        doc_path = api_info.get('doc_path', 'N/A')
        base_url = api_info.get('base_url', 'N/A')
        auth_type = api_info.get('auth_type', 'none')
        description = api_info.get('description', 'No description')

        api_summary = [f"**{api_name}**"]
        api_summary.append(f"  Description: {description}")
        api_summary.append(f"  Base URL: {base_url}")
        api_summary.append(f"  Auth Type: {auth_type}")
        api_summary.append(f"  Documentation: {doc_path}")

        result.append("\n".join(api_summary))

    return "\n\n".join(result)

def initialize_api_manager_agent():
    """
    Initialization function for API Manager agent.
    Loads API index and injects it into the agent's system prompt.

    This function is called automatically when the API Manager agent starts up.
    It replaces the {{API_INDEX}} placeholder in the system prompt with the
    current list of registered APIs.
    """
    try:
        agent = get_current_agent()

        # Get API index summary
        api_summary = _get_api_index_summary()

        # Update agent's system message with API index
        if agent and agent._system_messages:
            original_content = agent._system_messages[0].content
            updated_content = original_content.replace(
                "{{API_INDEX}}",
                api_summary
            )
            agent._system_messages[0].content = updated_content
            logger.info("API Manager agent initialized with API index")

        return "API Manager initialized successfully"
    except Exception as e:
        logger.error(f"Error initializing API Manager agent: {e}")
        return f"Error: {e}"

# --- Tool 1: Register API Documentation ---

class RegisterAPIInput(BaseModel):
    """Input model for registering API documentation"""
    api_name: str = Field(description="Unique name for the API (e.g., 'twitter_api', 'github_api')")
    base_url: str = Field(description="Base URL for the API (e.g., 'https://api.twitter.com/2')")
    auth_type: str = Field(
        default="none",
        description="Authentication type: 'none', 'bearer', 'api_key', 'oauth2', 'basic'"
    )
    description: str = Field(description="Brief description of the API and its purpose")
    documentation: str = Field(description="Full API documentation content (endpoints, parameters, examples)")

def register_api(
    api_name: str,
    base_url: str,
    auth_type: str = "none",
    description: str = "",
    documentation: str = ""
) -> str:
    """
    Register a new API by saving its documentation and adding it to the index.

    This tool should be used after the Researcher finds API documentation.
    It creates a documentation file and updates the central API index.

    Args:
        api_name: Unique identifier for the API (snake_case recommended)
        base_url: The base URL for API requests
        auth_type: Type of authentication required
        description: Brief description of what the API does
        documentation: Full documentation content including endpoints, params, examples

    Returns:
        Success message with the path to saved documentation, or error message
    """
    try:
        # Load existing index
        index = _load_api_index()

        # Create documentation file path
        doc_filename = f"{api_name}.md"
        doc_path = API_DOCS_PATH / doc_filename

        # Save documentation to file
        with open(doc_path, 'w') as f:
            f.write(f"# {api_name} API Documentation\n\n")
            f.write(f"**Base URL**: {base_url}\n")
            f.write(f"**Auth Type**: {auth_type}\n")
            f.write(f"**Description**: {description}\n\n")
            f.write("---\n\n")
            f.write(documentation)

        # Update index
        index[api_name] = {
            "doc_path": str(doc_path),
            "base_url": base_url,
            "auth_type": auth_type,
            "description": description,
            "registered_at": str(Path(doc_path).stat().st_mtime)
        }
        _save_api_index(index)

        # Update agent's system message if in agent context
        try:
            agent = get_current_agent()
            if agent and agent._system_messages:
                api_summary = _get_api_index_summary()
                agent._system_messages[0].content = agent._system_messages[0].content.replace(
                    "{{API_INDEX}}",
                    api_summary
                )
        except Exception as e:
            logger.warning(f"Could not update agent system message: {e}")

        logger.info(f"Registered API '{api_name}' with documentation at {doc_path}")
        return f"Successfully registered API '{api_name}'. Documentation saved to: {doc_path}"

    except Exception as e:
        logger.error(f"Error registering API '{api_name}': {e}")
        return f"Error: {str(e)}"

register_api_tool = FunctionTool(
    func=register_api,
    description=(
        "Register a new API by saving its documentation and adding it to the central index. "
        "Use this after the Researcher finds API documentation. Provide the API name, base URL, "
        "authentication type, description, and full documentation content."
    )
)

# --- Tool 2: Get API Documentation ---

class GetAPIDocInput(BaseModel):
    """Input model for retrieving API documentation"""
    api_name: str = Field(description="Name of the registered API")

def get_api_documentation(api_name: str) -> str:
    """
    Retrieve documentation for a registered API.

    Args:
        api_name: The name of the API to get documentation for

    Returns:
        The full documentation content, or error message if not found
    """
    try:
        index = _load_api_index()

        if api_name not in index:
            return f"Error: API '{api_name}' not found in index. Use list_apis to see registered APIs."

        doc_path = Path(index[api_name]['doc_path'])

        if not doc_path.exists():
            return f"Error: Documentation file not found at {doc_path}"

        with open(doc_path, 'r') as f:
            content = f.read()

        logger.info(f"Retrieved documentation for API '{api_name}'")
        return content

    except Exception as e:
        logger.error(f"Error retrieving API documentation for '{api_name}': {e}")
        return f"Error: {str(e)}"

get_api_documentation_tool = FunctionTool(
    func=get_api_documentation,
    description=(
        "Retrieve the full documentation for a registered API. "
        "Returns the complete documentation content including endpoints, parameters, and examples."
    )
)

# --- Tool 3: List Registered APIs ---

def list_apis() -> str:
    """
    List all registered APIs with their basic information.

    Returns:
        Formatted list of all APIs with name, base URL, auth type, and description
    """
    try:
        index = _load_api_index()

        if not index:
            return "No APIs registered yet. Use register_api to add new APIs."

        result = [f"Registered APIs ({len(index)} total):\n"]
        for api_name in sorted(index.keys()):
            api_info = index[api_name]
            result.append(
                f"• {api_name}\n"
                f"  Base URL: {api_info.get('base_url', 'N/A')}\n"
                f"  Auth: {api_info.get('auth_type', 'none')}\n"
                f"  Description: {api_info.get('description', 'No description')}"
            )

        return "\n".join(result)

    except Exception as e:
        logger.error(f"Error listing APIs: {e}")
        return f"Error: {str(e)}"

list_apis_tool = FunctionTool(
    func=list_apis,
    description="List all registered APIs with their basic information (name, base URL, auth type, description)."
)

# --- Tool 4: HTTP Request ---

class HTTPRequestInput(BaseModel):
    """Input model for HTTP requests"""
    method: str = Field(description="HTTP method: GET, POST, PUT, PATCH, DELETE")
    url: str = Field(description="Full URL for the request (can use base_url from API index + endpoint)")
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="HTTP headers as key-value pairs (e.g., {'Authorization': 'Bearer TOKEN', 'Content-Type': 'application/json'})"
    )
    body: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Request body as JSON object (for POST, PUT, PATCH requests)"
    )
    params: Optional[Dict[str, str]] = Field(
        default=None,
        description="URL query parameters as key-value pairs"
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds (default: 30)"
    )

def http_call(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, str]] = None,
    timeout: int = 30
) -> str:
    """
    Make an HTTP request to an API endpoint.

    Supports GET, POST, PUT, PATCH, DELETE methods with headers, body, and query parameters.
    Returns the response status, headers, and body (JSON or text).

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        url: Full URL for the request
        headers: Optional HTTP headers (e.g., Authorization, Content-Type)
        body: Optional request body as dictionary (will be JSON-encoded)
        params: Optional URL query parameters
        timeout: Request timeout in seconds

    Returns:
        Formatted response with status code, headers, and body content
    """
    try:
        method = method.upper()
        if method not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            return f"Error: Invalid HTTP method '{method}'. Use GET, POST, PUT, PATCH, or DELETE."

        logger.info(f"Making {method} request to {url}")

        # Prepare request arguments
        request_args = {
            'method': method,
            'url': url,
            'timeout': timeout
        }

        if headers:
            request_args['headers'] = headers

        if params:
            request_args['params'] = params

        if body and method in ['POST', 'PUT', 'PATCH']:
            request_args['json'] = body

        # Make the request
        response = requests.request(**request_args)

        # Format response
        result = [
            f"HTTP {method} {url}",
            f"Status: {response.status_code} {response.reason}",
            "",
            "Response Headers:",
        ]

        # Add key response headers
        for header in ['content-type', 'content-length', 'date']:
            if header in response.headers:
                result.append(f"  {header}: {response.headers[header]}")

        result.append("")
        result.append("Response Body:")

        # Try to parse JSON response
        try:
            json_body = response.json()
            result.append(json.dumps(json_body, indent=2))
        except:
            # Fallback to text
            text_body = response.text
            max_len = 5000
            if len(text_body) > max_len:
                result.append(text_body[:max_len] + f"\n... (truncated, total length: {len(text_body)})")
            else:
                result.append(text_body)

        # Log success/failure
        if 200 <= response.status_code < 300:
            logger.info(f"Request successful: {response.status_code}")
        else:
            logger.warning(f"Request returned non-2xx status: {response.status_code}")

        return "\n".join(result)

    except requests.exceptions.Timeout:
        logger.error(f"Request timeout for {url}")
        return f"Error: Request timed out after {timeout} seconds for {url}"

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {e}")
        return f"Error making request to {url}: {str(e)}"

    except Exception as e:
        logger.error(f"Unexpected error during HTTP request: {e}")
        return f"Error: {str(e)}"

http_call_tool = FunctionTool(
    func=http_call,
    description=(
        "Make an HTTP request to an API endpoint. Supports GET, POST, PUT, PATCH, DELETE methods. "
        "Provide the full URL, optional headers (including authentication), request body (for POST/PUT/PATCH), "
        "and query parameters. Returns the response status, headers, and body content (JSON or text)."
    )
)

# --- Export all tools ---

tools = [
    register_api_tool,
    get_api_documentation_tool,
    list_apis_tool,
    http_call_tool
]
