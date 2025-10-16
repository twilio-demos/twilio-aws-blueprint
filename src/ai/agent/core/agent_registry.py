"""
Agent Registry - Central configuration for all agents in the system.
"""

from enum import Enum
from typing import Optional, Set

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AgentRegistry(Enum):
    """Registry of all available agents with their complete configuration."""

    SUPERVISOR = "supervisor"
    AUTH_AGENT = "auth_agent"
    ACCOUNT_AGENT = "account_agent"
    KB_AGENT = "kb_agent"

    @property
    def can_route_to(self) -> Set[str]:
        """Define valid routing targets for each agent."""
        routing_map = {
            AgentRegistry.SUPERVISOR: {
                AgentRegistry.AUTH_AGENT.value,
                AgentRegistry.ACCOUNT_AGENT.value,
                AgentRegistry.KB_AGENT.value,
            },
            AgentRegistry.AUTH_AGENT: {AgentRegistry.SUPERVISOR.value},
            AgentRegistry.ACCOUNT_AGENT: {AgentRegistry.SUPERVISOR.value},
            AgentRegistry.KB_AGENT: {AgentRegistry.SUPERVISOR.value},
        }
        return routing_map.get(self, set())

    @property
    def agent_class(self):
        """Get the agent class for this node."""
        # Import here to avoid circular imports
        from src.ai.agent.agents.account_info.account_agent import AccountAgent
        from src.ai.agent.agents.auth.auth_agent import AuthAgent
        from src.ai.agent.agents.kb.kb_agent import KnowledgeBaseAgent
        from src.ai.agent.agents.supervisor.supervisor_agent import SupervisorAgent

        agent_map = {
            AgentRegistry.SUPERVISOR: SupervisorAgent,
            AgentRegistry.AUTH_AGENT: AuthAgent,
            AgentRegistry.ACCOUNT_AGENT: AccountAgent,
            AgentRegistry.KB_AGENT: KnowledgeBaseAgent,
        }
        return agent_map.get(self)

    def create_agent_instance(self):
        """Create an agent instance with the proper agent name."""
        agent_class = self.agent_class
        if agent_class:
            return agent_class(agent_name=self.value)
        return None

    @property
    def next_step_function(self):
        """Get the next step function for this agent."""
        # Import here to avoid circular imports
        from src.ai.agent.agents.account_info.account_agent import (
            account_agent_next_step,
        )
        from src.ai.agent.agents.auth.auth_agent import auth_agent_next_step
        from src.ai.agent.agents.kb.kb_agent import kb_agent_next_step

        function_map = {
            AgentRegistry.AUTH_AGENT: auth_agent_next_step,
            AgentRegistry.ACCOUNT_AGENT: account_agent_next_step,
            AgentRegistry.KB_AGENT: kb_agent_next_step,
        }
        return function_map.get(self)

    @property
    def tool_node_name(self) -> Optional[str]:
        """Get the tool node name for this agent (if it has tools)."""
        tool_map = {
            AgentRegistry.AUTH_AGENT: "auth_tool_node",
            AgentRegistry.ACCOUNT_AGENT: "account_tool_node",
            AgentRegistry.KB_AGENT: "kb_tool_node",
        }
        return tool_map.get(self)

    @property
    def tools(self):
        """Get the tools for this agent."""
        # Import here to avoid circular imports
        from src.ai.agent.agents.account_info.account_tools import (
            account_balance,
            account_info,
        )
        from src.ai.agent.agents.auth.auth_tools import authenticate_user
        from src.ai.agent.agents.kb.kb_tools import knowledge_base_search

        tool_map = {
            AgentRegistry.AUTH_AGENT: [authenticate_user],
            AgentRegistry.ACCOUNT_AGENT: [account_balance, account_info],
            AgentRegistry.KB_AGENT: [knowledge_base_search],
        }
        return tool_map.get(self, [])

    @classmethod
    def get_all_agent_names(cls) -> list[str]:
        """Get list of all agent names."""
        return [agent.value for agent in cls]

    @classmethod
    def is_valid_agent(cls, agent_name: str) -> bool:
        """Check if an agent name is valid."""
        try:
            cls(agent_name)
            return True
        except ValueError:
            return False

    @classmethod
    def get_supervisor(cls) -> "AgentRegistry":
        """Get the supervisor agent."""
        return cls.SUPERVISOR
