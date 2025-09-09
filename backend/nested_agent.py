from autogen_core import CancellationToken
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_agentchat.agents import BaseChatAgent  # Base class for custom agents
# Team classes and termination conditions
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.conditions import FunctionalTermination  # use documented functional termination
from typing import List
from schemas import AgentConfig
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from agent_factory import create_agent_from_config  # centralized agent instantiation
import types
from context import CURRENT_AGENT
import re  # ensure regex available

# Track current team agent names for selector validation
_TEAM_AGENT_NAMES: set[str] = set()

# Build manager-only termination condition (case-insensitive 'terminate')
def _manager_only_termination():
    return FunctionalTermination(
        lambda msgs: any(
            isinstance(m, BaseChatMessage)
            and getattr(m, "source", "") == "Manager"
            and "TERMINATE" in (getattr(m, "content", "") or "")
            for m in msgs
        )
    )

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
    """Deterministic custom selector with safeguards.
    Manager-only termination: Researcher/Developer saying TERMINATE just hands control back to Manager.
    Logic:
      * If no messages or last speaker not in team (e.g. user) -> Manager.
      * Manager turn: if TERMINATE -> None (custom ManagerTerminateCondition ends chat); else parse NEXT AGENT; else None.
      * Non-manager turn: if TERMINATE -> Manager; else allow same agent (loop) since allow_repeated_speaker=True.
    """
    if not messages:
        return "Manager"

    last = messages[-1]
    content = (getattr(last, "content", "") or "").strip()

    # If last speaker is outside team (e.g., 'user'), start with Manager
    if last.source not in _TEAM_AGENT_NAMES and last.source != "Manager":
        return "Manager"

    # Manager logic
    if last.source == "Manager":
        if "TERMINATE" in content:
            return None  # termination condition will catch TERMINATE token in stream
        # Parse NEXT AGENT (case-insensitive). Accept patterns like NEXT AGENT: Researcher
        match = re.search(r"NEXT\s+AGENT:\s*([A-Za-z0-9_ \-]+)", content, re.IGNORECASE)
        if match:
            agent_name = match.group(1).strip().rstrip('.')
            if agent_name and agent_name.lower() != "manager" and agent_name in _TEAM_AGENT_NAMES:
                return agent_name
        return None

    # Non-manager turn logic
    if "TERMINATE" in content:
        return "Manager"  # bounce to Manager for wrap-up; termination condition may also trigger
    # Allow same agent to keep going (tool loop) – framework permits due to allow_repeated_speaker=True
    return last.source


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
        # Update global set of team agent names for selector
        global _TEAM_AGENT_NAMES
        _TEAM_AGENT_NAMES = {a.name for a in sub_agents}
        sub_agents = [_wrap_agent_with_context(sa) for sa in sub_agents]

        # Compose termination: stop if Manager (or any agent) says TERMINATE, or after max messages
        max_messages = self.agent_cfg.max_consecutive_auto_reply or 5
        term_cond = _manager_only_termination() | MaxMessageTermination(max_messages)
        mode = self.agent_cfg.mode or "round_robin"

        if mode == "selector":
            use_custom_selector = (not self.agent_cfg.orchestrator_prompt or self.agent_cfg.orchestrator_prompt.strip() in {"", "__function__"})
            if use_custom_selector:
                self._team = SelectorGroupChat(
                    sub_agents,
                    termination_condition=term_cond,
                    selector_func=_custom_agent_selector,
                    model_client=self.default_model_client,
                    allow_repeated_speaker=True,  # enable chaining same agent for multi-step reasoning
                )
            else:
                self._team = SelectorGroupChat(
                    sub_agents,
                    termination_condition=term_cond,
                    selector_prompt=self.agent_cfg.orchestrator_prompt,
                    model_client=self.default_model_client,
                    allow_repeated_speaker=True,
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
