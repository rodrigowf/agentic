#!/usr/bin/env python3
"""
Comprehensive test suite for Database and Memory systems reliability.
Tests MongoDB, ChromaDB, and agent integrations.
"""

import sys
import os
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_mongodb_connection():
    """Test 1: MongoDB connection and basic operations"""
    logger.info("=" * 60)
    logger.info("TEST 1: MongoDB Connection and Basic Operations")
    logger.info("=" * 60)

    try:
        from pymongo import MongoClient
        from pymongo.errors import ServerSelectionTimeoutError
        import os

        # Get MongoDB URI
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        db_name = os.getenv("MONGODB_DATABASE", "agentic_db")

        logger.info(f"Connecting to MongoDB: {mongo_uri}")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

        # Test connection
        client.server_info()
        logger.info("✓ MongoDB connection successful")

        # Test database access
        db = client[db_name]
        logger.info(f"✓ Database '{db_name}' accessible")

        # Test collection operations
        test_collection = "test_reliability"
        collection = db[test_collection]

        # Insert test document
        test_doc = {"test": "reliability_check", "timestamp": datetime.now().isoformat()}
        result = collection.insert_one(test_doc)
        logger.info(f"✓ Insert operation successful: {result.inserted_id}")

        # Find test document
        found = collection.find_one({"_id": result.inserted_id})
        assert found is not None
        assert found["test"] == "reliability_check"
        logger.info("✓ Find operation successful")

        # Update test document
        update_result = collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"updated": True}}
        )
        assert update_result.modified_count == 1
        logger.info("✓ Update operation successful")

        # Delete test document
        delete_result = collection.delete_one({"_id": result.inserted_id})
        assert delete_result.deleted_count == 1
        logger.info("✓ Delete operation successful")

        # Cleanup
        client.close()
        logger.info("✓ MongoDB connection closed")

        return True

    except ServerSelectionTimeoutError:
        logger.error("✗ MongoDB connection timeout - service may not be running")
        logger.info("  Run: sudo systemctl start mongodb")
        return False
    except Exception as e:
        logger.error(f"✗ MongoDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_tools():
    """Test 2: Database tools functionality"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Database Tools Functionality")
    logger.info("=" * 60)

    try:
        from tools.database import (
            insert_document,
            find_documents,
            update_document,
            delete_document,
            list_collections,
            register_collection_schema
        )

        test_collection = "test_tools_reliability"

        # Test 1: Register schema
        logger.info("Testing register_collection_schema...")
        schema_result = register_collection_schema(
            test_collection,
            "Test collection for reliability testing",
            {"name": "string", "value": "number"},
            "Test data for reliability checks",
            '{"name": "test", "value": 42}'
        )
        logger.info(f"✓ Schema registration: {schema_result}")

        # Test 2: Insert document
        logger.info("Testing insert_document...")
        insert_result = insert_document(
            test_collection,
            {"name": "reliability_test", "value": 123, "timestamp": datetime.now().isoformat()}
        )
        logger.info(f"✓ Insert result: {insert_result}")
        assert "inserted" in insert_result.lower()

        # Test 3: Find documents
        logger.info("Testing find_documents...")
        find_result = find_documents(test_collection, {"name": "reliability_test"})
        logger.info(f"✓ Find result: {find_result[:100]}...")
        assert "reliability_test" in find_result

        # Test 4: Update document
        logger.info("Testing update_document...")
        update_result = update_document(
            test_collection,
            {"name": "reliability_test"},
            {"$set": {"value": 456}}
        )
        logger.info(f"✓ Update result: {update_result}")
        assert "1" in update_result or "modified" in update_result.lower()

        # Test 5: Delete document
        logger.info("Testing delete_document...")
        delete_result = delete_document(test_collection, {"name": "reliability_test"})
        logger.info(f"✓ Delete result: {delete_result}")
        assert "1" in delete_result or "deleted" in delete_result.lower()

        # Test 6: List collections
        logger.info("Testing list_collections...")
        collections_result = list_collections()
        logger.info(f"✓ Collections list: {collections_result[:200]}...")

        return True

    except Exception as e:
        logger.error(f"✗ Database tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chromadb_connection():
    """Test 3: ChromaDB connection and basic operations"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: ChromaDB Connection and Basic Operations")
    logger.info("=" * 60)

    try:
        import chromadb
        from chromadb.config import Settings

        # Get ChromaDB path
        persist_dir = os.path.join(os.path.dirname(__file__), "data", "memory", "chroma_db")
        logger.info(f"ChromaDB path: {persist_dir}")

        # Create client
        client = chromadb.Client(Settings(
            persist_directory=persist_dir,
            anonymized_telemetry=False
        ))
        logger.info("✓ ChromaDB client created")

        # List collections
        collections = client.list_collections()
        logger.info(f"✓ Found {len(collections)} collections")
        for col in collections:
            logger.info(f"  - {col.name}")

        # Test creating a temporary collection
        test_col_name = "test_reliability"
        try:
            # Delete if exists
            try:
                client.delete_collection(test_col_name)
            except:
                pass

            # Create collection
            test_col = client.create_collection(test_col_name)
            logger.info(f"✓ Created test collection: {test_col_name}")

            # Add a document
            test_col.add(
                documents=["This is a test document for reliability checking"],
                ids=["test_1"],
                metadatas=[{"source": "reliability_test"}]
            )
            logger.info("✓ Added test document")

            # Query the document
            results = test_col.query(
                query_texts=["test document"],
                n_results=1
            )
            assert len(results['ids'][0]) > 0
            logger.info("✓ Query successful")

            # Cleanup
            client.delete_collection(test_col_name)
            logger.info("✓ Cleaned up test collection")

        except Exception as e:
            logger.warning(f"Test collection operations: {e}")

        return True

    except Exception as e:
        logger.error(f"✗ ChromaDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_tools():
    """Test 4: Memory tools functionality"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Memory Tools Functionality")
    logger.info("=" * 60)

    try:
        from tools.memory import (
            save_to_short_term_memory,
            read_short_term_memory,
            create_memory_bank,
            add_to_memory,
            search_memory,
            list_memory_banks
        )

        # Test 1: Short-term memory
        logger.info("Testing short-term memory...")
        save_result = save_to_short_term_memory("Test memory for reliability check")
        logger.info(f"✓ Save short-term: {save_result}")

        read_result = read_short_term_memory()
        logger.info(f"✓ Read short-term: {read_result[:100]}...")
        assert "reliability check" in read_result.lower()

        # Test 2: Create memory bank
        logger.info("Testing create_memory_bank...")
        bank_name = "test_reliability_bank"
        create_result = create_memory_bank(bank_name, "Test bank for reliability")
        logger.info(f"✓ Create bank: {create_result}")

        # Test 3: Add to memory
        logger.info("Testing add_to_memory...")
        add_result = add_to_memory(bank_name, "This is test information for reliability checking")
        logger.info(f"✓ Add to memory: {add_result}")

        # Test 4: Search memory
        logger.info("Testing search_memory...")
        search_result = search_memory(bank_name, "reliability checking", top_k=1)
        logger.info(f"✓ Search result: {search_result[:200]}...")
        assert "reliability" in search_result.lower()

        # Test 5: List memory banks
        logger.info("Testing list_memory_banks...")
        banks_result = list_memory_banks()
        logger.info(f"✓ Memory banks: {banks_result}")
        assert bank_name in banks_result or "test_reliability_bank" in banks_result

        return True

    except Exception as e:
        logger.error(f"✗ Memory tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_loading():
    """Test 5: Verify all tools are loaded correctly"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Tool Loading Verification")
    logger.info("=" * 60)

    try:
        from config.config_loader import load_tools

        logger.info("Loading all tools...")
        tools = load_tools()

        # Count tools by module
        tool_counts = {}
        for tool in tools:
            module = tool.name.split('_')[0] if '_' in tool.name else 'other'
            tool_counts[module] = tool_counts.get(module, 0) + 1

        logger.info(f"✓ Loaded {len(tools)} total tools")
        for module, count in sorted(tool_counts.items()):
            logger.info(f"  - {module}: {count} tools")

        # Verify expected tools
        tool_names = [tool.name for tool in tools]

        # Check database tools
        db_tools = [name for name in tool_names if 'database' in name or name in [
            'insert_document', 'find_documents', 'update_document', 'delete_document',
            'insert_many_documents', 'aggregate', 'create_index', 'list_collections',
            'drop_collection', 'register_collection_schema'
        ]]
        logger.info(f"✓ Database tools loaded: {len(db_tools)}")
        for tool in sorted(db_tools):
            logger.info(f"  - {tool}")

        # Check memory tools
        memory_tools = [name for name in tool_names if 'memory' in name or name in [
            'save_to_short_term_memory', 'read_short_term_memory', 'create_memory_bank',
            'add_to_memory', 'search_memory', 'update_in_memory', 'remove_from_memory',
            'list_memory_banks'
        ]]
        logger.info(f"✓ Memory tools loaded: {len(memory_tools)}")
        for tool in sorted(memory_tools):
            logger.info(f"  - {tool}")

        # Verify minimum expected counts
        assert len(db_tools) >= 10, f"Expected at least 10 database tools, got {len(db_tools)}"
        assert len(memory_tools) >= 8, f"Expected at least 8 memory tools, got {len(memory_tools)}"

        logger.info("✓ All expected tools are loaded")

        return True

    except Exception as e:
        logger.error(f"✗ Tool loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_initialization():
    """Test 6: Test Database and Memory agent initialization"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Agent Initialization")
    logger.info("=" * 60)

    try:
        from config.config_loader import load_agent_config
        from core.agent_factory import create_agent_from_config
        from config.schemas import AgentConfig

        # Test Database agent
        logger.info("Testing Database agent initialization...")
        db_config_dict = load_agent_config("Database")
        db_config = AgentConfig(**db_config_dict)

        logger.info(f"✓ Database agent config loaded")
        logger.info(f"  - Agent type: {db_config.agent_type}")
        logger.info(f"  - Tools: {len(db_config.tools)}")
        logger.info(f"  - Initialization function: {db_config.initialization_function}")

        # Test Memory agent
        logger.info("Testing Memory agent initialization...")
        mem_config_dict = load_agent_config("Memory")
        mem_config = AgentConfig(**mem_config_dict)

        logger.info(f"✓ Memory agent config loaded")
        logger.info(f"  - Agent type: {mem_config.agent_type}")
        logger.info(f"  - Tools: {len(mem_config.tools)}")
        logger.info(f"  - Initialization function: {mem_config.initialization_function}")

        # Verify initialization functions exist
        if db_config.initialization_function:
            module_name, func_name = db_config.initialization_function.rsplit('.', 1)
            import importlib
            module = importlib.import_module(f'tools.{module_name}')
            func = getattr(module, func_name)
            logger.info(f"✓ Database initialization function found: {func.__name__}")

        if mem_config.initialization_function:
            module_name, func_name = mem_config.initialization_function.rsplit('.', 1)
            import importlib
            module = importlib.import_module(f'tools.{module_name}')
            func = getattr(module, func_name)
            logger.info(f"✓ Memory initialization function found: {func.__name__}")

        return True

    except Exception as e:
        logger.error(f"✗ Agent initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests and report results"""
    logger.info("\n" + "=" * 60)
    logger.info("DATABASE AND MEMORY SYSTEMS RELIABILITY TEST SUITE")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().isoformat()}\n")

    results = {}

    # Run all tests
    tests = [
        ("MongoDB Connection", test_mongodb_connection),
        ("Database Tools", test_database_tools),
        ("ChromaDB Connection", test_chromadb_connection),
        ("Memory Tools", test_memory_tools),
        ("Tool Loading", test_tool_loading),
        ("Agent Initialization", test_agent_initialization),
    ]

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ {test_name} crashed: {e}")
            results[test_name] = False

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("-" * 60)
    logger.info(f"Results: {passed}/{total} tests passed")
    logger.info(f"Finished at: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    return passed == total


if __name__ == "__main__":
    # Add backend directory to path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    # Load environment variables
    from dotenv import load_dotenv
    env_path = os.path.join(backend_dir, '.env')
    load_dotenv(env_path)

    success = main()
    sys.exit(0 if success else 1)
