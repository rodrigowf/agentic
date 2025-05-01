from pydantic import BaseModel
from typing import Any, Dict, List

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

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