# Task 2: Create File Manager Agent

**Status:** Pending
**Priority:** High
**Assigned to:** TBD
**Estimated Effort:** 8-12 hours

---

## Overview

Create a comprehensive file management agent that can create, read, understand, and manage files using a vector store database for semantic search and content organization.

---

## Objectives

- Build agent capable of all file operations (CRUD)
- Integrate ChromaDB for semantic file search
- Enable file content understanding and organization
- Provide both standalone and nested team usage
- Support integration with Memory agent for file-based memory

---

## Agent Specification

### Basic Configuration

**Agent Name:** `FileManager`

**Agent Type:** `looping` or `dynamic_init_looping`

**LLM:** GPT-4 or Claude (for understanding capabilities)

**Description:** "An agent that manages files with semantic search capabilities using vector embeddings."

**System Prompt:**
```
You are the FileManager, an expert at organizing and managing files.

Your capabilities:
- Create new files with specified content
- Read and understand file contents
- Update existing files
- Delete files (with confirmation)
- Search files semantically using vector embeddings
- Organize files by content and type
- Summarize file contents
- Index files to vector store for semantic search

You run in a loop until the task is complete. Say TERMINATE when done.

When working with files:
- Always confirm before deleting files
- Use semantic search to find related files
- Provide helpful summaries and organization suggestions
- Index important files to the vector store automatically
```

---

## Tools to Implement

### 1. File Operation Tools

**File:** `backend/tools/file_management.py`

#### `create_file(filepath: str, content: str) -> str`
```python
"""
Create a new file with specified content.

Args:
    filepath: Absolute or relative path to file
    content: Content to write to file

Returns:
    Success message or error
"""
```

#### `read_file(filepath: str) -> str`
```python
"""
Read file contents.

Args:
    filepath: Path to file to read

Returns:
    File contents or error message
"""
```

#### `update_file(filepath: str, content: str) -> str`
```python
"""
Update existing file with new content.

Args:
    filepath: Path to file
    content: New content

Returns:
    Success message or error
"""
```

#### `delete_file(filepath: str, confirm: bool = False) -> str`
```python
"""
Delete a file with confirmation.

Args:
    filepath: Path to file to delete
    confirm: Must be True to actually delete

Returns:
    Success message or error
"""
```

#### `list_files(directory: str, pattern: str = "*") -> str`
```python
"""
List files in directory with optional pattern matching.

Args:
    directory: Directory to list
    pattern: Glob pattern (e.g., "*.py", "*.json")

Returns:
    Formatted list of files with metadata
"""
```

#### `move_file(source: str, destination: str) -> str`
```python
"""
Move or rename a file.

Args:
    source: Current file path
    destination: New file path

Returns:
    Success message or error
"""
```

#### `copy_file(source: str, destination: str) -> str`
```python
"""
Copy a file to new location.

Args:
    source: Source file path
    destination: Destination path

Returns:
    Success message or error
"""
```

### 2. Vector Store Tools

**File:** `backend/tools/file_vectorstore.py`

#### `index_file_to_vectorstore(filepath: str, metadata: dict = None) -> str`
```python
"""
Index file content to ChromaDB for semantic search.

Args:
    filepath: Path to file to index
    metadata: Optional metadata (author, tags, etc.)

Returns:
    Success message with document ID
"""
```

#### `search_files_semantic(query: str, n_results: int = 5) -> str`
```python
"""
Semantic search across indexed files.

Args:
    query: Natural language search query
    n_results: Number of results to return

Returns:
    Formatted list of relevant files with snippets
"""
```

#### `get_file_from_vectorstore(file_id: str) -> str`
```python
"""
Retrieve file metadata and content from vector store.

Args:
    file_id: Document ID from vector store

Returns:
    File information and content
"""
```

#### `remove_file_from_vectorstore(filepath: str) -> str`
```python
"""
Remove file from vector store index.

Args:
    filepath: Path to file to remove from index

Returns:
    Success message or error
"""
```

#### `list_indexed_files() -> str`
```python
"""
List all files currently indexed in vector store.

Returns:
    Formatted list of indexed files with metadata
"""
```

### 3. File Understanding Tools

**File:** `backend/tools/file_management.py` (continued)

#### `summarize_file(filepath: str) -> str`
```python
"""
Generate AI summary of file contents.

Args:
    filepath: Path to file to summarize

Returns:
    Summary of file content and purpose
"""
```

#### `analyze_file_structure(filepath: str) -> str`
```python
"""
Analyze file structure (for code, JSON, etc.).

Args:
    filepath: Path to file to analyze

Returns:
    Structural analysis (functions, classes, schema, etc.)
"""
```

#### `suggest_file_organization(directory: str) -> str`
```python
"""
Suggest how to organize files in directory.

Args:
    directory: Directory to analyze

Returns:
    Organization suggestions based on content
"""
```

#### `find_duplicate_files(directory: str) -> str`
```python
"""
Find potential duplicate files by content hash.

Args:
    directory: Directory to scan

Returns:
    List of potential duplicates
"""
```

---

## Vector Store Integration

### ChromaDB Setup

**Collection Name:** `file_contents`

**Embedding Model:** OpenAI `text-embedding-ada-002` or similar

**Metadata Schema:**
```python
{
    "filepath": str,          # Full path to file
    "filename": str,          # Just filename
    "extension": str,         # File extension
    "size_bytes": int,        # File size
    "created_at": str,        # ISO timestamp
    "modified_at": str,       # ISO timestamp
    "file_type": str,         # code, document, data, etc.
    "summary": str,           # AI-generated summary
    "tags": List[str],        # User or AI tags
    "author": str,            # Optional
}
```

### Indexing Strategy

**Automatic Indexing:**
- When creating new files with `auto_index=True`
- When updating important files
- Batch indexing on startup (optional)

**Manual Indexing:**
- Via `index_file_to_vectorstore()` tool
- User can selectively index files

**Chunking Strategy:**
- For large files (>4000 tokens), split into chunks
- Maintain chunk metadata for reconstruction
- Overlap chunks by 200 tokens for context

---

## Implementation Details

### File Paths

**Working Directory:** `backend/workspace/` (configurable)

**Allowed Paths:**
- Inside workspace directory: ✅
- Absolute paths: ⚠️ Require validation
- Outside workspace: ❌ Block for security

**Path Validation:**
```python
def validate_filepath(filepath: str, workspace_dir: str) -> str:
    """Ensure filepath is safe and within allowed directory."""
    abs_path = os.path.abspath(filepath)
    workspace_abs = os.path.abspath(workspace_dir)

    if not abs_path.startswith(workspace_abs):
        raise ValueError("Path outside workspace not allowed")

    return abs_path
```

### Error Handling

All tools should:
- Return error messages (not raise exceptions)
- Validate inputs before operations
- Provide helpful error context
- Log errors for debugging

### Permissions

Consider implementing:
- Read-only mode for sensitive files
- Confirmation for destructive operations (delete, overwrite)
- File size limits (e.g., max 10MB for indexing)

---

## Agent Configuration File

**File:** `backend/agents/FileManager.json`

```json
{
  "name": "FileManager",
  "agent_type": "looping",
  "tools": [
    "create_file",
    "read_file",
    "update_file",
    "delete_file",
    "list_files",
    "move_file",
    "copy_file",
    "index_file_to_vectorstore",
    "search_files_semantic",
    "get_file_from_vectorstore",
    "remove_file_from_vectorstore",
    "list_indexed_files",
    "summarize_file",
    "analyze_file_structure",
    "suggest_file_organization",
    "find_duplicate_files"
  ],
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.0,
    "max_tokens": null
  },
  "prompt": {
    "system": "You are the FileManager, an expert at organizing and managing files...",
    "user": "Manage files as requested by the user."
  },
  "code_executor": null,
  "model_client_stream": false,
  "sources": null,
  "description": "An agent that manages files with semantic search capabilities using vector embeddings.",
  "system_message": null,
  "max_consecutive_auto_reply": 20,
  "reflect_on_tool_use": true,
  "terminate_on_text": false,
  "tool_call_loop": true,
  "sub_agents": null,
  "mode": null,
  "orchestrator_prompt": null,
  "include_inner_dialog": true
}
```

---

## Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `backend/agents/FileManager.json` | Agent configuration | Required |
| `backend/tools/file_management.py` | File operation tools | Required |
| `backend/tools/file_vectorstore.py` | Vector store tools | Required |
| `backend/tests/test_file_manager.py` | Unit tests | Recommended |
| `backend/docs/FILE_MANAGER_GUIDE.md` | User documentation | Recommended |

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `backend/config/config_loader.py` | If custom loading needed | Optional |
| `backend/agents/MainConversation.json` | Add FileManager to team | Optional |
| `frontend/src/App.js` | Add route if UI needed | Optional |

---

## Testing Plan

### Unit Tests

**File:** `backend/tests/test_file_manager.py`

```python
def test_create_file():
    """Test file creation"""

def test_read_file():
    """Test file reading"""

def test_update_file():
    """Test file updating"""

def test_delete_file():
    """Test file deletion with confirmation"""

def test_list_files():
    """Test directory listing"""

def test_search_semantic():
    """Test vector search"""

def test_index_file():
    """Test file indexing to ChromaDB"""

def test_path_validation():
    """Test path security validation"""
```

### Integration Tests

**File:** `backend/tests/integration/test_file_manager_integration.py`

```python
def test_full_file_lifecycle():
    """Create -> Read -> Update -> Delete"""

def test_semantic_search_workflow():
    """Index multiple files -> Search -> Retrieve"""

def test_agent_file_operations():
    """Test FileManager agent via API"""

def test_nested_team_integration():
    """Test FileManager in MainConversation"""
```

### Manual Testing

**Test Scenarios:**

1. **File CRUD:**
   - Create test file
   - Read contents
   - Update contents
   - Delete file

2. **Semantic Search:**
   - Index multiple documents
   - Search by topic
   - Verify relevant results

3. **Organization:**
   - Create messy directory
   - Ask for organization suggestions
   - Verify suggestions make sense

4. **Integration:**
   - Use from voice assistant
   - Use from MainConversation
   - Use standalone

---

## Success Criteria

- ✅ Can create, read, update, delete files
- ✅ Vector store successfully indexes file contents
- ✅ Semantic search returns relevant files
- ✅ Agent can understand file context and suggest organization
- ✅ Works both standalone and as sub-agent in nested teams
- ✅ Path validation prevents access outside workspace
- ✅ All unit tests pass
- ✅ Integration tests pass
- ✅ No security vulnerabilities
- ✅ Documentation complete

---

## Security Considerations

### Path Traversal Prevention

```python
# Block: ../../etc/passwd
# Block: /etc/passwd
# Allow: workspace/myfile.txt
# Allow: ./workspace/subfolder/file.txt
```

### File Size Limits

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_INDEX_SIZE = 1 * 1024 * 1024  # 1MB for vector store
```

### Dangerous Operations

- Require `confirm=True` for deletes
- Warn before overwriting existing files
- Rate limit operations to prevent abuse

---

## Performance Considerations

### ChromaDB Optimization

- Use batch indexing for multiple files
- Implement caching for frequent queries
- Limit search results to reasonable number (default 5-10)

### File Operations

- Stream large files instead of loading into memory
- Use async operations where possible
- Implement pagination for large directory listings

---

## Future Enhancements

- **File versioning:** Track changes over time
- **Collaborative editing:** Multiple agents working on same file
- **Auto-backup:** Automatic backup to vector store
- **Cross-file analysis:** Find dependencies and references
- **File templates:** Create files from templates
- **Batch operations:** Apply operations to multiple files
- **File watching:** Monitor and auto-index changed files

---

## Dependencies

**Required:**
- ChromaDB (vector store)
- OpenAI API (for embeddings)
- Python os, pathlib, shutil modules

**Optional:**
- Task #1 (Memory) - For file-based memory integration
- Task #3 (Agent Registry) - For automatic team integration

---

## Integration with Other Tasks

### With Memory Agent (Task #1)
- FileManager can store memories as files
- Memory agent can use FileManager for persistence
- Combined: "Remember this in a file" workflow

### With Planner Agent (Task #4)
- Planner can use FileManager for plan storage
- FileManager can organize planning documents
- Combined: "Create plan and save it" workflow

---

## Rollback Plan

If FileManager causes issues:

1. Remove from MainConversation sub_agents (if added)
2. Keep agent file but don't use
3. Vector store data can remain (no harm)
4. Re-enable when issues resolved

---

## Notes

- Consider using `aiofiles` for async file operations
- ChromaDB collection should be created on first use
- May want separate collections for different file types
- Consider file type detection (magic numbers, extensions)

---

**Last Updated:** 2025-11-29
