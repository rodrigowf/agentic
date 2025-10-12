"""
Mock tool responses for testing.

This module provides realistic mock responses for various tools used in the system.
These responses match the actual format returned by the tool implementations.
"""

from typing import Dict, Any, Optional
import base64
from datetime import datetime


# ============================================================================
# Research Tool Responses
# ============================================================================

MOCK_WEB_SEARCH_RESPONSE = """Web Search Results (Google CSE) for 'machine learning' (Found 5):
1. Title: Introduction to Machine Learning
   Snippet: Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed. This comprehensive guide covers the fundamentals.
   URL: https://example.com/ml-intro
---
2. Title: Machine Learning Algorithms Explained
   Snippet: Explore the most popular machine learning algorithms including supervised learning, unsupervised learning, and reinforcement learning techniques.
   URL: https://example.com/ml-algorithms
---
3. Title: Deep Learning vs Machine Learning
   Snippet: Understanding the key differences between deep learning and traditional machine learning approaches, including use cases and performance characteristics.
   URL: https://example.com/dl-vs-ml
---
4. Title: Machine Learning in Production
   Snippet: Best practices for deploying machine learning models in production environments, including monitoring, scaling, and maintenance strategies.
   URL: https://example.com/ml-production
---
5. Title: Machine Learning Tools and Frameworks
   Snippet: A comprehensive review of the most popular machine learning frameworks including TensorFlow, PyTorch, Scikit-learn, and emerging tools.
   URL: https://example.com/ml-tools"""

MOCK_ARXIV_SEARCH_RESPONSE = """ArXiv Search Results for 'quantum computing' (Top 3):
1. Title: Quantum Computing: A Gentle Introduction
   Authors: Eleanor Rieffel, Wolfgang Polak
   Published: 2023-05-15
   Summary: This paper provides a comprehensive introduction to quantum computing, covering the fundamental principles of quantum mechanics, quantum gates, and quantum algorithms. We discuss the potential applications of quantum computing in cryptography, optimization, and simulation of quantum systems...
   ArXiv URL: https://arxiv.org/abs/2305.12345
   PDF URL: https://arxiv.org/pdf/2305.12345.pdf
---
2. Title: Recent Advances in Quantum Error Correction
   Authors: John Preskill, Daniel Gottesman
   Published: 2023-06-20
   Summary: Quantum error correction is essential for building practical quantum computers. This review covers recent developments in topological codes, surface codes, and fault-tolerant quantum computation. We present new theoretical results and experimental implementations...
   ArXiv URL: https://arxiv.org/abs/2306.54321
   PDF URL: https://arxiv.org/pdf/2306.54321.pdf
---
3. Title: Quantum Supremacy and Its Implications
   Authors: Scott Aaronson, Dmitri Maslov
   Published: 2023-07-10
   Summary: We analyze the concept of quantum supremacy and its recent experimental demonstrations. This paper discusses the computational complexity implications and the future prospects for quantum computing hardware...
   ArXiv URL: https://arxiv.org/abs/2307.98765
   PDF URL: https://arxiv.org/pdf/2307.98765.pdf"""

MOCK_WIKIPEDIA_SEARCH_RESPONSE = """Wikipedia Search Results for 'artificial intelligence' (Lang: en, Top 3):
1. Title: Artificial Intelligence
   Summary: Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to natural intelligence displayed by animals including humans. AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions...
   URL: https://en.wikipedia.org/wiki/Artificial_intelligence
---
2. Title: History of Artificial Intelligence
   Summary: The history of artificial intelligence (AI) began in antiquity, with myths, stories and rumors of artificial beings endowed with intelligence or consciousness by master craftsmen. The seeds of modern AI were planted by classical philosophers who attempted to describe human thinking as a symbolic system...
   URL: https://en.wikipedia.org/wiki/History_of_artificial_intelligence
---
3. Title: Machine Learning
   Summary: Machine learning (ML) is a field of inquiry devoted to understanding and building methods that 'learn', that is, methods that leverage data to improve performance on some set of tasks. It is seen as a part of artificial intelligence...
   URL: https://en.wikipedia.org/wiki/Machine_learning"""

MOCK_FETCH_WEB_CONTENT_RESPONSE = """Introduction to Machine Learning

Machine learning is a subset of artificial intelligence (AI) that focuses on building applications that learn from data and improve their accuracy over time without being programmed to do so.

Key Concepts:

1. Supervised Learning: The algorithm learns from labeled training data and makes predictions based on that data.

2. Unsupervised Learning: The algorithm works on unlabeled data and tries to find patterns and relationships.

3. Reinforcement Learning: The algorithm learns by interacting with an environment and receiving rewards or penalties.

Common Algorithms:
- Linear Regression
- Logistic Regression
- Decision Trees
- Random Forests
- Neural Networks
- Support Vector Machines
- K-Means Clustering

Applications:
Machine learning is used in various fields including healthcare, finance, marketing, autonomous vehicles, and natural language processing. Recent advances in deep learning have enabled breakthrough applications in computer vision, speech recognition, and game playing.

Getting Started:
To begin with machine learning, you'll need a solid foundation in mathematics (linear algebra, calculus, statistics), programming skills (Python is recommended), and familiarity with ML libraries like TensorFlow, PyTorch, or Scikit-learn."""


# ============================================================================
# Memory Tool Responses
# ============================================================================

MOCK_MEMORY_SAVE_RESPONSE = "Short-term memory successfully updated."

MOCK_MEMORY_GET_RESPONSE = """Current Project Context:
- Working on agentic AI system with Python backend
- Using AutoGen framework for multi-agent coordination
- Frontend built with React and Material-UI
- Implementing voice assistant using OpenAI Realtime API
- Recent work: Added multimodal vision agent capabilities
- Next tasks: Improve memory management and add more tools"""

MOCK_MEMORY_BANK_CREATE_RESPONSE = "Memory bank 'UserPreferences' created successfully. Description: Store user preferences and settings"

MOCK_MEMORY_BANK_ADD_RESPONSE = "Successfully added information to memory bank 'UserPreferences'."

MOCK_MEMORY_BANK_SEARCH_RESPONSE = """Search results for 'favorite color' in memory bank 'UserPreferences':
1. User's favorite color is blue, specifically navy blue
2. User prefers dark color themes for UI
3. Color scheme preferences: Blue and green combinations"""

MOCK_MEMORY_BANK_LIST_RESPONSE = """Available Memory Banks:
- UserPreferences: Store user preferences and settings (5 entries)
- ProjectContext: Technical details about ongoing projects (12 entries)
- LearningNotes: Notes from learning sessions and research (8 entries)"""


# ============================================================================
# Image Tool Responses
# ============================================================================

def create_mock_image_base64(width: int = 200, height: int = 100, text: str = "TEST") -> str:
    """
    Create a simple base64-encoded test image.

    Args:
        width: Image width
        height: Image height
        text: Text to display on image

    Returns:
        Base64-encoded PNG image string
    """
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO

    # Create image
    img = Image.new('RGB', (width, height), color='blue')
    draw = ImageDraw.Draw(img)

    # Add text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Calculate text position (center)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((width - text_width) // 2, (height - text_height) // 2)

    draw.text(position, text, fill='white', font=font)

    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')


MOCK_SCREENSHOT_RESPONSE = "Screenshot saved to /home/rodrigo/agentic/backend/workspace/screenshot_20251011_143025.png"

MOCK_IMAGE_GENERATION_RESPONSE = "Image generated successfully: /home/rodrigo/agentic/backend/workspace/test_image_hello_world.png"

MOCK_SAMPLE_IMAGE_RESPONSE = f"Sample image created: /tmp/sample_chart.png\nImage data: data:image/png;base64,{create_mock_image_base64(400, 300, 'CHART')}"

# Pre-generated base64 image for consistent testing (small blue rectangle with "TEST")
MOCK_BASE64_IMAGE = create_mock_image_base64()


# ============================================================================
# Code Execution Responses
# ============================================================================

MOCK_PYTHON_EXECUTION_RESPONSE = """Successfully executed Python code.

Output:
Hello, World!
The result is: 42
[1, 4, 9, 16, 25]

Execution completed in 0.032 seconds."""

MOCK_BASH_EXECUTION_RESPONSE = """total 48
drwxrwxr-x 16 rodrigo rodrigo  4096 Oct 11 21:51 .
drwxr-xr-x 25 rodrigo rodrigo  4096 Oct 10 15:30 ..
drwxrwxr-x 10 rodrigo rodrigo  4096 Oct 11 18:22 backend
drwxrwxr-x  3 rodrigo rodrigo  4096 Oct 10 12:15 debug
drwxrwxr-x  4 rodrigo rodrigo  4096 Oct 10 15:20 docs
drwxrwxr-x  6 rodrigo rodrigo  4096 Oct 10 14:30 frontend
drwxrwxr-x  2 rodrigo rodrigo  4096 Oct 11 09:45 logs
-rw-rw-r--  1 rodrigo rodrigo 45821 Oct 11 21:52 CLAUDE.md
-rw-rw-r--  1 rodrigo rodrigo  1234 Oct 10 10:00 README.md"""

MOCK_GIT_STATUS_RESPONSE = """On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   backend/core/runner.py
	modified:   frontend/src/features/agents/components/RunConsole.js

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	backend/tests/fixtures/

no changes added to commit (use "git add" and/or "git commit -a")"""


# ============================================================================
# Error Responses
# ============================================================================

MOCK_TOOL_ERROR_RESPONSE = "Error: An unexpected error occurred during the web search for 'invalid query': Connection timeout. Please try again later."

MOCK_API_ERROR_RESPONSE = "Error fetching URL https://example.com/404: HTTP 404 Not Found. Please check the URL and network connection."

MOCK_PERMISSION_ERROR_RESPONSE = "Error: Permission denied when trying to access /root/restricted_file.txt"

MOCK_NOT_FOUND_ERROR_RESPONSE = "Error: Memory bank 'NonExistentBank' does not exist. Create it first using create_memory_bank."


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_tool_response(
    tool_name: str,
    success: bool = True,
    result: Optional[str] = None,
    execution_time: float = 0.1,
    error_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a mock tool response in the standard format.

    Args:
        tool_name: Name of the tool
        success: Whether the tool executed successfully
        result: Tool result (if successful)
        execution_time: Execution time in seconds
        error_message: Error message (if failed)

    Returns:
        Dictionary containing tool response data

    Example:
        >>> response = create_mock_tool_response("web_search", result="Found 5 results")
        >>> assert response["success"] == True
    """
    return {
        "tool_name": tool_name,
        "success": success,
        "result": result if success else None,
        "error": error_message if not success else None,
        "execution_time": execution_time,
        "timestamp": datetime.utcnow().isoformat()
    }


def create_mock_web_search_result(
    query: str,
    num_results: int = 5,
    use_google: bool = True
) -> str:
    """
    Generate a mock web search response with customizable parameters.

    Args:
        query: Search query
        num_results: Number of results to include
        use_google: Use Google CSE format vs DuckDuckGo

    Returns:
        Formatted search results string

    Example:
        >>> results = create_mock_web_search_result("AI", num_results=3)
        >>> assert "Found 3" in results
    """
    source = "Google CSE" if use_google else "DuckDuckGo"
    header = f"Web Search Results ({source}) for '{query}' (Found {num_results}):"

    results = [header]
    for i in range(num_results):
        results.append(
            f"{i+1}. Title: Result {i+1} for {query}\n"
            f"   Snippet: This is a sample search result snippet for the query '{query}'. "
            f"It contains relevant information about the topic.\n"
            f"   URL: https://example.com/result{i+1}"
        )

    return "\n---\n".join(results)


def create_mock_image_response(
    image_path: str,
    include_base64: bool = False
) -> str:
    """
    Create a mock image tool response.

    Args:
        image_path: Path where image was saved
        include_base64: Whether to include base64 data in response

    Returns:
        Tool response string

    Example:
        >>> response = create_mock_image_response("/tmp/test.png", include_base64=True)
        >>> assert "data:image/png;base64," in response
    """
    response = f"Image saved to {image_path}"

    if include_base64:
        response += f"\nImage data: data:image/png;base64,{MOCK_BASE64_IMAGE}"

    return response


# ============================================================================
# Export All
# ============================================================================

__all__ = [
    # Research responses
    "MOCK_WEB_SEARCH_RESPONSE",
    "MOCK_ARXIV_SEARCH_RESPONSE",
    "MOCK_WIKIPEDIA_SEARCH_RESPONSE",
    "MOCK_FETCH_WEB_CONTENT_RESPONSE",

    # Memory responses
    "MOCK_MEMORY_SAVE_RESPONSE",
    "MOCK_MEMORY_GET_RESPONSE",
    "MOCK_MEMORY_BANK_CREATE_RESPONSE",
    "MOCK_MEMORY_BANK_ADD_RESPONSE",
    "MOCK_MEMORY_BANK_SEARCH_RESPONSE",
    "MOCK_MEMORY_BANK_LIST_RESPONSE",

    # Image responses
    "MOCK_SCREENSHOT_RESPONSE",
    "MOCK_IMAGE_GENERATION_RESPONSE",
    "MOCK_SAMPLE_IMAGE_RESPONSE",
    "MOCK_BASE64_IMAGE",

    # Code execution responses
    "MOCK_PYTHON_EXECUTION_RESPONSE",
    "MOCK_BASH_EXECUTION_RESPONSE",
    "MOCK_GIT_STATUS_RESPONSE",

    # Error responses
    "MOCK_TOOL_ERROR_RESPONSE",
    "MOCK_API_ERROR_RESPONSE",
    "MOCK_PERMISSION_ERROR_RESPONSE",
    "MOCK_NOT_FOUND_ERROR_RESPONSE",

    # Helper functions
    "create_mock_tool_response",
    "create_mock_web_search_result",
    "create_mock_image_response",
    "create_mock_image_base64",
]
