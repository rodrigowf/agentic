"""
Module: agent_factory

Provides a factory function to instantiate various Agent types (assistant, nested team, looping, code executor)
based on a uniform AgentConfig schema.
"""

import os
from typing import List
from config.schemas import AgentConfig
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from core.looping_agent import LoopingAssistantAgent
from core.looping_code_executor_agent import LoopingCodeExecutorAgent
from core.multimodal_tools_looping_agent import MultimodalToolsLoopingAgent
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


def create_agent_from_config(
    agent_cfg: AgentConfig,
    all_tools: List[FunctionTool],
    model_client: OpenAIChatCompletionClient
) -> AssistantAgent:
    """
    Instantiate and return an Agent instance matching the given configuration.

    Parameters:
        agent_cfg (AgentConfig): Configuration object specifying agent type, tools, and settings.
        all_tools (List[FunctionTool]): List of available function tools to filter and attach.
        model_client (OpenAIChatCompletionClient): Default model client for chat completions.

    Returns:
        AssistantAgent: An instance of the requested agent type (AssistantAgent, LoopingAssistantAgent,
                        CodeExecutorAgent, or NestedTeamAgent).
    """
    # Filter tools for this agent
    agent_tools = [t for t in all_tools if t.name in (agent_cfg.tools or [])]

    # Nested team agent: import locally to avoid circular import
    if agent_cfg.agent_type == "nested_team":
        from core.nested_agent import NestedTeamAgent
        # Include flag for inner dialog in nested team agent config
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
        # Always provide model_client to enable code generation; streaming controlled by model_client_stream
        return CodeExecutorAgent(
            name=agent_cfg.name,
            code_executor=code_executor,
            model_client=model_client,
            system_message=agent_cfg.system_message,
            description=agent_cfg.description,
            sources=agent_cfg.sources,
            model_client_stream=agent_cfg.model_client_stream
        )

    # Looping assistant agent
    if agent_cfg.agent_type == 'looping':
        return LoopingAssistantAgent(
            name=agent_cfg.name,
            description=agent_cfg.description,
            system_message=agent_cfg.prompt.system,
            model_client=model_client,
            tools=agent_tools,
            reflect_on_tool_use=agent_cfg.reflect_on_tool_use,
            max_consecutive_auto_reply=agent_cfg.max_consecutive_auto_reply
        )

    # Looping code executor agent
    if agent_cfg.agent_type == 'looping_code_executor':
        ce_cfg = agent_cfg.code_executor or {}
        ce_type = ce_cfg.get('type')
        if ce_type == 'local':
            work_dir = ce_cfg.get('work_dir') or os.getcwd()
            code_executor = LocalCommandLineCodeExecutor(work_dir=work_dir)
        else:
            raise ValueError(f"Unsupported code_executor type: {ce_type}")
        return LoopingCodeExecutorAgent(
            name=agent_cfg.name,
            code_executor=code_executor,
            model_client=model_client,
            system_message=agent_cfg.system_message,
            description=agent_cfg.description,
            sources=agent_cfg.sources,
            model_client_stream=agent_cfg.model_client_stream,
            max_consecutive_auto_reply=agent_cfg.max_consecutive_auto_reply
        )

    # Multimodal tools looping agent
    if agent_cfg.agent_type == 'multimodal_tools_looping':
        return MultimodalToolsLoopingAgent(
            name=agent_cfg.name,
            description=agent_cfg.description,
            system_message=agent_cfg.prompt.system,
            model_client=model_client,
            tools=agent_tools,
            reflect_on_tool_use=agent_cfg.reflect_on_tool_use,
            max_consecutive_auto_reply=agent_cfg.max_consecutive_auto_reply
        )

    # Default: standard AssistantAgent
    return AssistantAgent(
        name=agent_cfg.name,
        description=agent_cfg.description,
        system_message=agent_cfg.prompt.system,
        model_client=model_client,
        tools=agent_tools,
    )
