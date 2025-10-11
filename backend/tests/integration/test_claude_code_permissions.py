#!/usr/bin/env python3
"""
Test script for Claude Code integration with bypassed permissions.
This simulates how the voice assistant uses Claude Code.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.claude_code_controller import ClaudeCodeSession


async def test_claude_code_permissions():
    """Test Claude Code with bypassPermissions mode."""
    print("=" * 60)
    print("Testing Claude Code with bypassPermissions mode")
    print("=" * 60)

    session = ClaudeCodeSession(
        working_dir="/home/rodrigo/agentic",
        model="claude-sonnet-4-5-20250929",
        permission_mode="bypassPermissions"
    )

    try:
        print("\n1. Starting Claude Code session...")
        await session.start()
        print("✓ Session started successfully")

        print("\n2. Sending test message that requires file operations...")
        test_message = "List the files in the current directory using the Bash tool with 'ls -la' command"
        await session.send_message(test_message)
        print(f"✓ Sent message: {test_message}")

        print("\n3. Streaming events from Claude Code...")
        print("-" * 60)

        event_count = 0
        tool_call_count = 0
        max_events = 20  # Limit events to avoid infinite loop

        async for event in session.stream_events():
            event_count += 1
            event_type = event.get("type", "unknown")

            print(f"\nEvent {event_count}: {event_type}")

            # Display key information based on event type
            if event_type == "SystemEvent":
                data = event.get("data", {})
                print(f"  System: {data.get('message')}")

            elif event_type == "TextMessage":
                data = event.get("data", {})
                content = data.get("content", "")[:100]  # First 100 chars
                print(f"  Content: {content}...")

            elif event_type == "ToolCallRequestEvent":
                tool_call_count += 1
                data = event.get("data", {})
                tool_name = data.get("name", "unknown")
                print(f"  Tool: {tool_name}")
                print(f"  ⚠️  PERMISSION CHECK: This should execute without asking!")

            elif event_type == "ToolCallExecutionEvent":
                data = event.get("data", {})
                result = data.get("result", "")[:100]  # First 100 chars
                is_error = data.get("is_error", False)
                status = "❌ ERROR" if is_error else "✓ SUCCESS"
                print(f"  {status}")
                print(f"  Result preview: {result}...")

            elif event_type == "TaskResult":
                data = event.get("data", {})
                outcome = data.get("outcome", "unknown")
                message = data.get("message", "")
                print(f"  Outcome: {outcome}")
                print(f"  Message: {message}")
                print("\n" + "=" * 60)
                print("TEST COMPLETED")
                print("=" * 60)
                break

            elif event_type == "error" or event_type == "Error":
                data = event.get("data", {})
                error_msg = data.get("message", str(event))
                print(f"  ❌ ERROR: {error_msg}")

            # Safety limit
            if event_count >= max_events:
                print(f"\n⚠️  Reached max events ({max_events}), stopping...")
                break

        print(f"\n4. Summary:")
        print(f"   - Total events: {event_count}")
        print(f"   - Tool calls: {tool_call_count}")

        if tool_call_count > 0:
            print("\n✓ SUCCESS: Claude Code executed tools without permission prompts!")
        else:
            print("\n⚠️  WARNING: No tool calls detected. This might indicate an issue.")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n5. Stopping session...")
        await session.stop()
        print("✓ Session stopped")


if __name__ == "__main__":
    asyncio.run(test_claude_code_permissions())
