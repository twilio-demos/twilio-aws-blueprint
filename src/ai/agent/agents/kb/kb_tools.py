from langchain_aws import AmazonKnowledgeBasesRetriever
from langchain_core.tools import tool

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
