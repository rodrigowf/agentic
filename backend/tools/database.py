# database.py - MongoDB database management tools with automatic schema tracking

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from utils.context import get_current_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DB_METADATA_PATH = Path("data/database")
DB_METADATA_PATH.mkdir(parents=True, exist_ok=True)
COLLECTIONS_SCHEMA_FILE = DB_METADATA_PATH / "collections_schema.json"

# MongoDB connection configuration
MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGODB_DATABASE", "agentic_db")

# Lazy initialization for MongoDB client
_mongo_client = None
_mongo_db = None

def _get_mongo_client():
    """Lazy initialization of MongoDB client"""
    global _mongo_client, _mongo_db
    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Test connection
            _mongo_client.admin.command('ping')
            _mongo_db = _mongo_client[MONGO_DB_NAME]
            logger.info(f"Connected to MongoDB: {MONGO_DB_NAME}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            error_msg = (
                f"MongoDB connection failed: {e}\n\n"
                "To enable MongoDB service:\n"
                "  sudo systemctl start mongodb\n"
                "  sudo systemctl enable mongodb  # (optional, to auto-start on boot)\n\n"
                "To check status:\n"
                "  sudo systemctl status mongodb\n\n"
                "See docs/DATABASE_AGENT_GUIDE.md for complete setup instructions."
            )
            raise ConnectionFailure(error_msg)
    return _mongo_client, _mongo_db

# --- Collection Schema Management ---

def _load_collections_schema() -> Dict[str, Dict]:
    """Load collection schemas from disk"""
    if COLLECTIONS_SCHEMA_FILE.exists():
        try:
            with open(COLLECTIONS_SCHEMA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading collections schema: {e}")
            return {}
    return {}

def _save_collections_schema(schema: Dict[str, Dict]):
    """Save collection schemas to disk"""
    try:
        with open(COLLECTIONS_SCHEMA_FILE, 'w') as f:
            json.dump(schema, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving collections schema: {e}")

def _get_collections_summary() -> str:
    """
    Get a formatted summary of all collections with their schemas.

    Returns:
        Formatted string listing all collections with descriptions and structures.
    """
    try:
        _, db = _get_mongo_client()
        schema = _load_collections_schema()

        # Get actual collections in database
        actual_collections = db.list_collection_names()

        if not actual_collections:
            return "(No collections in database yet)"

        result = []
        for coll_name in sorted(actual_collections):
            coll = db[coll_name]
            doc_count = coll.count_documents({})

            # Get schema info if available
            schema_info = schema.get(coll_name, {})
            description = schema_info.get('description', 'No description available')
            structure = schema_info.get('structure', {})
            usage = schema_info.get('usage', 'No usage notes')
            example = schema_info.get('example', None)

            coll_summary = [f"**{coll_name}** ({doc_count} documents)"]
            coll_summary.append(f"  Description: {description}")

            if structure:
                coll_summary.append(f"  Structure: {json.dumps(structure, indent=4)}")

            coll_summary.append(f"  Usage: {usage}")

            if example:
                coll_summary.append(f"  Example: {json.dumps(example, indent=4)}")

            result.append("\n".join(coll_summary))

        return "\n\n".join(result)
    except Exception as e:
        logger.error(f"Error getting collections summary: {e}")
        return "(Error loading collections)"

def _refresh_agent_system_message(agent=None):
    """
    Refreshes the agent's system message with current collections schema.
    This injects content into the {{COLLECTIONS_SCHEMA}} placeholder.

    Args:
        agent: The agent instance. If None, tries to get from context (for backward compatibility).
    """
    try:
        # If no agent provided, try to get from context (for backward compatibility)
        if agent is None:
            agent = get_current_agent()
            if agent is None:
                logger.warning("No current agent found in context. Cannot refresh system message.")
                return

        # Get collections summary
        collections_summary = _get_collections_summary()

        # Get the original system message template
        original_system_message = agent._system_messages[0].content if agent._system_messages else ""

        # Replace the placeholder with actual content
        updated_system_message = original_system_message.replace(
            "{{COLLECTIONS_SCHEMA}}",
            collections_summary
        )

        # Update the agent's system message
        if agent._system_messages:
            agent._system_messages[0].content = updated_system_message
            logger.info("Agent system message refreshed with current collections schema")
        else:
            logger.warning("Agent has no system messages to update")

    except Exception as e:
        logger.error(f"Error refreshing agent system message: {e}")

def initialize_database_agent(agent):
    """
    Initializes the Database agent by loading collections schema and injecting it into the system prompt.
    This should be called once when the agent is first created.

    Args:
        agent: The agent instance to initialize.

    Returns:
        Success or error message.
    """
    try:
        logger.info("Initializing Database agent with collections schema")

        # Ensure MongoDB connection
        _get_mongo_client()

        # Ensure schema file exists
        if not COLLECTIONS_SCHEMA_FILE.exists():
            COLLECTIONS_SCHEMA_FILE.write_text("{}", encoding='utf-8')
            logger.info("Created empty collections schema file")

        # Refresh the agent's system message with current schema
        _refresh_agent_system_message(agent)

        return "Database agent initialized successfully"
    except Exception as e:
        logger.error(f"Error initializing database agent: {e}")
        return f"Error initializing database agent: {str(e)}"

# --- Tool 1: Register Collection Schema ---

class RegisterCollectionSchemaInput(BaseModel):
    """Input model for registering collection schema"""
    collection_name: str = Field(description="The name of the collection")
    description: str = Field(description="Description of the collection's purpose")
    structure: Dict[str, Any] = Field(description="Field structure/schema definition (e.g., {'field_name': 'type'})")
    usage: str = Field(description="Usage notes and best practices")
    example: Optional[Dict[str, Any]] = Field(None, description="Example document")

def register_collection_schema(
    collection_name: str,
    description: str,
    structure: Dict[str, Any],
    usage: str,
    example: Optional[Dict[str, Any]] = None
) -> str:
    """
    Registers or updates a collection's schema metadata for documentation purposes.

    Args:
        collection_name: The name of the collection.
        description: Description of the collection's purpose.
        structure: Field structure/schema definition.
        usage: Usage notes and best practices.
        example: Example document (optional).

    Returns:
        Success message.
    """
    try:
        logger.info(f"Registering schema for collection: {collection_name}")

        schema = _load_collections_schema()

        schema[collection_name] = {
            "description": description,
            "structure": structure,
            "usage": usage,
            "example": example,
            "updated_at": datetime.now().isoformat()
        }

        _save_collections_schema(schema)

        # Refresh agent's system message with updated schema
        _refresh_agent_system_message()

        return f"Collection schema registered: {collection_name}"
    except Exception as e:
        logger.error(f"Error registering collection schema: {e}")
        return f"Error: {str(e)}"

register_collection_schema_tool = FunctionTool(
    func=register_collection_schema,
    description="Registers or updates a collection's schema metadata (description, structure, usage, example). Use this to document collections for future reference."
)

# --- Tool 2: Insert Document ---

class InsertDocumentInput(BaseModel):
    """Input model for inserting a document"""
    collection_name: str = Field(description="The name of the collection")
    document: Dict[str, Any] = Field(description="The document to insert")

def insert_document(collection_name: str, document: Dict[str, Any]) -> str:
    """
    Inserts a single document into a collection.

    Args:
        collection_name: The name of the collection.
        document: The document to insert.

    Returns:
        Success message with inserted ID.
    """
    try:
        logger.info(f"Inserting document into collection: {collection_name}")
        _, db = _get_mongo_client()
        collection = db[collection_name]

        result = collection.insert_one(document)

        return f"Document inserted with ID: {str(result.inserted_id)}"
    except Exception as e:
        logger.error(f"Error inserting document: {e}")
        return f"Error: {str(e)}"

insert_document_tool = FunctionTool(
    func=insert_document,
    description="Inserts a single document into a MongoDB collection. Returns the inserted document ID."
)

# --- Tool 3: Insert Many Documents ---

class InsertManyDocumentsInput(BaseModel):
    """Input model for inserting multiple documents"""
    collection_name: str = Field(description="The name of the collection")
    documents: List[Dict[str, Any]] = Field(description="List of documents to insert")

def insert_many_documents(collection_name: str, documents: List[Dict[str, Any]]) -> str:
    """
    Inserts multiple documents into a collection.

    Args:
        collection_name: The name of the collection.
        documents: List of documents to insert.

    Returns:
        Success message with count.
    """
    try:
        logger.info(f"Inserting {len(documents)} documents into collection: {collection_name}")
        _, db = _get_mongo_client()
        collection = db[collection_name]

        result = collection.insert_many(documents)

        return f"Inserted {len(result.inserted_ids)} documents successfully"
    except Exception as e:
        logger.error(f"Error inserting documents: {e}")
        return f"Error: {str(e)}"

insert_many_documents_tool = FunctionTool(
    func=insert_many_documents,
    description="Inserts multiple documents into a MongoDB collection in a single operation."
)

# --- Tool 4: Find Documents ---

class FindDocumentsInput(BaseModel):
    """Input model for finding documents"""
    collection_name: str = Field(description="The name of the collection")
    query: Dict[str, Any] = Field(description="MongoDB query filter")
    limit: Optional[int] = Field(10, description="Maximum number of documents to return")
    projection: Optional[Dict[str, int]] = Field(None, description="Fields to include/exclude")

def find_documents(
    collection_name: str,
    query: Dict[str, Any],
    limit: int = 10,
    projection: Optional[Dict[str, int]] = None
) -> str:
    """
    Finds documents in a collection matching the query.

    Args:
        collection_name: The name of the collection.
        query: MongoDB query filter (e.g., {'field': 'value'}).
        limit: Maximum number of documents to return.
        projection: Fields to include/exclude (e.g., {'field': 1}).

    Returns:
        JSON string of matching documents.
    """
    try:
        logger.info(f"Finding documents in collection: {collection_name}")
        _, db = _get_mongo_client()
        collection = db[collection_name]

        cursor = collection.find(query, projection).limit(limit)
        documents = list(cursor)

        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])

        result = {
            "count": len(documents),
            "documents": documents
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error finding documents: {e}")
        return f"Error: {str(e)}"

find_documents_tool = FunctionTool(
    func=find_documents,
    description="Finds documents in a MongoDB collection matching the query filter. Returns JSON array of matching documents."
)

# --- Tool 5: Update Document ---

class UpdateDocumentInput(BaseModel):
    """Input model for updating a document"""
    collection_name: str = Field(description="The name of the collection")
    query: Dict[str, Any] = Field(description="MongoDB query to find document(s)")
    update: Dict[str, Any] = Field(description="Update operations (e.g., {'$set': {'field': 'value'}})")
    update_many: Optional[bool] = Field(False, description="Update all matching documents (default: False)")

def update_document(
    collection_name: str,
    query: Dict[str, Any],
    update: Dict[str, Any],
    update_many: bool = False
) -> str:
    """
    Updates document(s) in a collection.

    Args:
        collection_name: The name of the collection.
        query: MongoDB query to find document(s).
        update: Update operations (e.g., {'$set': {'field': 'value'}}).
        update_many: Update all matching documents (default: False).

    Returns:
        Success message with count.
    """
    try:
        logger.info(f"Updating document(s) in collection: {collection_name}")
        _, db = _get_mongo_client()
        collection = db[collection_name]

        if update_many:
            result = collection.update_many(query, update)
            return f"Updated {result.modified_count} document(s)"
        else:
            result = collection.update_one(query, update)
            return f"Updated {result.modified_count} document"
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        return f"Error: {str(e)}"

update_document_tool = FunctionTool(
    func=update_document,
    description="Updates one or many documents in a MongoDB collection using update operations like $set, $inc, etc."
)

# --- Tool 6: Delete Document ---

class DeleteDocumentInput(BaseModel):
    """Input model for deleting documents"""
    collection_name: str = Field(description="The name of the collection")
    query: Dict[str, Any] = Field(description="MongoDB query to find document(s)")
    delete_many: Optional[bool] = Field(False, description="Delete all matching documents (default: False)")

def delete_document(
    collection_name: str,
    query: Dict[str, Any],
    delete_many: bool = False
) -> str:
    """
    Deletes document(s) from a collection.

    Args:
        collection_name: The name of the collection.
        query: MongoDB query to find document(s).
        delete_many: Delete all matching documents (default: False).

    Returns:
        Success message with count.
    """
    try:
        logger.info(f"Deleting document(s) from collection: {collection_name}")
        _, db = _get_mongo_client()
        collection = db[collection_name]

        if delete_many:
            result = collection.delete_many(query)
            return f"Deleted {result.deleted_count} document(s)"
        else:
            result = collection.delete_one(query)
            return f"Deleted {result.deleted_count} document"
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return f"Error: {str(e)}"

delete_document_tool = FunctionTool(
    func=delete_document,
    description="Deletes one or many documents from a MongoDB collection matching the query filter."
)

# --- Tool 7: Aggregate Query ---

class AggregateInput(BaseModel):
    """Input model for aggregation pipeline"""
    collection_name: str = Field(description="The name of the collection")
    pipeline: List[Dict[str, Any]] = Field(description="MongoDB aggregation pipeline stages")

def aggregate(collection_name: str, pipeline: List[Dict[str, Any]]) -> str:
    """
    Executes an aggregation pipeline on a collection.

    Args:
        collection_name: The name of the collection.
        pipeline: MongoDB aggregation pipeline stages.

    Returns:
        JSON string of aggregation results.
    """
    try:
        logger.info(f"Running aggregation on collection: {collection_name}")
        _, db = _get_mongo_client()
        collection = db[collection_name]

        cursor = collection.aggregate(pipeline)
        results = list(cursor)

        # Convert ObjectId to string
        for doc in results:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])

        return json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Error running aggregation: {e}")
        return f"Error: {str(e)}"

aggregate_tool = FunctionTool(
    func=aggregate,
    description="Executes a MongoDB aggregation pipeline for complex data processing, grouping, and transformations."
)

# --- Tool 8: Create Index ---

class CreateIndexInput(BaseModel):
    """Input model for creating an index"""
    collection_name: str = Field(description="The name of the collection")
    field_name: str = Field(description="The field to index")
    unique: Optional[bool] = Field(False, description="Create unique index (default: False)")

def create_index(collection_name: str, field_name: str, unique: bool = False) -> str:
    """
    Creates an index on a collection field.

    Args:
        collection_name: The name of the collection.
        field_name: The field to index.
        unique: Create unique index (default: False).

    Returns:
        Success message with index name.
    """
    try:
        logger.info(f"Creating index on {collection_name}.{field_name}")
        _, db = _get_mongo_client()
        collection = db[collection_name]

        result = collection.create_index([(field_name, 1)], unique=unique)

        return f"Index created: {result}"
    except Exception as e:
        logger.error(f"Error creating index: {e}")
        return f"Error: {str(e)}"

create_index_tool = FunctionTool(
    func=create_index,
    description="Creates an index on a collection field to improve query performance. Can create unique indexes."
)

# --- Tool 9: List Collections ---

def list_collections() -> str:
    """
    Lists all collections in the database.

    Returns:
        Formatted list of collections with document counts.
    """
    try:
        logger.info("Listing all collections")
        _, db = _get_mongo_client()

        collections = db.list_collection_names()

        if not collections:
            return "No collections exist yet."

        result = ["Collections in database:"]
        for coll_name in sorted(collections):
            count = db[coll_name].count_documents({})
            result.append(f"  - {coll_name} ({count} documents)")

        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        return f"Error: {str(e)}"

list_collections_tool = FunctionTool(
    func=list_collections,
    description="Lists all collections in the MongoDB database with document counts."
)

# --- Tool 10: Drop Collection ---

class DropCollectionInput(BaseModel):
    """Input model for dropping a collection"""
    collection_name: str = Field(description="The name of the collection to drop")

def drop_collection(collection_name: str) -> str:
    """
    Drops (deletes) a collection from the database.
    WARNING: This permanently deletes all documents in the collection.

    Args:
        collection_name: The name of the collection to drop.

    Returns:
        Success message.
    """
    try:
        logger.info(f"Dropping collection: {collection_name}")
        _, db = _get_mongo_client()

        db[collection_name].drop()

        # Remove from schema
        schema = _load_collections_schema()
        if collection_name in schema:
            del schema[collection_name]
            _save_collections_schema(schema)

        # Refresh agent's system message
        _refresh_agent_system_message()

        return f"Collection dropped: {collection_name}"
    except Exception as e:
        logger.error(f"Error dropping collection: {e}")
        return f"Error: {str(e)}"

drop_collection_tool = FunctionTool(
    func=drop_collection,
    description="Drops (permanently deletes) a collection and all its documents. Use with caution!"
)

# --- Export all tools ---

def get_database_tools() -> List[FunctionTool]:
    """Returns all database management tools"""
    return [
        register_collection_schema_tool,
        insert_document_tool,
        insert_many_documents_tool,
        find_documents_tool,
        update_document_tool,
        delete_document_tool,
        aggregate_tool,
        create_index_tool,
        list_collections_tool,
        drop_collection_tool,
    ]

# Make tools discoverable
tools = get_database_tools()

# --- Testing ---
if __name__ == "__main__":
    print("--- Database Tools Loaded ---")
    tools = get_database_tools()
    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"  Description: {tool.description}")
