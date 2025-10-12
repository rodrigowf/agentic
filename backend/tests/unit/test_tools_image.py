"""
Unit tests for tools/image_tools.py

Comprehensive tests for image tools:
- take_screenshot with various parameters and scenarios
- generate_test_image with different dimensions and content
- get_sample_image with different types (chart, diagram, photo)
- Image file creation and validation
- Error handling
- PIL operations
- Mock screenshot backends (mss, pyautogui, gnome_dbus, cli)
"""

import pytest
import os
import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call, Mock
from PIL import Image

# Import image tools
from tools.image_tools import (
    take_screenshot,
    generate_test_image,
    get_sample_image,
    _select_screenshot_command,
    _image_is_effectively_black,
    _create_placeholder_image,
    take_screenshot_tool,
    generate_test_image_tool,
    get_sample_image_tool,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    """Create temporary workspace directory for screenshots."""
    workspace = tmp_path / "workspace" / "screenshots"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return workspace


@pytest.fixture
def mock_pil_image():
    """Mock PIL Image."""
    with patch("tools.image_tools.Image") as mock_img:
        yield mock_img


@pytest.fixture
def sample_image_path(tmp_path):
    """Create a sample test image."""
    img_path = tmp_path / "test_image.png"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(img_path)
    return img_path


@pytest.fixture
def black_image_path(tmp_path):
    """Create a black test image."""
    img_path = tmp_path / "black_image.png"
    img = Image.new("RGB", (100, 100), color="black")
    img.save(img_path)
    return img_path


# ============================================================================
# Test Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Test internal helper functions."""

    def test_select_screenshot_command_wayland(self, monkeypatch):
        """Test screenshot command selection on Wayland."""
        monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")

        with patch("tools.image_tools.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: cmd == "grim"

            target_path = Path("/tmp/test.png")
            command = _select_screenshot_command(target_path)

            assert command is not None
            assert command[0] == "grim"
            assert str(target_path) in command

    def test_select_screenshot_command_x11(self, monkeypatch):
        """Test screenshot command selection on X11."""
        monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

        with patch("tools.image_tools.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: cmd == "scrot"

            target_path = Path("/tmp/test.png")
            command = _select_screenshot_command(target_path)

            assert command is not None
            assert command[0] == "scrot"

    def test_select_screenshot_command_macos(self, monkeypatch):
        """Test screenshot command selection on macOS."""
        monkeypatch.setattr("sys.platform", "darwin")

        with patch("tools.image_tools.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: cmd == "screencapture"

            target_path = Path("/tmp/test.png")
            command = _select_screenshot_command(target_path)

            assert command is not None
            assert command[0] == "screencapture"
            assert "-x" in command

    def test_select_screenshot_command_none_available(self):
        """Test when no screenshot command is available."""
        with patch("tools.image_tools.shutil.which") as mock_which:
            mock_which.return_value = None

            target_path = Path("/tmp/test.png")
            command = _select_screenshot_command(target_path)

            assert command is None

    def test_image_is_effectively_black_true(self, black_image_path):
        """Test detecting black image."""
        result = _image_is_effectively_black(black_image_path)
        assert result is True

    def test_image_is_effectively_black_false(self, sample_image_path):
        """Test detecting non-black image."""
        result = _image_is_effectively_black(sample_image_path)
        assert result is False

    def test_image_is_effectively_black_no_pil(self, sample_image_path):
        """Test black detection when PIL is not available."""
        with patch.dict('sys.modules', {'PIL': None, 'PIL.Image': None}):
            result = _image_is_effectively_black(sample_image_path)
            assert result is False  # Should return False if PIL not available

    def test_image_is_effectively_black_error(self, tmp_path):
        """Test black detection with corrupted image."""
        bad_image = tmp_path / "bad.png"
        bad_image.write_text("not an image")

        result = _image_is_effectively_black(bad_image)
        assert result is False  # Should handle gracefully

    def test_create_placeholder_image(self, tmp_path):
        """Test creating placeholder image."""
        target_path = tmp_path / "screenshot.png"
        description = "Test screenshot"
        reason = "Test failure reason"

        placeholder_path, message = _create_placeholder_image(target_path, description, reason)

        assert placeholder_path.exists()
        assert placeholder_path.name.endswith("_placeholder.png")
        assert "Warning" in message
        assert description in message
        assert reason in message

        # Verify image is valid
        img = Image.open(placeholder_path)
        assert img.size == (1280, 720)
        assert img.mode == "RGB"

    def test_create_placeholder_image_no_pil(self, tmp_path):
        """Test placeholder creation when PIL is not available."""
        target_path = tmp_path / "screenshot.png"

        with patch("tools.image_tools.Image", side_effect=ImportError):
            placeholder_path, message = _create_placeholder_image(
                target_path, "desc", "reason"
            )

            assert "PIL (Pillow) library not installed" in message
            assert not placeholder_path.exists()


# ============================================================================
# Test take_screenshot
# ============================================================================

class TestTakeScreenshot:
    """Test take_screenshot function."""

    @patch("tools.image_tools.mss.mss")
    def test_take_screenshot_mss_success(self, mock_mss, temp_workspace):
        """Test successful screenshot using mss backend."""
        mock_sct = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct

        def side_effect_shot(output):
            # Create a test image
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(output)

        mock_sct.shot = side_effect_shot

        result = take_screenshot("Test description")

        assert "Screenshot captured and saved to:" in result
        assert "Test description" in result
        assert ".png" in result

        # Extract and verify path
        path_match = re.search(r"saved to: (.+\.png)", result)
        assert path_match
        screenshot_path = Path(path_match.group(1))
        assert screenshot_path.exists()

    @patch("tools.image_tools.pyautogui.screenshot")
    def test_take_screenshot_pyautogui_success(self, mock_pyautogui, temp_workspace):
        """Test successful screenshot using pyautogui backend."""
        # Mock mss to fail so pyautogui is tried
        with patch("tools.image_tools.mss.mss", side_effect=ImportError):
            mock_img = MagicMock()

            def side_effect_save(path):
                img = Image.new("RGB", (100, 100), color="green")
                img.save(path)

            mock_img.save = side_effect_save
            mock_pyautogui.return_value = mock_img

            result = take_screenshot("Test with pyautogui")

            assert "Screenshot captured and saved to:" in result

    @patch("tools.image_tools.subprocess.run")
    def test_take_screenshot_gnome_dbus_success(self, mock_run, temp_workspace):
        """Test successful screenshot using GNOME D-Bus."""
        # Mock other backends to fail
        with patch("tools.image_tools.mss.mss", side_effect=ImportError), \
             patch("tools.image_tools.pyautogui.screenshot", side_effect=ImportError):

            def side_effect_run(cmd, **kwargs):
                if "gdbus" in cmd:
                    # Create screenshot file
                    screenshot_path = Path(cmd[-1])
                    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    img = Image.new("RGB", (100, 100), color="yellow")
                    img.save(screenshot_path)

                    result = MagicMock()
                    result.returncode = 0
                    result.stderr = b""
                    return result
                return MagicMock(returncode=1)

            mock_run.side_effect = side_effect_run

            result = take_screenshot("Test with D-Bus")

            assert "Screenshot captured and saved to:" in result

    @patch("tools.image_tools.subprocess.run")
    def test_take_screenshot_cli_success(self, mock_run, temp_workspace, monkeypatch):
        """Test successful screenshot using CLI tool."""
        monkeypatch.setenv("XDG_SESSION_TYPE", "x11")

        # Mock other backends to fail
        with patch("tools.image_tools.mss.mss", side_effect=ImportError), \
             patch("tools.image_tools.pyautogui.screenshot", side_effect=ImportError), \
             patch("tools.image_tools.shutil.which") as mock_which:

            mock_which.side_effect = lambda cmd: cmd == "scrot"

            def side_effect_run(cmd, **kwargs):
                if cmd[0] == "scrot":
                    # Create screenshot file
                    screenshot_path = Path(cmd[-1])
                    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    img = Image.new("RGB", (100, 100), color="purple")
                    img.save(screenshot_path)

                    result = MagicMock()
                    result.returncode = 0
                    result.stdout = b""
                    result.stderr = b""
                    return result
                elif "gdbus" in cmd:
                    result = MagicMock()
                    result.returncode = 1
                    result.stderr = b"error"
                    return result
                return MagicMock(returncode=1)

            mock_run.side_effect = side_effect_run

            result = take_screenshot("Test with CLI")

            assert "Screenshot captured and saved to:" in result

    def test_take_screenshot_with_custom_path(self, temp_workspace):
        """Test screenshot with custom output path."""
        custom_path = temp_workspace / "custom_screenshot.png"

        with patch("tools.image_tools.mss.mss") as mock_mss:
            mock_sct = MagicMock()

            def side_effect_shot(output):
                img = Image.new("RGB", (100, 100), color="orange")
                img.save(output)

            mock_sct.shot = side_effect_shot
            mock_mss.return_value.__enter__.return_value = mock_sct

            result = take_screenshot("Custom path test", output_path=str(custom_path))

            assert str(custom_path) in result
            assert custom_path.exists()

    def test_take_screenshot_all_backends_fail(self, temp_workspace):
        """Test when all screenshot backends fail."""
        # Mock all backends to fail
        with patch("tools.image_tools.mss.mss", side_effect=ImportError), \
             patch("tools.image_tools.pyautogui.screenshot", side_effect=ImportError), \
             patch("tools.image_tools.subprocess.run") as mock_run, \
             patch("tools.image_tools.shutil.which", return_value=None):

            mock_run.return_value = MagicMock(returncode=1, stderr=b"error")

            result = take_screenshot("Should fail")

            assert "Warning: Screenshot capture failed" in result
            assert "placeholder" in result.lower()

    def test_take_screenshot_black_image_fallback(self, temp_workspace):
        """Test fallback when captured image is all black."""
        with patch("tools.image_tools.mss.mss") as mock_mss:
            mock_sct = MagicMock()

            def side_effect_shot(output):
                # Create black image
                img = Image.new("RGB", (100, 100), color="black")
                img.save(output)

            mock_sct.shot = side_effect_shot
            mock_mss.return_value.__enter__.return_value = mock_sct

            result = take_screenshot("Should detect black")

            assert "placeholder" in result.lower()
            assert "all black" in result.lower()

    def test_take_screenshot_preferred_backend(self, temp_workspace, monkeypatch):
        """Test using preferred backend via environment variable."""
        monkeypatch.setenv("SCREENSHOT_BACKEND", "pyautogui")

        with patch("tools.image_tools.mss.mss") as mock_mss, \
             patch("tools.image_tools.pyautogui.screenshot") as mock_pyautogui:

            mock_img = MagicMock()

            def side_effect_save(path):
                img = Image.new("RGB", (100, 100), color="cyan")
                img.save(path)

            mock_img.save = side_effect_save
            mock_pyautogui.return_value = mock_img

            result = take_screenshot("Preferred backend test")

            # pyautogui should be tried first
            mock_pyautogui.assert_called_once()
            assert "Screenshot captured and saved to:" in result


# ============================================================================
# Test generate_test_image
# ============================================================================

class TestGenerateTestImage:
    """Test generate_test_image function."""

    def test_generate_test_image_default_size(self, temp_workspace):
        """Test generating test image with default size."""
        result = generate_test_image("Test content")

        assert "Generated test image saved to:" in result
        assert "workspace/test_image.png" in result

        # Verify image exists and has correct properties
        img_path = Path.cwd() / "workspace" / "test_image.png"
        assert img_path.exists()

        img = Image.open(img_path)
        assert img.size == (400, 300)
        assert img.mode == "RGB"

    def test_generate_test_image_custom_size(self, temp_workspace):
        """Test generating test image with custom dimensions."""
        result = generate_test_image("Custom size test", width=800, height=600)

        assert "Generated test image saved to:" in result

        img_path = Path.cwd() / "workspace" / "test_image.png"
        img = Image.open(img_path)
        assert img.size == (800, 600)

    def test_generate_test_image_with_long_description(self, temp_workspace):
        """Test generating image with long text description."""
        long_text = "This is a very long description " * 10

        result = generate_test_image(long_text, width=600, height=400)

        assert "Generated test image saved to:" in result
        img_path = Path.cwd() / "workspace" / "test_image.png"
        assert img_path.exists()

    def test_generate_test_image_no_pil(self, temp_workspace):
        """Test error handling when PIL is not available."""
        with patch("tools.image_tools.Image", side_effect=ImportError):
            result = generate_test_image("Test")

            assert "Error: PIL (Pillow) library not installed" in result

    def test_generate_test_image_error(self, temp_workspace):
        """Test error handling during image generation."""
        with patch("tools.image_tools.Image.new") as mock_new:
            mock_new.side_effect = Exception("Image creation error")

            result = generate_test_image("Test")

            assert "Error generating test image" in result


# ============================================================================
# Test get_sample_image
# ============================================================================

class TestGetSampleImage:
    """Test get_sample_image function."""

    def test_get_sample_image_chart(self, temp_workspace):
        """Test generating sample chart image."""
        result = get_sample_image("chart")

        assert "Sample chart image saved to:" in result
        assert "workspace/sample_chart.png" in result

        img_path = Path.cwd() / "workspace" / "sample_chart.png"
        assert img_path.exists()

        img = Image.open(img_path)
        assert img.size == (400, 300)
        assert img.mode == "RGB"

    def test_get_sample_image_diagram(self, temp_workspace):
        """Test generating sample diagram image."""
        result = get_sample_image("diagram")

        assert "Sample diagram image saved to:" in result

        img_path = Path.cwd() / "workspace" / "sample_diagram.png"
        assert img_path.exists()

    def test_get_sample_image_photo(self, temp_workspace):
        """Test generating sample photo image."""
        result = get_sample_image("photo")

        assert "Sample photo image saved to:" in result

        img_path = Path.cwd() / "workspace" / "sample_photo.png"
        assert img_path.exists()

    def test_get_sample_image_default(self, temp_workspace):
        """Test default sample image type."""
        result = get_sample_image()

        # Default is chart
        assert "Sample chart image saved to:" in result

    def test_get_sample_image_invalid_type(self, temp_workspace):
        """Test with unknown image type (should still work)."""
        result = get_sample_image("unknown_type")

        # Should fallback to photo generation
        assert "Sample unknown_type image saved to:" in result

    def test_get_sample_image_no_pil(self, temp_workspace):
        """Test error handling when PIL is not available."""
        with patch("tools.image_tools.Image", side_effect=ImportError):
            result = get_sample_image("chart")

            assert "Error: PIL (Pillow) library not installed" in result

    def test_get_sample_image_error(self, temp_workspace):
        """Test error handling during sample generation."""
        with patch("tools.image_tools.Image.new") as mock_new:
            mock_new.side_effect = Exception("Random generation error")

            result = get_sample_image("chart")

            assert "Error generating sample image" in result


# ============================================================================
# Test Tool Integration
# ============================================================================

class TestToolIntegration:
    """Test FunctionTool wrappers."""

    def test_all_tools_exported(self):
        """Test that all tools are exported correctly."""
        from tools.image_tools import tools

        assert len(tools) == 3

        tool_names = [tool.name for tool in tools]
        expected_names = ["take_screenshot", "generate_test_image", "get_sample_image"]

        for name in expected_names:
            assert name in tool_names

    def test_take_screenshot_tool_callable(self):
        """Test that take_screenshot_tool is callable."""
        assert take_screenshot_tool is not None
        assert hasattr(take_screenshot_tool, 'run')
        assert callable(take_screenshot_tool.run)
        assert take_screenshot_tool.name == "take_screenshot"
        assert len(take_screenshot_tool.description) > 20

    def test_generate_test_image_tool_callable(self):
        """Test that generate_test_image_tool is callable."""
        assert generate_test_image_tool is not None
        assert hasattr(generate_test_image_tool, 'run')
        assert callable(generate_test_image_tool.run)
        assert generate_test_image_tool.name == "generate_test_image"

    def test_get_sample_image_tool_callable(self):
        """Test that get_sample_image_tool is callable."""
        assert get_sample_image_tool is not None
        assert hasattr(get_sample_image_tool, 'run')
        assert callable(get_sample_image_tool.run)
        assert get_sample_image_tool.name == "get_sample_image"


# ============================================================================
# Test Edge Cases and Boundary Conditions
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_take_screenshot_empty_description(self, temp_workspace):
        """Test screenshot with empty description."""
        with patch("tools.image_tools.mss.mss") as mock_mss:
            mock_sct = MagicMock()

            def side_effect_shot(output):
                img = Image.new("RGB", (100, 100), color="red")
                img.save(output)

            mock_sct.shot = side_effect_shot
            mock_mss.return_value.__enter__.return_value = mock_sct

            result = take_screenshot("")

            assert "Screenshot captured and saved to:" in result

    def test_generate_test_image_very_small(self, temp_workspace):
        """Test generating very small image."""
        result = generate_test_image("Small", width=10, height=10)

        assert "Generated test image saved to:" in result

        img_path = Path.cwd() / "workspace" / "test_image.png"
        img = Image.open(img_path)
        assert img.size == (10, 10)

    def test_generate_test_image_very_large(self, temp_workspace):
        """Test generating very large image."""
        result = generate_test_image("Large", width=4000, height=3000)

        assert "Generated test image saved to:" in result

        img_path = Path.cwd() / "workspace" / "test_image.png"
        img = Image.open(img_path)
        assert img.size == (4000, 3000)

    def test_screenshot_directory_creation(self, tmp_path, monkeypatch):
        """Test that screenshot directory is created if it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        with patch("tools.image_tools.mss.mss") as mock_mss:
            mock_sct = MagicMock()

            def side_effect_shot(output):
                Path(output).parent.mkdir(parents=True, exist_ok=True)
                img = Image.new("RGB", (100, 100), color="blue")
                img.save(output)

            mock_sct.shot = side_effect_shot
            mock_mss.return_value.__enter__.return_value = mock_sct

            result = take_screenshot("Test")

            workspace_dir = tmp_path / "workspace" / "screenshots"
            assert workspace_dir.exists()

    def test_image_is_effectively_black_with_tolerance(self, tmp_path):
        """Test black detection with near-black image."""
        # Create almost black image (very dark gray)
        img_path = tmp_path / "dark_gray.png"
        img = Image.new("RGB", (100, 100), color=(3, 3, 3))
        img.save(img_path)

        result = _image_is_effectively_black(img_path, tolerance=5)
        assert result is True

    def test_placeholder_with_special_characters(self, tmp_path):
        """Test placeholder creation with special characters in description."""
        target_path = tmp_path / "test.png"
        description = "Test with <special> & characters"
        reason = "Failure with 'quotes'"

        placeholder_path, message = _create_placeholder_image(
            target_path, description, reason
        )

        assert placeholder_path.exists()
        assert description in message


# ============================================================================
# Test Regression: Black Screenshot Placeholder
# ============================================================================

class TestRegressionBlackScreenshot:
    """Regression test for black screenshot detection (from original test)."""

    def test_take_screenshot_generates_placeholder_when_capture_is_black(
        self, temp_workspace, monkeypatch
    ):
        """If capture succeeds but produces a black frame, a placeholder image is generated."""

        calls = {}

        def fake_select_command(target_path: Path):
            calls["command"] = target_path
            return ["fake_screenshot", str(target_path)]

        def fake_run(cmd, capture_output, timeout, check=False):
            target = Path(cmd[-1])
            target.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (100, 100), color="black").save(target)
            FakeCompleted = type(
                "FakeCompleted", (), {"returncode": 0, "stdout": b"", "stderr": b""}
            )
            return FakeCompleted()

        monkeypatch.setattr("tools.image_tools._select_screenshot_command", fake_select_command)
        monkeypatch.setattr("tools.image_tools.subprocess.run", fake_run)

        # Mock other backends to fail
        with patch("tools.image_tools.mss.mss", side_effect=ImportError), \
             patch("tools.image_tools.pyautogui.screenshot", side_effect=ImportError):

            message = take_screenshot("Describe my desktop")

            assert "placeholder" in message.lower()
            match = re.search(r"Generated placeholder image at: (?P<path>.+\.png)", message)
            assert match, "Placeholder path not found in message"

            placeholder_path = Path(match.group("path"))
            assert placeholder_path.exists()

            # Placeholder should not be all black
            assert not _image_is_effectively_black(placeholder_path)

            # Ensure command selection was attempted
            assert "command" in calls
