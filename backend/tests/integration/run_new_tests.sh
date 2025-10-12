#!/bin/bash
# Script to run the new integration tests

set -e

echo "======================================"
echo "Running New Integration Tests"
echo "======================================"
echo ""

# Change to backend directory
cd "$(dirname "$0")/../.."

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not in virtual environment"
    echo "Run: source venv/bin/activate"
    echo ""
fi

# Function to run a test file
run_test() {
    local test_file=$1
    local test_name=$2

    echo "--------------------------------------"
    echo "Running: $test_name"
    echo "--------------------------------------"

    if pytest "tests/integration/$test_file" -v; then
        echo "✓ $test_name PASSED"
    else
        echo "✗ $test_name FAILED"
        return 1
    fi
    echo ""
}

# Track results
FAILED=0

# Run each test file
run_test "test_api_agents.py" "Agent API Tests" || FAILED=$((FAILED+1))
run_test "test_api_tools.py" "Tool API Tests" || FAILED=$((FAILED+1))
run_test "test_api_voice.py" "Voice API Tests" || FAILED=$((FAILED+1))
run_test "test_websocket_agents.py" "WebSocket Tests" || FAILED=$((FAILED+1))
run_test "test_database_operations.py" "Database Tests" || FAILED=$((FAILED+1))

# Summary
echo "======================================"
echo "Test Summary"
echo "======================================"
if [ $FAILED -eq 0 ]; then
    echo "✓ All tests PASSED"
    exit 0
else
    echo "✗ $FAILED test suite(s) FAILED"
    exit 1
fi
