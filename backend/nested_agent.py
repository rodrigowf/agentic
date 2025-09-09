from autogen_core import CancellationToken
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_agentchat.agents import BaseChatAgent  # Base class for custom agents
# Team classes and termination conditions
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from typing import List
from schemas import AgentConfig
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from agent_factory import create_agent_from_config  # centralized agent instantiation
import types
from context import CURRENT_AGENT
import re  # <-- added for pattern matching

# Helper to wrap an agent so its run/run_stream set the context var to itself
def _wrap_agent_with_context(agent):
    prev_run = getattr(agent, 'run', None)
    if prev_run:
        async def run_with_context(self, *args, **kwargs):
            prev = CURRENT_AGENT.get()
            CURRENT_AGENT.set(self)
            try:
                return await prev_run(*args, **kwargs)
            finally:
                CURRENT_AGENT.set(prev)
        agent.run = types.MethodType(run_with_context, agent)
    prev_stream = getattr(agent, 'run_stream', None)
    if prev_stream:
        async def stream_with_context(self, *args, **kwargs):
            prev = CURRENT_AGENT.get()
            CURRENT_AGENT.set(self)
            try:
                async for evt in prev_stream(*args, **kwargs):
                    yield evt
            finally:
                CURRENT_AGENT.set(prev)
        agent.run_stream = types.MethodType(stream_with_context, agent)
    return agent

def _custom_agent_selector(messages):
    """
    A custom selector function that selects the next agent based on a marker
    in the last message. Defaults to a 'Manager' agent if no marker is found.
    """
    from typing import Sequence
    from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
    
    if not messages:
        # If no messages, start with the default agent
        return "Manager"

    last_content = messages[-1].content.strip()
    
    match = re.search(r"NEXT AGENT:\s*([A-Za-z0-9_ \-]+)\.?$", last_content)
    if match:
        agent_name = match.group(1).strip()
        return agent_name

    # Default case: select the Manager
    return "Manager"


class NestedTeamAgent(BaseChatAgent):
    """An agent that delegates to a nested team of sub-agents."""
    def __init__(self, agent_cfg: AgentConfig, all_tools: List[FunctionTool], default_model_client: OpenAIChatCompletionClient):
        """Build nested team agent from its config, tools, and default model client."""
        super().__init__(agent_cfg.name, description=agent_cfg.description or "Nested team agent")
        self.agent_cfg = agent_cfg
        self.all_tools = all_tools
        self.default_model_client = default_model_client
        self._init_team()

    def _init_team(self):
        # Instantiate sub-agents via centralized factory
        sub_agents = [
            create_agent_from_config(sub_cfg, self.all_tools, self.default_model_client)
            for sub_cfg in (self.agent_cfg.sub_agents or [])
        ]
        # Wrap sub-agents so tools see the correct CURRENT_AGENT inside nested runs
        sub_agents = [_wrap_agent_with_context(sa) for sa in sub_agents]
        
        term_cond = MaxMessageTermination(self.agent_cfg.max_consecutive_auto_reply or 5)
        mode = self.agent_cfg.mode or "round_robin"

        if mode == "selector":
            use_custom_selector = (not self.agent_cfg.orchestrator_prompt or self.agent_cfg.orchestrator_prompt.strip() in {"", "__function__"})
            
            if use_custom_selector:
                self._team = SelectorGroupChat(
                    sub_agents,
                    termination_condition=term_cond,
                    selector_func=_custom_agent_selector,
                    model_client=self.default_model_client
                )
            else:
                self._team = SelectorGroupChat(
                    sub_agents,
                    termination_condition=term_cond,
                    selector_prompt=self.agent_cfg.orchestrator_prompt,
                    model_client=self.default_model_client
                )
        else:
            self._team = RoundRobinGroupChat(agents=sub_agents, termination_condition=term_cond)
        

    async def on_messages(
        self, messages: list[BaseChatMessage], cancellation_token: CancellationToken
    ) -> Response:
        # Run the inner team on the incoming messages (which include the new user prompt).
        result = await self._team.run(task=messages, cancellation_token=cancellation_token)
        # The inner team returns a TaskResult with a message history.
        all_msgs = result.messages
        final_msg = all_msgs[-1]  # team's final response message
        # Inner messages: those generated by sub-agents during this turn (exclude initial input and final output)
        inner_dialog = all_msgs[len(messages):-1] if len(all_msgs) > len(messages) else []
        # Return response with or without inner dialog based on config
        if self.agent_cfg.include_inner_dialog:
            return Response(chat_message=final_msg, inner_messages=inner_dialog)
        else:
            return Response(chat_message=final_msg)

    async def on_messages_stream(
        self, messages: list[BaseChatMessage], cancellation_token: CancellationToken
    ):
        # Stream inner team events (each BaseChatMessage or event from sub-agents) as they occur
        async for event in self._team.run_stream(task=messages, cancellation_token=cancellation_token):
            yield event

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        # Reset the inner team conversation state
        await self._team.reset()

    @property
    def produced_message_types(self):
        # Support text messages and any message types used by sub-agents (e.g., tool events, images if any).
        # At minimum, include TextMessage as the final output type.
        return (TextMessage,)

    # The old from_config is preserved for backward compatibility
    @classmethod
    def from_config(
        cls,
        agent_cfg: AgentConfig,
        all_tools: List[FunctionTool],
        default_model_client: OpenAIChatCompletionClient
    ) -> "NestedTeamAgent":
        return cls(agent_cfg, all_tools, default_model_client)
