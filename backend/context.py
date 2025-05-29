import contextvars

CURRENT_AGENT = contextvars.ContextVar("CURRENT_AGENT", default=None)

def get_current_agent():
    """Helper to get current agent in tool context."""
    return CURRENT_AGENT.get()
