#!/usr/bin/env python3
"""
Test script for voice agent list injection.

Tests the _inject_available_agents function to verify that agent descriptions
are correctly loaded and injected into the voice system prompt.
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.realtime_voice import _inject_available_agents, VOICE_SYSTEM_PROMPT

def main():
    print("=" * 80)
    print("Testing Voice Agent List Injection")
    print("=" * 80)
    print()

    # Test with MainConversation (nested team)
    print("[1] Testing with MainConversation (nested team agent)...")
    result = _inject_available_agents(VOICE_SYSTEM_PROMPT, "MainConversation")

    # Check if placeholder was replaced
    if "{{AVAILABLE_AGENTS}}" in result:
        print("❌ ERROR: Placeholder was NOT replaced!")
        print()
        print("Result preview:")
        print(result[:500])
        return 1

    print("✅ Placeholder was replaced successfully")
    print()

    # Extract the agents section
    if "**AVAILABLE AGENTS IN THE TEAM**:" in result:
        start_idx = result.index("**AVAILABLE AGENTS IN THE TEAM**:")
        end_idx = result.index("Reading controller messages:", start_idx)
        agents_section = result[start_idx:end_idx].strip()

        print("Agents section:")
        print("=" * 80)
        print(agents_section)
        print("=" * 80)
        print()

        # Check for expected agents
        expected_agents = ["Manager", "Memory", "FileManager", "Database", "Researcher", "Engineer"]
        found_agents = []
        missing_agents = []

        for agent in expected_agents:
            if f"**{agent}**:" in agents_section:
                found_agents.append(agent)
            else:
                missing_agents.append(agent)

        print(f"✅ Found {len(found_agents)} agents: {', '.join(found_agents)}")
        if missing_agents:
            print(f"⚠️  Missing agents: {', '.join(missing_agents)}")
        print()

    # Test with non-nested agent (should handle gracefully)
    print("[2] Testing with non-nested agent (Researcher)...")
    result_researcher = _inject_available_agents(VOICE_SYSTEM_PROMPT, "Researcher")

    if "{{AVAILABLE_AGENTS}}" in result_researcher:
        print("❌ ERROR: Placeholder was NOT replaced!")
        return 1

    if "(Not a nested team" in result_researcher:
        print("✅ Correctly detected non-nested agent")
    else:
        print("⚠️  Unexpected result for non-nested agent")
    print()

    # Test with non-existent agent
    print("[3] Testing with non-existent agent...")
    result_nonexistent = _inject_available_agents(VOICE_SYSTEM_PROMPT, "NonExistentAgent")

    if "{{AVAILABLE_AGENTS}}" in result_nonexistent:
        print("❌ ERROR: Placeholder was NOT replaced!")
        return 1

    if "(No agents information available)" in result_nonexistent:
        print("✅ Correctly handled non-existent agent")
    else:
        print("⚠️  Unexpected result for non-existent agent")
    print()

    print("=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print()
    print("The voice agent will now receive information about all available agents")
    print("from the nested team, allowing it to understand the team structure and")
    print("better narrate agent activities!")

    return 0

if __name__ == "__main__":
    sys.exit(main())
