from langchain_aws import AmazonKnowledgeBasesRetriever, ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import END
from langgraph.types import Command

from src.ai.agent.core.agent_config import agent_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id=agent_config.knowledge_base_id,
    retrieval_config=agent_config.retrieval_config,
    min_score_confidence=agent_config.min_score_confidence,
    region_name=agent_config.region_name,
)


@tool
def knowledge_base_search(query: str) -> str:
    """Search the Bedrock Knowledge Base for information."""

    try:
        # Log the query for debugging
        logger.info("Knowledge base search invoked:", {"query": query})
        docs = retriever.invoke(query)
        logger.info("Knowledge base search results:", {"num_docs": len(docs)})
        return "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        logger.error("Error during knowledge base search:", {"error": str(e)})
        return "I encountered an error while searching the knowledge base."


class KnowledgeBaseAgent:
    MODEL_NAME = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    REGION_NAME = "us-east-1"

    def __init__(self):
        kb_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    """You are a knowledge base assistant. Answer user questions using the knowledge base."
                    Only use the knowledge base to answer questions. If the answer is not in the knowledge base, say "I don't know".
                    Keep answers concise and relevant to the user's query.
                    Provide answers in a friendly and professional tone.
                """
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        llm = ChatBedrockConverse(model=self.MODEL_NAME, region_name=self.REGION_NAME)
        tools = [knowledge_base_search]
        runnable = kb_prompt | llm.bind_tools(tools)
        self.runnable = runnable
        self.tools = tools

    def __call__(self, state, config: RunnableConfig):
        result = self.runnable.invoke(state, config)
        logger.info("KB agent invoked:", {"result": result})
        return Command(update={"messages": [result]})


def kb_agent_next_step(state):
    messages = state.get("messages", [])
    if not messages:
        return END
    last_message = messages[-1]
    if (
        hasattr(last_message, "tool_calls")
        and isinstance(last_message.tool_calls, list)
        and len(last_message.tool_calls) > 0
    ):
        logger.info("KB agent next step:", {"step": "kb_tool_node"})
        return "kb_tool_node"
    logger.info("KB agent next step:", {"step": "END"})
    return END
