#!/usr/bin/env python3
"""
Test script to verify Database agent configuration and placeholder injection.
Tests the {{COLLECTIONS_SCHEMA}} placeholder injection without requiring MongoDB connection.
"""

import sys
sys.path.insert(0, '.')

from config.config_loader import load_agents

def test_database_agent():
    """Test that Database agent is properly configured"""

    print("=" * 80)
    print("Testing Database Agent Configuration")
    print("=" * 80)

    # Load all agent configs
    all_agents = load_agents('agents')
    print(f"\n✅ Loaded {len(all_agents)} agent configs")

    # Find Database agent
    database_agent = None
    for cfg in all_agents:
        if cfg.name == 'Database':
            database_agent = cfg
            break

    if not database_agent:
        print("\n❌ ERROR: Database agent not found!")
        return False

    print(f"✅ Found Database agent")

    # Check agent type
    if database_agent.agent_type != 'dynamic_init_looping':
        print(f"\n❌ ERROR: Wrong agent type: {database_agent.agent_type}")
        return False

    print(f"✅ Agent type: {database_agent.agent_type}")

    # Check initialization function
    if database_agent.initialization_function != 'database.initialize_database_agent':
        print(f"\n❌ ERROR: Wrong initialization function: {database_agent.initialization_function}")
        return False

    print(f"✅ Initialization function: {database_agent.initialization_function}")

    # Check tools
    expected_tools = [
        'register_collection_schema',
        'insert_document',
        'insert_many_documents',
        'find_documents',
        'update_document',
        'delete_document',
        'aggregate',
        'create_index',
        'list_collections',
        'drop_collection'
    ]

    missing_tools = []
    for tool in expected_tools:
        if tool not in database_agent.tools:
            missing_tools.append(tool)

    if missing_tools:
        print(f"\n❌ ERROR: Missing tools: {missing_tools}")
        return False

    print(f"✅ All {len(expected_tools)} tools configured")

    # Check system prompt has placeholder
    if '{{COLLECTIONS_SCHEMA}}' not in database_agent.prompt.system:
        print("\n❌ ERROR: {{COLLECTIONS_SCHEMA}} placeholder not found in system prompt!")
        return False

    print(f"✅ System prompt contains {{{{COLLECTIONS_SCHEMA}}}} placeholder")

    # Check description
    if not database_agent.description:
        print("\n❌ ERROR: Agent has no description!")
        return False

    if 'MongoDB' not in database_agent.description:
        print("\n❌ ERROR: Description doesn't mention MongoDB!")
        return False

    print(f"✅ Description: {database_agent.description[:100]}...")

    # Check MainConversation includes Database
    main_conv = None
    for cfg in all_agents:
        if cfg.name == 'MainConversation':
            main_conv = cfg
            break

    if not main_conv:
        print("\n❌ ERROR: MainConversation not found!")
        return False

    database_in_team = any(a.name == 'Database' for a in main_conv.sub_agents)
    if not database_in_team:
        print("\n❌ ERROR: Database not in MainConversation sub_agents!")
        return False

    print(f"✅ Database agent included in MainConversation")

    print("\n" + "=" * 80)
    print("Database Agent Configuration")
    print("=" * 80)
    print(f"Name: {database_agent.name}")
    print(f"Type: {database_agent.agent_type}")
    print(f"Model: {database_agent.llm.model}")
    print(f"Tools: {len(database_agent.tools)}")
    print(f"  - {', '.join(database_agent.tools[:5])}")
    print(f"  - ... and {len(database_agent.tools) - 5} more")
    print(f"Description: {database_agent.description}")

    return True

if __name__ == "__main__":
    success = test_database_agent()

    print("\n" + "=" * 80)
    if success:
        print("✅ TEST PASSED: Database agent configuration is correct!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Install MongoDB: sudo apt-get install mongodb")
        print("2. Start MongoDB: sudo systemctl start mongodb")
        print("3. Install pymongo: pip install pymongo>=4.6.0")
        print("4. Test with actual MongoDB connection")
        sys.exit(0)
    else:
        print("❌ TEST FAILED: Database agent configuration has issues!")
        print("=" * 80)
        sys.exit(1)
