#!/usr/bin/env python3
"""
Backend-only E2E Test for MainConversation -> HTMLDisplay Flow

This test directly connects to the backend WebSocket API and monitors
the agent orchestration flow to verify HTMLDisplay is invoked.

Usage: python3 debug/e2e_backend_test.py
"""

import asyncio
import json
import websockets
import os
from datetime import datetime
from pathlib import Path

# Configuration
BACKEND_URL = "ws://localhost:8000"
AGENT_NAME = "MainConversation"
TEST_TASK = "Please research the weather forecast for Rio de Janeiro for tomorrow, then display it to me with a beautiful HTML visualization."
TIMEOUT_SECONDS = 180  # 3 minutes

# Output directory
OUTPUT_DIR = Path(__file__).parent / "e2e_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Log file
LOG_FILE = OUTPUT_DIR / f"backend_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def log(message: str, data=None):
    """Log a message to console and file."""
    timestamp = datetime.now().isoformat()
    if data:
        log_line = f"[{timestamp}] {message}: {json.dumps(data, indent=2, default=str)}"
    else:
        log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, "a") as f:
        f.write(log_line + "\n")


async def run_test():
    """Main test function."""
    log("=" * 60)
    log("Starting Backend E2E Test for MainConversation -> HTMLDisplay")
    log("=" * 60)
    log(f"Test task: {TEST_TASK}")
    log(f"Connecting to: {BACKEND_URL}/api/runs/{AGENT_NAME}")

    # Track messages and agents
    all_messages = []
    agents_involved = set()
    html_display_invoked = False
    manager_terminate = False
    agent_finished = False

    try:
        ws_url = f"{BACKEND_URL}/api/runs/{AGENT_NAME}"
        log(f"Opening WebSocket connection to: {ws_url}")

        async with websockets.connect(ws_url) as ws:
            log("WebSocket connected!")

            # Send the run command
            run_message = json.dumps({"type": "run", "data": TEST_TASK})
            log(f"Sending run command: {run_message[:100]}...")
            await ws.send(run_message)
            log("Run command sent, waiting for agent messages...")

            start_time = asyncio.get_event_loop().time()

            while True:
                try:
                    # Check timeout
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > TIMEOUT_SECONDS:
                        log(f"TIMEOUT after {elapsed:.0f} seconds")
                        break

                    # Wait for message with timeout
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    except asyncio.TimeoutError:
                        # Log progress every 30 seconds
                        if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                            log(f"Progress at {int(elapsed)}s - Messages: {len(all_messages)}, Agents: {list(agents_involved)}")
                        continue

                    # Parse message
                    try:
                        msg_data = json.loads(message)
                        all_messages.append(msg_data)

                        msg_type = msg_data.get("type", "")
                        data = msg_data.get("data", {})

                        # Extract source agent
                        source = None
                        if isinstance(data, dict):
                            source = data.get("source")

                        if source:
                            agents_involved.add(source)

                        # Check for HTMLDisplay
                        if source == "HTMLDisplay":
                            html_display_invoked = True
                            log("HTMLDisplay INVOKED!", {"content": str(data.get("content", ""))[:200]})

                        # Check for Manager TERMINATE
                        if source == "Manager":
                            content = data.get("content", "") if isinstance(data, dict) else str(data)
                            if "TERMINATE" in content:
                                manager_terminate = True
                                log("Manager TERMINATE detected", {"content": content[:300]})

                        # Check for agent run finished
                        if msg_type == "system":
                            system_msg = data.get("message", "") if isinstance(data, dict) else str(data)
                            if "Agent run finished" in system_msg:
                                agent_finished = True
                                log("Agent run finished!")
                                break

                        # Log important messages
                        if msg_type in ["agent", "tool_call", "tool_result", "error"]:
                            content_preview = ""
                            if isinstance(data, dict):
                                content_preview = str(data.get("content", data.get("message", "")))[:150]
                            else:
                                content_preview = str(data)[:150]
                            log(f"[{msg_type}] from {source}", {"preview": content_preview})

                        # Log system messages
                        if msg_type == "system":
                            log(f"[SYSTEM]", data)

                        # Log errors
                        if msg_type == "error":
                            log("ERROR!", data)

                    except json.JSONDecodeError:
                        log(f"Non-JSON message: {message[:100]}")

                except websockets.exceptions.ConnectionClosed as e:
                    log(f"WebSocket closed: {e}")
                    break

    except Exception as e:
        log(f"Connection error: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")

    # Generate report
    log("")
    log("=" * 60)
    log("TEST REPORT")
    log("=" * 60)

    report = {
        "success": agent_finished and html_display_invoked,
        "agent_finished": agent_finished,
        "html_display_invoked": html_display_invoked,
        "manager_terminated": manager_terminate,
        "agents_involved": list(agents_involved),
        "total_messages": len(all_messages),
    }

    log("Report", report)

    # Save all messages
    messages_file = OUTPUT_DIR / "backend_test_messages.json"
    with open(messages_file, "w") as f:
        json.dump(all_messages, f, indent=2, default=str)
    log(f"All messages saved to: {messages_file}")

    # Analyze the flow
    log("")
    log("FLOW ANALYSIS:")

    # Show agent sequence
    agent_sequence = []
    for msg in all_messages:
        data = msg.get("data", {})
        if isinstance(data, dict) and data.get("source"):
            agent_sequence.append(data["source"])

    log(f"Agent sequence (first 50): {agent_sequence[:50]}")

    # Show Manager messages
    log("")
    log("MANAGER MESSAGES:")
    for msg in all_messages:
        data = msg.get("data", {})
        if isinstance(data, dict) and data.get("source") == "Manager":
            content = data.get("content", "")
            log(f"  -> {content[:400]}")

    # Show Researcher completion
    log("")
    log("RESEARCHER MESSAGES (last 3):")
    researcher_msgs = [msg for msg in all_messages
                       if isinstance(msg.get("data", {}), dict)
                       and msg.get("data", {}).get("source") == "Researcher"]
    for msg in researcher_msgs[-3:]:
        content = msg.get("data", {}).get("content", "")
        log(f"  -> {content[:300]}...")

    # Check HTML output directory
    log("")
    log("HTML OUTPUT CHECK:")
    html_output_dir = Path(__file__).parent.parent / "backend" / "data" / "workspace" / "html_outputs"
    if html_output_dir.exists():
        html_files = list(html_output_dir.glob("*.html"))
        log(f"HTML files in output dir: {[f.name for f in html_files[-5:]]}")
    else:
        log(f"HTML output directory does not exist: {html_output_dir}")

    log("")
    log("=" * 60)

    if report["success"]:
        log("TEST PASSED! HTMLDisplay was invoked correctly.")
    else:
        if not html_display_invoked:
            log("TEST FAILED: HTMLDisplay was NOT invoked!")
            log("This means Manager did not delegate to HTMLDisplay after Researcher finished.")
        else:
            log("TEST FAILED: Agent did not finish properly")

    log("=" * 60)
    log(f"Results saved to: {OUTPUT_DIR}")

    return report


if __name__ == "__main__":
    asyncio.run(run_test())
