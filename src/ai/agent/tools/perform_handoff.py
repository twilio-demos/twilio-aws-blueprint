from typing import Any

from langchain_core.tools import tool

from src.utils.logger import get_logger

logger = get_logger(__name__)

"""
PerformHandoff tool used by agents to hand off the conversation out from ConversationRelay. This could be used for transferring to a human agent, a <Pay> workflow, another system, etc. It could also be used to re-initialize ConversationRelay with new parameters.
"""


@tool
def perform_handoff_tool(data: dict[str, Any]) -> dict[str, Any]:
    """
    Tool function used by agents to hand off the conversation out from ConversationRelay. This could be used for transferring to a human agent, a <Pay> workflow, another system, etc. It could also be used to re-initialize ConversationRelay with new parameters.

    Args:
        data: Dictionary with data to provide ConversationRelay for the handoff.

    Examples:
        perform_handoff_tool({ "result": "agent_escalation", "taskrouter_workflow": "WWxxxx" })
        perform_handoff_tool({ "result": "pay", "order_reference": "12345" })
    """

    logger.info("PerformHandoff tool invoked:", {"data": data})

    return data
