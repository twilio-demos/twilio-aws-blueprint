from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import Command

from src.ai.agent.agents.kb.kb_tools import knowledge_base_search
from src.ai.agent.core.bedrock import BedrockClientFactory
from src.ai.agent.tools.complete_or_escalate import complete_or_escalate_tool
from src.utils.logger import get_logger

logger = get_logger(__name__)

# retriever = AmazonKnowledgeBasesRetriever(
#     knowledge_base_id=agent_config.knowledge_base_id,
#     retrieval_config=agent_config.retrieval_config,
#     min_score_confidence=agent_config.min_score_confidence,
#     region_name=agent_config.region_name,
# )


# @tool
# def knowledge_base_search(query: str) -> str:
#     """Search the Bedrock Knowledge Base for information."""

#     try:
#         # Log the query for debugging
#         logger.info("Knowledge base search invoked:", {"query": query})
#         docs = retriever.invoke(query)
#         logger.info("Knowledge base search results:", {"num_docs": len(docs)})
#         return "\n\n".join([doc.page_content for doc in docs])
#     except Exception as e:
#         logger.error("Error during knowledge base search:", {"error": str(e)})
#         return "I encountered an error while searching the knowledge base."


class KnowledgeBaseAgent:
    def __init__(self):
        kb_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a banking information specialist at Owl Bank helping customers over the phone.

                        Answer questions using only the information from the knowledge base. If you don't find the answer, simply say "I don't have that information available right now."

                        VOICE CHANNEL GUIDELINES:
                        - Keep responses brief and conversational - this is a phone call
                        - Use natural spoken language, avoid reading like a document
                        - Break complex information into digestible pieces
                        - If information is lengthy, summarize key points first

                        When to use complete_or_escalate_tool:
                        - General banking question fully answered: cancel=True, reason="Banking information provided successfully"
                        - Information not available in knowledge base after search: cancel=True, reason="Information not available, user needs further assistance"

                        If user asks about personal account details or non-banking topics:
                        - Politely redirect them to appropriate topics
                        - Do NOT use any tools for redirects, just respond with text

                        Stay friendly, professional, and concise. Focus on what the customer needs to know.
                        Do NOT mention specialists, agents, transfers or routing in your responses.
                """,
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        llm = BedrockClientFactory.get_latency_optimized_llm_with_guardrails()
        tools = [knowledge_base_search, complete_or_escalate_tool]
        runnable = kb_prompt | llm.bind_tools(tools)
        self.runnable = runnable
        self.tools = tools

    def __call__(self, state, config: RunnableConfig):
        result = self.runnable.invoke(state, config)
        logger.info("KB agent invoked:", {"result": result})
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
        hasattr(last_message, "type")
        and last_message.type == "tool"
        and hasattr(last_message, "name")
        and last_message.name == "complete_or_escalate_tool"
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
