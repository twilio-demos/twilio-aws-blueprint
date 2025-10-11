"""Authentication agent for handling user authentication and verification."""

from auth_tools import authenticate_user
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.ai.agent.agents.base_agent import BaseAgent
from src.ai.agent.core.bedrock import BedrockClientFactory
from src.ai.agent.tools.complete_or_escalate import complete_or_escalate_tool
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AuthAgent(BaseAgent):
    def __init__(self):
        auth_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an authentication assistant for voice interactions.

                    Your ONLY role is to verify user identity which is needed for account access. Do not answer questions about accounts, balances, transactions, or any other topics.

                    Authentication process:
                    - Collect: first name, last name, and date of birth
                    - Verify the information using authenticate_user tool
                    - Confirm success or failure
                    - ONLY Use complete_or_escalate_tool when authentication is complete. 

                    When to use complete_or_escalate_tool:
                    - Authentication successful: cancel=True, reason="Authentication completed successfully"
                    - Authentication failed after multiple attempts: cancel=True, reason="Authentication failed after verification"

                    If user asks about anything else:
                    - Politely redirect them to authentication first
                    - Do NOT use any tools, just respond with text

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
                    """,
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        llm = BedrockClientFactory.get_latency_optimized_llm_with_guardrails()

        tools = [authenticate_user, complete_or_escalate_tool]

        runnable = auth_prompt | llm.bind_tools(tools)
        super().__init__(runnable, tools)

    def __call__(self, state, config: RunnableConfig):
        result = self.runnable.invoke(state, config)

        logger.info("Auth agent invoked:", {"result": result})

        return Command(update={"messages": [result]})


def auth_agent_next_step(state):
    """
    Determines the next step in the auth agent workflow.

    Args:
        state: The state object containing messages

    Returns:
        str: Either "auth_tool_node", "complete_or_escalate_tool", or END
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
            "Auth agent escalating to supervisor after CompleteOrEscalate tool result"
        )
        return "leave_skill"

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
