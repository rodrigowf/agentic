#!/usr/bin/env python3
"""
Comprehensive test script for database tools and operations.
Tests all MongoDB tools with actual database connection.
"""

import sys
sys.path.insert(0, '.')

from tools.database import (
    register_collection_schema,
    insert_document,
    insert_many_documents,
    find_documents,
    update_document,
    delete_document,
    aggregate,
    create_index,
    list_collections,
    drop_collection,
    _get_mongo_client
)
import json

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_connection():
    """Test MongoDB connection"""
    print_section("TEST 1: MongoDB Connection")
    try:
        client, db = _get_mongo_client()
        result = client.admin.command('ping')
        print(f"✅ Connected to MongoDB successfully")
        print(f"   Database: {db.name}")
        print(f"   Ping result: {result}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_register_schema():
    """Test collection schema registration"""
    print_section("TEST 2: Register Collection Schema")
    try:
        result = register_collection_schema(
            collection_name="test_users",
            description="Test user collection for database agent testing",
            structure={
                "username": "string (unique)",
                "email": "string (unique)",
                "age": "number",
                "created_at": "datetime",
                "active": "boolean"
            },
            usage="Store test user data. Always create unique indexes on username and email.",
            example={
                "username": "test_user",
                "email": "test@example.com",
                "age": 25,
                "created_at": "2025-12-01T10:00:00Z",
                "active": True
            }
        )
        print(f"✅ {result}")
        return True
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        return False

def test_insert_single():
    """Test single document insert"""
    print_section("TEST 3: Insert Single Document")
    try:
        result = insert_document(
            collection_name="test_users",
            document={
                "username": "alice",
                "email": "alice@example.com",
                "age": 28,
                "created_at": "2025-12-01T10:00:00Z",
                "active": True
            }
        )
        print(f"✅ {result}")
        return True
    except Exception as e:
        print(f"❌ Insert failed: {e}")
        return False

def test_insert_many():
    """Test bulk insert"""
    print_section("TEST 4: Insert Many Documents")
    try:
        result = insert_many_documents(
            collection_name="test_users",
            documents=[
                {"username": "bob", "email": "bob@example.com", "age": 32, "active": True},
                {"username": "charlie", "email": "charlie@example.com", "age": 24, "active": False},
                {"username": "diana", "email": "diana@example.com", "age": 29, "active": True},
                {"username": "eve", "email": "eve@example.com", "age": 35, "active": True}
            ]
        )
        print(f"✅ {result}")
        return True
    except Exception as e:
        print(f"❌ Bulk insert failed: {e}")
        return False

def test_find():
    """Test document queries"""
    print_section("TEST 5: Find Documents")
    try:
        # Find all active users
        result = find_documents(
            collection_name="test_users",
            query={"active": True},
            limit=10
        )
        data = json.loads(result)
        print(f"✅ Found {data['count']} active users")
        for doc in data['documents']:
            print(f"   - {doc['username']} ({doc['email']})")

        # Find with age filter
        result2 = find_documents(
            collection_name="test_users",
            query={"age": {"$gte": 30}},
            limit=10
        )
        data2 = json.loads(result2)
        print(f"✅ Found {data2['count']} users aged 30+")

        return True
    except Exception as e:
        print(f"❌ Find failed: {e}")
        return False

def test_update():
    """Test document updates"""
    print_section("TEST 6: Update Documents")
    try:
        # Update single user
        result = update_document(
            collection_name="test_users",
            query={"username": "alice"},
            update={"$set": {"age": 29}},
            update_many=False
        )
        print(f"✅ {result}")

        # Update multiple users
        result2 = update_document(
            collection_name="test_users",
            query={"active": False},
            update={"$set": {"active": True}},
            update_many=True
        )
        print(f"✅ {result2}")

        # Increment age
        result3 = update_document(
            collection_name="test_users",
            query={"username": "bob"},
            update={"$inc": {"age": 1}},
            update_many=False
        )
        print(f"✅ Incremented age: {result3}")

        return True
    except Exception as e:
        print(f"❌ Update failed: {e}")
        return False

def test_aggregate():
    """Test aggregation pipeline"""
    print_section("TEST 7: Aggregation Pipeline")
    try:
        # Count by active status
        result = aggregate(
            collection_name="test_users",
            pipeline=[
                {"$group": {
                    "_id": "$active",
                    "count": {"$sum": 1},
                    "avg_age": {"$avg": "$age"}
                }},
                {"$sort": {"_id": 1}}
            ]
        )
        data = json.loads(result)
        print(f"✅ Aggregation results:")
        for item in data:
            status = "active" if item['_id'] else "inactive"
            print(f"   - {status}: {item['count']} users, avg age: {item.get('avg_age', 0):.1f}")

        return True
    except Exception as e:
        print(f"❌ Aggregation failed: {e}")
        return False

def test_create_index():
    """Test index creation"""
    print_section("TEST 8: Create Indexes")
    try:
        # Create unique index on username
        result = create_index(
            collection_name="test_users",
            field_name="username",
            unique=True
        )
        print(f"✅ Created unique index: {result}")

        # Create regular index on age
        result2 = create_index(
            collection_name="test_users",
            field_name="age",
            unique=False
        )
        print(f"✅ Created regular index: {result2}")

        return True
    except Exception as e:
        print(f"❌ Index creation failed: {e}")
        return False

def test_list_collections():
    """Test collection listing"""
    print_section("TEST 9: List Collections")
    try:
        result = list_collections()
        print(f"✅ Collections list:\n{result}")
        return True
    except Exception as e:
        print(f"❌ List collections failed: {e}")
        return False

def test_delete():
    """Test document deletion"""
    print_section("TEST 10: Delete Documents")
    try:
        # Delete single document
        result = delete_document(
            collection_name="test_users",
            query={"username": "eve"},
            delete_many=False
        )
        print(f"✅ {result}")

        # Verify deletion
        verify = find_documents(
            collection_name="test_users",
            query={},
            limit=10
        )
        data = json.loads(verify)
        print(f"✅ Remaining users: {data['count']}")

        return True
    except Exception as e:
        print(f"❌ Delete failed: {e}")
        return False

def test_drop_collection():
    """Test collection dropping"""
    print_section("TEST 11: Drop Collection")
    try:
        result = drop_collection(collection_name="test_users")
        print(f"✅ {result}")

        # Verify collection is gone
        verify = list_collections()
        print(f"✅ Collections after drop:\n{verify}")

        return True
    except Exception as e:
        print(f"❌ Drop collection failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 80)
    print("  DATABASE TOOLS COMPREHENSIVE TEST SUITE")
    print("=" * 80)

    tests = [
        ("MongoDB Connection", test_connection),
        ("Register Schema", test_register_schema),
        ("Insert Single Document", test_insert_single),
        ("Insert Many Documents", test_insert_many),
        ("Find Documents", test_find),
        ("Update Documents", test_update),
        ("Aggregation Pipeline", test_aggregate),
        ("Create Indexes", test_create_index),
        ("List Collections", test_list_collections),
        ("Delete Documents", test_delete),
        ("Drop Collection", test_drop_collection),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "-" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
