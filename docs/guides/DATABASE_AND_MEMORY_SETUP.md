# Database and Memory System Setup Guide

**Last Updated:** 2025-12-02
**Status:** Production Ready
**Applies To:** Jetson Nano and local development

---

## Table of Contents

1. [Overview](#overview)
2. [MongoDB Setup](#mongodb-setup)
3. [ChromaDB Memory Setup](#chromadb-memory-setup)
4. [Environment Configuration](#environment-configuration)
5. [Verification](#verification)
6. [Version Compatibility](#version-compatibility)
7. [Troubleshooting](#troubleshooting)
8. [Migration Guide](#migration-guide)

---

## Overview

The agentic system uses two database systems:

- **MongoDB**: Document database for structured data (Database agent)
- **ChromaDB**: Vector database for semantic memory search (Memory agent)

Both systems work together to provide comprehensive data storage and retrieval capabilities.

---

## MongoDB Setup

### Jetson Nano (Production)

**Installation:**
```bash
# Install MongoDB 3.6 (latest available for Ubuntu 18.04)
sudo apt-get update
sudo apt-get install -y mongodb

# Verify installation
mongod --version
# Expected: db version v3.6.3
```

**Enable and Start Service:**
```bash
# Start MongoDB
sudo systemctl start mongodb

# Enable auto-start on boot
sudo systemctl enable mongodb

# Check status
sudo systemctl status mongodb
```

**Install Compatible PyMongo:**
```bash
# MongoDB 3.6 requires PyMongo 3.x
cd ~/agentic/backend
source ~/miniconda3/etc/profile.d/conda.sh
conda activate agentic
pip install --no-deps pymongo==3.12.3
```

**Configuration:**
- **Port:** 27017 (default)
- **Database:** agentic_db
- **Access:** localhost only (no authentication for local use)

### Local Development

For local development, you can either:

**Option 1: Use Jetson's MongoDB remotely**
```bash
# In .env file
MONGODB_URI=mongodb://192.168.0.200:27017/
MONGODB_DATABASE=agentic_db
```

**Option 2: Install MongoDB locally**
```bash
# macOS
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community

# Ubuntu 20.04+ (MongoDB 4.4+)
wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod

# Use PyMongo 4.x for MongoDB 4.0+
pip install pymongo>=4.6.0
```

**Option 3: Docker (recommended for development)**
```bash
# Run MongoDB 4.4 in Docker
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -v ~/mongodb-data:/data/db \
  mongo:4.4

# Use PyMongo 4.x
pip install pymongo>=4.6.0
```

---

## ChromaDB Memory Setup

### Installation

ChromaDB is installed via pip with specific version requirements:

```bash
cd ~/agentic/backend
source venv/bin/activate  # or conda activate agentic

# Install ChromaDB with dependencies
pip install chromadb==0.4.24

# Required dependencies
pip install "numpy<2.0"  # ChromaDB 0.4.24 requires NumPy < 2.0

# On Jetson Nano (ARM64), install tokenizers via conda
conda install -y -c conda-forge tokenizers
```

### Data Structure

ChromaDB stores data in:
```
backend/data/memory/
├── chroma_db/                    # ChromaDB vector database
│   ├── chroma.sqlite3           # Metadata and collections
│   └── {collection_id}/         # HNSW vector indexes
│       ├── data_level0.bin
│       ├── header.bin
│       ├── length.bin
│       └── link_lists.bin
├── memory_index.json            # Memory bank registry
└── short_term_memory.txt        # Short-term context
```

### Creating Memory Banks

Memory banks are created automatically when the Memory agent runs, or you can create them programmatically:

```python
from tools.memory import create_memory_bank, add_to_memory

# Create a new memory bank
create_memory_bank(
    "project_info",
    "Stores project-related information and requirements"
)

# Add information
add_to_memory(
    "project_info",
    "The agentic system uses AutoGen for multi-agent orchestration."
)
```

### Embeddings Configuration

ChromaDB uses OpenAI embeddings by default:

- **Model:** `text-embedding-3-small`
- **Dimensions:** 1536
- **API Key:** Configured in `.env` (OPENAI_API_KEY)

**Cost Consideration:**
- ~$0.00002 per 1K tokens
- Typical document: 100-500 tokens
- Cost per document: $0.000002-$0.00001

---

## Environment Configuration

### .env File Setup

Add these configurations to `/home/rodrigo/agentic/backend/.env`:

```bash
# OpenAI (required for embeddings)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic (optional, for Claude models)
ANTHROPIC_API_KEY=your_anthropic_key_here

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=agentic_db

# For remote MongoDB (optional)
# MONGODB_URI=mongodb://192.168.0.200:27017/
```

### Memory Configuration

The Memory agent automatically loads configuration from:

**Location:** `backend/agents/Memory.json`

Key settings:
- `initialization_function`: `"memory.initialize_memory_agent"`
- Tools: 8 memory management tools
- Short-term memory placeholder: `{{SHORT_TERM_MEMORY}}`
- Memory banks placeholder: `{{MEMORY_BANKS}}`

### Database Configuration

The Database agent configuration:

**Location:** `backend/agents/Database.json`

Key settings:
- `initialization_function`: `"database.initialize_database_agent"`
- Tools: 10 MongoDB operation tools
- Collections schema placeholder: `{{COLLECTIONS_SCHEMA}}`

---

## Verification

### Check MongoDB

```bash
# On Jetson
ssh rodrigo@192.168.0.200

# Check service status
sudo systemctl status mongodb

# Test connection
mongo --eval "db.adminCommand('ping')"
# Expected: { "ok" : 1 }

# Check Python connectivity
python3 << EOF
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
print(f"MongoDB version: {client.server_info()['version']}")
print(f"Databases: {client.list_database_names()}")
EOF
```

### Check ChromaDB

```bash
cd ~/agentic/backend
source venv/bin/activate  # or conda activate agentic

python3 << EOF
import sys
sys.path.insert(0, '/home/rodrigo/agentic/backend')
from tools.memory import _get_chroma_client, _load_memory_index

# Test ChromaDB connection
client = _get_chroma_client()
collections = client.list_collections()
print(f"ChromaDB collections: {len(collections)}")
for coll in collections:
    print(f"  - {coll.name}: {coll.count()} documents")

# Test memory index
index = _load_memory_index()
print(f"Memory banks: {list(index.keys())}")
EOF
```

### Check Tools Loaded

```bash
# Check via API
curl -s http://192.168.0.200/api/tools | python3 -c "
import sys, json
data = json.load(sys.stdin)
memory = [t['name'] for t in data if 'memory.py' in t.get('filename', '')]
database = [t['name'] for t in data if 'database.py' in t.get('filename', '')]
print(f'Memory tools: {len(memory)}')
print(f'Database tools: {len(database)}')
"
```

**Expected Output:**
```
Memory tools: 8
Database tools: 10
```

---

## Version Compatibility

### Jetson Nano (ARM64, Ubuntu 18.04)

| Component | Version | Reason |
|-----------|---------|--------|
| MongoDB | 3.6.3 | Latest available for Ubuntu 18.04 |
| PyMongo | 3.12.3 | Compatible with MongoDB 3.6 |
| ChromaDB | 0.4.24 | Stable version with good ARM64 support |
| NumPy | 1.26.4 | ChromaDB 0.4.24 requires < 2.0 |
| Tokenizers | 0.22.1 | Pre-built ARM64 binary via conda-forge |

### Desktop Development (x86_64, Ubuntu 20.04+)

| Component | Version | Reason |
|-----------|---------|--------|
| MongoDB | 4.4+ | Modern features, better performance |
| PyMongo | 4.13.0+ | Full feature support |
| ChromaDB | 0.4.24 | Match Jetson for consistency |
| NumPy | 1.26.4 | ChromaDB compatibility |

### Key Version Notes

**MongoDB 3.6 vs 4.0+:**
- MongoDB 3.6 lacks some modern features (transactions, change streams)
- All Database agent operations work correctly on 3.6
- For production with modern MongoDB features, use Docker on Jetson

**PyMongo Compatibility:**
- PyMongo 4.x requires MongoDB 4.0+
- PyMongo 3.12.3 works with MongoDB 3.6-4.x
- Always match PyMongo version to your MongoDB version

**ChromaDB:**
- Version 0.4.24 has stable schema
- Requires NumPy < 2.0
- ARM64 support via conda-forge tokenizers

---

## Troubleshooting

### MongoDB Issues

**Problem: MongoDB won't start**
```bash
# Check logs
sudo journalctl -u mongodb -n 50

# Common fix: Remove lock file
sudo rm /var/lib/mongodb/mongod.lock
sudo chown -R mongodb:mongodb /var/lib/mongodb
sudo systemctl restart mongodb
```

**Problem: "tuple indices must be integers or slices, not str"**

This indicates PyMongo version mismatch. Fix:
```bash
# For MongoDB 3.6
pip install --no-deps pymongo==3.12.3

# For MongoDB 4.0+
pip install --no-deps pymongo>=4.6.0
```

**Problem: Connection refused**
```bash
# Check if MongoDB is running
sudo systemctl status mongodb

# Start if not running
sudo systemctl start mongodb

# Check port
ss -tlnp | grep 27017
```

### ChromaDB Issues

**Problem: "no such column: collections.topic"**

This means you have an old database with incompatible schema. Fix:
```bash
# Backup old database
mv backend/data/memory/chroma_db backend/data/memory/chroma_db_old

# Recreate with current schema (see Migration Guide below)
```

**Problem: "AttributeError: np.float_ was removed"**

NumPy 2.0 compatibility issue:
```bash
pip install "numpy<2.0"
```

**Problem: "error: failed to parse the 'edition' key (Rust 2024)"**

Tokenizers build issue on ARM64:
```bash
# Use conda-forge pre-built binary
conda install -y -c conda-forge tokenizers
```

**Problem: "Embedding dimension mismatch"**

ChromaDB is using wrong embedding function:
```python
# Ensure collection uses OpenAI embeddings (1536 dims)
# Check when creating collection:
collection = client.create_collection(
    name="my_collection",
    metadata={"hnsw:space": "l2"}  # Don't specify embedding function
)
# Then manually add with OpenAI embeddings
```

### Memory Agent Issues

**Problem: Memory bank not found**

```bash
# Check memory_index.json
cat backend/data/memory/memory_index.json

# Recreate if empty
python3 << EOF
from tools.memory import create_memory_bank
create_memory_bank("personal_info", "User information")
EOF
```

**Problem: Short-term memory not loading**

```bash
# Check file exists
ls -la backend/data/memory/short_term_memory.txt

# Recreate if missing
touch backend/data/memory/short_term_memory.txt
```

---

## Migration Guide

### From Old ChromaDB Schema

If you have an old ChromaDB database with schema incompatibility:

**Step 1: Extract documents**
```python
import sqlite3
import json

# Connect to old database
conn = sqlite3.connect('backend/data/memory/chroma_db/chroma.sqlite3')
cursor = conn.cursor()

# Extract documents
cursor.execute("""
SELECT e.embedding_id, em.string_value
FROM embeddings e
JOIN embedding_metadata em ON e.id = em.id
WHERE em.key = 'chroma:document'
ORDER BY e.seq_id
""")

documents = []
for embedding_id, document in cursor.fetchall():
    documents.append({
        'id': embedding_id,
        'document': document
    })

# Save for migration
with open('/tmp/chroma_documents.json', 'w') as f:
    json.dump(documents, f, indent=2)

conn.close()
print(f"Extracted {len(documents)} documents")
```

**Step 2: Backup and remove old database**
```bash
mv backend/data/memory/chroma_db backend/data/memory/chroma_db_backup
mkdir -p backend/data/memory/chroma_db
```

**Step 3: Recreate with new schema**
```python
import sys
sys.path.insert(0, '/home/rodrigo/agentic/backend')
import json
import os
from dotenv import dotenv_values

# Load environment
env_vars = dotenv_values('.env')
os.environ.update(env_vars)

from tools.memory import _get_chroma_client, _get_openai_client, _save_memory_index

# Create fresh client
client = _get_chroma_client()

# Get memory banks from backup
with open('backend/data/memory/chroma_db_backup/../memory_index.json') as f:
    old_index = json.load(f)

# Load extracted documents
with open('/tmp/chroma_documents.json') as f:
    documents = json.load(f)

# Get OpenAI client
openai_client = _get_openai_client()

# Group documents by collection (if you had multiple)
# For single collection 'personal_info':
collection_name = 'personal_info'
collection_desc = old_index.get(collection_name, 'User information')

# Create collection
collection = client.create_collection(
    name=collection_name,
    metadata={"description": collection_desc}
)

# Add documents with embeddings
for doc in documents:
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=doc['document']
    )
    embedding = response.data[0].embedding

    collection.add(
        ids=[doc['id']],
        documents=[doc['document']],
        embeddings=[embedding]
    )

print(f"Migrated {collection.count()} documents to {collection_name}")

# Update index
_save_memory_index(old_index)
```

**Step 4: Verify migration**
```python
from tools.memory import _get_chroma_client

client = _get_chroma_client()
collections = client.list_collections()

for coll in collections:
    print(f"{coll.name}: {coll.count()} documents")
    # Test peek
    if coll.count() > 0:
        results = coll.peek(limit=3)
        for i, doc in enumerate(results['documents'], 1):
            print(f"  {i}. {doc[:80]}...")
```

### From MongoDB 3.6 to 4.0+

If upgrading MongoDB version:

**Step 1: Backup data**
```bash
# Export all databases
mongodump --out=/tmp/mongodb_backup

# Or specific database
mongodump --db=agentic_db --out=/tmp/mongodb_backup
```

**Step 2: Install MongoDB 4.0+ (via Docker recommended)**
```bash
# Stop old MongoDB
sudo systemctl stop mongodb
sudo systemctl disable mongodb

# Run MongoDB 4.4 in Docker
docker run -d \
  --name mongodb \
  --restart unless-stopped \
  -p 27017:27017 \
  -v ~/mongodb-data:/data/db \
  mongo:4.4
```

**Step 3: Restore data**
```bash
# Restore to new MongoDB
mongorestore /tmp/mongodb_backup

# Verify
mongo agentic_db --eval "db.getCollectionNames()"
```

**Step 4: Upgrade PyMongo**
```bash
pip install --no-deps pymongo>=4.6.0
```

**Step 5: Restart backend**
```bash
sudo systemctl restart agentic-backend
```

---

## Related Documentation

- **[DATABASE_AGENT_GUIDE.md](DATABASE_AGENT_GUIDE.md)** - Database agent usage and tools
- **[JETSON_DEPLOYMENT_GUIDE.md](../deployment/JETSON_DEPLOYMENT_GUIDE.md)** - Complete Jetson setup
- **[JETSON_DEPENDENCY_FIXES.md](../deployment/JETSON_DEPENDENCY_FIXES.md)** - ARM64 dependency solutions
- **[CLAUDE.md](../../CLAUDE.md)** - Main project documentation

---

## Quick Reference Commands

```bash
# === MongoDB ===
# Start/stop service
sudo systemctl start mongodb
sudo systemctl stop mongodb
sudo systemctl status mongodb

# Test connection
mongo --eval "db.adminCommand('ping')"

# === ChromaDB ===
# Check collections
python3 -c "from tools.memory import _get_chroma_client; print(_get_chroma_client().list_collections())"

# === Backend ===
# Restart after changes
sudo systemctl restart agentic-backend

# Check logs
sudo journalctl -u agentic-backend -f

# === Tools Verification ===
# Check loaded tools
curl -s http://192.168.0.200/api/tools | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total tools: {len(data)}')
"
```

---

**Document Maintained By:** Claude Code
**Last Updated:** 2025-12-02
**Status:** Production Ready
