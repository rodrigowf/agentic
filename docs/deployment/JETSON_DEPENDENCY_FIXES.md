# Jetson Nano Dependency Fixes

**Date:** 2025-12-01
**Platform:** Jetson Nano (ARM64, Ubuntu 18.04.6 LTS)
**Environment:** Conda (agentic environment)

---

## Overview

This document describes the dependency installation and configuration for the Memory and Database agents on the Jetson Nano server. Due to ARM64 architecture and older system libraries, some packages required special handling.

---

## Memory Agent Dependencies

### Problem

The Memory agent requires ChromaDB for vector similarity search, but ChromaDB has several dependencies that are difficult to install on ARM64:

1. **NumPy 2.0 incompatibility** - ChromaDB 0.4.24 requires NumPy < 2.0
2. **Rust compilation issues** - Some dependencies require Rust 2024 edition (not available on Jetson)
3. **Tokenizers dependency** - Required for embedding functions, needs pre-built binaries

### Solution

**Step 1: Downgrade NumPy**

```bash
ssh rodrigo@192.168.0.200
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic
pip install "numpy<2.0"
```

**Result:** NumPy downgraded from 2.0.1 → 1.26.4

**Step 2: Install chroma-hnswlib**

```bash
pip install chroma-hnswlib==0.7.3
```

**Result:** Exact version required by ChromaDB 0.4.24

**Step 3: Install tokenizers via conda-forge**

```bash
conda install -y -c conda-forge tokenizers
```

**Result:** Installed tokenizers 0.22.1 with pre-built ARM64 binary (including hf-xet dependency)

**Step 4: Verify installation**

```bash
python -c "import chromadb; print('✅ chromadb version:', chromadb.__version__); client = chromadb.Client(); print('✅ Client created successfully')"
```

**Output:**
```
✅ chromadb version: 0.4.24
✅ Client created successfully
```

### Memory Agent Tools

All 8 memory tools now load successfully:

- `get_short_term_memory` - Retrieve current short-term memory
- `overwrite_short_term_memory` - Update short-term memory
- `create_memory_bank` - Create new vector database
- `add_to_memory` - Add information to memory bank
- `search_memory` - Semantic similarity search
- `replace_data` - Update existing memory
- `remove_data` - Delete from memory bank
- `list_memory_banks` - List all memory banks

---

## Database Agent Dependencies

### Problem

The Database agent requires MongoDB for document storage, but:

1. **Conda conflicts** - MongoDB 4.2.14 (conda) requires OpenSSL 1.1.x, but Node.js 20 requires OpenSSL 3.x
2. **Resource constraints** - Jetson Nano has limited RAM (4GB), running MongoDB 24/7 wastes memory
3. **PyMongo installed** - Python client already available via conda

### Solution

**Step 1: Install MongoDB system-wide (via apt)**

```bash
ssh rodrigo@192.168.0.200
sudo apt-get update
sudo apt-get install -y mongodb
```

**Result:** MongoDB 3.6.3 installed (~203 MB disk space)

**Step 2: Disable MongoDB service (save memory)**

```bash
sudo systemctl stop mongodb
sudo systemctl disable mongodb
```

**Why:** MongoDB consumes 200-500MB RAM when running. Keep service disabled until needed.

**Step 3: Verify pymongo**

```bash
python -c "import pymongo; print('✅ pymongo version:', pymongo.__version__)"
```

**Output:**
```
✅ pymongo version: 4.13.0
```

### Database Agent Tools

All 10 database tools now load successfully:

- `insert_document` - Insert single document
- `insert_many_documents` - Bulk insert
- `find_documents` - Query with filters
- `update_document` - Update operations
- `delete_document` - Delete operations
- `aggregate` - Aggregation pipelines
- `create_index` - Performance optimization
- `list_collections` - List all collections
- `register_collection_schema` - Document collection structure
- `drop_collection` - Delete collection

### Enabling MongoDB When Needed

**Start MongoDB temporarily:**
```bash
sudo systemctl start mongodb
```

**Start MongoDB permanently (auto-start on boot):**
```bash
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

**Check status:**
```bash
sudo systemctl status mongodb
```

**Stop MongoDB:**
```bash
sudo systemctl stop mongodb
```

### Error Handling

When Database agent tools are called without MongoDB running, they return a helpful error message:

```
MongoDB connection failed: localhost:27017: [Errno 111] Connection refused

To enable MongoDB service:
  sudo systemctl start mongodb
  sudo systemctl enable mongodb  # (optional, to auto-start on boot)

To check status:
  sudo systemctl status mongodb

See docs/DATABASE_AGENT_GUIDE.md for complete setup instructions.
```

---

## API Agent Dependencies

All API agent tools loaded successfully without additional dependencies:

**From api.py:**
- `http_request` - Make HTTP calls
- `save_api_docs` - Save documentation
- `read_api_docs` - Read documentation
- `get_api_index` - List all APIs
- `delete_api_docs` - Delete documentation

**From api_tools.py:**
- `http_call` - HTTP execution
- `register_api` - Register new API
- `get_api_documentation` - Get API docs
- `list_apis` - List registered APIs

---

## Verification

### Check All Tools Loaded

```bash
curl -s http://localhost:8000/api/tools | python3 -m json.tool | grep '"name"' | wc -l
```

**Expected:** 39 tools (as of 2025-12-01)

### Check Memory Tools

```bash
curl -s http://localhost:8000/api/tools | python3 -c "import sys, json; data = json.load(sys.stdin); tools = [t['name'] for t in data if 'memory.py' in t['filename']]; print('\n'.join(sorted(tools)))"
```

### Check Database Tools

```bash
curl -s http://localhost:8000/api/tools | python3 -c "import sys, json; data = json.load(sys.stdin); tools = [t['name'] for t in data if 'database.py' in t['filename']]; print('\n'.join(sorted(tools)))"
```

---

## Summary

| Agent | Status | Dependencies | Notes |
|-------|--------|--------------|-------|
| **Memory** | ✅ Enabled | ChromaDB 0.4.24, NumPy 1.26.4, tokenizers 0.22.1 | All tools loaded successfully |
| **Database** | ✅ Enabled | PyMongo 4.13.0, MongoDB 3.6.3 (disabled) | MongoDB service disabled by default to save RAM |
| **API** | ✅ Enabled | None (uses requests library) | All tools loaded successfully |

**Memory Usage:**
- ChromaDB: ~50-100MB when in use (lazy loading)
- MongoDB (when enabled): ~200-500MB
- Recommended: Keep MongoDB disabled until needed

**Environment Backup:**
```bash
# Backup created before changes
~/agentic-env-backup-20251201-061443.yml
```

---

## Troubleshooting

### ChromaDB Import Error

```python
import chromadb  # AttributeError: np.float_ was removed
```

**Fix:** Downgrade NumPy to 1.26.4
```bash
pip install "numpy<2.0"
```

### Tokenizers Build Error

```
error: failed to parse the 'edition' key (Rust 2024 edition not supported)
```

**Fix:** Install via conda-forge (pre-built binary)
```bash
conda install -y -c conda-forge tokenizers
```

### MongoDB Connection Refused

```
pymongo.errors.ConnectionFailure: localhost:27017: [Errno 111] Connection refused
```

**Fix:** Start MongoDB service
```bash
sudo systemctl start mongodb
```

---

## Related Documentation

- [DATABASE_AGENT_GUIDE.md](DATABASE_AGENT_GUIDE.md) - Complete Database agent usage
- [JETSON_DEPLOYMENT_GUIDE.md](JETSON_DEPLOYMENT_GUIDE.md) - Server deployment guide
- [CLAUDE.md](../CLAUDE.md) - Main development documentation

---

**Last Updated:** 2025-12-01
**Tested On:** Jetson Nano (ARM64, Ubuntu 18.04.6 LTS, conda agentic environment)
