# FileManager Agent - Quick Reference Card

**Agent Name:** `FileManager`
**Type:** `dynamic_init_looping`
**Location:** `/home/rodrigo/agentic/backend/agents/FileManager.json`

---

## 🎯 Quick Start

**Access via Frontend:**
```
http://localhost:3000/agents/FileManager
```

**Example Tasks:**
- "List all markdown files in the workspace"
- "Create a new file called notes.txt with my meeting notes"
- "Read the docling_research_summary.md file"
- "Move all screenshots to a backup folder"
- "Delete old test files (with confirmation)"

---

## 🛠️ Available Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `create_file` | Create new file | `create_file("notes.txt", "My notes...")` |
| `read_file` | Read file contents | `read_file("notes.txt")` |
| `update_file` | Modify existing file | `update_file("notes.txt", "Updated notes...")` |
| `delete_file` | Delete file (needs confirm) | `delete_file("old.txt", confirm=True)` |
| `list_files` | List files with pattern | `list_files(".", "*.md")` |
| `move_file` | Move/rename file | `move_file("old.txt", "new.txt")` |
| `copy_file` | Copy file | `copy_file("src.txt", "backup.txt")` |

---

## 🔒 Security

**Workspace Directory:** `/home/rodrigo/agentic/backend/workspace/`

✅ **Allowed:**
- `myfile.txt` (relative path)
- `./subfolder/file.txt` (relative)
- `workspace/myfile.txt` (within workspace)

❌ **Blocked:**
- `/etc/passwd` (outside workspace)
- `../../etc/passwd` (directory traversal)
- Any absolute path outside workspace

---

## 📋 Current Workspace

**Files:** 15 files
**Directories:** 1 directory (screenshots/)

**Notable Files:**
- `docling_research_summary.md` (26.7KB) - Docling research
- `filemanager_implementation_summary.md` - This implementation
- `filemanager_quick_reference.md` - This file
- Various test images and screenshots

---

## 🚀 Dynamic Features

**Auto-Loaded Context:**
- Complete file hierarchy loaded on startup
- File descriptions generated automatically
- Current workspace state always available
- No manual context updates needed

**Smart Descriptions:**
- Markdown, Python, JSON files recognized
- Test/sample/screenshot files labeled
- File sizes and timestamps included

---

## 💡 Usage Tips

1. **Check workspace first:** `list_files()` shows current state
2. **Use relative paths:** Simpler than absolute paths
3. **Confirm deletions:** Always use `confirm=True`
4. **Pattern matching:** Use `*.py` to filter by extension
5. **Read before modify:** Check file contents first

---

## 🧪 Testing Commands

```python
# List all files
list_files(".")

# List only markdown files
list_files(".", "*.md")

# Read a file
read_file("docling_research_summary.md")

# Create test file
create_file("test.txt", "Hello World!")

# Update file
update_file("test.txt", "Hello Updated World!")

# Copy file
copy_file("test.txt", "test_backup.txt")

# Move file
move_file("test.txt", "renamed.txt")

# Delete file (requires confirmation)
delete_file("renamed.txt", confirm=True)
```

---

## 📊 Implementation Details

**Agent Config:** `backend/agents/FileManager.json`
**Tools Module:** `backend/tools/file_management.py`
**Initialization:** `initialize_filemanager_agent()`
**Workspace Base:** `/home/rodrigo/agentic/backend/workspace/`

**System Prompt Placeholder:** `{{WORKSPACE_HIERARCHY}}`
- Replaced automatically on agent startup
- Contains full file/folder structure
- Updates on each agent initialization

---

## 🔄 Next Phase: Vector Store Integration

**Planned Tools:**
- `index_file_to_vectorstore()` - Index files for semantic search
- `search_files_semantic()` - Natural language file search
- `remove_file_from_vectorstore()` - Remove from index
- `list_indexed_files()` - Show indexed files

**Optional: Docling Integration**
- Multi-format support (PDF, DOCX, XLSX)
- Table extraction
- OCR for scanned documents
- Audio/video transcription

---

**Status:** ✅ Phase 1 Complete - Ready for Testing & Review
