"""
Module: dynamic_init_looping_agent

Provides a DynamicInitLoopingAgent that extends LoopingAssistantAgent with
custom initialization function support. The initialization function can be
used to modify the agent's system prompt, set up state, or perform any other
setup logic before the agent starts processing tasks.
"""

import logging
import importlib
from typing import Optional
from core.looping_agent import LoopingAssistantAgent

logger = logging.getLogger(__name__)


class DynamicInitLoopingAgent(LoopingAssistantAgent):
    """
    A looping agent that calls a custom initialization function after creation.

    The initialization function can modify the agent's system prompt, set up state,
    load resources, or perform any other setup logic. This makes the agent flexible
    and configurable without hard-coding initialization logic in the runner.

    The initialization function should:
    - Be defined in a module under the 'tools/' directory
    - Take no arguments
    - Use get_current_agent() from utils.context to access the agent instance
    - Perform any initialization logic (modify system message, load data, etc.)
    - Return a string message (success/error) or None

    Example initialization function (in tools/memory.py):
        ```python
        from utils.context import get_current_agent

        def initialize_memory_agent():
            agent = get_current_agent()
            # Load memory content
            memory_content = load_memory_from_file()
            # Update agent's system message
            if agent._system_messages:
                agent._system_messages[0].content = agent._system_messages[0].content.replace(
                    "{{SHORT_TERM_MEMORY}}",
                    memory_content
                )
            return "Memory agent initialized"
        ```

    Args:
        initialization_function: String in format 'module.function_name' (e.g., 'memory.initialize_memory_agent')
                                The module should be in the tools/ directory.
        *args, **kwargs: Additional arguments passed to LoopingAssistantAgent
    """

    def __init__(self, *args, initialization_function: Optional[str] = None, **kwargs):
        """
        Initialize the agent and run the custom initialization function if provided.

        Args:
            initialization_function: Optional function reference (format: 'module.function_name')
            *args, **kwargs: Arguments passed to parent LoopingAssistantAgent
        """
        super().__init__(*args, **kwargs)
        self.initialization_function = initialization_function

        # Run initialization if function is specified
        if initialization_function:
            try:
                self._run_initialization()
                logger.info(f"Agent '{self.name}' initialized with custom function: {initialization_function}")
            except Exception as e:
                logger.error(f"Failed to run initialization function '{initialization_function}': {e}")
                # Don't fail agent creation, just log the error
                # This allows the agent to still function even if init fails

    def _run_initialization(self):
        """
        Dynamically import and call the initialization function.

        The function is imported from tools/{module}.py and called with no arguments.
        The function should use get_current_agent() to access the agent instance.

        Raises:
            ValueError: If the function string is invalid or missing parts
            ImportError: If the module cannot be imported
            AttributeError: If the function doesn't exist in the module
        """
        if not self.initialization_function:
            return

        # Parse the function string (format: 'module.function_name')
        parts = self.initialization_function.split('.')
        if len(parts) < 2:
            raise ValueError(
                f"Invalid initialization_function format: '{self.initialization_function}'. "
                f"Expected format: 'module.function_name' (e.g., 'memory.initialize_memory_agent')"
            )

        module_name = parts[0]
        function_name = '.'.join(parts[1:])  # Support nested function names

        # Import the module from tools package
        try:
            module = importlib.import_module(f'tools.{module_name}')
            logger.debug(f"Successfully imported module: tools.{module_name}")
        except ImportError as e:
            raise ImportError(
                f"Failed to import module 'tools.{module_name}' for initialization function. "
                f"Make sure the module exists in the tools/ directory. Error: {e}"
            )

        # Get the function from the module
        try:
            init_func = getattr(module, function_name)
            logger.debug(f"Successfully found function: {function_name}")
        except AttributeError:
            raise AttributeError(
                f"Function '{function_name}' not found in module 'tools.{module_name}'. "
                f"Available functions: {[name for name in dir(module) if not name.startswith('_')]}"
            )

        # Call the function
        try:
            result = init_func()
            if result:
                logger.info(f"Initialization function returned: {result}")
        except Exception as e:
            raise Exception(
                f"Error executing initialization function '{self.initialization_function}': {e}"
            )
