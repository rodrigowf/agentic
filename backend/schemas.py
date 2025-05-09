from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, List, Callable, Optional

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            # Add custom encoders if needed
        },
        populate_by_name=True,
        str_strip_whitespace=True,
        extra='forbid'  # Prevent extra fields
    )

class ToolInfo(BaseSchema):
    """Simplified representation of a tool for API responses."""
    name: str
    description: str
    parameters: Dict[str, Any]  # Keep parameters schema for frontend display if needed
    filename: Optional[str] = None  # Keep filename for reference if possible

class LLMConfig(BaseSchema):
    provider: str  # openai, anthropic, gemini
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None

class PromptConfig(BaseSchema):
    system: str
    user: str

class AgentConfig(BaseSchema):
    name: str
    tools: List[str]
    llm: LLMConfig
    prompt: PromptConfig
    max_consecutive_auto_reply: Optional[int] = Field(default=5, description="Optional. Maximum consecutive auto-replies. Defaults to 5 if not provided.")  # Renamed from max_turns
    reflect_on_tool_use: bool = True
    terminate_on_text: bool = False  # Keep for potential future use or backward compat if needed, but default to False
    tool_call_loop: bool = False  # New field to control looping agent behavior

class GenerateToolRequest(BaseSchema):
    prompt: str = Field(..., description="The natural language prompt describing the tool to be generated.")

class BaseChatMessage(BaseModel):
    content: str
    source: str
    models_usage: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    type: str = "TextMessage"

    class Config:
        json_encoders = {
            # Add any custom serializers here
            'BaseModel': lambda x: x.dict()
        }
        extra = "allow"  # Allow extra fields
        validate_assignment = True
        arbitrary_types_allowed = True
        
    def model_dump(self, **kwargs):
        # Ensure consistent serialization
        return {
            "content": self.content,
            "source": self.source,
            "models_usage": self.models_usage,
            "metadata": self.metadata,
            "type": self.type
        }