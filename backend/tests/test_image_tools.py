import re
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tools import image_tools


@pytest.fixture(autouse=True)
def _ensure_tmp_workspace(tmp_path, monkeypatch):
    """Run tests inside a temporary workspace directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace" / "screenshots").mkdir(parents=True, exist_ok=True)


def test_take_screenshot_generates_placeholder_when_capture_is_black(monkeypatch):
    """If capture succeeds but produces a black frame, a placeholder image is generated."""

    calls = {}

    def fake_select_command(target_path: Path):
        calls["command"] = target_path
        return ["fake_screenshot", str(target_path)]

    def fake_run(cmd, capture_output, timeout, check=False):  # pragma: no cover - executed in test
        from PIL import Image

        target = Path(cmd[-1])
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (100, 100), color="black").save(target)
        FakeCompleted = type("FakeCompleted", (), {"returncode": 0, "stdout": b"", "stderr": b""})
        return FakeCompleted()

    monkeypatch.setattr(image_tools, "_select_screenshot_command", fake_select_command)
    monkeypatch.setattr(image_tools.subprocess, "run", fake_run)

    message = image_tools.take_screenshot("Describe my desktop")

    assert "placeholder" in message.lower()
    match = re.search(r"Generated placeholder image at: (?P<path>.+\.png)", message)
    assert match, "Placeholder path not found in message"

    placeholder_path = Path(match.group("path"))
    assert placeholder_path.exists()

    # Placeholder should not be all black
    assert not image_tools._image_is_effectively_black(placeholder_path)

    # Ensure command selection was attempted
    assert "command" in calls
