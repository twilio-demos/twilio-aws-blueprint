from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.ai.agent.agents.base_agent import BaseAgent
from src.ai.agent.core.agent_config import agent_config
from src.ai.agent.core.agent_registry import AgentRegistry
from src.ai.agent.core.bedrock_client import BedrockClientFactory
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SupervisorAgent(BaseAgent):
    def __init__(self, agent_name=None):
        # Check if KB agent is available
        kb_enabled = bool(agent_config.knowledge_base_id)

        # Build routing instructions based on available agents
        routing_instructions = f"""Route requests as follows:
                    - '{AgentRegistry.AUTH_AGENT.value}' for identity verification
                    - '{AgentRegistry.ACCOUNT_AGENT.value}' for account inquiries (balance, transactions, account details)"""

        if kb_enabled:
            routing_instructions += f"""
                    - '{AgentRegistry.KB_AGENT.value}' ONLY for general banking information like FDIC coverage"""

        routing_instructions += """
                    - 'FINISH' when the customer's request is complete and conversation should end"""

        # Build valid agent list for validation using enum
        valid_agents = [
            AgentRegistry.AUTH_AGENT.value,
            AgentRegistry.ACCOUNT_AGENT.value,
            "finish",
        ]
        if kb_enabled:
            valid_agents.append(AgentRegistry.KB_AGENT.value)

        self.valid_agents = valid_agents
        self.kb_enabled = kb_enabled

        supervisor_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"""
                    You are the main coordinator for Owl Bank Customer Support on a voice call.

                    Your role is to silently route requests to the appropriate specialist based on the customer's needs. 
                    Do NOT mention specialists, agents, or routing in your responses.

                    {routing_instructions}

                    IMPORTANT: Check the conversation for any tool calls. If you see that the complete_or_escalate_tool was called by a specialist and question was answered
                    respond with "FINISH" to end the conversation appropriately.

                    VOICE CHANNEL GUIDELINES:
                    - Keep responses brief and conversational
                    - Use natural spoken language
                    - Avoid technical jargon or mentioning internal processes
                    - The customer should never know they're being routed between specialists

                    Based on the MOST RECENT user message AND the conversation context, which specialist should handle this?
                    Respond with one of: {", ".join(valid_agents)} or "FINISH" to end the conversation.""",
                ),
                ("placeholder", "{messages}"),
            ]
        )

        llm = BedrockClientFactory.get_latency_optimized_llm_with_guardrails()

        super().__init__(supervisor_prompt | llm, agent_name=agent_name)

    def __call__(self, state, config: RunnableConfig):
        dialog_state = None
        user_authenticated = False
        if isinstance(state, dict):
            dialog_state = state.get("dialog_state", [])
            user_authenticated = state.get("user_authenticated", False)
        else:
            logger.warning(f"Expected state to be dict, got {type(state)}: {state}")
            dialog_state = []

        if dialog_state and dialog_state[-1] != "supervisor":
            logger.info(
                "SupervisorAgent routing to current agent:",
                {"current_agent": dialog_state[-1]},
            )
            return Command(
                goto=dialog_state[-1],
            )

        result = self.runnable.invoke(state, config)

        # CHECK IF GUARDRAILS WERE INVOKED
        if hasattr(result, "response_metadata"):
            trace = result.response_metadata.get("trace", {})
            guardrail = trace.get("guardrail", {})
            if guardrail:
                input_assessment = guardrail.get("inputAssessment", {})
                for policy_id, policy_data in input_assessment.items():
                    content_policy = policy_data.get("contentPolicy", {})
                    filters = content_policy.get("filters", [])
                    for filter_item in filters:
                        if filter_item.get("action") == "BLOCKED":
                            logger.warning(
                                "Guardrails blocked input - ending conversation turn",
                                {
                                    "filter_type": filter_item.get("type"),
                                    "confidence": filter_item.get("confidence"),
                                },
                            )
                            # End the turn
                            return Command(goto=END)

        if isinstance(result.content, str):
            content_text = result.content
        elif isinstance(result.content, list):
            text_blocks = []
            for block in result.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_blocks.append(block.get("text", ""))
            content_text = " ".join(text_blocks)
        else:
            content_text = ""

        next_agent = content_text.strip().lower()

        logger.info(
            "SupervisorAgent raw next_agent response:", {"next_agent": next_agent}
        )

        if next_agent == "finish" or next_agent == "__end__":
            return Command(goto=END)

        if next_agent == AgentRegistry.ACCOUNT_AGENT.value and not user_authenticated:
            print("User not authenticated, routing to auth_agent.")
            return Command(
                goto=AgentRegistry.AUTH_AGENT.value,
                update={
                    "messages": [
                        "User needs to be authenticated before they can access the account information."
                    ],
                    "dialog_state": dialog_state + [AgentRegistry.AUTH_AGENT.value],
                },
            )

        # Validate agent using enum
        if next_agent not in self.valid_agents:
            next_agent = AgentRegistry.AUTH_AGENT.value

        logger.info("SupervisorAgent decided next_agent:", {"next_agent": next_agent})

        return Command(
            goto=next_agent,
            update={"dialog_state": dialog_state + [next_agent]},
        )
