# Agent State
"""
State definitions for the multi-agent system.
"""

import operator
from typing import Annotated, Optional, Sequence, TypedDict

from src.types.models import Message
from src.utils.logger import get_logger

logger = get_logger(__name__)


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


def dialog_stack_reducer(current_stack: list[str], operation) -> list[str]:
    """
    Reducer that wraps update_dialog_stack for LangGraph.

    Args:
        current_stack: Current dialog stack
        operation: Either a dict with 'push'/'pop' keys, a list (direct assignment),
                   or string "pop" for popping
            Examples:
                {'push': 'auth_agent'}
                {'pop': True}
                ['supervisor', 'auth_agent']  # Direct assignment
                "pop"  # Pop operation
    """
    if not operation:
        return current_stack

    # Handle direct list assignment (backward compatibility)
    if isinstance(operation, list):
        return operation

    # Handle string "pop" operation
    if operation == "pop":
        return update_dialog_stack(
            current_stack=current_stack,
            push=None,
            pop=True,
        )

    # Handle dictionary operations
    if isinstance(operation, dict):
        return update_dialog_stack(
            current_stack=current_stack,
            push=operation.get("push"),
            pop=operation.get("pop", False),
        )

    # Fallback: return current stack unchanged
    logger.warning(
        f"Unknown dialog_stack operation type: {type(operation)}, value: {operation}"
    )
    return current_stack


class BaseAgentState(TypedDict):
    """State shared between all agents in the system."""

    session_id: str
    call_sid: str
    messages: Annotated[Sequence[Message], operator.add]
    dialog_state: Annotated[list[str], dialog_stack_reducer]


class AIAgentState(BaseAgentState):
    """State shared between all agents in the system."""

    user_authenticated: bool  # whether the user is authenticated
    username: Optional[str]
