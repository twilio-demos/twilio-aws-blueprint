"""Account information agent for handling account-related requests."""

from account_tools import account_balance, account_info
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.ai.agent.agents.base_agent import BaseAgent
from src.ai.agent.core.bedrock import BedrockClientFactory
from src.ai.agent.tools.complete_or_escalate import complete_or_escalate_tool
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AccountAgent(BaseAgent):
    def __init__(self):
        account_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
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

                        When to use complete_or_escalate_tool:
                        - User's account question is fully answered: cancel=True, reason="Account inquiry completed"
                        - User asks about general banking info that you cannot answer: cancel=True, reason="User needs general banking information"

                        If user asks about non-account topics:
                        - Politely redirect them to account information questions
                        - Do NOT use any tools for redirects, just respond with text

                        Example responses:
                        - "Your checking balance is one thousand two hundred thirty four dollars and fifty six cents."
                        - "You have three accounts: checking, savings, and credit card."
                        - "Which account would you like to know about?"
                        """,
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        llm = BedrockClientFactory.get_latency_optimized_llm_with_guardrails()

        tools = [account_info, account_balance, complete_or_escalate_tool]

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
        str: Either "account_tool_node", "leave_skill", or END
    """
    messages = state.get("messages", [])

    if not messages:
        return END

    last_message = messages[-1]

    # Check if we just processed a CompleteOrEscalate tool result
    if (
        hasattr(last_message, "type")
        and last_message.type == "tool"
        and hasattr(last_message, "name")
        and last_message.name == "complete_or_escalate_tool"
    ):
        logger.info(
            "Account agent escalating to supervisor after CompleteOrEscalate tool result"
        )
        return "leave_skill"

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
