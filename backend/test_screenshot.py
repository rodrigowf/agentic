#!/usr/bin/env python3
"""
Test script for screenshot agent to debug image handling.
"""

import asyncio
import json
import logging
from pathlib import Path

from config_loader import load_agent_config
from runner import create_agent_and_run_streaming

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_screenshot_agent():
    """Test the screenshot agent with image handling."""
    
    # Load the screenshot agent config
    config_path = Path("agents/ScreenshotAgent.json")
    if not config_path.exists():
        logger.error(f"Agent config not found: {config_path}")
        return
    
    # Simple screenshot task
    task = "Take a screenshot of the current screen and tell me what you see in the image."
    
    logger.info(f"Testing screenshot agent with task: {task}")
    
    try:
        # Create and run the agent
        async for event in create_agent_and_run_streaming(str(config_path), task):
            # Pretty print each event
            if isinstance(event, dict):
                event_type = event.get('type', 'unknown')
                logger.info(f"Event type: {event_type}")
                
                if event_type == "ToolCallExecutionEvent":
                    logger.info("🔧 Tool execution event received")
                    content = event.get('content', [])
                    for result in content:
                        logger.info(f"Tool result: {result.get('name', 'unknown')} -> {type(result.get('content', ''))}")
                        if 'screenshot' in result.get('name', '').lower():
                            logger.info(f"Screenshot tool content type: {type(result.get('content', ''))}")
                            if hasattr(result.get('content', ''), '__class__'):
                                logger.info(f"Screenshot tool content class: {result.get('content', '').__class__}")
                
                print(json.dumps(event, indent=2, default=str))
            else:
                logger.info(f"Non-dict event: {type(event)}")
                print(event)
            
    except Exception as e:
        logger.error(f"Error running screenshot agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_screenshot_agent())
