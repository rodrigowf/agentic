# API Agent Guide

**Created:** 2025-12-01
**Status:** ✅ Implemented and tested

---

## Overview

The **API Agent** is a specialized nested team designed to interact with any web API through HTTP(S) requests. It consists of multiple coordinated agents that can find documentation, make API calls, manage authentication, and maintain a persistent catalog of API documentation.

---

## Architecture

### Team Structure

```
API (nested_team)
├── APIManager (orchestrator)
├── APIDocs (manages documentation storage)
├── HTTPRequest (executes HTTP requests)
├── Researcher (finds API documentation)
└── Engineer (retrieves credentials)
```

### Agent Roles

**APIManager** (Orchestrator)
- Coordinates the team
- Maintains awareness of stored API documentation via `{{API_DOCS_INDEX}}`
- Delegates tasks to appropriate specialists
- Manages multi-step API workflows
- Separates concerns between documentation and execution

**APIDocs** (Documentation Specialist)
- Stores API documentation in markdown files
- Retrieves stored documentation when needed
- Manages the API documentation index
- Updates and deletes documentation
- Organizes documentation with clear naming conventions

**HTTPRequest** (Execution Specialist)
- Executes HTTP requests (GET, POST, PUT, DELETE, PATCH)
- Handles authentication headers
- Parses and summarizes API responses
- Debugs failed requests
- Explains HTTP status codes and errors

**Researcher** (Specialist - from existing agents)
- Finds and summarizes API documentation from web sources
- Locates base URLs, endpoints, auth methods
- Provides documentation to APIDocs for storage

**Engineer** (Specialist - from existing agents)
- Retrieves credentials from files (.env, config files)
- Creates helper scripts for complex API workflows
- Handles authentication setup

---

## Features

### 1. HTTP Request Capabilities

The API agent can make any type of HTTP request:

```python
# GET request
http_request("https://api.example.com/users")

# POST with authentication
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
```

**Supported Methods:**
- `GET` - Retrieve data
- `POST` - Create new resources
- `PUT` - Update existing resources
- `DELETE` - Remove resources
- `PATCH` - Partial updates

### 2. API Documentation Management

The agent maintains a persistent catalog of API documentation:

**Storage Location:** `/home/rodrigo/agentic/backend/api_docs/`

**Index File:** `api_docs/api_index.json`

**Documentation Format:** Markdown (`.md` files)

**Example Index:**
```json
{
  "apis": {
    "github_api": {
      "file": "github_api.md",
      "description": "GitHub REST API v3 for user and repo operations",
      "path": "/home/rodrigo/agentic/backend/api_docs/github_api.md"
    },
    "openai_api": {
      "file": "openai_api.md",
      "description": "OpenAI API for completions and embeddings",
      "path": "/home/rodrigo/agentic/backend/api_docs/openai_api.md"
    }
  }
}
```

### 3. Dynamic System Prompt Updates

The **APIManager** uses dynamic initialization to always have the latest API documentation index in its system prompt:

- Uses `initialization_function: "api.initialize_api_manager"`
- Replaces `{{API_DOCS_INDEX}}` placeholder with current index
- Updates automatically on agent startup
- No manual prompt editing required

---

## Tools Reference

### 1. `http_request`

Make HTTP requests to any URL.

**Parameters:**
- `url` (string, required) - Full URL to request
- `method` (string) - HTTP method (default: "GET")
- `headers` (dict) - Optional HTTP headers
- `params` (dict) - Optional query parameters
- `body` (dict) - Optional request body (JSON encoded)
- `timeout` (int) - Timeout in seconds (default: 30)

**Returns:** Response status, headers, and body

**Example:**
```python
http_request(
    "https://api.github.com/users/octocat",
    method="GET",
    headers={"Accept": "application/vnd.github.v3+json"}
)
```

### 2. `save_api_docs`

Save API documentation to a markdown file and update the index.

**Parameters:**
- `api_name` (string, required) - Name/identifier for the API
- `content` (string, required) - Documentation content (markdown)
- `description` (string, required) - Short description for the index

**Returns:** Success message with file path

**Example:**
```python
save_api_docs(
    "github_api",
    "# GitHub API\n\n## Authentication\n...",
    "GitHub REST API v3 for user and repo operations"
)
```

### 3. `get_api_index`

Get the complete API documentation index.

**Parameters:** None

**Returns:** Formatted list of all stored API documentation

**Example Output:**
```
API Documentation Index:

- **github_api**: GitHub REST API v3 for user and repo operations
  File: github_api.md
  Path: /home/rodrigo/agentic/backend/api_docs/github_api.md
```

### 4. `read_api_docs`

Read stored API documentation by name.

**Parameters:**
- `api_name` (string, required) - Name of the API

**Returns:** Full documentation content

**Example:**
```python
read_api_docs("github_api")
```

### 5. `delete_api_docs`

Delete API documentation and remove from index.

**Parameters:**
- `api_name` (string, required) - Name of the API to delete

**Returns:** Success or error message

**Example:**
```python
delete_api_docs("github_api")
```

---

## Usage Examples

### Example 1: Simple GET Request

**User:** "Get information about the GitHub user 'octocat'"

**Workflow:**
1. Manager checks if GitHub API docs exist (via `{{API_DOCS_INDEX}}`)
2. If no docs: Researcher finds GitHub API documentation
3. APIDocs stores the documentation
4. HTTPRequest executes: `http_request("https://api.github.com/users/octocat")`
5. HTTPRequest summarizes the response

### Example 2: POST Request with Authentication

**User:** "Create a new repository on GitHub called 'my-project'"

**Workflow:**
1. Manager checks for GitHub API docs
2. Manager asks user for GitHub personal access token
3. HTTPRequest executes:
   ```python
   http_request(
       "https://api.github.com/user/repos",
       method="POST",
       headers={"Authorization": "Bearer ghp_xxxxx"},
       body={"name": "my-project", "private": false}
   )
   ```
4. HTTPRequest confirms repository creation

### Example 3: Credentials from File

**User:** "Get my OpenAI API usage for this month"

**Workflow:**
1. Manager checks for OpenAI API docs
2. If no docs: Researcher finds OpenAI API documentation
3. Manager delegates to Engineer to retrieve API key from `.env` file
4. HTTPRequest executes:
   ```python
   http_request(
       "https://api.openai.com/v1/usage",
       method="GET",
       headers={"Authorization": "Bearer sk-xxxxx"}
   )
   ```
5. HTTPRequest summarizes usage statistics

### Example 4: Multi-Step Workflow

**User:** "Find all my GitHub repositories and create issues titled 'Update README' on each one"

**Workflow:**
1. Manager breaks down into steps:
   - Step 1: Get list of repositories
   - Step 2: For each repo, create an issue
2. HTTPRequest gets repos: `GET /user/repos`
3. For each repository:
   - HTTPRequest creates issue: `POST /repos/{owner}/{repo}/issues`
4. Manager summarizes total issues created

---

## Best Practices

### For Users

1. **Provide API Keys When Prompted**
   - If the agent asks for credentials, provide them directly
   - Or specify where they're stored (e.g., "API key is in .env file")

2. **Be Specific About Requirements**
   - Specify exact endpoints if known
   - Mention authentication requirements upfront
   - Provide example request/response formats if available

3. **Reuse Documentation**
   - Once documentation is stored, the agent can reuse it
   - No need to re-research the same API

### For Developers

1. **Documentation Structure**
   - Use clear, consistent naming (lowercase with underscores)
   - Include: base URL, endpoints, auth method, request/response formats
   - Add examples for common operations

2. **Error Handling**
   - The agent will explain API errors
   - Check response status codes for debugging
   - Verify authentication is correct

3. **Security**
   - Never commit API keys to documentation files
   - Store credentials in `.env` or secure files
   - Use read-only tokens when possible

---

## File Locations

| Purpose | Location |
|---------|----------|
| **API Tools** | `/home/rodrigo/agentic/backend/tools/api.py` |
| **APIDocs Config** | `/home/rodrigo/agentic/backend/agents/APIDocs.json` |
| **HTTPRequest Config** | `/home/rodrigo/agentic/backend/agents/HTTPRequest.json` |
| **APIManager Config** | `/home/rodrigo/agentic/backend/agents/APIManager.json` |
| **API Team Config** | `/home/rodrigo/agentic/backend/agents/API.json` |
| **API Documentation** | `/home/rodrigo/agentic/backend/api_docs/*.md` |
| **API Index** | `/home/rodrigo/agentic/backend/api_docs/api_index.json` |
| **This Guide** | `/home/rodrigo/agentic/docs/API_AGENT_GUIDE.md` |

---

## Testing

### Unit Tests

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate

# Test HTTP request
python3 -c "
from tools.api import http_request
result = http_request('https://jsonplaceholder.typicode.com/posts/1')
print(result)
"

# Test documentation storage
python3 -c "
from tools.api import save_api_docs, get_api_index, read_api_docs

# Save docs
save_api_docs('test_api', '# Test API', 'Test API documentation')

# Get index
print(get_api_index())

# Read docs
print(read_api_docs('test_api'))
"
```

### Integration Test

Use the frontend to test the full agent workflow:

1. Navigate to `http://localhost:3000/agentic/`
2. Select "MainConversation" agent
3. Send message: "Get the first post from JSONPlaceholder API"
4. Verify the agent:
   - Asks Researcher to find documentation
   - Stores documentation via APIHandler
   - Makes HTTP request
   - Returns the result

---

## Troubleshooting

### Issue: "No documentation found"

**Solution:**
- Ask the agent to research the API first
- Or provide documentation manually: "Here's the API docs: [content]"
- Check `api_docs/api_index.json` to see what's stored

### Issue: "Request timeout"

**Solution:**
- Check internet connection
- Verify the API URL is correct
- Increase timeout: `http_request(..., timeout=60)`

### Issue: "Authentication failed (401)"

**Solution:**
- Verify API key is correct
- Check if key needs specific header format (Bearer, API-Key, etc.)
- Ensure key has required permissions

### Issue: "Cannot parse response"

**Solution:**
- API might return non-JSON response
- Check response format in documentation
- The agent will show raw text if JSON parsing fails

---

## Future Enhancements

Potential improvements:

- 🔮 **OAuth Flow Support** - Handle OAuth 2.0 authentication
- 🔮 **Rate Limiting** - Respect API rate limits automatically
- 🔮 **Batch Requests** - Execute multiple requests in parallel
- 🔮 **GraphQL Support** - Tools for GraphQL queries
- 🔮 **Webhook Handling** - Receive and process webhooks
- 🔮 **Response Caching** - Cache API responses for efficiency
- 🔮 **API Testing Suite** - Automated API testing workflows

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Main development guide
- [Dynamic Agent Description Injection](DYNAMIC_AGENT_DESCRIPTION_INJECTION.md) - How `{{AVAILABLE_AGENTS}}` works
- [Dynamic Init Agent Implementation](DYNAMIC_INIT_AGENT_IMPLEMENTATION.md) - How `{{API_DOCS_INDEX}}` is injected
- [Backend Refactoring Summary](REFACTORING_SUMMARY.md) - Backend architecture

---

**End of API Agent Guide**
