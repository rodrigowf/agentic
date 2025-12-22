"""
Handlers module for custom_loop agent output processing.

Handlers are functions that process agent output each iteration,
providing feedback (text, images) back to the model.

Each handler module should export a `process_output` function with signature:

    def process_output(
        output: str,
        iteration: int,
        config: dict,
        context: dict
    ) -> OutputHandlerResult

Where context contains:
    - agent_name: str
    - output_dir: Path
    - any other handler-specific state
"""

from .base import OutputHandlerResult, load_handler

__all__ = ['OutputHandlerResult', 'load_handler']
