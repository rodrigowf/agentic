#!/usr/bin/env python3
"""Test the take_screenshot function to verify it produces proper screenshots."""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.image_tools import take_screenshot


def test_screenshot():
    """Test take_screenshot function."""
    print("=" * 60)
    print("Testing take_screenshot function")
    print("=" * 60)

    # Test 1: Basic screenshot with auto-generated path
    print("\n[Test 1] Taking screenshot with auto-generated path...")
    result1 = take_screenshot("Test screenshot - basic capture")
    print(f"Result: {result1}")

    # Test 2: Screenshot with custom path
    custom_path = "/home/rodrigo/agentic/workspace/screenshots/test_custom.png"
    print(f"\n[Test 2] Taking screenshot with custom path: {custom_path}")
    result2 = take_screenshot("Test screenshot - custom path", output_path=custom_path)
    print(f"Result: {result2}")

    # Check if files were created
    print("\n" + "=" * 60)
    print("Verifying screenshots...")
    print("=" * 60)

    # Extract file paths from results
    def extract_path(result_str):
        if "saved to:" in result_str:
            # Extract path after "saved to:"
            parts = result_str.split("saved to:")
            if len(parts) > 1:
                path_part = parts[1].split("\n")[0].strip()
                return Path(path_part)
        return None

    path1 = extract_path(result1)
    path2 = extract_path(result2)

    # Verify files exist
    for i, path in enumerate([path1, path2], 1):
        if path and path.exists():
            size = path.stat().st_size
            print(f"✓ Test {i}: Screenshot exists at {path}")
            print(f"  Size: {size:,} bytes")

            # Check if it's a valid PNG file
            with open(path, 'rb') as f:
                header = f.read(8)
                is_png = header == b'\x89PNG\r\n\x1a\n'
                print(f"  Valid PNG: {is_png}")

            # Try to analyze with PIL if available
            try:
                from PIL import Image
                with Image.open(path) as img:
                    print(f"  Dimensions: {img.width}x{img.height}")
                    print(f"  Format: {img.format}")
                    print(f"  Mode: {img.mode}")
            except ImportError:
                print("  PIL not available for detailed analysis")
            except Exception as e:
                print(f"  Error analyzing image: {e}")
        else:
            print(f"✗ Test {i}: Screenshot not found at {path}")

    # Show environment info
    print("\n" + "=" * 60)
    print("Environment Information")
    print("=" * 60)
    print(f"Display: {os.environ.get('DISPLAY', 'Not set')}")
    print(f"Wayland Display: {os.environ.get('WAYLAND_DISPLAY', 'Not set')}")
    print(f"XDG Session Type: {os.environ.get('XDG_SESSION_TYPE', 'Not set')}")
    print(f"Screenshot Backend: {os.environ.get('SCREENSHOT_BACKEND', 'Auto-detect')}")

    # Check available screenshot utilities
    print("\n" + "=" * 60)
    print("Available Screenshot Utilities")
    print("=" * 60)

    import shutil
    utilities = ['mss', 'pyautogui', 'grim', 'hyprshot', 'scrot', 'screencapture']

    for util in utilities:
        if util in ['mss', 'pyautogui']:
            try:
                __import__(util)
                print(f"✓ {util}: Available (Python library)")
            except ImportError:
                print(f"✗ {util}: Not installed (Python library)")
        else:
            if shutil.which(util):
                print(f"✓ {util}: Available (CLI tool)")
            else:
                print(f"✗ {util}: Not found (CLI tool)")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_screenshot()
