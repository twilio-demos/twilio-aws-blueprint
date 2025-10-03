"""Authentication agent for handling user authentication and verification."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.utils.logger import get_logger

from ...core.bedrock import BedrockClientFactory
from ..base_agent import BaseAgent
from .auth_tools import authenticate_user

logger = get_logger(__name__)


class AuthAgent(BaseAgent):
    MODEL_NAME = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    REGION_NAME = "us-east-1"

    def __init__(self):
        auth_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an authentication assistant for voice interactions.

                    Your ONLY role is to verify user identity. Do not answer questions about accounts, balances, transactions, or any other topics.

                    Authentication process:
                    - Collect: first name, last name, and date of birth
                    - Verify the information
                    - Confirm success or failure

                    If user asks about anything else:
                    - Do NOT provide suggestions or alternatives
                    - Redirect back to supervisor node

                    Current status: {user_authenticated}

                    Voice guidelines:
                    - Keep responses under 15 words
                    - Use natural, conversational language
                    - Ask for one piece of information at a time
                    - Never mention technical terms, customer service, or other systems

                    Example responses:
                    Authentication:
                    - "I'll need your first name, last name, and date of birth."
                    - "What's your date of birth? Month, day, and year please."
                    - "Thanks! You're all verified."
                    - "I couldn't verify those details. Let's try again."

                    Off-topic questions:
                    - "Let me verify your identity first. What's your first name?"
                    """,
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        llm = BedrockClientFactory.get_latency_optimized_llm_with_guardrails()

        tools = [authenticate_user]

        runnable = auth_prompt | llm.bind_tools(tools)
        super().__init__(runnable, tools)

    def __call__(self, state, config: RunnableConfig):
        result = self.runnable.invoke(state, config)

        logger.info("Auth agent invoked:", {"result": result})

        return Command(
            update={
                "messages": [result],
            }
        )


def auth_agent_next_step(state):
    """
    Determines the next step in the auth agent workflow.

    Args:
        state: The state object containing messages

    Returns:
        str: Either "auth_tool_node" or END
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
        logger.info("Auth agent next step:", {"step": "auth_tool_node"})
        return "auth_tool_node"

    logger.info("Auth agent next step:", {"step": "END"})
    return END
