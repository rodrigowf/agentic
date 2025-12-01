# memory.py - Modern memory management tools using ChromaDB and OpenAI embeddings

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from utils.context import get_current_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
MEMORY_BASE_PATH = Path("data/memory")
MEMORY_BASE_PATH.mkdir(parents=True, exist_ok=True)
SHORT_TERM_MEMORY_FILE = MEMORY_BASE_PATH / "short_term_memory.txt"
MEMORY_INDEX_FILE = MEMORY_BASE_PATH / "memory_index.json"
CHROMA_PERSIST_DIR = str(MEMORY_BASE_PATH / "chroma_db")

# Lazy initialization for OpenAI client and ChromaDB
_openai_client = None
_chroma_client = None

def _get_openai_client():
    """Lazy initialization of OpenAI client"""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client

def _get_chroma_client():
    """Lazy initialization of ChromaDB client"""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client

# --- Memory Index Management ---

def _load_memory_index() -> Dict[str, str]:
    """Load the memory banks index from disk"""
    if MEMORY_INDEX_FILE.exists():
        try:
            with open(MEMORY_INDEX_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memory index: {e}")
            return {}
    return {}

def _save_memory_index(index: Dict[str, str]):
    """Save the memory banks index to disk"""
    try:
        with open(MEMORY_INDEX_FILE, 'w') as f:
            json.dump(index, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving memory index: {e}")

def _get_embedding(text: str) -> List[float]:
    """Generate embedding for text using OpenAI"""
    try:
        client = _get_openai_client()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise

def _get_memory_banks_summary() -> str:
    """
    Get a formatted summary of all available memory banks.

    Returns:
        Formatted string listing all memory banks with descriptions and counts.
    """
    try:
        index = _load_memory_index()

        if not index:
            return "(No memory banks created yet)"

        result = []
        client = _get_chroma_client()
        for name, description in index.items():
            try:
                collection = client.get_collection(name=name)
                count = collection.count()
                result.append(f"- **{name}**: {description} ({count} entries)")
            except Exception:
                result.append(f"- **{name}**: {description} (collection not found)")

        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error getting memory banks summary: {e}")
        return "(Error loading memory banks)"

def _refresh_agent_system_message(agent=None):
    """
    Refreshes the agent's system message with current short-term memory content
    and available memory banks list.
    This injects content into the {{SHORT_TERM_MEMORY}} and {{MEMORY_BANKS}} placeholders.

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

        # Get current short-term memory
        st_memory_content = ""
        if SHORT_TERM_MEMORY_FILE.exists():
            st_memory_content = SHORT_TERM_MEMORY_FILE.read_text(encoding='utf-8')

        if not st_memory_content.strip():
            st_memory_content = "(Empty - no short-term memory stored yet)"

        # Get memory banks summary
        memory_banks_summary = _get_memory_banks_summary()

        # Get the original system message template
        original_system_message = agent._system_messages[0].content if agent._system_messages else ""

        # Replace the placeholders with actual content
        updated_system_message = original_system_message.replace(
            "{{SHORT_TERM_MEMORY}}",
            st_memory_content
        ).replace(
            "{{MEMORY_BANKS}}",
            memory_banks_summary
        )

        # Update the agent's system message
        if agent._system_messages:
            agent._system_messages[0].content = updated_system_message
            logger.info("Agent system message refreshed with current short-term memory and memory banks")
        else:
            logger.warning("Agent has no system messages to update")

    except Exception as e:
        logger.error(f"Error refreshing agent system message: {e}")

def initialize_memory_agent(agent):
    """
    Initializes the Memory agent by loading short-term memory and injecting it into the system prompt.
    This should be called once when the agent is first created.

    Args:
        agent: The agent instance to initialize.

    Returns:
        Success or error message.
    """
    try:
        logger.info("Initializing Memory agent with short-term memory")

        # Ensure short-term memory file exists
        if not SHORT_TERM_MEMORY_FILE.exists():
            SHORT_TERM_MEMORY_FILE.write_text("", encoding='utf-8')
            logger.info("Created empty short-term memory file")

        # Refresh the agent's system message with current memory
        _refresh_agent_system_message(agent)

        return "Memory agent initialized successfully"
    except Exception as e:
        logger.error(f"Error initializing memory agent: {e}")
        return f"Error initializing memory agent: {str(e)}"

# --- Tool 1: Overwrite Short-Term Memory ---

class OverwriteShortTermMemoryInput(BaseModel):
    """Input model for overwriting short-term memory"""
    full_new_content: str = Field(
        description="The full new content to replace the current SHORT TERM MEMORY content."
    )

def overwrite_short_term_memory(full_new_content: str) -> str:
    """
    Overwrites the SHORT TERM MEMORY content with new information.

    Args:
        full_new_content: The full new content to replace the current SHORT TERM MEMORY.

    Returns:
        Success message confirming the update.
    """
    try:
        logger.info("Overwriting short-term memory")
        SHORT_TERM_MEMORY_FILE.write_text(full_new_content, encoding='utf-8')

        # Refresh the agent's system message with the new content
        _refresh_agent_system_message()

        return "Short-term memory successfully updated."
    except Exception as e:
        logger.error(f"Error overwriting short-term memory: {e}")
        return f"Error updating short-term memory: {str(e)}"

overwrite_short_term_memory_tool = FunctionTool(
    func=overwrite_short_term_memory,
    description="Overwrites the SHORT TERM MEMORY content with new information. Use this to update temporary context that should be readily available. Keep it concise (under 4000 tokens)."
)

# --- Tool 2: Get Short-Term Memory ---

def get_short_term_memory() -> str:
    """
    Retrieves the current SHORT TERM MEMORY content.

    Returns:
        The current short-term memory content.
    """
    try:
        if SHORT_TERM_MEMORY_FILE.exists():
            content = SHORT_TERM_MEMORY_FILE.read_text(encoding='utf-8')
            return content if content.strip() else "Short-term memory is empty."
        else:
            SHORT_TERM_MEMORY_FILE.write_text("", encoding='utf-8')
            return "Short-term memory is empty."
    except Exception as e:
        logger.error(f"Error reading short-term memory: {e}")
        return f"Error reading short-term memory: {str(e)}"

get_short_term_memory_tool = FunctionTool(
    func=get_short_term_memory,
    description="Retrieves the current SHORT TERM MEMORY content. Use this to check what's currently in temporary memory."
)

# --- Tool 3: Create Memory Bank ---

class CreateMemoryBankInput(BaseModel):
    """Input model for creating a memory bank"""
    memory_name: str = Field(description="The name of the new MEMORY BANK to be created.")
    description: str = Field(description="A short description of the new MEMORY BANK including the type of information it will store.")

def create_memory_bank(memory_name: str, description: str) -> str:
    """
    Creates a new MEMORY BANK for storing related information with semantic search.

    Args:
        memory_name: The name of the new memory bank.
        description: A description of what this memory bank will store.

    Returns:
        Success message confirming creation.
    """
    try:
        logger.info(f"Creating memory bank: {memory_name}")

        # Load current index
        index = _load_memory_index()

        # Check if already exists
        if memory_name in index:
            return f"Memory bank '{memory_name}' already exists. Description: {index[memory_name]}"

        # Create ChromaDB collection
        try:
            client = _get_chroma_client()
            collection = client.get_or_create_collection(
                name=memory_name,
                metadata={"description": description}
            )
            logger.info(f"ChromaDB collection '{memory_name}' created with {collection.count()} items")
        except Exception as e:
            logger.error(f"Error creating ChromaDB collection: {e}")
            return f"Error creating memory bank: {str(e)}"

        # Update index
        index[memory_name] = description
        _save_memory_index(index)

        return f"Memory bank '{memory_name}' created successfully. Description: {description}"
    except Exception as e:
        logger.error(f"Error creating memory bank '{memory_name}': {e}")
        return f"Error creating memory bank: {str(e)}"

create_memory_bank_tool = FunctionTool(
    func=create_memory_bank,
    description="Creates a new MEMORY BANK for organizing and storing related information. Each memory bank uses vector similarity search for efficient retrieval."
)

# --- Tool 4: Add to Memory ---

class AddToMemoryInput(BaseModel):
    """Input model for adding to memory"""
    memory_name: str = Field(description="The name of the MEMORY BANK to add information to.")
    information: str = Field(description="The textual information to be stored in the specified MEMORY BANK.")

def add_to_memory(memory_name: str, information: str) -> str:
    """
    Adds information to a specified MEMORY BANK.

    Args:
        memory_name: The name of the memory bank.
        information: The information to store.

    Returns:
        Success message confirming the addition.
    """
    try:
        logger.info(f"Adding to memory bank: {memory_name}")

        # Verify bank exists
        index = _load_memory_index()
        if memory_name not in index:
            return f"Memory bank '{memory_name}' does not exist. Create it first using create_memory_bank."

        # Get collection
        client = _get_chroma_client()
        collection = client.get_collection(name=memory_name)

        # Generate embedding
        embedding = _get_embedding(information)

        # Generate unique ID
        import uuid
        doc_id = str(uuid.uuid4())

        # Add to collection
        collection.add(
            embeddings=[embedding],
            documents=[information],
            ids=[doc_id]
        )

        logger.info(f"Added entry to '{memory_name}'. Total entries: {collection.count()}")
        return f"Successfully added information to memory bank '{memory_name}'."
    except Exception as e:
        logger.error(f"Error adding to memory '{memory_name}': {e}")
        return f"Error adding to memory: {str(e)}"

add_to_memory_tool = FunctionTool(
    func=add_to_memory,
    description="Adds information to a specified MEMORY BANK. The information will be indexed for semantic similarity search."
)

# --- Tool 5: Search Memory ---

class SearchMemoryInput(BaseModel):
    """Input model for searching memory"""
    memory_name: str = Field(description="The name of the MEMORY BANK to search.")
    search_query: str = Field(description="The search query for semantic similarity search. Be as descriptive as possible.")
    n_results: int = Field(default=3, ge=1, le=10, description="Number of similar results to return (1-10).")

def search_memory(memory_name: str, search_query: str, n_results: int = 3) -> str:
    """
    Searches a MEMORY BANK for information similar to the query.

    Args:
        memory_name: The name of the memory bank to search.
        search_query: The search query for similarity matching.
        n_results: Number of results to return (1-10).

    Returns:
        Formatted search results or error message.
    """
    try:
        logger.info(f"Searching memory bank '{memory_name}' for: {search_query}")

        # Verify bank exists
        index = _load_memory_index()
        if memory_name not in index:
            return f"Memory bank '{memory_name}' does not exist."

        # Get collection
        client = _get_chroma_client()
        collection = client.get_collection(name=memory_name)

        # Check if empty
        if collection.count() == 0:
            return f"Memory bank '{memory_name}' is empty. No results found."

        # Generate query embedding
        query_embedding = _get_embedding(search_query)

        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count())
        )

        if not results['documents'] or not results['documents'][0]:
            return f"No results found in memory bank '{memory_name}' for query: {search_query}"

        # Format results
        formatted_results = [f"Search results for '{search_query}' in memory bank '{memory_name}':"]
        for i, doc in enumerate(results['documents'][0], 1):
            formatted_results.append(f"{i}. {doc}")

        logger.info(f"Found {len(results['documents'][0])} results in '{memory_name}'")
        return "\n".join(formatted_results)
    except Exception as e:
        logger.error(f"Error searching memory '{memory_name}': {e}")
        return f"Error searching memory: {str(e)}"

search_memory_tool = FunctionTool(
    func=search_memory,
    description="Searches a MEMORY BANK using semantic similarity. Returns the most relevant information based on the search query. Results are ordered by similarity."
)

# --- Tool 6: Replace Data ---

class ReplaceDataInput(BaseModel):
    """Input model for replacing data in memory"""
    memory_name: str = Field(description="The name of the MEMORY BANK to modify.")
    old_information: str = Field(description="The old information to be replaced.")
    new_information: str = Field(description="The new information to replace the old information.")

def replace_data(memory_name: str, old_information: str, new_information: str) -> str:
    """
    Replaces information in a MEMORY BANK.

    Args:
        memory_name: The name of the memory bank.
        old_information: The information to find and replace.
        new_information: The new information.

    Returns:
        Success or error message.
    """
    try:
        logger.info(f"Replacing data in memory bank: {memory_name}")

        # Verify bank exists
        index = _load_memory_index()
        if memory_name not in index:
            return f"Memory bank '{memory_name}' does not exist."

        # Get collection
        client = _get_chroma_client()
        collection = client.get_collection(name=memory_name)

        # Search for exact or similar match
        old_embedding = _get_embedding(old_information)
        results = collection.query(
            query_embeddings=[old_embedding],
            n_results=1
        )

        if not results['documents'] or not results['documents'][0]:
            return f"Information not found in memory bank '{memory_name}'."

        # Get the ID of the best match
        doc_id = results['ids'][0][0]

        # Delete old entry
        collection.delete(ids=[doc_id])

        # Add new entry
        new_embedding = _get_embedding(new_information)
        collection.add(
            embeddings=[new_embedding],
            documents=[new_information],
            ids=[doc_id]  # Reuse same ID
        )

        logger.info(f"Replaced entry in '{memory_name}'")
        return f"Successfully replaced information in memory bank '{memory_name}'."
    except Exception as e:
        logger.error(f"Error replacing data in '{memory_name}': {e}")
        return f"Error replacing data: {str(e)}"

replace_data_tool = FunctionTool(
    func=replace_data,
    description="Replaces information in a MEMORY BANK. Finds the most similar entry to old_information and replaces it with new_information."
)

# --- Tool 7: Remove Data ---

class RemoveDataInput(BaseModel):
    """Input model for removing data from memory"""
    memory_name: str = Field(description="The name of the MEMORY BANK to delete information from.")
    information: str = Field(description="The information to be deleted from the MEMORY BANK.")

def remove_data(memory_name: str, information: str) -> str:
    """
    Removes information from a MEMORY BANK.

    Args:
        memory_name: The name of the memory bank.
        information: The information to remove.

    Returns:
        Success or error message.
    """
    try:
        logger.info(f"Removing data from memory bank: {memory_name}")

        # Verify bank exists
        index = _load_memory_index()
        if memory_name not in index:
            return f"Memory bank '{memory_name}' does not exist."

        # Get collection
        client = _get_chroma_client()
        collection = client.get_collection(name=memory_name)

        # Search for the information
        embedding = _get_embedding(information)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=1
        )

        if not results['documents'] or not results['documents'][0]:
            return f"Information not found in memory bank '{memory_name}'."

        # Delete the entry
        doc_id = results['ids'][0][0]
        collection.delete(ids=[doc_id])

        logger.info(f"Removed entry from '{memory_name}'. Remaining: {collection.count()}")
        return f"Successfully removed information from memory bank '{memory_name}'."
    except Exception as e:
        logger.error(f"Error removing data from '{memory_name}': {e}")
        return f"Error removing data: {str(e)}"

remove_data_tool = FunctionTool(
    func=remove_data,
    description="Removes information from a MEMORY BANK. Finds and deletes the most similar entry to the provided information."
)

# --- Tool 8: List Memory Banks ---

def list_memory_banks() -> str:
    """
    Lists all available MEMORY BANKs and their descriptions.

    Returns:
        Formatted list of memory banks.
    """
    try:
        logger.info("Listing all memory banks")
        index = _load_memory_index()

        if not index:
            return "No memory banks exist yet. Create one using create_memory_bank."

        result = ["Available Memory Banks:"]
        client = _get_chroma_client()
        for name, description in index.items():
            try:
                collection = client.get_collection(name=name)
                count = collection.count()
                result.append(f"- {name}: {description} ({count} entries)")
            except Exception:
                result.append(f"- {name}: {description} (collection not found)")

        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error listing memory banks: {e}")
        return f"Error listing memory banks: {str(e)}"

list_memory_banks_tool = FunctionTool(
    func=list_memory_banks,
    description="Lists all available MEMORY BANKs with their descriptions and entry counts. Use this to see what memory banks are available."
)

# --- Helper function to get all tools ---

def get_memory_tools() -> List[FunctionTool]:
    """Returns all memory management tools"""
    return [
        get_short_term_memory_tool,
        overwrite_short_term_memory_tool,
        create_memory_bank_tool,
        add_to_memory_tool,
        search_memory_tool,
        replace_data_tool,
        remove_data_tool,
        list_memory_banks_tool,
    ]

# --- Testing ---
if __name__ == "__main__":
    print("--- Memory Tools Loaded ---")
    tools = get_memory_tools()
    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"  Description: {tool.description}")
