"""
HTML Display output handler for custom_loop agents.

This handler:
1. Detects if output is HTML or "DONE" signal
2. Saves HTML to incremental files (html_001.html, html_002.html, ...)
3. Takes screenshot using Puppeteer
4. Captures console logs
5. Returns screenshot + logs as feedback to the model
"""

import logging
import shutil
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, Any

from .base import OutputHandlerResult, get_incremental_filename

logger = logging.getLogger(__name__)

# Default output directory for HTML files
DEFAULT_OUTPUT_DIR = Path("data/workspace/html_outputs")

# Path to the Puppeteer capture script
PUPPETEER_SCRIPT = Path(__file__).parent / "puppeteer_capture.js"

# Node.js executable path - try nvm path first, then fall back to bare "node"
NODE_EXECUTABLE = Path.home() / ".nvm/versions/node/v22.21.1/bin/node"
if not NODE_EXECUTABLE.exists():
    # Fall back to system node if nvm not available
    NODE_EXECUTABLE = shutil.which("node") or "node"
else:
    NODE_EXECUTABLE = str(NODE_EXECUTABLE)

# Default termination signal (can be overridden in config)
DEFAULT_TERMINATE_SIGNAL = "TERMINATE"


def extract_html(output: str, terminate_signal: str = DEFAULT_TERMINATE_SIGNAL) -> str | None:
    """
    Extract HTML content from model output.

    The model might output:
    - Pure HTML starting with <!DOCTYPE or <html>
    - HTML wrapped in markdown code blocks
    - Mixed text with HTML

    Args:
        output: Raw model output
        terminate_signal: Signal that indicates termination (default: TERMINATE)

    Returns:
        Extracted HTML string, or None if no HTML found
    """
    output = output.strip()

    # Check for termination signal first
    if output.upper() == terminate_signal.upper():
        return None

    # Try to extract from markdown code blocks
    # Pattern: ```html ... ``` or ``` ... ```
    code_block_pattern = r'```(?:html)?\s*\n?([\s\S]*?)\n?```'
    matches = re.findall(code_block_pattern, output, re.IGNORECASE)

    if matches:
        # Return the largest code block (most likely the full HTML)
        html = max(matches, key=len).strip()
        if html.startswith('<'):
            return html

    # Check if output starts with HTML-like content
    if output.startswith('<!DOCTYPE') or output.startswith('<html') or output.startswith('<'):
        return output

    # Check if there's HTML anywhere in the output
    html_pattern = r'(<!DOCTYPE[\s\S]*</html>|<html[\s\S]*</html>)'
    match = re.search(html_pattern, output, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def run_puppeteer_capture(html_path: Path, screenshot_path: Path) -> Dict[str, Any]:
    """
    Run the Puppeteer script to capture screenshot and console logs.

    Args:
        html_path: Path to the HTML file to capture
        screenshot_path: Path where screenshot should be saved

    Returns:
        Dict with 'success', 'console_logs', and 'error' keys
    """
    if not PUPPETEER_SCRIPT.exists():
        logger.error(f"Puppeteer script not found: {PUPPETEER_SCRIPT}")
        return {
            "success": False,
            "console_logs": "",
            "error": f"Puppeteer script not found: {PUPPETEER_SCRIPT}"
        }

    try:
        # Run the Node.js script
        logger.info(f"[html_display] Running puppeteer with node: {NODE_EXECUTABLE}")
        result = subprocess.run(
            [
                NODE_EXECUTABLE,
                str(PUPPETEER_SCRIPT),
                str(html_path.absolute()),
                str(screenshot_path.absolute())
            ],
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout
            cwd=str(PUPPETEER_SCRIPT.parent)
        )

        if result.returncode == 0:
            # Parse JSON output from the script
            try:
                output_data = json.loads(result.stdout)
                return {
                    "success": True,
                    "console_logs": output_data.get("console_logs", ""),
                    "error": None
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "console_logs": result.stdout,
                    "error": None
                }
        else:
            logger.error(f"Puppeteer script failed: {result.stderr}")
            return {
                "success": False,
                "console_logs": "",
                "error": result.stderr
            }

    except subprocess.TimeoutExpired:
        logger.error("Puppeteer script timed out")
        return {
            "success": False,
            "console_logs": "",
            "error": "Screenshot capture timed out after 30 seconds"
        }
    except Exception as e:
        logger.error(f"Failed to run Puppeteer: {e}")
        return {
            "success": False,
            "console_logs": "",
            "error": str(e)
        }


def process_output(
    output: str,
    iteration: int,
    config: Dict[str, Any],
    context: Dict[str, Any]
) -> OutputHandlerResult:
    """
    Process model output for HTML display.

    This is the main handler function called by custom_loop agent.

    Args:
        output: Raw text output from the model
        iteration: Current iteration number (1-based)
        config: Handler configuration from agent JSON (supports 'terminate_signal' key)
        context: Runtime context (agent_name, output_dir, etc.)

    Returns:
        OutputHandlerResult with feedback for the model
    """
    output_stripped = output.strip()
    logger.info(f"[html_display] Processing output at iteration {iteration}, length: {len(output_stripped)}")
    logger.debug(f"[html_display] Output preview: {output_stripped[:200]}...")

    # Get termination signal from config (default: TERMINATE)
    terminate_signal = config.get("terminate_signal", DEFAULT_TERMINATE_SIGNAL)

    # Check for termination signal
    if output_stripped.upper() == terminate_signal.upper() or output_stripped.upper().endswith(terminate_signal.upper()):
        logger.info(f"[html_display] Received {terminate_signal} signal at iteration {iteration}")
        return OutputHandlerResult(
            should_continue=False,
            feedback_text="HTML generation complete.",
            metadata={"terminated_by": f"{terminate_signal}_signal"}
        )

    # Extract HTML from output
    html_content = extract_html(output, terminate_signal)
    logger.info(f"[html_display] Extracted HTML: {html_content is not None}, length: {len(html_content) if html_content else 0}")

    if not html_content:
        logger.warning(f"[html_display] No HTML found in output at iteration {iteration}")
        return OutputHandlerResult(
            should_continue=True,
            feedback_text=(
                "I couldn't find valid HTML in your output. "
                "Please output the complete HTML document starting with <!DOCTYPE html> "
                f"or output {terminate_signal} if you're finished."
            ),
            metadata={"error": "no_html_found"}
        )

    # Get output directory from config or use default
    output_dir = Path(config.get("output_dir", DEFAULT_OUTPUT_DIR))
    logger.info(f"[html_display] Output directory: {output_dir.absolute()}")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"[html_display] Failed to create output directory: {e}")
        return OutputHandlerResult(
            should_continue=False,
            feedback_text=f"Failed to create output directory: {e}",
            metadata={"error": str(e)}
        )

    # Save HTML with incremental filename
    try:
        html_path = get_incremental_filename(output_dir, prefix="html", extension=".html")
        logger.info(f"[html_display] Writing HTML to: {html_path.absolute()}")
        html_path.write_text(html_content, encoding="utf-8")
        logger.info(f"[html_display] Successfully saved HTML to: {html_path}")
    except Exception as e:
        logger.error(f"[html_display] Failed to save HTML: {e}")
        return OutputHandlerResult(
            should_continue=False,
            feedback_text=f"Failed to save HTML file: {e}",
            metadata={"error": str(e)}
        )

    # Generate screenshot path
    screenshot_path = html_path.with_suffix(".png")

    # Run Puppeteer to capture screenshot and console logs
    capture_result = run_puppeteer_capture(html_path, screenshot_path)

    # Build feedback message
    feedback_parts = []

    if capture_result["success"]:
        feedback_parts.append(f"HTML saved to: {html_path.name}")
        feedback_parts.append(f"Screenshot captured: {screenshot_path.name}")

        if capture_result["console_logs"]:
            feedback_parts.append(f"\nConsole output:\n{capture_result['console_logs']}")
        else:
            feedback_parts.append("\nConsole output: (no output)")

        feedback_parts.append(
            f"\nReview the screenshot above. If the HTML looks correct, output {terminate_signal}. "
            "Otherwise, output the corrected full HTML."
        )
    else:
        feedback_parts.append(f"HTML saved to: {html_path.name}")
        feedback_parts.append(f"Screenshot capture failed: {capture_result['error']}")
        feedback_parts.append(
            "\nI couldn't capture a screenshot, but the HTML was saved. "
            f"If you believe it's correct, output {terminate_signal}. Otherwise, output corrected HTML."
        )

    feedback_text = "\n".join(feedback_parts)

    # Collect images for multimodal feedback
    feedback_images = []
    if capture_result["success"] and screenshot_path.exists():
        feedback_images.append(str(screenshot_path.absolute()))

    return OutputHandlerResult(
        should_continue=True,
        feedback_text=feedback_text,
        feedback_images=feedback_images,
        saved_file=str(html_path),
        metadata={
            "iteration": iteration,
            "html_file": str(html_path),
            "screenshot_file": str(screenshot_path) if screenshot_path.exists() else None,
            "console_logs": capture_result.get("console_logs", ""),
            "capture_success": capture_result["success"]
        }
    )
