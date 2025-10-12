"""
Unit tests for tools/memory.py

Tests all memory management functions:
- Short-term memory operations (overwrite, get)
- Memory bank operations (create, add, search, replace, remove, list)
- ChromaDB integration (mocked)
- File system operations for short-term memory
- Agent context updates
- Error handling
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call, mock_open
from typing import List

# Import memory tools
from tools.memory import (
    overwrite_short_term_memory,
    get_short_term_memory,
    create_memory_bank,
    add_to_memory,
    search_memory,
    replace_data,
    remove_data,
    list_memory_banks,
    initialize_memory_agent,
    _load_memory_index,
    _save_memory_index,
    _get_embedding,
    _refresh_agent_system_message,
    SHORT_TERM_MEMORY_FILE,
    MEMORY_INDEX_FILE,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_memory_dir(tmp_path, monkeypatch):
    """Create temporary directory for memory files."""
    memory_dir = tmp_path / "memories"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Patch the memory paths
    monkeypatch.setattr("tools.memory.MEMORY_BASE_PATH", memory_dir)
    monkeypatch.setattr("tools.memory.SHORT_TERM_MEMORY_FILE", memory_dir / "short_term_memory.txt")
    monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", memory_dir / "memory_index.json")
    monkeypatch.setattr("tools.memory.CHROMA_PERSIST_DIR", str(memory_dir / "chroma_db"))

    return memory_dir


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for embeddings."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]  # Standard embedding size
    mock.embeddings.create.return_value = mock_response
    return mock


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client."""
    mock = MagicMock()

    # Mock collection
    mock_collection = MagicMock()
    mock_collection.count.return_value = 0
    mock_collection.add = MagicMock()
    mock_collection.query = MagicMock(return_value={
        'documents': [['Test document 1', 'Test document 2']],
        'ids': [['id1', 'id2']]
    })
    mock_collection.delete = MagicMock()

    mock.get_or_create_collection.return_value = mock_collection
    mock.get_collection.return_value = mock_collection

    return mock


@pytest.fixture
def mock_agent():
    """Mock agent with system messages."""
    agent = MagicMock()
    agent._system_messages = [
        MagicMock(content="You are a helpful assistant. Short-term memory: {{SHORT_TERM_MEMORY}}")
    ]
    return agent


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global variables before each test."""
    import tools.memory
    tools.memory._openai_client = None
    tools.memory._chroma_client = None
    yield


# ============================================================================
# Test Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Test internal helper functions."""

    def test_load_memory_index_empty(self, temp_memory_dir, monkeypatch):
        """Test loading memory index when file doesn't exist."""
        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", temp_memory_dir / "memory_index.json")

        index = _load_memory_index()
        assert index == {}

    def test_load_memory_index_with_data(self, temp_memory_dir, monkeypatch):
        """Test loading memory index with existing data."""
        index_file = temp_memory_dir / "memory_index.json"
        test_data = {"bank1": "Description 1", "bank2": "Description 2"}

        with open(index_file, 'w') as f:
            json.dump(test_data, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)

        index = _load_memory_index()
        assert index == test_data

    def test_load_memory_index_corrupted(self, temp_memory_dir, monkeypatch):
        """Test loading corrupted memory index returns empty dict."""
        index_file = temp_memory_dir / "memory_index.json"

        with open(index_file, 'w') as f:
            f.write("invalid json {{{")

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)

        index = _load_memory_index()
        assert index == {}

    def test_save_memory_index(self, temp_memory_dir, monkeypatch):
        """Test saving memory index."""
        index_file = temp_memory_dir / "memory_index.json"
        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)

        test_data = {"bank1": "Description 1"}
        _save_memory_index(test_data)

        assert index_file.exists()
        with open(index_file) as f:
            saved_data = json.load(f)
        assert saved_data == test_data

    @patch("tools.memory._get_openai_client")
    def test_get_embedding_success(self, mock_get_client, mock_openai_client):
        """Test generating embeddings successfully."""
        mock_get_client.return_value = mock_openai_client

        result = _get_embedding("test text")

        assert result == [0.1] * 1536
        mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="test text"
        )

    @patch("tools.memory._get_openai_client")
    def test_get_embedding_failure(self, mock_get_client):
        """Test embedding generation failure."""
        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception, match="API Error"):
            _get_embedding("test text")

    @patch("tools.memory.get_current_agent")
    def test_refresh_agent_system_message(self, mock_get_agent, mock_agent, temp_memory_dir, monkeypatch):
        """Test refreshing agent system message with memory."""
        st_memory_file = temp_memory_dir / "short_term_memory.txt"
        st_memory_file.write_text("Important context here")

        monkeypatch.setattr("tools.memory.SHORT_TERM_MEMORY_FILE", st_memory_file)
        mock_get_agent.return_value = mock_agent

        _refresh_agent_system_message()

        assert "Important context here" in mock_agent._system_messages[0].content
        assert "{{SHORT_TERM_MEMORY}}" not in mock_agent._system_messages[0].content

    @patch("tools.memory.get_current_agent")
    def test_refresh_agent_system_message_no_agent(self, mock_get_agent):
        """Test refresh when no agent is available."""
        mock_get_agent.return_value = None

        # Should not raise an error
        _refresh_agent_system_message()

    @patch("tools.memory.get_current_agent")
    def test_refresh_agent_system_message_empty_memory(self, mock_get_agent, mock_agent, temp_memory_dir, monkeypatch):
        """Test refresh with empty short-term memory."""
        st_memory_file = temp_memory_dir / "short_term_memory.txt"
        st_memory_file.write_text("")

        monkeypatch.setattr("tools.memory.SHORT_TERM_MEMORY_FILE", st_memory_file)
        mock_get_agent.return_value = mock_agent

        _refresh_agent_system_message()

        assert "(Empty - no short-term memory stored yet)" in mock_agent._system_messages[0].content


# ============================================================================
# Test Short-Term Memory Operations
# ============================================================================

class TestShortTermMemory:
    """Test short-term memory functions."""

    @patch("tools.memory._refresh_agent_system_message")
    def test_overwrite_short_term_memory(self, mock_refresh, temp_memory_dir, monkeypatch):
        """Test overwriting short-term memory."""
        st_memory_file = temp_memory_dir / "short_term_memory.txt"
        monkeypatch.setattr("tools.memory.SHORT_TERM_MEMORY_FILE", st_memory_file)

        result = overwrite_short_term_memory("New memory content")

        assert "successfully updated" in result
        assert st_memory_file.read_text() == "New memory content"
        mock_refresh.assert_called_once()

    @patch("tools.memory._refresh_agent_system_message")
    def test_overwrite_short_term_memory_error(self, mock_refresh, monkeypatch):
        """Test error handling in overwrite."""
        # Patch to raise exception
        def raise_error(*args, **kwargs):
            raise IOError("Disk full")

        monkeypatch.setattr("pathlib.Path.write_text", raise_error)

        result = overwrite_short_term_memory("Test content")

        assert "Error updating short-term memory" in result
        assert "Disk full" in result

    def test_get_short_term_memory(self, temp_memory_dir, monkeypatch):
        """Test retrieving short-term memory."""
        st_memory_file = temp_memory_dir / "short_term_memory.txt"
        st_memory_file.write_text("Stored memory content")

        monkeypatch.setattr("tools.memory.SHORT_TERM_MEMORY_FILE", st_memory_file)

        result = get_short_term_memory()

        assert result == "Stored memory content"

    def test_get_short_term_memory_empty(self, temp_memory_dir, monkeypatch):
        """Test retrieving empty short-term memory."""
        st_memory_file = temp_memory_dir / "short_term_memory.txt"
        st_memory_file.write_text("")

        monkeypatch.setattr("tools.memory.SHORT_TERM_MEMORY_FILE", st_memory_file)

        result = get_short_term_memory()

        assert result == "Short-term memory is empty."

    def test_get_short_term_memory_no_file(self, temp_memory_dir, monkeypatch):
        """Test retrieving memory when file doesn't exist."""
        st_memory_file = temp_memory_dir / "short_term_memory.txt"
        monkeypatch.setattr("tools.memory.SHORT_TERM_MEMORY_FILE", st_memory_file)

        result = get_short_term_memory()

        assert result == "Short-term memory is empty."
        assert st_memory_file.exists()  # Should create file

    @patch("tools.memory._refresh_agent_system_message")
    def test_initialize_memory_agent(self, mock_refresh, temp_memory_dir, monkeypatch):
        """Test initializing memory agent."""
        st_memory_file = temp_memory_dir / "short_term_memory.txt"
        monkeypatch.setattr("tools.memory.SHORT_TERM_MEMORY_FILE", st_memory_file)

        result = initialize_memory_agent()

        assert "successfully" in result
        assert st_memory_file.exists()
        mock_refresh.assert_called_once()


# ============================================================================
# Test Memory Bank Operations
# ============================================================================

class TestMemoryBanks:
    """Test memory bank CRUD operations."""

    @patch("tools.memory._get_chroma_client")
    def test_create_memory_bank(self, mock_get_client, mock_chroma_client, temp_memory_dir, monkeypatch):
        """Test creating a new memory bank."""
        index_file = temp_memory_dir / "memory_index.json"
        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_client.return_value = mock_chroma_client

        result = create_memory_bank("test_bank", "Test description")

        assert "created successfully" in result
        assert "Test description" in result

        # Verify index was updated
        with open(index_file) as f:
            index = json.load(f)
        assert "test_bank" in index
        assert index["test_bank"] == "Test description"

        # Verify ChromaDB collection was created
        mock_chroma_client.get_or_create_collection.assert_called_once_with(
            name="test_bank",
            metadata={"description": "Test description"}
        )

    @patch("tools.memory._get_chroma_client")
    def test_create_memory_bank_already_exists(self, mock_get_client, mock_chroma_client, temp_memory_dir, monkeypatch):
        """Test creating a memory bank that already exists."""
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({"test_bank": "Existing description"}, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_client.return_value = mock_chroma_client

        result = create_memory_bank("test_bank", "New description")

        assert "already exists" in result
        assert "Existing description" in result

    @patch("tools.memory._get_chroma_client")
    def test_create_memory_bank_chromadb_error(self, mock_get_client, temp_memory_dir, monkeypatch):
        """Test error handling when ChromaDB fails."""
        mock_client = MagicMock()
        mock_client.get_or_create_collection.side_effect = Exception("Database error")
        mock_get_client.return_value = mock_client

        index_file = temp_memory_dir / "memory_index.json"
        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)

        result = create_memory_bank("test_bank", "Description")

        assert "Error creating memory bank" in result
        assert "Database error" in result

    @patch("tools.memory._get_embedding")
    @patch("tools.memory._get_chroma_client")
    def test_add_to_memory(self, mock_get_client, mock_get_embedding, mock_chroma_client, temp_memory_dir, monkeypatch):
        """Test adding information to memory bank."""
        # Setup index
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({"test_bank": "Test description"}, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_client.return_value = mock_chroma_client
        mock_get_embedding.return_value = [0.1] * 1536

        result = add_to_memory("test_bank", "Important information")

        assert "Successfully added" in result

        # Verify embedding was generated
        mock_get_embedding.assert_called_once_with("Important information")

        # Verify ChromaDB add was called
        mock_collection = mock_chroma_client.get_collection.return_value
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert call_args[1]['documents'] == ["Important information"]
        assert len(call_args[1]['embeddings']) == 1
        assert len(call_args[1]['ids']) == 1

    @patch("tools.memory._get_chroma_client")
    def test_add_to_memory_nonexistent_bank(self, mock_get_client, temp_memory_dir, monkeypatch):
        """Test adding to non-existent memory bank."""
        index_file = temp_memory_dir / "memory_index.json"
        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)

        result = add_to_memory("nonexistent_bank", "Information")

        assert "does not exist" in result
        assert "Create it first" in result

    @patch("tools.memory._get_embedding")
    @patch("tools.memory._get_chroma_client")
    def test_search_memory(self, mock_get_client, mock_get_embedding, mock_chroma_client, temp_memory_dir, monkeypatch):
        """Test searching memory bank."""
        # Setup index
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({"test_bank": "Test description"}, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_client.return_value = mock_chroma_client
        mock_get_embedding.return_value = [0.1] * 1536

        # Mock collection with results
        mock_collection = MagicMock()
        mock_collection.count.return_value = 5
        mock_collection.query.return_value = {
            'documents': [['Result 1', 'Result 2', 'Result 3']],
            'ids': [['id1', 'id2', 'id3']]
        }
        mock_chroma_client.get_collection.return_value = mock_collection

        result = search_memory("test_bank", "test query", n_results=3)

        assert "Search results" in result
        assert "Result 1" in result
        assert "Result 2" in result
        assert "Result 3" in result

        # Verify query was called
        mock_collection.query.assert_called_once()
        call_args = mock_collection.query.call_args
        assert call_args[1]['n_results'] == 3

    @patch("tools.memory._get_chroma_client")
    def test_search_memory_empty_bank(self, mock_get_client, temp_memory_dir, monkeypatch):
        """Test searching empty memory bank."""
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({"test_bank": "Test description"}, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0

        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client

        result = search_memory("test_bank", "query")

        assert "empty" in result
        assert "No results found" in result

    @patch("tools.memory._get_embedding")
    @patch("tools.memory._get_chroma_client")
    def test_replace_data(self, mock_get_client, mock_get_embedding, mock_chroma_client, temp_memory_dir, monkeypatch):
        """Test replacing data in memory bank."""
        # Setup index
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({"test_bank": "Test description"}, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_client.return_value = mock_chroma_client
        mock_get_embedding.return_value = [0.1] * 1536

        # Mock collection with existing data
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [['Old data']],
            'ids': [['doc_id_1']]
        }
        mock_chroma_client.get_collection.return_value = mock_collection

        result = replace_data("test_bank", "Old data", "New data")

        assert "Successfully replaced" in result

        # Verify delete was called
        mock_collection.delete.assert_called_once_with(ids=['doc_id_1'])

        # Verify add was called
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert call_args[1]['documents'] == ["New data"]
        assert call_args[1]['ids'] == ['doc_id_1']

    @patch("tools.memory._get_embedding")
    @patch("tools.memory._get_chroma_client")
    def test_replace_data_not_found(self, mock_get_client, mock_get_embedding, temp_memory_dir, monkeypatch):
        """Test replacing data that doesn't exist."""
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({"test_bank": "Test description"}, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_embedding.return_value = [0.1] * 1536

        # Mock empty results
        mock_collection = MagicMock()
        mock_collection.query.return_value = {'documents': [[]], 'ids': [[]]}

        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client

        result = replace_data("test_bank", "Nonexistent", "New")

        assert "not found" in result

    @patch("tools.memory._get_embedding")
    @patch("tools.memory._get_chroma_client")
    def test_remove_data(self, mock_get_client, mock_get_embedding, mock_chroma_client, temp_memory_dir, monkeypatch):
        """Test removing data from memory bank."""
        # Setup index
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({"test_bank": "Test description"}, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_client.return_value = mock_chroma_client
        mock_get_embedding.return_value = [0.1] * 1536

        # Mock collection with data to remove
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [['Data to remove']],
            'ids': [['doc_id_1']]
        }
        mock_collection.count.return_value = 2  # 3 before, 2 after
        mock_chroma_client.get_collection.return_value = mock_collection

        result = remove_data("test_bank", "Data to remove")

        assert "Successfully removed" in result
        mock_collection.delete.assert_called_once_with(ids=['doc_id_1'])

    @patch("tools.memory._get_chroma_client")
    def test_list_memory_banks(self, mock_get_client, mock_chroma_client, temp_memory_dir, monkeypatch):
        """Test listing all memory banks."""
        # Setup index
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({
                "bank1": "Description 1",
                "bank2": "Description 2"
            }, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_client.return_value = mock_chroma_client

        # Mock collection counts
        mock_collection = MagicMock()
        mock_collection.count.return_value = 5
        mock_chroma_client.get_collection.return_value = mock_collection

        result = list_memory_banks()

        assert "Available Memory Banks:" in result
        assert "bank1" in result
        assert "Description 1" in result
        assert "bank2" in result
        assert "Description 2" in result
        assert "5 entries" in result

    def test_list_memory_banks_empty(self, temp_memory_dir, monkeypatch):
        """Test listing memory banks when none exist."""
        index_file = temp_memory_dir / "memory_index.json"
        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)

        result = list_memory_banks()

        assert "No memory banks exist yet" in result


# ============================================================================
# Test Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling across memory operations."""

    def test_get_embedding_no_api_key(self, monkeypatch):
        """Test embedding generation without API key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Force reinitialization
        import tools.memory
        tools.memory._openai_client = None

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            from tools.memory import _get_openai_client
            _get_openai_client()

    @patch("tools.memory._get_embedding")
    @patch("tools.memory._get_chroma_client")
    def test_add_to_memory_embedding_error(self, mock_get_client, mock_get_embedding, mock_chroma_client, temp_memory_dir, monkeypatch):
        """Test add_to_memory when embedding generation fails."""
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({"test_bank": "Test"}, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_client.return_value = mock_chroma_client
        mock_get_embedding.side_effect = Exception("API rate limit")

        result = add_to_memory("test_bank", "Test data")

        assert "Error adding to memory" in result
        assert "API rate limit" in result

    @patch("tools.memory._get_embedding")
    @patch("tools.memory._get_chroma_client")
    def test_search_memory_chromadb_error(self, mock_get_client, mock_get_embedding, temp_memory_dir, monkeypatch):
        """Test search_memory when ChromaDB query fails."""
        index_file = temp_memory_dir / "memory_index.json"
        with open(index_file, 'w') as f:
            json.dump({"test_bank": "Test"}, f)

        monkeypatch.setattr("tools.memory.MEMORY_INDEX_FILE", index_file)
        mock_get_embedding.return_value = [0.1] * 1536

        mock_collection = MagicMock()
        mock_collection.count.return_value = 5
        mock_collection.query.side_effect = Exception("Database connection error")

        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client

        result = search_memory("test_bank", "query")

        assert "Error searching memory" in result


# ============================================================================
# Test Tool Integration
# ============================================================================

class TestToolIntegration:
    """Test FunctionTool wrappers."""

    def test_all_tools_exported(self):
        """Test that all tools are exported correctly."""
        from tools.memory import get_memory_tools

        tools = get_memory_tools()

        # Verify all 8 tools are present
        assert len(tools) == 8

        tool_names = [tool.name for tool in tools]
        expected_names = [
            "get_short_term_memory",
            "overwrite_short_term_memory",
            "create_memory_bank",
            "add_to_memory",
            "search_memory",
            "replace_data",
            "remove_data",
            "list_memory_banks"
        ]

        for name in expected_names:
            assert name in tool_names

    def test_tool_descriptions(self):
        """Test that tools have proper descriptions."""
        from tools.memory import get_memory_tools

        tools = get_memory_tools()

        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 10  # Non-trivial description
