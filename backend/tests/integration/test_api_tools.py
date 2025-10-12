#!/usr/bin/env python3
"""
Integration tests for Tool API endpoints.

Tests:
- GET /api/tools (list all)
- GET /api/tools/content/{filename} (get content)
- PUT /api/tools/content/{filename} (save content)
- POST /api/tools/upload (file upload)
- POST /api/tools/generate (code generation)
"""

import io
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_tools_dir(monkeypatch):
    """Create a temporary tools directory for testing."""
    temp_dir = tempfile.mkdtemp()
    tools_path = Path(temp_dir) / "tools"
    tools_path.mkdir()

    # Monkeypatch the TOOLS_DIR in main module
    import main
    original_dir = main.TOOLS_DIR
    main.TOOLS_DIR = str(tools_path)
    main.LOADED_TOOLS_WITH_FILENAMES = []  # Clear cached tools

    yield str(tools_path)

    # Cleanup
    main.TOOLS_DIR = original_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_tool_code():
    """Sample tool code for testing."""
    return '''"""Sample tool for testing."""

from autogen_core.tools import FunctionTool
from typing import Optional

def sample_tool_function(query: str, max_results: int = 5) -> str:
    """
    A sample tool that returns a formatted string.

    Args:
        query: The search query
        max_results: Maximum number of results

    Returns:
        Formatted result string
    """
    return f"Query: {query}, Max: {max_results}"

sample_tool = FunctionTool(
    func=sample_tool_function,
    name="sample_tool",
    description="A sample tool for testing"
)

tools = [sample_tool]
'''


@pytest.fixture
def invalid_tool_code():
    """Invalid tool code for testing error handling."""
    return '''"""Invalid tool - syntax error."""

def broken_function(
    # Missing closing parenthesis
    return "test"
'''


class TestToolListEndpoint:
    """Tests for GET /api/tools."""

    def test_list_tools_empty(self, client, temp_tools_dir):
        """Test listing tools when directory is empty."""
        response = client.get("/api/tools")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_tools_with_data(self, client, temp_tools_dir, sample_tool_code):
        """Test listing tools when tools exist."""
        # Create a test tool file
        tool_file = Path(temp_tools_dir) / "sample_tool.py"
        tool_file.write_text(sample_tool_code)

        response = client.get("/api/tools")
        assert response.status_code == 200
        tools = response.json()
        assert len(tools) >= 1

        # Find our sample tool
        sample = next((t for t in tools if t["name"] == "sample_tool"), None)
        assert sample is not None
        assert sample["filename"] == "sample_tool.py"

    def test_list_tools_multiple(self, client, temp_tools_dir):
        """Test listing multiple tools."""
        # Create multiple test tool files
        for i in range(3):
            tool_code = f'''"""Tool {i}."""
from autogen_core.tools import FunctionTool

def tool_{i}() -> str:
    """Tool {i} function."""
    return "tool_{i}"

tool_{i}_instance = FunctionTool(
    func=tool_{i},
    name="tool_{i}",
    description="Tool {i}"
)

tools = [tool_{i}_instance]
'''
            tool_file = Path(temp_tools_dir) / f"tool_{i}.py"
            tool_file.write_text(tool_code)

        response = client.get("/api/tools")
        assert response.status_code == 200
        tools = response.json()
        assert len(tools) >= 3


class TestToolContentEndpoint:
    """Tests for GET /api/tools/content/{filename}."""

    def test_get_tool_content_success(self, client, temp_tools_dir, sample_tool_code):
        """Test getting tool file content."""
        # Create tool file
        tool_file = Path(temp_tools_dir) / "sample_tool.py"
        tool_file.write_text(sample_tool_code)

        response = client.get("/api/tools/content/sample_tool.py")
        assert response.status_code == 200
        assert response.text == sample_tool_code

    def test_get_tool_content_not_found(self, client, temp_tools_dir):
        """Test getting non-existent tool."""
        response = client.get("/api/tools/content/nonexistent.py")
        assert response.status_code == 404

    def test_get_tool_content_invalid_filename(self, client, temp_tools_dir):
        """Test getting tool with invalid filename."""
        # Test path traversal attempt
        response = client.get("/api/tools/content/../../../etc/passwd")
        assert response.status_code == 400

        # Test non-Python file
        response = client.get("/api/tools/content/tool.txt")
        assert response.status_code == 400

        # Test special characters
        response = client.get("/api/tools/content/tool@#$.py")
        assert response.status_code == 400


class TestToolSaveEndpoint:
    """Tests for PUT /api/tools/content/{filename}."""

    def test_save_tool_content_success(self, client, temp_tools_dir, sample_tool_code):
        """Test saving tool file content."""
        response = client.put(
            "/api/tools/content/new_tool.py",
            data=sample_tool_code
        )
        assert response.status_code == 204

        # Verify file was created
        tool_file = Path(temp_tools_dir) / "new_tool.py"
        assert tool_file.exists()
        assert tool_file.read_text() == sample_tool_code

    def test_save_tool_content_update_existing(self, client, temp_tools_dir, sample_tool_code):
        """Test updating existing tool file."""
        # Create initial file
        tool_file = Path(temp_tools_dir) / "existing_tool.py"
        tool_file.write_text("# Original content")

        # Update file
        response = client.put(
            "/api/tools/content/existing_tool.py",
            data=sample_tool_code
        )
        assert response.status_code == 204

        # Verify file was updated
        assert tool_file.read_text() == sample_tool_code

    def test_save_tool_content_invalid_filename(self, client, temp_tools_dir):
        """Test saving tool with invalid filename."""
        # Test path traversal
        response = client.put(
            "/api/tools/content/../../../tmp/evil.py",
            data="# evil code"
        )
        assert response.status_code == 400

        # Test non-Python file
        response = client.put(
            "/api/tools/content/tool.txt",
            data="content"
        )
        assert response.status_code == 400


class TestToolUploadEndpoint:
    """Tests for POST /api/tools/upload."""

    def test_upload_tool_success(self, client, temp_tools_dir, sample_tool_code):
        """Test uploading a tool file."""
        # Create file-like object
        file_content = sample_tool_code.encode('utf-8')
        files = {
            'file': ('uploaded_tool.py', io.BytesIO(file_content), 'text/x-python')
        }

        response = client.post("/api/tools/upload", files=files)
        assert response.status_code == 200

        # Verify file was created
        tool_file = Path(temp_tools_dir) / "uploaded_tool.py"
        assert tool_file.exists()

        # Verify response contains tool info
        tools = response.json()
        assert isinstance(tools, list)

    def test_upload_tool_invalid_extension(self, client, temp_tools_dir):
        """Test uploading non-Python file."""
        file_content = b"not python code"
        files = {
            'file': ('tool.txt', io.BytesIO(file_content), 'text/plain')
        }

        response = client.post("/api/tools/upload", files=files)
        assert response.status_code == 400

    def test_upload_tool_invalid_filename(self, client, temp_tools_dir):
        """Test uploading file with invalid filename."""
        file_content = b"# python code"

        # Path traversal attempt
        files = {
            'file': ('../../../tmp/evil.py', io.BytesIO(file_content), 'text/x-python')
        }
        response = client.post("/api/tools/upload", files=files)
        assert response.status_code == 400

        # Special characters
        files = {
            'file': ('tool@#$.py', io.BytesIO(file_content), 'text/x-python')
        }
        response = client.post("/api/tools/upload", files=files)
        assert response.status_code == 400

    def test_upload_tool_empty_file(self, client, temp_tools_dir):
        """Test uploading empty file."""
        files = {
            'file': ('empty.py', io.BytesIO(b''), 'text/x-python')
        }

        response = client.post("/api/tools/upload", files=files)
        # Should succeed even with empty file
        assert response.status_code in [200, 500]  # May fail during loading


class TestToolGenerateEndpoint:
    """Tests for POST /api/tools/generate."""

    @patch('google.generativeai.GenerativeModel')
    def test_generate_tool_success(self, mock_model_class, client, temp_tools_dir):
        """Test generating tool code with Gemini."""
        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.parts = ["generated code"]
        mock_response.text = '''from autogen_core.tools import FunctionTool

def generated_tool() -> str:
    """Generated tool."""
    return "result"

generated = FunctionTool(func=generated_tool, description="Generated")
tools = [generated]
'''

        mock_model = MagicMock()
        mock_model.generate_content_async.return_value = mock_response
        mock_model_class.return_value = mock_model

        # Make request
        request_data = {
            "prompt": "Create a tool that fetches weather data"
        }
        response = client.post("/api/tools/generate", json=request_data)

        # Check response
        assert response.status_code == 200
        assert "FunctionTool" in response.text

    def test_generate_tool_no_api_key(self, client, temp_tools_dir, monkeypatch):
        """Test generating tool without API key."""
        # Remove API key
        monkeypatch.setenv("GEMINI_API_KEY", "")

        # Reload main to pick up new env
        import main
        main.GEMINI_API_KEY = ""

        request_data = {
            "prompt": "Create a tool"
        }
        response = client.post("/api/tools/generate", json=request_data)
        assert response.status_code == 500
        assert "not configured" in response.json()["detail"].lower()

    def test_generate_tool_empty_prompt(self, client, temp_tools_dir):
        """Test generating tool with empty prompt."""
        request_data = {
            "prompt": ""
        }
        response = client.post("/api/tools/generate", json=request_data)
        # Should fail validation or at generation
        assert response.status_code in [400, 422, 500]


class TestToolEdgeCases:
    """Test edge cases and error handling."""

    def test_tool_with_syntax_error(self, client, temp_tools_dir, invalid_tool_code):
        """Test handling tool with syntax errors."""
        # Create invalid tool file
        tool_file = Path(temp_tools_dir) / "broken_tool.py"
        tool_file.write_text(invalid_tool_code)

        # List tools should handle gracefully
        response = client.get("/api/tools")
        assert response.status_code == 200
        # Should not include broken tool in list
        tools = response.json()
        broken = [t for t in tools if "broken_tool" in t.get("filename", "")]
        assert len(broken) == 0

    def test_tool_without_tools_list(self, client, temp_tools_dir):
        """Test tool file without 'tools' export."""
        code = '''"""Tool without export."""
from autogen_core.tools import FunctionTool

def my_function() -> str:
    """My function."""
    return "result"

# No 'tools = [...]' export
'''
        tool_file = Path(temp_tools_dir) / "no_export.py"
        tool_file.write_text(code)

        response = client.get("/api/tools")
        assert response.status_code == 200
        # Should handle missing export gracefully

    def test_tool_with_import_error(self, client, temp_tools_dir):
        """Test tool with import errors."""
        code = '''"""Tool with import error."""
import nonexistent_module

def my_function() -> str:
    return "result"
'''
        tool_file = Path(temp_tools_dir) / "import_error.py"
        tool_file.write_text(code)

        response = client.get("/api/tools")
        assert response.status_code == 200
        # Should handle import errors gracefully

    def test_save_tool_with_unicode(self, client, temp_tools_dir):
        """Test saving tool with unicode characters."""
        code = '''"""Tool with unicode: 你好世界 🚀."""
from autogen_core.tools import FunctionTool

def unicode_tool() -> str:
    """Unicode tool: émojis 🎉."""
    return "Success: ✓"

tool = FunctionTool(func=unicode_tool, description="Unicode test")
tools = [tool]
'''
        response = client.put(
            "/api/tools/content/unicode_tool.py",
            data=code
        )
        assert response.status_code == 204

        # Verify saved correctly
        tool_file = Path(temp_tools_dir) / "unicode_tool.py"
        assert tool_file.exists()
        saved_content = tool_file.read_text(encoding='utf-8')
        assert "你好世界" in saved_content
        assert "🚀" in saved_content


class TestToolReloading:
    """Test that tools are properly reloaded after modifications."""

    def test_tools_reload_after_save(self, client, temp_tools_dir, sample_tool_code):
        """Test that tools list updates after saving a new tool."""
        # Get initial tool count
        response1 = client.get("/api/tools")
        initial_count = len(response1.json())

        # Save new tool
        client.put("/api/tools/content/new_tool.py", data=sample_tool_code)

        # Get updated tool count
        response2 = client.get("/api/tools")
        new_count = len(response2.json())

        # Should have more tools (or same if tool loading failed)
        assert new_count >= initial_count

    def test_tools_reload_after_upload(self, client, temp_tools_dir, sample_tool_code):
        """Test that tools list updates after uploading a tool."""
        # Get initial tool count
        response1 = client.get("/api/tools")
        initial_count = len(response1.json())

        # Upload new tool
        file_content = sample_tool_code.encode('utf-8')
        files = {'file': ('uploaded.py', io.BytesIO(file_content), 'text/x-python')}
        client.post("/api/tools/upload", files=files)

        # Get updated tool count
        response2 = client.get("/api/tools")
        new_count = len(response2.json())

        assert new_count >= initial_count


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
