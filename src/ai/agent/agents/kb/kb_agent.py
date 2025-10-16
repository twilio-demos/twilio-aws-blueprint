from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.ai.agent.agents.base_agent import BaseAgent
from src.ai.agent.agents.kb.kb_tools import knowledge_base_search
from src.ai.agent.core.bedrock_client import BedrockClientFactory
from src.ai.agent.tools.complete_or_escalate import complete_or_escalate_tool
from src.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeBaseAgent(BaseAgent):
    def __init__(self, agent_name=None):
        kb_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a knowledgeable banking specialist at Owl Bank assisting customers over the phone.

                    YOUR ROLE:
                    Answer banking questions using ONLY information retrieved from the knowledge base tool.
                    If information isn't found after searching, acknowledge you don't have that specific information available.

                    VOICE CHANNEL BEST PRACTICES:
                    - Keep responses concise and conversational (2-3 sentences typically)
                    - Use natural spoken language - avoid formal or document-like phrasing
                    - For complex topics, provide the most important point first
                    - Avoid jargon; use plain language a customer would understand on a call
                    - Don't list multiple items unless asked - summarize instead
                    

                    TOOL USAGE:
                    1. knowledge_base_search: Use when customer asks banking-related questions
                    - Search for relevant information in the knowledge base
                    - If first search doesn't yield results, try rephrasing your search query once
                    - Base your answer ONLY on retrieved information

                    2. complete_or_escalate_tool: Use in these scenarios:
                    - Successfully answered banking question: cancel=True, reason="Question answered successfully"
                    - Info not in KB after searching: cancel=True, reason="Information unavailable in knowledge base"
                    - Personal account questions asked: cancel=False, reason="Customer needs account-specific assistance"
                    - Non-banking topics asked: cancel=False, reason="Request outside banking knowledge scope"

                    HANDLING OFF-TOPIC REQUESTS:
                    If customer asks about:
                    - Personal account details (balances, transactions, passwords, etc.)
                    - Non-banking topics
                    - Requests requiring account access or actions

                    IMMEDIATELY call complete_or_escalate_tool with cancel=False and appropriate reason.
                    Do NOT answer these requests yourself - they need to be routed elsewhere.

                    IMPORTANT:
                    - Never mention "agents," "specialists," "transfers," or "routing" in your responses
                    - Never fabricate information not found in the knowledge base
                    - Stay helpful, warm, and professional
                    """,
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        llm = BedrockClientFactory.get_latency_optimized_llm_with_guardrails()
        tools = [knowledge_base_search, complete_or_escalate_tool]
        runnable = kb_prompt | llm.bind_tools(tools)
        super().__init__(runnable, tools, agent_name)

    def __call__(self, state, config: RunnableConfig):
        result = self.runnable.invoke(state, config)
        logger.info("KB agent invoked:", {"result": result})

        # Save agent message to DynamoDB
        self._save_agent_message(result, config)

        return Command(update={"messages": [result]})


def kb_agent_next_step(state):
    """
    Determines the next step in the KB agent workflow.

    Args:
        state: The state object containing messages

    Returns:
        str: Either "kb_tool_node", "supervisor", or END
    """
    messages = state.get("messages", [])
    if not messages:
        return END
    last_message = messages[-1]

    # Check if we just processed a CompleteOrEscalate tool result
    if (
        hasattr(last_message, "tool_calls")
        and isinstance(last_message.tool_calls, list)
        and len(last_message.tool_calls) > 0
        and last_message.tool_calls[0]["name"] == "complete_or_escalate_tool"
    ):
        logger.info(
            "KB agent escalating to supervisor after CompleteOrEscalate tool result"
        )
        return "leave_skill"

    if (
        hasattr(last_message, "tool_calls")
        and isinstance(last_message.tool_calls, list)
        and len(last_message.tool_calls) > 0
    ):
        logger.info("KB agent next step:", {"step": "kb_tool_node"})
        return "kb_tool_node"
    logger.info("KB agent next step:", {"step": "END"})
    return END
