"""
Tool for taking a screenshot and returning it as an Autogen Image.
"""
import io
import base64
try:
    from PIL import ImageGrab
except ImportError:
    import pyscreenshot as ImageGrab
from autogen_core import Image as AGImage
from autogen_core.tools import FunctionTool


def take_screenshot() -> AGImage:
    """Capture the current screen using Pillow ImageGrab (or pyscreenshot) and return it as an Autogen Image object."""
    # Grab the screen
    img = ImageGrab.grab()
    # Convert to PNG bytes
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    # Create AGImage from base64
    return AGImage.from_base64(img_b64)

# Wrap function in a FunctionTool
take_screenshot_tool = FunctionTool(
    name="take_screenshot",
    func=take_screenshot,
    description="Capture the current screen and return the image.",
)
