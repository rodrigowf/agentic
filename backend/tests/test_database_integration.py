#!/usr/bin/env python3
"""
Integration test for Database agent with schema tracking and initialization.
Tests the {{COLLECTIONS_SCHEMA}} placeholder injection with actual MongoDB data.
"""

import sys
sys.path.insert(0, '.')

from config.config_loader import load_agents, load_tools
from core.agent_factory import create_agent_from_config
from unittest.mock import MagicMock
from tools.database import (
    register_collection_schema,
    insert_document,
    list_collections,
    drop_collection
)
import json

def test_database_agent_initialization():
    """Test Database agent initialization with schema tracking"""

    print("=" * 80)
    print("DATABASE AGENT INTEGRATION TEST")
    print("=" * 80)

    # Step 1: Create some test data in MongoDB
    print("\n[1] Setting up test database...")

    # Register and create a test collection
    register_collection_schema(
        collection_name="products",
        description="Product catalog for e-commerce",
        structure={
            "name": "string",
            "sku": "string (unique)",
            "price": "number",
            "category": "string",
            "in_stock": "boolean"
        },
        usage="Product inventory. Always index on SKU.",
        example={
            "name": "Laptop",
            "sku": "TECH-001",
            "price": 999.99,
            "category": "Electronics",
            "in_stock": True
        }
    )
    print("✅ Registered 'products' collection schema")

    # Insert some test data
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
    insert_document(
        collection_name="products",
        document={
            "name": "Mouse",
            "sku": "TECH-002",
            "price": 29.99,
            "category": "Electronics",
            "in_stock": True
        }
    )
    print("✅ Inserted 2 test products")

    # Register another collection
    register_collection_schema(
        collection_name="orders",
        description="Customer orders and transactions",
        structure={
            "order_id": "string (unique)",
            "customer_email": "string",
            "total": "number",
            "items": "array",
            "status": "string"
        },
        usage="Track customer orders. Index on customer_email and status.",
        example={
            "order_id": "ORD-12345",
            "customer_email": "customer@example.com",
            "total": 1029.98,
            "items": ["TECH-001"],
            "status": "pending"
        }
    )
    print("✅ Registered 'orders' collection schema")

    insert_document(
        collection_name="orders",
        document={
            "order_id": "ORD-12345",
            "customer_email": "customer@example.com",
            "total": 1029.98,
            "items": ["TECH-001", "TECH-002"],
            "status": "pending"
        }
    )
    print("✅ Inserted 1 test order")

    # Step 2: Load Database agent configuration
    print("\n[2] Loading Database agent configuration...")
    all_agents = load_agents('agents')
    database_agent_cfg = None
    for cfg in all_agents:
        if cfg.name == 'Database':
            database_agent_cfg = cfg
            break

    if not database_agent_cfg:
        print("❌ ERROR: Database agent not found!")
        return False

    print(f"✅ Loaded Database agent config")

    # Step 3: Load tools
    print("\n[3] Loading tools...")
    tools_list = load_tools('tools')
    tools = [t[0] for t in tools_list]
    print(f"✅ Loaded {len(tools)} tools")

    # Step 4: Create mock model client
    mock_model_client = MagicMock()

    # Step 5: Create Database agent (this triggers initialization)
    print("\n[4] Creating Database agent (triggering initialization)...")
    try:
        database_agent = create_agent_from_config(database_agent_cfg, tools, mock_model_client)
        print(f"✅ Created Database agent: {database_agent.name}")
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 6: Check system message for schema injection
    print("\n[5] Verifying {{COLLECTIONS_SCHEMA}} placeholder injection...")

    if not database_agent._system_messages:
        print("❌ ERROR: Agent has no system messages!")
        return False

    system_msg = database_agent._system_messages[0].content

    # Check placeholder was replaced
    if '{{COLLECTIONS_SCHEMA}}' in system_msg:
        print("❌ ERROR: Placeholder was NOT replaced!")
        return False

    print("✅ Placeholder was replaced")

    # Check if our test collections appear in the system message
    if 'products' not in system_msg:
        print("❌ ERROR: 'products' collection not found in system message!")
        return False

    if 'orders' not in system_msg:
        print("❌ ERROR: 'orders' collection not found in system message!")
        return False

    print("✅ Both test collections found in system message")

    # Check if descriptions are present
    if 'Product catalog for e-commerce' not in system_msg:
        print("❌ ERROR: Product collection description not found!")
        return False

    if 'Customer orders and transactions' not in system_msg:
        print("❌ ERROR: Orders collection description not found!")
        return False

    print("✅ Collection descriptions found")

    # Print first 2000 characters of system message
    print("\n[6] Database Agent System Message Preview:")
    print("=" * 80)
    print(system_msg[:2000])
    print("...")
    print("=" * 80)

    # Step 7: Verify collections list
    print("\n[7] Verifying database state...")
    collections_output = list_collections()
    print(f"Collections:\n{collections_output}")

    # Step 8: Cleanup
    print("\n[8] Cleanup...")
    drop_collection("products")
    drop_collection("orders")
    print("✅ Test collections cleaned up")

    return True

def main():
    try:
        success = test_database_agent_initialization()

        print("\n" + "=" * 80)
        if success:
            print("✅ INTEGRATION TEST PASSED!")
            print("=" * 80)
            print("\nThe Database agent successfully:")
            print("  1. Connected to MongoDB")
            print("  2. Loaded collection schemas from disk")
            print("  3. Injected schemas into system prompt")
            print("  4. Replaced {{COLLECTIONS_SCHEMA}} placeholder")
            print("  5. Included all collection metadata")
            print("\nThe agent is ready for production use!")
            return True
        else:
            print("❌ INTEGRATION TEST FAILED!")
            print("=" * 80)
            return False
    except Exception as e:
        print(f"\n❌ TEST CRASHED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
