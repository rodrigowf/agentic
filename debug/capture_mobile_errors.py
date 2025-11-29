#!/usr/bin/env python3
"""
Capture console errors from mobile Chrome via DevTools Protocol
"""
import asyncio
import websockets
import json
import sys
from datetime import datetime

async def capture_errors():
    uri = "ws://localhost:9222/devtools/page/1289"

    print(f"🔍 Connecting to mobile Chrome: {uri}")
    print("=" * 80)

    try:
        async with websockets.connect(uri) as ws:
            # Enable console and runtime
            await ws.send(json.dumps({"id": 1, "method": "Console.enable"}))
            await ws.send(json.dumps({"id": 2, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 3, "method": "Log.enable"}))

            print("✅ Connected - listening for errors and MobileVoice logs...\n")

            error_count = 0

            async for message in ws:
                data = json.loads(message)
                method = data.get("method")

                # Console API calls (console.log, console.error, etc.)
                if method == "Runtime.consoleAPICalled":
                    params = data.get("params", {})
                    args = params.get("args", [])
                    msg_type = params.get("type", "log")

                    # Build message
                    parts = []
                    for arg in args:
                        if arg.get("type") == "string":
                            parts.append(arg.get("value", ""))
                        else:
                            parts.append(str(arg.get("value", arg.get("description", ""))))

                    full_msg = " ".join(parts)

                    # Print all MobileVoice logs
                    if "[MobileVoice" in full_msg:
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                        if msg_type == "error":
                            print(f"❌ [{timestamp}] {full_msg}")
                            error_count += 1
                        elif msg_type == "warning":
                            print(f"⚠️  [{timestamp}] {full_msg}")
                        else:
                            print(f"ℹ️  [{timestamp}] {full_msg}")

                # Runtime exceptions
                elif method == "Runtime.exceptionThrown":
                    exception = data.get("params", {}).get("exceptionDetails", {})
                    text = exception.get("text", "Unknown error")
                    description = exception.get("exception", {}).get("description", "")

                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"\n💥 [{timestamp}] EXCEPTION THROWN!")
                    print(f"   {text}")
                    if description:
                        print(f"   {description}")
                    print()
                    error_count += 1

                # Log entries (errors from browser)
                elif method == "Log.entryAdded":
                    entry = data.get("params", {}).get("entry", {})
                    level = entry.get("level")
                    text = entry.get("text", "")

                    if level == "error":
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"🚨 [{timestamp}] LOG ERROR: {text}")
                        error_count += 1

    except websockets.exceptions.ConnectionClosed:
        print("\n❌ Connection closed")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("📱 Mobile Voice Error Capture Tool")
    print("Press Ctrl+C to stop\n")

    try:
        asyncio.run(capture_errors())
    except KeyboardInterrupt:
        print("\n\n✅ Stopped by user")
