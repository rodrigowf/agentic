from pydantic import BaseModel, Field
from typing import Any, Dict, List, Callable, Optional

class ToolInfo(BaseModel):
    """Simplified representation of a tool for API responses."""
    name: str
    description: str
    parameters: Dict[str, Any]  # Keep parameters schema for frontend display if needed
    filename: Optional[str] = None  # Keep filename for reference if possible

class LLMConfig(BaseModel):
    provider: str  # openai, anthropic, gemini
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None

class PromptConfig(BaseModel):
    system: str
    user: str

class AgentConfig(BaseModel):
    name: str
    tools: List[str]
    llm: LLMConfig
    prompt: PromptConfig
    max_turns: int = 5
    reflect_on_tool_use: bool = True
    terminate_on_text: bool = True

class GenerateToolRequest(BaseModel):
    prompt: str = Field(..., description="The natural language prompt describing the tool to be generated.")