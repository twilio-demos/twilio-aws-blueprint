"""Main AI Agent Runner implementation."""

import uuid
from decimal import Decimal
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from src.ai.agent.core.agent_graph import AgentGraph
from src.ai.agent.core.agent_registry import AgentRegistry
from src.ai.agent.core.base_agent_runner import BaseAgentRunner
from src.services.threadservice import instance as thread_service
from src.types.models import StreamChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Constants
CONTENT_PREVIEW_LENGTH = 200


class AIAgentRunner(BaseAgentRunner):
    """LangGraph-based AI Agent Runner that coordinates all agents and handles user interactions."""

    def __init__(self):
        """
        Initialize the AI Agent Runner.
        """
        super().__init__()
        self.agent_graph: AgentGraph = AgentGraph()
        self._session_data = {}
        self.thread_service = thread_service
        # Ensure config is initialized from parent class
        if not hasattr(self, "config") or self.config is None:
            self.config = RunnableConfig(configurable={"thread_id": str(uuid.uuid4())})
        self.initialize_agent_system()

    def initialize_agent_system(self) -> None:
        """Initialize the LangGraph agent system."""
        logger.info("LangGraph agent system initialized")

    def get_agent_system_info(self) -> dict:
        """Get information about the LangGraph agent system."""
        if not self.agent_graph:
            return {"error": "Agent system not initialized"}

        return {
            "system_type": "LangGraph",
            "agents": list(self.agent_graph.agents.keys()),
            "agent_count": len(self.agent_graph.agents),
            "tool_nodes": list(self.agent_graph.tool_nodes.keys()),
            "tool_node_count": len(self.agent_graph.tool_nodes),
            "kb_enabled": self.agent_graph.kb_enabled,
        }

    async def stream_request(
        self, user_input: str, thread_id: str | None
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Process a user request with streaming responses.

        Args:
            user_input: User's input text
            thread_id: Optional thread ID for conversation tracking

        Yields:
            Streaming response chunks
        """
        logger.info("Streaming request:", {"user_input": user_input})
        logger.info("=" * 60)

        # Update config with the provided thread_id so agents use the same thread_id
        if thread_id is not None:
            self.config = RunnableConfig(configurable={"thread_id": thread_id})
            logger.info(f"Updated agent config to use thread_id: {thread_id}")

        try:
            if not self.agent_graph.graph.get_state(self.config).values:
                logger.info("Initializing agent state with defaults")
                self.agent_graph.graph.update_state(
                    self.config,
                    {"messages": [], "user_authenticated": False, "username": None},
                )

            for msg, metadata in self.agent_graph.graph.stream(
                {"messages": [HumanMessage(content=user_input)]},
                self.config,
                stream_mode="messages",
            ):
                # Log message type and source
                if isinstance(msg, AIMessage):
                    sender = (
                        metadata.get("langgraph_node")
                        if isinstance(metadata, dict)
                        else "unknown"
                    )
                    logger.info(f"Processing AIMessage from {sender}")
                    logger.debug(
                        f"AIMessage content preview: {str(msg.content)[:CONTENT_PREVIEW_LENGTH]}..."
                    )
                elif isinstance(msg, ToolMessage):
                    logger.info(f"Processing ToolMessage: {msg.name}")
                else:
                    logger.info(f"Processing {type(msg).__name__}")

                # Handle different message types
                if isinstance(msg, HumanMessage):
                    logger.debug(f"[User] {msg.content}")
                    logger.debug(
                        f"HumanMessage detected - Content: '{msg.content}', NOT saving (already saved)"
                    )

                elif isinstance(msg, AIMessage):
                    # Extract sender (reuse logic from above)
                    sender = (
                        metadata.get("langgraph_node")
                        if isinstance(metadata, dict)
                        else "unknown"
                    )

                    # Skip supervisor messages entirely - they are internal routing decisions
                    if sender == AgentRegistry.SUPERVISOR.value:
                        logger.info(f"[{AgentRegistry.SUPERVISOR.value}] {msg.content}")
                        continue

                    # Emit agent change event
                    if sender:
                        yield {"type": "agent", "data": sender}

                    # Stream metadata for evals but don't persist to DynamoDB
                    if metadata and isinstance(metadata, dict):
                        # Convert metadata to safe types (avoid Decimal issues)
                        safe_metadata = self.convert_decimals(metadata)

                        # Optionally stream full metadata for evals
                        yield {
                            "type": "metadata",
                            "data": {"agent": sender, "metadata": safe_metadata},
                        }

                    # Stream content as it arrives
                    if isinstance(msg.content, str):
                        if msg.content:  # Only stream non-empty content
                            yield {"type": "content", "data": msg.content}

                    elif isinstance(msg.content, list):
                        # Stream text content as it arrives
                        for block in msg.content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text = block.get("text", "")
                                    if text:
                                        yield {"type": "content", "data": text}

                elif isinstance(msg, ToolMessage):
                    # Log the tool result
                    logger.info(f"[Tool Result] {msg.content}")

            logger.info("🔍 Stream completed")

        except Exception as e:
            import traceback

            error_msg = f"Streaming error: {str(e)}"
            logger.error(f"{error_msg}")
            logger.error(f"Full traceback: {traceback.format_exc()}")

    def convert_decimals(self, obj):
        """
        Convert metadata to DynamoDB-safe types.

        DynamoDB requires specific data types. This method recursively converts
        numbers to Decimal objects and handles nested structures.

        Args:
            obj: The object to convert (can be dict, list, tuple, or primitive)

        Returns:
            The converted object with DynamoDB-safe types
        """
        if isinstance(obj, (int, float)):
            # Convert numbers to Decimal for DynamoDB
            return Decimal(str(obj))
        elif isinstance(obj, Decimal):
            # Already a Decimal, keep as is
            return obj
        elif isinstance(obj, dict):
            return {k: self.convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self.convert_decimals(item) for item in obj]
        else:
            return obj

    def get_session_data(self, key: str, default=None):
        """Get session-specific data."""
        return self._session_data.get(key, default)

    def set_session_data(self, key: str, value):
        """Set session-specific data."""
        self._session_data[key] = value

    def clear_session_data(self) -> None:
        """Clear all session-specific data."""
        self._session_data.clear()
