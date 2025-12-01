# file_management.py - File management tools with workspace hierarchy awareness

import os
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool
from utils.context import get_current_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
WORKSPACE_DIR = Path("/home/rodrigo/agentic/backend/workspace")
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# Security: Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# --- Initialization Function for Dynamic System Prompt ---

def initialize_filemanager_agent(agent):
    """
    Initialize FileManager agent by scanning workspace and injecting hierarchy into system prompt.
    This function is called automatically when the agent starts.

    Args:
        agent: The agent instance to initialize.

    Returns:
        Success or error message.
    """
    try:
        # Scan workspace directory
        hierarchy = scan_workspace_hierarchy(str(WORKSPACE_DIR))

        # Format hierarchy as readable text
        hierarchy_text = format_hierarchy_for_prompt(hierarchy)

        # Update agent's system message with workspace hierarchy
        if agent and agent._system_messages:
            current_prompt = agent._system_messages[0].content
            updated_prompt = current_prompt.replace(
                "{{WORKSPACE_HIERARCHY}}",
                hierarchy_text
            )
            agent._system_messages[0].content = updated_prompt
            logger.info(f"FileManager initialized with workspace hierarchy ({len(hierarchy['files'])} files, {len(hierarchy['dirs'])} directories)")

        return f"Workspace loaded: {len(hierarchy['files'])} files, {len(hierarchy['dirs'])} directories"

    except Exception as e:
        logger.error(f"Failed to initialize FileManager: {e}")
        return f"Error initializing FileManager: {e}"


def scan_workspace_hierarchy(base_path: str) -> Dict:
    """
    Recursively scan workspace directory and build hierarchy structure.

    Returns:
        Dictionary with files and directories information
    """
    base = Path(base_path)
    hierarchy = {
        "base_path": str(base),
        "files": [],
        "dirs": []
    }

    try:
        for item in base.rglob("*"):
            relative_path = item.relative_to(base)

            if item.is_file():
                # Get file metadata
                stat = item.stat()
                file_info = {
                    "path": str(relative_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "extension": item.suffix,
                    "description": get_file_description(item)
                }
                hierarchy["files"].append(file_info)

            elif item.is_dir():
                # Get directory info
                dir_info = {
                    "path": str(relative_path),
                    "description": get_dir_description(item)
                }
                hierarchy["dirs"].append(dir_info)

    except Exception as e:
        logger.error(f"Error scanning workspace: {e}")

    return hierarchy


def get_file_description(file_path: Path) -> str:
    """Generate brief description of file based on name and extension."""
    ext = file_path.suffix.lower()
    name = file_path.stem

    # Common file type descriptions
    descriptions = {
        ".md": "Markdown document",
        ".txt": "Text file",
        ".py": "Python script",
        ".json": "JSON data file",
        ".csv": "CSV data file",
        ".png": "PNG image",
        ".jpg": "JPEG image",
        ".jpeg": "JPEG image",
        ".pdf": "PDF document",
        ".docx": "Word document",
        ".xlsx": "Excel spreadsheet",
        ".pptx": "PowerPoint presentation",
        ".html": "HTML file",
        ".css": "CSS stylesheet",
        ".js": "JavaScript file",
    }

    base_desc = descriptions.get(ext, "File")

    # Add context from filename
    if "test" in name.lower():
        return f"Test {base_desc.lower()}"
    elif "sample" in name.lower():
        return f"Sample {base_desc.lower()}"
    elif "screenshot" in name.lower():
        return f"Screenshot {base_desc.lower()}"
    elif "research" in name.lower():
        return f"Research {base_desc.lower()}"

    return base_desc


def get_dir_description(dir_path: Path) -> str:
    """Generate brief description of directory based on name."""
    name = dir_path.name.lower()

    descriptions = {
        "screenshots": "Screenshot storage",
        "images": "Image files",
        "data": "Data files",
        "docs": "Documentation",
        "tests": "Test files",
        "temp": "Temporary files",
        "archive": "Archived files",
        "exports": "Exported files",
    }

    return descriptions.get(name, "Directory")


def format_hierarchy_for_prompt(hierarchy: Dict) -> str:
    """
    Format workspace hierarchy as readable text for system prompt.
    """
    lines = [
        "## Current Workspace Structure",
        "",
        f"**Base Path:** `{hierarchy['base_path']}`",
        f"**Total Files:** {len(hierarchy['files'])}",
        f"**Total Directories:** {len(hierarchy['dirs'])}",
        ""
    ]

    # Add directories
    if hierarchy['dirs']:
        lines.append("### Directories:")
        for dir_info in sorted(hierarchy['dirs'], key=lambda x: x['path']):
            lines.append(f"- `{dir_info['path']}/` - {dir_info['description']}")
        lines.append("")

    # Add files (grouped by directory)
    if hierarchy['files']:
        lines.append("### Files:")

        # Group files by directory
        files_by_dir = {}
        for file_info in hierarchy['files']:
            dir_name = str(Path(file_info['path']).parent)
            if dir_name == ".":
                dir_name = "(root)"
            if dir_name not in files_by_dir:
                files_by_dir[dir_name] = []
            files_by_dir[dir_name].append(file_info)

        # Output grouped files
        for dir_name in sorted(files_by_dir.keys()):
            if dir_name != "(root)":
                lines.append(f"\n**{dir_name}/**")
            else:
                lines.append(f"\n**Root directory:**")

            for file_info in sorted(files_by_dir[dir_name], key=lambda x: x['path']):
                size_kb = file_info['size'] / 1024
                size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
                lines.append(f"  - `{Path(file_info['path']).name}` ({size_str}) - {file_info['description']}")

    return "\n".join(lines)


# --- Path Validation ---

def validate_filepath(filepath: str, workspace_dir: Path = WORKSPACE_DIR) -> Path:
    """
    Validate filepath is safe and within workspace directory.

    Args:
        filepath: Path to validate (relative or absolute)
        workspace_dir: Base workspace directory

    Returns:
        Absolute Path object if valid

    Raises:
        ValueError: If path is outside workspace or invalid
    """
    # Convert to Path object
    path = Path(filepath)

    # If relative, make relative to workspace
    if not path.is_absolute():
        path = workspace_dir / path

    # Resolve to absolute path (handles .. and .)
    try:
        abs_path = path.resolve()
        workspace_abs = workspace_dir.resolve()
    except Exception as e:
        raise ValueError(f"Invalid path: {e}")

    # Check if within workspace
    try:
        abs_path.relative_to(workspace_abs)
    except ValueError:
        raise ValueError(f"Path outside workspace not allowed: {filepath}")

    return abs_path


# --- File CRUD Operations ---

class CreateFileInput(BaseModel):
    filepath: str = Field(..., description="Path to file (relative to workspace or absolute)")
    content: str = Field(..., description="Content to write to file")
    overwrite: bool = Field(False, description="If True, overwrite existing file")


def create_file(filepath: str, content: str, overwrite: bool = False) -> str:
    """
    Create a new file with specified content.

    Args:
        filepath: Path to file (relative to workspace or absolute within workspace)
        content: Content to write to file
        overwrite: If True, overwrite existing file (default: False)

    Returns:
        Success message with file path
    """
    try:
        # Validate path
        abs_path = validate_filepath(filepath)

        # Check if file exists
        if abs_path.exists() and not overwrite:
            return f"Error: File already exists: {filepath}. Use overwrite=True to replace."

        # Create parent directories if needed
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        abs_path.write_text(content, encoding='utf-8')

        size_kb = len(content.encode('utf-8')) / 1024
        logger.info(f"Created file: {filepath} ({size_kb:.1f}KB)")

        return f"✓ Created file: {filepath} ({size_kb:.1f}KB)"

    except ValueError as e:
        logger.error(f"Path validation error: {e}")
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Error creating file {filepath}: {e}")
        return f"Error creating file: {e}"


class ReadFileInput(BaseModel):
    filepath: str = Field(..., description="Path to file to read")


def read_file(filepath: str) -> str:
    """
    Read file contents.

    Args:
        filepath: Path to file (relative to workspace or absolute within workspace)

    Returns:
        File contents as string
    """
    try:
        # Validate path
        abs_path = validate_filepath(filepath)

        # Check if file exists
        if not abs_path.exists():
            return f"Error: File not found: {filepath}"

        if not abs_path.is_file():
            return f"Error: Path is not a file: {filepath}"

        # Check file size
        file_size = abs_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return f"Error: File too large ({file_size / 1024 / 1024:.1f}MB). Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"

        # Read file
        content = abs_path.read_text(encoding='utf-8')

        logger.info(f"Read file: {filepath} ({len(content)} characters)")
        return content

    except ValueError as e:
        logger.error(f"Path validation error: {e}")
        return f"Error: {e}"
    except UnicodeDecodeError:
        return f"Error: File is not text (binary file cannot be read as text): {filepath}"
    except Exception as e:
        logger.error(f"Error reading file {filepath}: {e}")
        return f"Error reading file: {e}"


class UpdateFileInput(BaseModel):
    filepath: str = Field(..., description="Path to file to update")
    content: str = Field(..., description="New content for file")


def update_file(filepath: str, content: str) -> str:
    """
    Update existing file with new content.

    Args:
        filepath: Path to file (relative to workspace or absolute within workspace)
        content: New content for file

    Returns:
        Success message
    """
    try:
        # Validate path
        abs_path = validate_filepath(filepath)

        # Check if file exists
        if not abs_path.exists():
            return f"Error: File not found: {filepath}. Use create_file to create new file."

        if not abs_path.is_file():
            return f"Error: Path is not a file: {filepath}"

        # Write new content
        abs_path.write_text(content, encoding='utf-8')

        size_kb = len(content.encode('utf-8')) / 1024
        logger.info(f"Updated file: {filepath} ({size_kb:.1f}KB)")

        return f"✓ Updated file: {filepath} ({size_kb:.1f}KB)"

    except ValueError as e:
        logger.error(f"Path validation error: {e}")
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Error updating file {filepath}: {e}")
        return f"Error updating file: {e}"


class DeleteFileInput(BaseModel):
    filepath: str = Field(..., description="Path to file to delete")
    confirm: bool = Field(..., description="Must be True to actually delete file (safety check)")


def delete_file(filepath: str, confirm: bool = False) -> str:
    """
    Delete a file with confirmation.

    Args:
        filepath: Path to file (relative to workspace or absolute within workspace)
        confirm: Must be True to actually delete (safety check)

    Returns:
        Success message or error
    """
    try:
        # Validate path
        abs_path = validate_filepath(filepath)

        # Check if file exists
        if not abs_path.exists():
            return f"Error: File not found: {filepath}"

        if not abs_path.is_file():
            return f"Error: Path is not a file: {filepath}"

        # Safety check
        if not confirm:
            return f"Error: Must set confirm=True to delete file: {filepath}"

        # Delete file
        abs_path.unlink()

        logger.info(f"Deleted file: {filepath}")
        return f"✓ Deleted file: {filepath}"

    except ValueError as e:
        logger.error(f"Path validation error: {e}")
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Error deleting file {filepath}: {e}")
        return f"Error deleting file: {e}"


class ListFilesInput(BaseModel):
    directory: str = Field(".", description="Directory to list (relative to workspace, default: root)")
    pattern: str = Field("*", description="Glob pattern to filter files (e.g., '*.py', '*.json')")


def list_files(directory: str = ".", pattern: str = "*") -> str:
    """
    List files in directory with optional pattern matching.

    Args:
        directory: Directory to list (relative to workspace, default: root)
        pattern: Glob pattern (e.g., "*.py", "*.json", default: "*")

    Returns:
        Formatted list of files with metadata
    """
    try:
        # Validate path
        abs_path = validate_filepath(directory)

        # Check if directory exists
        if not abs_path.exists():
            return f"Error: Directory not found: {directory}"

        if not abs_path.is_dir():
            return f"Error: Path is not a directory: {directory}"

        # List files matching pattern
        files = sorted(abs_path.glob(pattern))

        if not files:
            return f"No files found matching pattern '{pattern}' in {directory}"

        # Format output
        lines = [f"Files in {directory} (pattern: {pattern}):", ""]

        for file_path in files:
            if file_path.is_file():
                stat = file_path.stat()
                size_kb = stat.st_size / 1024
                size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                lines.append(f"  {file_path.name}")
                lines.append(f"    Size: {size_str} | Modified: {modified}")
            elif file_path.is_dir():
                lines.append(f"  {file_path.name}/ (directory)")

        logger.info(f"Listed {len(files)} items in {directory}")
        return "\n".join(lines)

    except ValueError as e:
        logger.error(f"Path validation error: {e}")
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Error listing directory {directory}: {e}")
        return f"Error listing directory: {e}"


class MoveFileInput(BaseModel):
    source: str = Field(..., description="Source file path")
    destination: str = Field(..., description="Destination file path")


def move_file(source: str, destination: str) -> str:
    """
    Move or rename a file.

    Args:
        source: Current file path
        destination: New file path

    Returns:
        Success message
    """
    try:
        # Validate paths
        abs_source = validate_filepath(source)
        abs_dest = validate_filepath(destination)

        # Check source exists
        if not abs_source.exists():
            return f"Error: Source file not found: {source}"

        if not abs_source.is_file():
            return f"Error: Source is not a file: {source}"

        # Check destination doesn't exist
        if abs_dest.exists():
            return f"Error: Destination already exists: {destination}"

        # Create destination parent directories
        abs_dest.parent.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(abs_source), str(abs_dest))

        logger.info(f"Moved file: {source} → {destination}")
        return f"✓ Moved file: {source} → {destination}"

    except ValueError as e:
        logger.error(f"Path validation error: {e}")
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Error moving file {source}: {e}")
        return f"Error moving file: {e}"


class CopyFileInput(BaseModel):
    source: str = Field(..., description="Source file path")
    destination: str = Field(..., description="Destination file path")


def copy_file(source: str, destination: str) -> str:
    """
    Copy a file to new location.

    Args:
        source: Source file path
        destination: Destination file path

    Returns:
        Success message
    """
    try:
        # Validate paths
        abs_source = validate_filepath(source)
        abs_dest = validate_filepath(destination)

        # Check source exists
        if not abs_source.exists():
            return f"Error: Source file not found: {source}"

        if not abs_source.is_file():
            return f"Error: Source is not a file: {source}"

        # Check destination doesn't exist
        if abs_dest.exists():
            return f"Error: Destination already exists: {destination}"

        # Create destination parent directories
        abs_dest.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(str(abs_source), str(abs_dest))

        size_kb = abs_dest.stat().st_size / 1024
        logger.info(f"Copied file: {source} → {destination} ({size_kb:.1f}KB)")
        return f"✓ Copied file: {source} → {destination} ({size_kb:.1f}KB)"

    except ValueError as e:
        logger.error(f"Path validation error: {e}")
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Error copying file {source}: {e}")
        return f"Error copying file: {e}"


# --- Tool Registration ---

create_file_tool = FunctionTool(
    func=create_file,
    name="create_file",
    description="Create a new file with specified content. Use overwrite=True to replace existing file."
)

read_file_tool = FunctionTool(
    func=read_file,
    name="read_file",
    description="Read the contents of a file. Returns the full text content."
)

update_file_tool = FunctionTool(
    func=update_file,
    name="update_file",
    description="Update an existing file with new content. Use this to modify files."
)

delete_file_tool = FunctionTool(
    func=delete_file,
    name="delete_file",
    description="Delete a file. Requires confirm=True for safety. Use with caution."
)

list_files_tool = FunctionTool(
    func=list_files,
    name="list_files",
    description="List files in a directory with optional glob pattern filtering (e.g., '*.py', '*.json')."
)

move_file_tool = FunctionTool(
    func=move_file,
    name="move_file",
    description="Move or rename a file. Creates parent directories as needed."
)

copy_file_tool = FunctionTool(
    func=copy_file,
    name="copy_file",
    description="Copy a file to a new location. Creates parent directories as needed."
)

# Export tools
tools = [
    create_file_tool,
    read_file_tool,
    update_file_tool,
    delete_file_tool,
    list_files_tool,
    move_file_tool,
    copy_file_tool,
]
