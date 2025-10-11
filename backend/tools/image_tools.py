"""Image-related tools for testing multimodal agent capabilities."""

import logging
import os
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from pydantic import BaseModel, Field

from autogen_core.tools import FunctionTool

logger = logging.getLogger(__name__)


class TakeScreenshotInput(BaseModel):
    """Input schema for take_screenshot tool."""

    description: str = Field(..., description="Description of what to capture in the screenshot")
    output_path: Optional[str] = Field(None, description="Optional path to save screenshot")


def _select_screenshot_command(target_path: Path) -> Optional[list[str]]:
    """Pick an available CLI screenshot tool for the current session."""

    session_type = (os.environ.get("XDG_SESSION_TYPE") or "").lower()
    wayland_display = os.environ.get("WAYLAND_DISPLAY")
    commands: list[list[str]] = []

    # Prefer Wayland-native tools when Wayland session is detected
    if session_type == "wayland" or wayland_display:
        if shutil.which("grim"):
            commands.append(["grim", str(target_path)])
        if shutil.which("hyprshot"):
            commands.append(["hyprshot", "--silent", "--filename", str(target_path)])
        if shutil.which("spectacle"):
            commands.append(["spectacle", "-b", "-n", "-o", str(target_path)])
        if shutil.which("flameshot"):
            commands.append(["flameshot", "full", "--path", str(target_path)])

    # X11 fallback
    if shutil.which("scrot"):
        commands.append(["scrot", str(target_path)])
    if shutil.which("maim"):
        commands.append(["maim", str(target_path)])
    if shutil.which("import"):  # ImageMagick
        commands.append(["import", "-window", "root", str(target_path)])

    # macOS fallback
    if sys.platform == "darwin" and shutil.which("screencapture"):
        commands.append(["screencapture", "-x", str(target_path)])

    return commands[0] if commands else None


def _image_is_effectively_black(image_path: Path, tolerance: int = 5) -> bool:
    """Return True if the image contains only near-black pixels."""

    try:
        from PIL import Image, ImageStat
    except ImportError:
        logger.debug("PIL not available; cannot verify screenshot contents.")
        return False

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            extrema = img.getextrema()
            # getextrema returns ((min_r, max_r), ...)
            is_constant = all((channel_min == channel_max) for channel_min, channel_max in extrema)
            if is_constant:
                return all(channel_max <= tolerance for _, channel_max in extrema)

            stats = ImageStat.Stat(img)
            # If total luminance is extremely low, treat as black
            avg_luminance = sum(stats.mean) / len(stats.mean)
            return avg_luminance <= tolerance
    except Exception as exc:  # pragma: no cover - defensive safety
        logger.warning("Failed to analyze screenshot %s: %s", image_path, exc)
        return False


def _create_placeholder_image(target_path: Path, description: str, reason: str) -> Tuple[Path, str]:
    """Generate an informative placeholder image when real capture fails."""

    placeholder_path = target_path.with_stem(f"{target_path.stem}_placeholder")

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        message = (
            "Error: PIL (Pillow) library not installed. Cannot create placeholder screenshot. "
            f"Original issue: {reason}"
        )
        logger.error(message)
        return placeholder_path, message

    width, height = 1280, 720
    background = (30, 30, 30)
    accent = (255, 166, 0)
    text_color = (230, 230, 230)

    img = Image.new("RGB", (width, height), color=background)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except Exception:  # pragma: no cover - font availability varies
        font_title = ImageFont.load_default()

    try:
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except Exception:  # pragma: no cover
        font_body = ImageFont.load_default()

    draw.text((40, 40), "Screenshot unavailable", fill=accent, font=font_title)

    wrapped_reason = textwrap.fill(f"Reason: {reason}", width=50)
    wrapped_description = textwrap.fill(f"Requested capture: {description}", width=58)

    draw.text((40, 140), wrapped_reason, fill=text_color, font=font_body)
    draw.text((40, 240), wrapped_description, fill=text_color, font=font_body)

    footer = (
        "This placeholder was generated automatically because the environment "
        "could not capture the actual screen. Configure X11/Wayland permissions "
        "or run in a graphical session for real screenshots."
    )
    draw.text((40, height - 160), textwrap.fill(footer, width=65), fill=(180, 180, 180), font=font_body)

    placeholder_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(placeholder_path)

    message = (
        f"Warning: Screenshot capture failed ({reason}). Generated placeholder image at: {placeholder_path}.\n\n"
        f"Description: {description}"
    )
    logger.warning(message)
    return placeholder_path, message


def take_screenshot(description: str, output_path: Optional[str] = None) -> str:
    """Capture the current screen or generate an informative placeholder."""

    workspace = Path(os.getcwd()) / "workspace" / "screenshots"

    if output_path:
        file_path = Path(output_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        workspace.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = workspace / f"screenshot_{timestamp}.png"

    capture_errors: list[str] = []

    def attempt_mss() -> tuple[bool, Optional[str]]:
        try:
            import mss

            with mss.mss() as sct:
                sct.shot(output=str(file_path))
            if not file_path.exists():
                return False, "mss wrote no file"
            logger.info("Screenshot captured via mss: %s", file_path)
            return True, None
        except ImportError:
            return False, "mss not installed"
        except Exception as exc:  # pragma: no cover - defensive safety
            return False, f"mss capture failed: {exc}"

    def attempt_pyautogui() -> tuple[bool, Optional[str]]:
        try:
            import pyautogui

            screenshot = pyautogui.screenshot()
            screenshot.save(str(file_path))
            if not file_path.exists():
                return False, "pyautogui wrote no file"
            logger.info("Screenshot captured via pyautogui: %s", file_path)
            return True, None
        except ImportError:
            return False, "pyautogui not installed"
        except Exception as exc:  # pragma: no cover - defensive safety
            return False, f"pyautogui capture failed: {exc}"

    def attempt_gnome_dbus() -> tuple[bool, Optional[str]]:
        """Try GNOME/Unity Shell screenshot via D-Bus (works on GNOME/Unity Wayland)."""
        try:
            # Use gdbus to call GNOME Shell screenshot (works on GNOME and Unity)
            cmd = [
                "gdbus", "call", "--session",
                "--dest", "org.gnome.Shell.Screenshot",
                "--object-path", "/org/gnome/Shell/Screenshot",
                "--method", "org.gnome.Shell.Screenshot.Screenshot",
                "true", "false", str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=10, check=False)

            if result.returncode != 0:
                stderr = result.stderr.decode(errors="ignore") if result.stderr else ""
                return False, f"D-Bus screenshot failed: {stderr}"

            if not file_path.exists():
                return False, "D-Bus screenshot did not create file"

            logger.info("Screenshot captured via D-Bus: %s", file_path)
            return True, None

        except FileNotFoundError:
            return False, "gdbus command not found"
        except subprocess.TimeoutExpired:
            return False, "D-Bus screenshot timed out"
        except Exception as exc:  # pragma: no cover - defensive safety
            return False, f"D-Bus error: {exc}"

    def attempt_cli() -> tuple[bool, Optional[str]]:
        command = _select_screenshot_command(file_path)
        if command is None:
            return False, "No supported screenshot utility (grim, hyprshot, scrot, screencapture)"

        try:
            result = subprocess.run(command, capture_output=True, timeout=10, check=False)
        except FileNotFoundError:
            return False, f"Command not found: {command[0]}"
        except subprocess.TimeoutExpired:
            return False, f"Screenshot command timed out: {' '.join(command)}"
        except Exception as exc:  # pragma: no cover - defensive safety
            return False, f"Unexpected error from {' '.join(command)}: {exc}"

        if result.returncode != 0:
            stdout = result.stdout.decode(errors="ignore") if result.stdout else ""
            stderr = result.stderr.decode(errors="ignore") if result.stderr else ""
            return False, f"{' '.join(command)} exited with code {result.returncode}: {stderr or stdout}"

        if not file_path.exists():
            return False, "Screenshot file was not created by CLI tool"

        logger.info("Screenshot captured via command: %s", " ".join(command))
        return True, None

    capture_attempts: list[tuple[str, callable]] = [
        ("gnome_dbus", attempt_gnome_dbus),
        ("mss", attempt_mss),
        ("pyautogui", attempt_pyautogui),
        ("cli", attempt_cli),
    ]

    preferred_backend = os.environ.get("SCREENSHOT_BACKEND", "").strip().lower()
    if preferred_backend:
        capture_attempts.sort(key=lambda pair: 0 if pair[0] == preferred_backend else 1)

    captured = False
    used_backend: Optional[str] = None
    for backend_name, attempt in capture_attempts:
        success, error = attempt()
        if success:
            captured = True
            used_backend = backend_name
            break
        if error:
            capture_errors.append(f"{backend_name}: {error}")

    if captured and _image_is_effectively_black(file_path):
        capture_errors.append("Captured image appears to be all black")
        captured = False
        used_backend = None

    if captured:
        logger.info("Screenshot saved to %s using backend %s - %s", file_path, used_backend, description)
        return f"Screenshot captured and saved to: {file_path}\n\nDescription: {description}"

    reason = ", ".join(capture_errors) if capture_errors else "unknown failure"
    placeholder_path, message = _create_placeholder_image(file_path, description, reason)
    return message


class GenerateImageInput(BaseModel):
    """Input schema for generate_test_image tool."""
    content_description: str = Field(..., description="Description of image content")
    width: int = Field(400, description="Image width in pixels")
    height: int = Field(300, description="Image height in pixels")


def generate_test_image(content_description: str, width: int = 400, height: int = 300) -> str:
    """
    Generate a test image with text and save it to a file.

    This tool creates an actual image file for testing multimodal capabilities.

    Args:
        content_description: Description to render as text in the image
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        String with the file path to the generated image
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create workspace directory
        workspace = Path(os.getcwd()) / "workspace"
        workspace.mkdir(exist_ok=True)

        # Create image
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # Add text to image
        try:
            # Try to use a nice font
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            # Fallback to default font
            font = ImageFont.load_default()

        # Wrap text
        text = f"Test Image:\n{content_description}"

        # Calculate text position (centered)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        # Draw text
        draw.text((x, y), text, fill='black', font=font)

        # Save image
        image_path = workspace / "test_image.png"
        img.save(image_path)

        logger.info(f"Generated test image: {image_path}")
        return f"Generated test image saved to: {image_path}"

    except ImportError:
        logger.error("PIL (Pillow) not installed")
        return "Error: PIL (Pillow) library not installed. Cannot generate test images."
    except Exception as e:
        logger.error(f"Error generating test image: {e}")
        return f"Error generating test image: {str(e)}"


class GetSampleImageInput(BaseModel):
    """Input schema for get_sample_image tool."""
    image_type: str = Field("chart", description="Type of sample image: 'chart', 'diagram', or 'photo'")


def get_sample_image(image_type: str = "chart") -> str:
    """
    Returns a path to a sample image for testing.

    This tool creates simple sample images on-the-fly for testing multimodal capabilities.

    Args:
        image_type: Type of sample image to generate

    Returns:
        String describing the sample image with file path or base64 data
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import random

        workspace = Path(os.getcwd()) / "workspace"
        workspace.mkdir(exist_ok=True)

        if image_type == "chart":
            # Create a simple bar chart
            img = Image.new('RGB', (400, 300), color='white')
            draw = ImageDraw.Draw(img)

            # Draw bars
            data = [60, 120, 90, 150, 110]
            bar_width = 60
            for i, value in enumerate(data):
                x = 30 + i * 70
                y = 250 - value
                draw.rectangle([x, y, x + bar_width, 250], fill='blue', outline='black')

            # Add title
            draw.text((150, 20), "Sample Bar Chart", fill='black')

        elif image_type == "diagram":
            # Create a simple flow diagram
            img = Image.new('RGB', (400, 300), color='white')
            draw = ImageDraw.Draw(img)

            # Draw boxes and arrows
            draw.rectangle([50, 50, 150, 100], fill='lightblue', outline='black')
            draw.rectangle([250, 50, 350, 100], fill='lightgreen', outline='black')
            draw.rectangle([150, 150, 250, 200], fill='lightyellow', outline='black')

            draw.text((80, 70), "Start", fill='black')
            draw.text((275, 70), "Process", fill='black')
            draw.text((180, 170), "End", fill='black')

            # Draw arrows
            draw.line([150, 75, 250, 75], fill='black', width=2)
            draw.line([300, 100, 200, 150], fill='black', width=2)

        else:  # photo
            # Create a colorful abstract image
            img = Image.new('RGB', (400, 300), color='white')
            draw = ImageDraw.Draw(img)

            # Draw random colored circles
            for _ in range(10):
                x = random.randint(0, 400)
                y = random.randint(0, 300)
                r = random.randint(20, 60)
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                draw.ellipse([x-r, y-r, x+r, y+r], fill=color, outline='black')

        # Save image
        image_path = workspace / f"sample_{image_type}.png"
        img.save(image_path)

        logger.info(f"Generated sample {image_type} image: {image_path}")
        return f"Sample {image_type} image saved to: {image_path}"

    except ImportError:
        logger.error("PIL (Pillow) not installed")
        return "Error: PIL (Pillow) library not installed. Cannot generate sample images."
    except Exception as e:
        logger.error(f"Error generating sample image: {e}")
        return f"Error generating sample image: {str(e)}"


# Create FunctionTool instances
take_screenshot_tool = FunctionTool(
    func=take_screenshot,
    name="take_screenshot",
    description="Take a REAL screenshot of the current screen. Captures the entire display and saves it as a PNG file. Returns the file path to the screenshot image."
)

generate_test_image_tool = FunctionTool(
    func=generate_test_image,
    name="generate_test_image",
    description="Generate a test image with custom text for testing multimodal capabilities. Returns the file path to the generated image."
)

get_sample_image_tool = FunctionTool(
    func=get_sample_image,
    name="get_sample_image",
    description="Get a sample image (chart, diagram, or photo) for testing. Returns the file path to the sample image."
)

# Export tools
tools = [take_screenshot_tool, generate_test_image_tool, get_sample_image_tool]
