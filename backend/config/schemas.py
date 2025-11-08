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
    agent_type: str = Field(default="assistant", description="'assistant' for single LLM agent, 'nested_team' for nested team agent, 'code_executor' for code executor agent, 'looping' for looping agent, 'looping_code_executor' for looping code executor agent, 'dynamic_init_looping' for looping agent with custom initialization")
    tools: List[str]
    llm: Optional[LLMConfig] = None
    prompt: Optional[PromptConfig] = None
    # CodeExecutorAgent-specific fields
    code_executor: Optional[dict] = Field(default=None, description="Configuration for code executor (e.g., {'type': 'local'}). Required for code_executor agent_type.")
    model_client_stream: Optional[bool] = Field(default=False, description="Whether to stream model client output in CodeExecutorAgent.")
    sources: Optional[List[str]] = Field(default=None, description="Additional source file paths for code execution.")
    description: Optional[str] = Field(default=None, description="Optional description for CodeExecutorAgent.")
    system_message: Optional[str] = Field(default=None, description="System message for CodeExecutorAgent.")
    max_consecutive_auto_reply: Optional[int] = Field(default=5, description="Optional. Maximum consecutive auto-replies. Defaults to 5 if not provided.")  # Renamed from max_turns
    reflect_on_tool_use: bool = True
    terminate_on_text: bool = False  # Keep for potential future use or backward compat if needed, but default to False
    tool_call_loop: bool = False  # New field to control looping agent behavior
    # Dynamic initialization configuration
    initialization_function: Optional[str] = Field(default=None, description="Python function to call during agent initialization (format: 'module.function_name', e.g., 'memory.initialize_memory_agent'). The function will be called with no arguments after agent creation and can modify the agent's state, system prompt, or perform any setup logic.")
    # Nested team-specific configuration
    sub_agents: Optional[List["AgentConfig"]] = None
    mode: Optional[str] = None
    orchestrator_prompt: Optional[str] = None
    orchestrator_agent_name: Optional[str] = Field(default="Manager", description="Name of the orchestrator agent for nested teams. Defaults to 'Manager'.")
    orchestrator_pattern: Optional[str] = Field(default="NEXT AGENT: <Name>", description="Pattern to use for selecting the next agent. Use <Name> as placeholder for agent name.")
    include_inner_dialog: bool = Field(default=True, description="Include inner dialog messages in the response for nested team agents.")

# Resolve forward references for recursive sub_agents
AgentConfig.update_forward_refs()

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