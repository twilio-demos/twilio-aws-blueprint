from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.utils.logger import get_logger

from ..base_agent import BaseAgent

logger = get_logger(__name__)


class SupervisorAgent(BaseAgent):
    def __init__(self):
        supervisor_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are the main coordinator for Owl Bank Customer Support. "
                    "Determine which specialist should handle each request: "
                    "- 'auth_agent' for authentication and user verification"
                    "- 'account_agent' for account-related inquiries such as account balance, transaction history"
                    "- 'FINISH' when conversation is complete"
                    "\nAvailable specialists: auth_agent, account_agent",
                ),
                ("placeholder", "{messages}"),
                (
                    "user",
                    "Based on the MOST RECENT conversation above, which specialist should handle this? "
                    "Respond with ONLY one of: auth_agent, account_agent, FINISH",
                ),
            ]
        )

        llm = ChatBedrockConverse(
            model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            region_name="us-east-1",
        )
        super().__init__(supervisor_prompt | llm)

    def __call__(self, state, config: RunnableConfig):
        result = self.runnable.invoke(state, config)

        if isinstance(result.content, str):
            content_text = result.content
        elif isinstance(result.content, list):
            content_text = " ".join(
                block.get("text", "")
                for block in result.content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        else:
            content_text = ""

        next_agent = content_text.strip().lower()

        if next_agent == "account_agent" and not state.get("user_authenticated", False):
            print("User not authenticated, routing to auth_agent.")
            next_agent = "auth_agent"

        if next_agent not in ["auth_agent", "account_agent", "finish"]:
            next_agent = "auth_agent"

        logger.info("SupervisorAgent decided next_agent:", {"next_agent": next_agent})

        if next_agent == "finish":
            return Command(goto=END)

        return Command(
            goto=next_agent,
        )
