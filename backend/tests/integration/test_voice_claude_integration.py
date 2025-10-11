#!/usr/bin/env python3
"""
Integration test for Voice Assistant + Claude Code with bypassed permissions.
This simulates the complete flow when the voice assistant sends a task to Claude Code.
"""

import asyncio
import websockets
import json
import sys


async def test_voice_claude_integration():
    """Test complete voice assistant to Claude Code integration."""
    print("=" * 70)
    print("Voice Assistant + Claude Code Integration Test")
    print("Testing: Permission-free Claude Code execution via WebSocket")
    print("=" * 70)

    uri = "ws://localhost:8002/api/runs/ClaudeCode"

    try:
        print(f"\n1. Connecting to Claude Code WebSocket: {uri}")
        async with websockets.connect(uri) as websocket:
            print("✓ Connected successfully")

            # Send a simple test message that requires tool usage
            test_message = {
                "type": "user_message",
                "data": "Please list the Python files in the backend directory using the Bash tool"
            }

            print(f"\n2. Sending test message:")
            print(f"   {test_message['data']}")
            await websocket.send(json.dumps(test_message))
            print("✓ Message sent")

            print("\n3. Receiving events from Claude Code...")
            print("-" * 70)

            event_count = 0
            tool_calls = []
            errors = []
            max_events = 25  # Safety limit
            completed = False

            while event_count < max_events:
                try:
                    # Wait for event with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    event = json.loads(message)
                    event_count += 1

                    event_type = event.get("type", "unknown")
                    print(f"\nEvent {event_count}: {event_type}")

                    # Handle different event types
                    if event_type == "SystemEvent":
                        data = event.get("data", {})
                        msg = data.get("message", "")
                        print(f"  System: {msg}")

                    elif event_type == "TextMessage":
                        data = event.get("data", {})
                        content = data.get("content", "")[:150]
                        print(f"  Content: {content}...")

                    elif event_type == "ToolCallRequestEvent":
                        data = event.get("data", {})
                        tool_name = data.get("name", "unknown")
                        tool_calls.append({
                            "name": tool_name,
                            "arguments": data.get("arguments", {}),
                            "id": data.get("id")
                        })
                        print(f"  🛠️  Tool: {tool_name}")
                        print(f"  ⚠️  PERMISSION CHECK: Should execute without asking!")

                    elif event_type == "ToolCallExecutionEvent":
                        data = event.get("data", {})
                        is_error = data.get("is_error", False)
                        result = data.get("result", "")[:200]

                        if is_error:
                            errors.append(result)
                            print(f"  ❌ ERROR")
                            print(f"  Error: {result}")
                        else:
                            print(f"  ✅ SUCCESS")
                            print(f"  Result preview: {result}...")

                    elif event_type == "TaskResult":
                        data = event.get("data", {})
                        outcome = data.get("outcome", "unknown")
                        message_text = data.get("message", "")[:200]
                        print(f"  Outcome: {outcome}")
                        print(f"  Message: {message_text}...")
                        completed = True
                        break

                    elif event_type == "Error" or event_type == "error":
                        data = event.get("data", {})
                        error_msg = data.get("message", str(event))
                        errors.append(error_msg)
                        print(f"  ❌ ERROR: {error_msg}")

                    elif event_type == "system":
                        # Initial system event
                        data = event.get("data", {})
                        print(f"  System: {data}")

                except asyncio.TimeoutError:
                    print("\n⚠️  Timeout waiting for events (30s)")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("\n⚠️  WebSocket connection closed")
                    break
                except json.JSONDecodeError as e:
                    print(f"\n❌ JSON decode error: {e}")
                    break

            # Final report
            print("\n" + "=" * 70)
            print("TEST RESULTS")
            print("=" * 70)
            print(f"Total events received: {event_count}")
            print(f"Tool calls made: {len(tool_calls)}")
            print(f"Errors encountered: {len(errors)}")
            print(f"Task completed: {'✓ Yes' if completed else '✗ No'}")

            if tool_calls:
                print("\nTool calls executed:")
                for i, tool_call in enumerate(tool_calls, 1):
                    print(f"  {i}. {tool_call['name']}")
                    args = tool_call.get('arguments', {})
                    if 'command' in args:
                        print(f"     Command: {args['command']}")

            if errors:
                print("\nErrors:")
                for i, error in enumerate(errors, 1):
                    print(f"  {i}. {error[:100]}...")

            # Verdict
            print("\n" + "=" * 70)
            if len(tool_calls) > 0 and len(errors) == 0 and completed:
                print("✅ TEST PASSED")
                print("Claude Code executed tools without permission prompts!")
                print("The voice assistant integration is working correctly.")
                return True
            elif len(tool_calls) > 0 and len(errors) > 0:
                print("⚠️  TEST PARTIAL")
                print("Tools were called but some errors occurred.")
                print("Check the errors above for details.")
                return False
            elif len(tool_calls) == 0:
                print("❌ TEST FAILED")
                print("No tool calls were made. Claude Code may be waiting for permissions.")
                print("Check permission_mode configuration.")
                return False
            else:
                print("❌ TEST FAILED")
                print("Task did not complete successfully.")
                return False

    except websockets.exceptions.WebSocketException as e:
        print(f"\n❌ WebSocket error: {e}")
        print("\nTroubleshooting:")
        print("1. Is the backend running? (cd backend && uvicorn main:app --reload)")
        print("2. Is the correct port being used? (Check with: ps aux | grep uvicorn)")
        print("3. Check backend logs for errors")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_voice_claude_integration())
    sys.exit(0 if success else 1)
