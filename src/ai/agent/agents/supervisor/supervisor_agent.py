from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.utils.logger import get_logger

from ...core.bedrock import BedrockClientFactory
from ..base_agent import BaseAgent

logger = get_logger(__name__)


class SupervisorAgent(BaseAgent):
    MODEL_NAME = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    REGION_NAME = "us-east-1"

    def __init__(self):
        supervisor_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                    You are the main coordinator for Owl Bank Customer Support on a voice call.

                    Your role is to silently route requests to the appropriate specialist based on the customer's needs. 
                    Do NOT mention specialists, agents, or routing in your responses.

                    Route requests as follows:
                    - 'auth_agent' for identity verification
                    - 'account_agent' for account inquiries (balance, transactions, account details)
                    - 'kb_agent' ONLY for general banking information like FDIC coverage
                    - 'FINISH' when the customer's request is complete and conversation should end

                    VOICE CHANNEL GUIDELINES:
                    - Keep responses brief and conversational
                    - Use natural spoken language
                    - Avoid technical jargon or mentioning internal processes
                    - The customer should never know they're being routed between specialists

                    Based on the MOST RECENT exchange, which specialist should handle this?
                    Respond with ONLY one of: auth_agent, account_agent, kb_agent, FINISH""",
                ),
                ("placeholder", "{messages}"),
            ]
        )

        llm = BedrockClientFactory.get_latency_optimized_llm_with_guardrails()

        super().__init__(supervisor_prompt | llm)

    def __call__(self, state, config: RunnableConfig):
        if state.get("current_agent"):
            logger.info(
                "SupervisorAgent routing to current agent:",
                {"current_agent": state["current_agent"]},
            )
            return Command(
                goto=state["current_agent"],
            )

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
            return Command(
                goto="auth_agent",
                update={"next_agent": next_agent, "current_agent": "auth_agent"},
            )

        # TODO: Add more robust validation, possibly using route to a general_agent
        if next_agent not in ["auth_agent", "account_agent", "kb_agent", "finish"]:
            next_agent = "auth_agent"

        logger.info("SupervisorAgent decided next_agent:", {"next_agent": next_agent})

        if next_agent == "finish":
            return Command(goto=END)

        return Command(
            goto=next_agent,
            update={"next_agent": None, "current_agent": next_agent},
        )
