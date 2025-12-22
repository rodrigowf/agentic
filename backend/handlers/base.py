"""
Base classes and utilities for output handlers.

Output handlers process the raw text output from a custom_loop agent,
perform actions (save files, run code, etc.), and return feedback
to be sent back to the model.
"""

import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OutputHandlerResult:
    """
    Result returned by an output handler after processing model output.

    Attributes:
        should_continue: If False, the agent loop terminates (e.g., "DONE" detected)
        feedback_text: Text feedback to send back to the model
        feedback_images: List of image paths to send as multimodal input
        saved_file: Path to any file saved by the handler
        metadata: Additional data for logging/debugging
    """
    should_continue: bool = True
    feedback_text: Optional[str] = None
    feedback_images: List[str] = field(default_factory=list)
    saved_file: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def load_handler(handler_path: str) -> Callable:
    """
    Dynamically load an output handler function from a module path.

    Args:
        handler_path: String in format 'module.function_name'
                      (e.g., 'html_display.process_output')
                      The module should be in the handlers/ directory.

    Returns:
        The handler function

    Raises:
        ValueError: If the handler path format is invalid
        ImportError: If the module cannot be imported
        AttributeError: If the function doesn't exist in the module
    """
    if not handler_path:
        raise ValueError("Handler path cannot be empty")

    parts = handler_path.split('.')
    if len(parts) < 2:
        raise ValueError(
            f"Invalid handler path format: '{handler_path}'. "
            f"Expected format: 'module.function_name' (e.g., 'html_display.process_output')"
        )

    module_name = parts[0]
    function_name = '.'.join(parts[1:])

    try:
        module = importlib.import_module(f'handlers.{module_name}')
        logger.debug(f"Successfully imported handler module: handlers.{module_name}")
    except ImportError as e:
        raise ImportError(
            f"Failed to import handler module 'handlers.{module_name}'. "
            f"Make sure the module exists in the handlers/ directory. Error: {e}"
        )

    try:
        handler_func = getattr(module, function_name)
        logger.debug(f"Successfully found handler function: {function_name}")
    except AttributeError:
        available = [name for name in dir(module) if not name.startswith('_')]
        raise AttributeError(
            f"Function '{function_name}' not found in module 'handlers.{module_name}'. "
            f"Available functions: {available}"
        )

    return handler_func


def get_incremental_filename(output_dir: Path, prefix: str = "output", extension: str = ".html") -> Path:
    """
    Generate an incremental filename in the output directory.

    Args:
        output_dir: Directory to save files in
        prefix: Filename prefix (e.g., "html" -> "html_001.html")
        extension: File extension including dot

    Returns:
        Path to the new file (e.g., output_dir/html_001.html)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find existing files and get the next number
    existing = list(output_dir.glob(f"{prefix}_*{extension}"))

    max_num = 0
    for f in existing:
        try:
            # Extract number from filename like "html_001.html"
            num_str = f.stem.split('_')[-1]
            num = int(num_str)
            max_num = max(max_num, num)
        except (ValueError, IndexError):
            continue

    next_num = max_num + 1
    filename = f"{prefix}_{next_num:03d}{extension}"

    return output_dir / filename
