from typing import Annotated, Any, Dict

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command

from src.utils.logger import get_logger

from ...data.mock_database import get_database

logger = get_logger(__name__)


@tool
def account_info(username: str, account_type: str = "checking") -> Dict[str, Any]:
    """Get account information based on user details.
    Args:
        username: The username of the account holder
        account_type: The type of account to retrieve (default: "checking")
    """
    db = get_database()
    user_account = db.get_account_info(username, account_type)
    if not user_account:
        logger.info(
            "Account information not found:",
            {"username": username, "account_type": account_type},
        )
        return {"success": False, "message": "User not found"}

    logger.info(
        "Account information retrieved successfully:", {"user_account": user_account}
    )
    return {"success": True, "user_account": user_account}


@tool
def account_balance(
    username: str, account_type: str, tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Get the account balance for a specific user.
    Args:
        username: The username of the account holder
        account_type: The type of account to retrieve
    """
    db = get_database()
    user_account = db.get_account_info(username, account_type)
    if not user_account:
        logger.info(
            "Account balance could not be retrieved:",
            {"username": username, "account_type": account_type},
        )
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="balance could not be retrieved for user and account type.",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    logger.info(
        "Account balance retrieved successfully for user:", {"username": username}
    )

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="balance retrieved successfully. the balance is $"
                    + str(user_account.balance),
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )
