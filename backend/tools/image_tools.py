"""
Image-related tools for testing multimodal agent capabilities.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from autogen_core.tools import FunctionTool

logger = logging.getLogger(__name__)


class TakeScreenshotInput(BaseModel):
    """Input schema for take_screenshot tool."""
    description: str = Field(..., description="Description of what to capture in the screenshot")
    output_path: Optional[str] = Field(None, description="Optional path to save screenshot")


def take_screenshot(description: str, output_path: Optional[str] = None) -> str:
    """
    Simulates taking a screenshot and returns the file path.

    In a real implementation, this would use a tool like pyautogui or a headless browser
    to capture a screenshot. For testing purposes, this returns a mock file path.

    Args:
        description: Description of what to capture
        output_path: Optional custom path to save screenshot

    Returns:
        String describing the screenshot file path
    """
    try:
        # For testing, we'll just return a mock path
        if output_path:
            file_path = output_path
        else:
            workspace = Path(os.getcwd()) / "workspace"
            workspace.mkdir(exist_ok=True)
            file_path = str(workspace / "screenshot.png")

        logger.info(f"Mock screenshot taken: {file_path}")
        return f"Screenshot captured and saved to: {file_path}\n\nNote: This is a mock implementation. In production, this would contain an actual screenshot image file."
    except Exception as e:
        logger.error(f"Error in take_screenshot: {e}")
        return f"Error taking screenshot: {str(e)}"


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
    description="Take a screenshot of the current screen or window. Returns the file path to the screenshot image."
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
