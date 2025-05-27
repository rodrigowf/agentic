import os
from typing import List
from schemas import AgentConfig
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from looping_agent import LoopingAssistantAgent
from nested_agent import NestedTeamAgent
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


def create_agent_from_config(
    agent_cfg: AgentConfig,
    all_tools: List[FunctionTool],
    model_client: OpenAIChatCompletionClient
) -> AssistantAgent:
    """
    Factory function to instantiate different Agent types based on AgentConfig.
    Supports nested_team, code_executor, looping, and standard assistant.
    """
    # Filter tools for this agent
    agent_tools = [t for t in all_tools if t.name in (agent_cfg.tools or [])]

    # Nested team agent
    if agent_cfg.agent_type == "nested_team":
        return NestedTeamAgent.from_config(agent_cfg, all_tools, model_client)

    # Code executor agent
    if agent_cfg.agent_type == "code_executor":
        ce_cfg = agent_cfg.code_executor or {}
        ce_type = ce_cfg.get('type')
        if ce_type == 'local':
            work_dir = ce_cfg.get('work_dir') or os.getcwd()
            code_executor = LocalCommandLineCodeExecutor(work_dir=work_dir)
        else:
            raise ValueError(f"Unsupported code_executor type: {ce_type}")
        return CodeExecutorAgent(
            name=agent_cfg.name,
            code_executor=code_executor,
            model_client=model_client if agent_cfg.model_client_stream else None,
            system_message=agent_cfg.system_message,
            description=agent_cfg.description,
            sources=agent_cfg.sources,
            model_client_stream=agent_cfg.model_client_stream
        )

    # Looping assistant agent
    if agent_cfg.agent_type == 'looping':
        return LoopingAssistantAgent(
            name=agent_cfg.name,
            system_message=agent_cfg.prompt.system,
            model_client=model_client,
            tools=agent_tools,
            reflect_on_tool_use=agent_cfg.reflect_on_tool_use,
            max_consecutive_auto_reply=agent_cfg.max_consecutive_auto_reply
        )

    # Default: standard AssistantAgent
    return AssistantAgent(
        name=agent_cfg.name,
        system_message=agent_cfg.prompt.system,
        model_client=model_client,
        tools=agent_tools,
        max_consecutive_auto_reply=agent_cfg.max_consecutive_auto_reply
    )
