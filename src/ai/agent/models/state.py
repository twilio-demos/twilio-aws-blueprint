# Agent State
"""
State definitions for the multi-agent system.
"""

import operator
from typing import Annotated, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State shared between all agents in the system."""

    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_authenticated: bool  # whether the user is authenticated
    username: Optional[str]


def default_agent_state() -> AgentState:
    """Returns a default-initialized AgentState."""
    return {
        "messages": [],
        "user_authenticated": False,
        "username": None,
    }
