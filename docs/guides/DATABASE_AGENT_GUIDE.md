# Database Agent Guide

**Agent Added:** 2025-12-01
**Location:** `backend/agents/Database.json`
**Tools:** `backend/tools/database.py`
**Status:** Production Ready

---

## Overview

The Database agent is a MongoDB database administrator that manages a full database cluster. It handles all CRUD operations, complex aggregation queries, indexing, and maintains automatic collection schema documentation.

## Key Features

### 1. Full CRUD Operations
- **Create**: Insert single or multiple documents
- **Read**: Query with filters, projections, and limits
- **Update**: Modify documents with MongoDB update operators
- **Delete**: Remove single or multiple documents

### 2. Advanced MongoDB Features
- **Aggregation Pipelines**: Complex data processing and analytics
- **Indexing**: Create indexes for performance optimization
- **Collection Management**: List, create, and drop collections

### 3. Automatic Schema Tracking
- **Collection Documentation**: Automatically maintains schemas
- **Dynamic System Prompt**: {{COLLECTIONS_SCHEMA}} placeholder
- **Real-time Updates**: Schema refreshes after changes
- **Comprehensive Metadata**: Structure, usage, examples

---

## Setup

### 1. Install MongoDB

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y mongodb
```

**Start MongoDB service (when needed):**
```bash
# Start temporarily (until next reboot)
sudo systemctl start mongodb

# OR start permanently (auto-start on boot)
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

**Check MongoDB status:**
```bash
sudo systemctl status mongodb
```

**Stop MongoDB (to save memory):**
```bash
sudo systemctl stop mongodb
```

**⚠️ Jetson Nano Note:** MongoDB is installed but disabled by default to conserve RAM (200-500MB). The Database agent tools will return helpful instructions if MongoDB isn't running. See [JETSON_DEPENDENCY_FIXES.md](JETSON_DEPENDENCY_FIXES.md) for details.

**macOS:**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Docker:**
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 2. Install Python Dependencies

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
pip install pymongo>=4.6.0
```

### 3. Configure Environment

Add to `/home/rodrigo/agentic/backend/.env`:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=agentic_db
```

**For remote MongoDB:**
```bash
MONGODB_URI=mongodb://username:password@host:27017/
```

**For MongoDB Atlas:**
```bash
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

### 4. Verify Installation

```bash
cd /home/rodrigo/agentic/backend
source venv/bin/activate
python3 test_database_agent.py
```

---

## Usage

### Agent Description

The agent is configured in [Database.json](../backend/agents/Database.json):

```json
{
  "name": "Database",
  "agent_type": "dynamic_init_looping",
  "initialization_function": "database.initialize_database_agent",
  "description": "A MongoDB database administrator that manages a full database cluster. Handles all CRUD operations (create, read, update, delete), aggregation queries, indexing, and maintains automatic collection schema documentation..."
}
```

### Available Tools

#### 1. **register_collection_schema**
Document a collection's schema for future reference.

```python
register_collection_schema(
    collection_name="users",
    description="User accounts and profiles",
    structure={
        "username": "string (unique)",
        "email": "string (unique)",
        "created_at": "datetime",
        "profile": "object"
    },
    usage="Store user account information. Index on username and email.",
    example={
        "username": "john_doe",
        "email": "john@example.com",
        "created_at": "2025-12-01T10:00:00Z",
        "profile": {"name": "John Doe", "age": 30}
    }
)
```

#### 2. **insert_document**
Insert a single document.

```python
insert_document(
    collection_name="users",
    document={
        "username": "jane_doe",
        "email": "jane@example.com",
        "created_at": "2025-12-01T10:30:00Z"
    }
)
# Returns: "Document inserted with ID: 507f1f77bcf86cd799439011"
```

#### 3. **insert_many_documents**
Bulk insert multiple documents.

```python
insert_many_documents(
    collection_name="users",
    documents=[
        {"username": "user1", "email": "user1@example.com"},
        {"username": "user2", "email": "user2@example.com"},
        {"username": "user3", "email": "user3@example.com"}
    ]
)
# Returns: "Inserted 3 documents successfully"
```

#### 4. **find_documents**
Query documents with filters.

```python
find_documents(
    collection_name="users",
    query={"username": "jane_doe"},
    limit=10,
    projection={"username": 1, "email": 1}
)
# Returns JSON array of matching documents
```

**Advanced Queries:**
```python
# Find with comparison operators
find_documents(
    collection_name="users",
    query={"age": {"$gte": 18, "$lt": 65}},
    limit=100
)

# Find with regex
find_documents(
    collection_name="users",
    query={"email": {"$regex": "@example.com$"}},
    limit=50
)
```

#### 5. **update_document**
Update one or many documents.

```python
# Update single document
update_document(
    collection_name="users",
    query={"username": "jane_doe"},
    update={"$set": {"email": "jane.doe@example.com"}},
    update_many=False
)

# Update multiple documents
update_document(
    collection_name="users",
    query={"status": "pending"},
    update={"$set": {"status": "active"}},
    update_many=True
)

# Increment a value
update_document(
    collection_name="users",
    query={"username": "jane_doe"},
    update={"$inc": {"login_count": 1}}
)
```

#### 6. **delete_document**
Delete one or many documents.

```python
# Delete single document
delete_document(
    collection_name="users",
    query={"username": "old_user"},
    delete_many=False
)

# Delete multiple documents
delete_document(
    collection_name="users",
    query={"status": "inactive"},
    delete_many=True
)
```

#### 7. **aggregate**
Run aggregation pipelines for complex queries.

```python
# Group by and count
aggregate(
    collection_name="users",
    pipeline=[
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
)

# Match, group, and sort
aggregate(
    collection_name="orders",
    pipeline=[
        {"$match": {"status": "completed"}},
        {"$group": {
            "_id": "$user_id",
            "total_spent": {"$sum": "$amount"},
            "order_count": {"$sum": 1}
        }},
        {"$sort": {"total_spent": -1}},
        {"$limit": 10}
    ]
)
```

#### 8. **create_index**
Create indexes for performance.

```python
# Regular index
create_index(
    collection_name="users",
    field_name="username",
    unique=False
)

# Unique index
create_index(
    collection_name="users",
    field_name="email",
    unique=True
)
```

#### 9. **list_collections**
List all collections in the database.

```python
list_collections()
# Returns:
# Collections in database:
#   - users (1234 documents)
#   - orders (5678 documents)
#   - products (910 documents)
```

#### 10. **drop_collection**
Permanently delete a collection.

```python
drop_collection(collection_name="old_data")
# WARNING: This deletes all documents!
```

---

## Automatic Schema Tracking

### How It Works

The Database agent uses the `{{COLLECTIONS_SCHEMA}}` placeholder in its system prompt, similar to the Memory agent's approach.

**Workflow:**
1. Agent starts → `initialize_database_agent()` is called
2. Loads collection schemas from `backend/database_metadata/collections_schema.json`
3. Queries MongoDB for actual collections
4. Combines schema metadata with collection stats
5. Injects formatted summary into `{{COLLECTIONS_SCHEMA}}` placeholder

**Schema File Location:**
```
backend/database_metadata/collections_schema.json
```

**Example Schema Entry:**
```json
{
  "users": {
    "description": "User accounts and profiles",
    "structure": {
      "username": "string (unique)",
      "email": "string (unique)",
      "created_at": "datetime",
      "profile": "object"
    },
    "usage": "Store user account information. Index on username and email.",
    "example": {
      "username": "john_doe",
      "email": "john@example.com",
      "created_at": "2025-12-01T10:00:00Z",
      "profile": {"name": "John Doe", "age": 30}
    },
    "updated_at": "2025-12-01T10:15:30.123456"
  }
}
```

### Runtime System Prompt

After initialization, the agent sees:

```
**CURRENT COLLECTIONS SCHEMA**:
**users** (1234 documents)
  Description: User accounts and profiles
  Structure: {
    "username": "string (unique)",
    "email": "string (unique)",
    "created_at": "datetime",
    "profile": "object"
  }
  Usage: Store user account information. Index on username and email.
  Example: {
    "username": "john_doe",
    "email": "john@example.com",
    "created_at": "2025-12-01T10:00:00Z",
    "profile": {"name": "John Doe", "age": 30}
  }

**orders** (5678 documents)
  Description: Customer orders and transactions
  ...
```

### Registering New Schemas

**Always register schemas when creating new collections:**

```python
# 1. Register the schema
register_collection_schema(
    collection_name="products",
    description="Product catalog",
    structure={
        "name": "string",
        "sku": "string (unique)",
        "price": "number",
        "category": "string",
        "in_stock": "boolean"
    },
    usage="Product inventory management. Index on SKU and category.",
    example={
        "name": "Laptop",
        "sku": "TECH-001",
        "price": 999.99,
        "category": "Electronics",
        "in_stock": True
    }
)

# 2. Create index for performance
create_index(collection_name="products", field_name="sku", unique=True)
create_index(collection_name="products", field_name="category")

# 3. Insert data
insert_document(
    collection_name="products",
    document={
        "name": "Laptop",
        "sku": "TECH-001",
        "price": 999.99,
        "category": "Electronics",
        "in_stock": True
    }
)
```

---

## Best Practices

### 1. Schema Documentation
✅ **Do**: Register schemas for every collection
```python
register_collection_schema(...)  # Always document!
```

❌ **Don't**: Create collections without schemas
```python
insert_document(collection_name="mystery_data", ...)  # Bad!
```

### 2. Indexing
✅ **Do**: Create indexes on frequently queried fields
```python
create_index(collection_name="users", field_name="email", unique=True)
```

❌ **Don't**: Skip indexes on large collections
```python
# Slow query on large collection without index
find_documents(collection_name="users", query={"email": "..."})
```

### 3. Bulk Operations
✅ **Do**: Use `insert_many_documents` for bulk inserts
```python
insert_many_documents(collection_name="logs", documents=[...1000 docs...])
```

❌ **Don't**: Loop with `insert_document`
```python
for doc in docs:
    insert_document(...)  # Slow!
```

### 4. Query Optimization
✅ **Do**: Use projections to limit returned fields
```python
find_documents(
    collection_name="users",
    query={"status": "active"},
    projection={"username": 1, "email": 1}  # Only return these fields
)
```

❌ **Don't**: Return all fields unnecessarily
```python
find_documents(collection_name="users", query={"status": "active"})  # Returns everything
```

### 5. Testing Queries
✅ **Do**: Test with limits first
```python
find_documents(collection_name="users", query={}, limit=10)  # Test query
```

❌ **Don't**: Run unbounded queries on production
```python
find_documents(collection_name="users", query={}, limit=1000000)  # Dangerous!
```

---

## Common Patterns

### User Management

```python
# Register schema
register_collection_schema(
    collection_name="users",
    description="User accounts",
    structure={"username": "string", "email": "string", "created_at": "datetime"},
    usage="User authentication and profiles",
    example={"username": "john", "email": "john@example.com"}
)

# Create indexes
create_index(collection_name="users", field_name="username", unique=True)
create_index(collection_name="users", field_name="email", unique=True)

# Insert user
insert_document(
    collection_name="users",
    document={"username": "john", "email": "john@example.com", "created_at": "2025-12-01"}
)

# Find user
find_documents(collection_name="users", query={"username": "john"})

# Update user
update_document(
    collection_name="users",
    query={"username": "john"},
    update={"$set": {"email": "newemail@example.com"}}
)
```

### Analytics

```python
# Count by category
aggregate(
    collection_name="products",
    pipeline=[
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
)

# Average price by category
aggregate(
    collection_name="products",
    pipeline=[
        {"$group": {
            "_id": "$category",
            "avg_price": {"$avg": "$price"},
            "total_products": {"$sum": 1}
        }}
    ]
)
```

### Data Migration

```python
# Bulk insert from external source
data = [...]  # Load from CSV/API/etc
insert_many_documents(collection_name="imported_data", documents=data)

# Update all documents with new field
update_document(
    collection_name="users",
    query={},
    update={"$set": {"migration_version": "v2"}},
    update_many=True
)
```

---

## Troubleshooting

### Connection Issues

**Problem**: "Failed to connect to MongoDB"

**Solution**:
```bash
# Check if MongoDB is running
sudo systemctl status mongodb

# Start MongoDB
sudo systemctl start mongodb

# Check connection
mongo --eval "db.adminCommand('ping')"
```

### Schema Not Updating

**Problem**: {{COLLECTIONS_SCHEMA}} placeholder not replaced

**Solution**:
```bash
# Check schema file exists
ls -la backend/database_metadata/collections_schema.json

# Verify initialization function
grep "initialize_database_agent" backend/agents/Database.json

# Check logs
tail -f backend/logs/backend.log | grep Database
```

### Permission Errors

**Problem**: "OperationFailure: not authorized"

**Solution**:
```bash
# Set MongoDB URI with credentials
export MONGODB_URI="mongodb://username:password@localhost:27017/"

# Or update .env file
echo "MONGODB_URI=mongodb://username:password@localhost:27017/" >> backend/.env
```

---

## Security Considerations

### 1. Connection Strings
- ⚠️ Never commit credentials to git
- ✅ Use environment variables
- ✅ Use `.env` file (gitignored)

### 2. Input Validation
- ⚠️ MongoDB injection possible with unsanitized input
- ✅ Agent validates inputs through Pydantic models
- ✅ All query parameters are typed

### 3. Access Control
- ⚠️ Agent has full database access
- ✅ Use MongoDB user permissions
- ✅ Create limited-access database users for production

**Example limited user:**
```bash
use agentic_db
db.createUser({
  user: "agentic_agent",
  pwd: "secure_password",
  roles: [{ role: "readWrite", db: "agentic_db" }]
})
```

---

## Integration with MainConversation

The Database agent is included in MainConversation's sub-agents:

```json
{
  "sub_agents": [
    "Manager",
    "Memory",
    "FileManager",
    "Database",
    "Researcher",
    "Engineer"
  ]
}
```

The Manager receives:
```
- Database: A MongoDB database administrator that manages a full database cluster.
  Handles all CRUD operations (create, read, update, delete), aggregation queries,
  indexing, and maintains automatic collection schema documentation. All collections
  are tracked with their structure, usage notes, and examples. Best for: persistent
  data storage, complex queries, data analytics, multi-document operations, and any
  task requiring database interactions.
```

---

## Related Documentation

- **Main Guide**: [CLAUDE.md](../CLAUDE.md) - Section on "Creating New Agents"
- **Implementation**: [database.py](../backend/tools/database.py) - MongoDB tools
- **Agent Config**: [Database.json](../backend/agents/Database.json)
- **Test Script**: [test_database_agent.py](../backend/test_database_agent.py)
- **Similar Pattern**: [Memory Agent](../backend/agents/Memory.json) - Uses {{SHORT_TERM_MEMORY}} placeholder

---

## Troubleshooting

### MongoDB Connection Refused

**Error:**
```
MongoDB connection failed: localhost:27017: [Errno 111] Connection refused

To enable MongoDB service:
  sudo systemctl start mongodb
  sudo systemctl enable mongodb  # (optional, to auto-start on boot)

To check status:
  sudo systemctl status mongodb
```

**Solution:**
```bash
# Start MongoDB service
sudo systemctl start mongodb

# Verify it's running
sudo systemctl status mongodb

# Try database operation again
```

### MongoDB Not Installed

**Error:**
```
ImportError: No module named 'pymongo'
```

**Solution:**
```bash
# Install pymongo
pip install pymongo>=4.6.0

# Install MongoDB server (if not already installed)
sudo apt-get install -y mongodb
```

### Memory Concerns on Jetson Nano

**Issue:** MongoDB consumes 200-500MB RAM when running.

**Solutions:**

1. **Start/Stop as needed:**
   ```bash
   # Before using Database agent
   sudo systemctl start mongodb

   # After using Database agent
   sudo systemctl stop mongodb
   ```

2. **Use on-demand only:**
   - Keep MongoDB disabled by default
   - Start it only when Database agent is actively needed
   - Stop after completing database tasks

3. **Monitor memory:**
   ```bash
   # Check MongoDB memory usage
   ps aux | grep mongod

   # Check total system memory
   free -h
   ```

### Collection Schema Not Updating

**Issue:** {{COLLECTIONS_SCHEMA}} placeholder not refreshing after schema changes.

**Solution:**
```bash
# Restart backend to reload agent
sudo systemctl restart agentic-backend

# Or manually trigger initialization (in Python)
from tools.database import initialize_database_agent
initialize_database_agent()
```

### Permission Denied on Data Directory

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/var/lib/mongodb'
```

**Solution:**
```bash
# Fix MongoDB data directory permissions
sudo chown -R mongodb:mongodb /var/lib/mongodb
sudo systemctl restart mongodb
```

---

## Changelog

### 2025-12-01 - Initial Implementation
- Created MongoDB tools module with 10 tools
- Implemented automatic schema tracking
- Created Database agent with dynamic initialization
- Added {{COLLECTIONS_SCHEMA}} placeholder support
- Integrated into MainConversation
- Created comprehensive test suite
- Added helpful error messages with service enable instructions
- Updated setup documentation for Jetson Nano deployment

---

**Status:** Production Ready (requires MongoDB installation)
**Dependencies:** MongoDB 3.6+, pymongo>=4.6.0
**Breaking Changes:** None
**Jetson Note:** MongoDB installed but disabled by default to conserve RAM
