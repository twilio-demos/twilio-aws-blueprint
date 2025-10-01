"""Authentication tools for the auth agent."""

from datetime import date
from typing import Annotated, Any, Dict

from dateutil import parser as date_parser
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command

from src.utils.logger import get_logger

from ...data.mock_database import get_database

logger = get_logger(__name__)


class AuthResult:
    """Result of an authentication attempt."""

    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "message": self.message}


@tool
def authenticate_user(
    first_name: str,
    last_name: str,
    date_of_birth: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Authenticate a user with personal information.

    Args:
        first_name: The user's first name
        last_name: The user's last name
        date_of_birth: The user's date of birth
    """
    db = get_database()

    logger.info(
        "Authenticating user:",
        {
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": date_of_birth,
        },
    )

    try:
        # Parse any valid date string into a date object
        parsed_date: date = date_parser.parse(date_of_birth).date()

        dob_str = parsed_date.strftime("%Y-%m-%d")

        user = db.authenticate_user(first_name, last_name, dob_str)
        if user:
            return Command(
                update={
                    "user_authenticated": True,
                    "messages": [
                        ToolMessage(
                            content="User authenticated successfully.",
                            tool_call_id=tool_call_id,
                        )
                    ],
                    "username": user.username,
                }
            )
        else:
            return Command(
                update={
                    "user_authenticated": False,
                    "messages": [
                        ToolMessage(
                            content="User authentication failed.",
                            tool_call_id=tool_call_id,
                        )
                    ],
                }
            )

    except Exception as e:
        return Command(
            update={
                "user_authenticated": False,
                "messages": [
                    ToolMessage(
                        content=f"Authentication error: {str(e)}",
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )
