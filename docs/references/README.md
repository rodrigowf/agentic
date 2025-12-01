# Reference Code & Examples

This folder contains reference implementations, code examples, and Jupyter notebooks from AutoGen documentation and legacy implementations.

---

## Python Reference Files

### `AssistantAgent.py`
- **Purpose:** Reference implementation of AutoGen's AssistantAgent class
- **Source:** AutoGen library source code
- **Use:** Understanding AssistantAgent internals and capabilities

### `autogen_agentchat.agents._code_executor_agent.py`
- **Purpose:** Reference implementation of code executor agent
- **Source:** AutoGen library source code
- **Use:** Understanding code execution capabilities in agents

### `memory.py`
- **Purpose:** Legacy memory agent implementation (v0.2 AutoGen)
- **Status:** Historical reference - DO NOT USE directly
- **Note:** Modern implementation is in `backend/tools/memory.py`
- **Use:** Understanding original memory system design

### `vectorstore.py`
- **Purpose:** Legacy vector store implementation using FAISS
- **Status:** Historical reference - replaced by ChromaDB
- **Use:** Understanding original embedding/similarity search approach

---

## Jupyter Notebooks

### `group-chat.ipynb`
- **Purpose:** AutoGen group chat examples and patterns
- **Use:** Learning multi-agent conversation orchestration

### `selector-group-chat.ipynb`
- **Purpose:** Selector group chat pattern examples
- **Use:** Understanding orchestrator-based agent selection

### `multimodality-images.ipynb`
- **Purpose:** Multimodal agent examples with images
- **Use:** Learning how to integrate images with AutoGen agents

### `termination.ipynb`
- **Purpose:** Agent termination condition examples
- **Use:** Understanding when and how to stop agent conversations

---

## Text Documentation

### `autogen_migration-guide.txt`
- **Purpose:** Official AutoGen v0.2 to v0.4 migration guide
- **Source:** AutoGen documentation
- **Use:** Understanding breaking changes and migration path
- **Note:** Project currently uses AutoGen 0.5.x

---

## How to Use These References

### For Learning
1. **New to AutoGen?** Start with the notebooks (`group-chat.ipynb`, `selector-group-chat.ipynb`)
2. **Adding multimodal features?** See `multimodality-images.ipynb`
3. **Understanding termination?** Check `termination.ipynb`

### For Implementation
1. **Do NOT copy code directly** - These are older implementations
2. **Use as reference** to understand patterns and approaches
3. **Check current implementations** in `backend/` for modern versions

### For Migration
- Consult `autogen_migration-guide.txt` when updating AutoGen versions
- Cross-reference with official AutoGen documentation

---

## Relationship to Current Codebase

| Reference File | Current Implementation | Location |
|----------------|------------------------|----------|
| `memory.py` (legacy) | Memory agent with ChromaDB | `backend/tools/memory.py` |
| `vectorstore.py` (legacy) | ChromaDB integration | Used in memory tools |
| `AssistantAgent.py` | Looping agents | `backend/core/looping_agent.py` |
| `_code_executor_agent.py` | Code executor agent | `backend/core/looping_code_executor_agent.py` |
| Group chat notebooks | Nested team agents | `backend/core/nested_agent.py` |
| Multimodality notebook | Multimodal agents | `backend/core/multimodal_tools_looping_agent.py` |

---

## Important Notes

### ⚠️ **Do Not Use Directly**
These files are **reference only**. The codebase has evolved significantly:
- Uses AutoGen 0.5.x (not 0.2 or 0.4)
- Uses ChromaDB (not FAISS)
- Different agent architecture
- Modern async patterns

### ✅ **When to Reference**
- Understanding AutoGen concepts and patterns
- Designing new agent types
- Debugging agent behavior
- Learning best practices

### 🔄 **Updating**
If you add new reference files:
1. Add description to this README
2. Note the source and version
3. Explain relationship to current implementation
4. Mark as legacy/reference if outdated

---

**Last Updated:** 2025-12-01
