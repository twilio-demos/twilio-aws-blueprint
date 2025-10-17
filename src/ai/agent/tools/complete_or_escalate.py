from langchain_core.tools import tool

from src.utils.logger import get_logger

logger = get_logger(__name__)

"""
CompleteOrEscalate tool for agent delegation and task completion.
"""


@tool
def complete_or_escalate_tool(cancel: bool, reason: str) -> dict:
    """
    Tool function to handle task completion or escalation back to supervisor.

    A tool to mark the current task as completed and/or to escalate control of the dialog
    to the main assistant, who can re-route the dialog based on the user's needs.

    Args:
        cancel: Whether to cancel the current task and return control to supervisor
        reason: The reason for completing/escalating the task

    Returns:
        dict: Result indicating the completion/escalation action

    Examples:
        complete_or_escalate_tool(True, "User changed their mind about the current task.")
        complete_or_escalate_tool(True, "I have fully completed the task.")
        complete_or_escalate_tool(False, "I need to search the user's emails or calendar for more information.")
    """
    action = "escalated" if cancel else "completed"

    result = {
        "action": action,
        "cancel": cancel,
        "reason": reason,
        "message": f"Task {action}: {reason}",
        "return_to_supervisor": True,
    }

    logger.info("CompleteOrEscalate tool invoked:", {"result": result})

    return result
