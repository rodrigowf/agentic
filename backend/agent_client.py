"""
Module: agent_client

Provides a client class for interacting with pre-configured AutoGen agents
from a Python script environment.
"""
import asyncio
import os
from typing import List, Optional
from dotenv import load_dotenv

# AutoGen core components
from autogen_core.tools import FunctionTool
from autogen_agentchat.messages import TextMessage

# Project-specific components
from config_loader import load_agents, load_tools
from agent_factory import create_agent_from_config
from schemas import AgentConfig

# Model clients
from autogen_ext.models.openai import OpenAIChatCompletionClient
# Add other model clients if you support them, e.g., Anthropic, Gemini
# from autogen_ext.models.anthropic import AnthropicChatCompletionClient
# from autogen_ext.models.gemini import GeminiChatCompletionClient

class AgentClient:
    """
    A client for interacting with a specific, pre-configured AutoGen agent.

    This class loads an agent's configuration and tools, instantiates the
    agent, and provides a simple interface to interact with it.
    """
    def __init__(self, agent_name: str, agents_dir: str = "agents", tools_dir: str = "tools"):
        """
        Initializes the AgentClient.

        Args:
            agent_name (str): The name of the agent to load (must match the .json file name).
            agents_dir (str, optional): The directory where agent configurations are stored. Defaults to "agents".
            tools_dir (str, optional): The directory where tool Python files are stored. Defaults to "tools".
        """
        load_dotenv()
        self.agent_name = agent_name
        self.agent: Optional[AssistantAgent] = None
        self._agents_dir = agents_dir
        self._tools_dir = tools_dir
        self._all_tools: List[FunctionTool] = []
        self._agent_cfg: Optional[AgentConfig] = None

        self._load_configs()
        self._setup_agent()

    def _load_configs(self):
        """Loads agent and tool configurations from disk."""
        print("Loading configurations...")
        agents = load_agents(self._agents_dir)
        self._agent_cfg = next((cfg for cfg in agents if cfg.name == self.agent_name), None)

        if not self._agent_cfg:
            raise ValueError(f"Agent configuration for '{self.agent_name}' not found in '{self._agents_dir}'.")

        loaded_tools_with_filenames = load_tools(self._tools_dir)
        self._all_tools = [tool for tool, _ in loaded_tools_with_filenames]
        print("Configurations loaded.")

    def _setup_agent(self):
        """Instantiates the agent and its dependencies."""
        if not self._agent_cfg:
            raise RuntimeError("Agent configuration not loaded. Cannot set up agent.")

        print(f"Setting up agent '{self.agent_name}'...")
        # --- Model Client Setup ---
        # This example defaults to OpenAI. Extend this logic to support other providers
        # based on self._agent_cfg.llm.provider.
        model_client = None
        if self._agent_cfg.llm:
            provider = self._agent_cfg.llm.provider.lower()
            model = self._agent_cfg.llm.model
            api_key = os.getenv("OPENAI_API_KEY") # Generalize if using more providers

            if provider == "openai":
                model_client = OpenAIChatCompletionClient(api_key=api_key, model=model)
            # Add elif blocks for 'anthropic', 'gemini', etc.
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        else:
            # Fallback or default client if no LLM is specified in the config
            print("Warning: LLM config not found for agent. Using default OpenAI client.")
            api_key = os.getenv("OPENAI_API_KEY")
            model_client = OpenAIChatCompletionClient(api_key=api_key)


        # --- Agent Instantiation ---
        self.agent = create_agent_from_config(self._agent_cfg, self._all_tools, model_client)
        print(f"Agent '{self.agent_name}' is ready.")

    async def chat(self, message: str) -> str:
        """
        Sends a message to the agent and returns the final text response.

        Args:
            message (str): The user's message to the agent.

        Returns:
            str: The agent's final text response.
        """
        if not self.agent:
            raise RuntimeError("Agent is not initialized.")

        print(f"\n> You: {message}")

        final_response = ""
        # The agent's run_stream method is an async generator
        async for event in self.agent.run_stream(task=message):
            if event.type == "TextMessage":
                # Assuming TextMessage has a 'content' attribute
                text_chunk = event.content
                print(f"\r> {self.agent.name}: {final_response}{text_chunk}", end="", flush=True)
                final_response += text_chunk

        print() # Newline after streaming is complete
        return final_response

async def main():
    """
    Example usage of the AgentClient.
    
    To run this, execute `python -m backend.agent_client` from the root project directory.
    Make sure to replace 'Developer' with the name of an agent you have defined.
    """
    try:
        # Replace 'Developer' with the name of an agent defined in your `agents` directory
        client = AgentClient(agent_name="Developer") 
        
        # Example: Ask the agent to do something
        response = await client.chat("Write a python script to list files in the current directory.")
        print(f"\n--- Final Response from {client.agent_name} ---\n{response}")

    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # This allows running the client directly for testing purposes.
    # Ensure you run this from the root of your project directory, e.g.,
    # python -m backend.agent_client
    asyncio.run(main())
