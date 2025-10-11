# Agent State
"""
State definitions for the multi-agent system.
"""

import operator
from typing import Annotated, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage


def update_dialog_stack(
    current_stack: list[str], push: Optional[str] = None, pop: bool = False
) -> list[str]:
    """
    Manage the dialog stack state.

    Args:
        current_stack: Current dialog stack
        push: Node name to push onto stack (None = no push)
        pop: If True, remove top item from stack

    Returns:
        Updated dialog stack
    """
    if pop and current_stack:
        return current_stack[:-1]

    if push is not None:
        return current_stack + [push]

    return current_stack


def dialog_stack_reducer(
    current_stack: list[str], operation: Optional[dict]
) -> list[str]:
    """
    Reducer that wraps update_dialog_stack for LangGraph.

    Args:
        current_stack: Current stack state
        operation: Dict with 'push' and/or 'pop' keys
            Examples:
                {'push': 'auth_agent'}
                {'pop': True}
    """
    if not operation:
        return current_stack

    # Handle case where operation is not a dictionary
    if not isinstance(operation, dict):
        print(
            f"Warning: Expected dict for operation, got {type(operation)}: {operation}"
        )
        return current_stack

    return update_dialog_stack(
        current_stack=current_stack,
        push=operation.get("push"),
        pop=operation.get("pop", False),
    )


class AgentState(TypedDict):
    """State shared between all agents in the system."""

    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_authenticated: bool  # whether the user is authenticated
    username: Optional[str]
    dialog_state: Annotated[list[str], dialog_stack_reducer]


def default_agent_state() -> AgentState:
    """Returns a default-initialized AgentState."""
    return {
        "messages": [],
        "user_authenticated": False,
        "username": None,
        "dialog_state": ["supervisor"],
    }
