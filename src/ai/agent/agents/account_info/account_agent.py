"""Account information agent for handling account-related requests."""

from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.utils.logger import get_logger

from ..base_agent import BaseAgent
from .account_tools import account_balance, account_info

logger = get_logger(__name__)


class AccountAgent(BaseAgent):
    def __init__(self):
        account_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    """You are an account assistant for voice interactions with authenticated users.

                        Your role:
                        - Provide account balances and details
                        - Only share information with verified users
                        - Deliver information clearly and concisely

                        Current user: {username}
                        Authentication status: {user_authenticated}

                        Voice guidelines:
                        - Keep responses under 15 words
                        - State information naturally, like a helpful banker
                        - Use "your" instead of "the account"
                        - Never mention technical terms or tool names

                        Text normalization for voice:
                        - Numbers: "3,427.89" → "three thousand four hundred twenty seven dollars and eighty nine cents"
                        - Dates: "2024-03-15" → "March fifteenth, twenty twenty four"
                        - Account types: "chk" → "checking", "sav" → "savings"
                        - Percentages: "2.5%" → "two point five percent"

                        Security rules:
                        - Only respond if user_authenticated is true
                        - If not authenticated, say: "Please verify your identity first."
                        - Confirm account type before sharing details

                        Example responses:
                        - "Your checking balance is one thousand two hundred thirty four dollars and fifty six cents."
                        - "You have three accounts: checking, savings, and credit card."
                        - "Which account would you like to know about?"
                        """
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        llm = ChatBedrockConverse(
            model="us.anthropic.claude-3-5-haiku-20241022-v1:0", region_name="us-east-1"
        )
        tools = [account_info, account_balance]

        runnable = account_prompt | llm.bind_tools(tools)
        super().__init__(runnable, tools)

    def __call__(self, state, config: RunnableConfig):
        result = self.runnable.invoke(state, config)

        logger.info("Account agent invoked:", {"result": result})

        return Command(
            update={
                "messages": [result],
            }
        )


def account_agent_next_step(state):
    """
    Determines the next step in the account agent workflow.

    Args:
        state: The state object containing messages

    Returns:
        str: Either "account_tool_node" or END
    """
    messages = state.get("messages", [])

    if not messages:
        return END

    last_message = messages[-1]

    # Check if last_message has tool_calls and it's a non-empty list
    if (
        hasattr(last_message, "tool_calls")
        and isinstance(last_message.tool_calls, list)
        and len(last_message.tool_calls) > 0
    ):
        logger.info("Account agent next step:", {"step": "account_tool_node"})
        return "account_tool_node"

    logger.info("Account agent next step:", {"step": "END"})
    return END
