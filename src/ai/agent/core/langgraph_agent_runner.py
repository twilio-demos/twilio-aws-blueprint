"""Main AI Agent Runner implementation."""

import json
from decimal import Decimal
from typing import AsyncGenerator, Awaitable, Callable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from src.ai.agent.agents.message_builder import AgentMessageBuilder
from src.ai.agent.core.agent_graph import AgentGraph
from src.ai.agent.core.agent_registry import AgentRegistry
from src.ai.agent.core.base_agent_runner import BaseAgentRunner
from src.types.models import Message, Session, StreamChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Constants
CONTENT_PREVIEW_LENGTH = 200


class AIAgentRunner(BaseAgentRunner):
    """LangGraph-based AI Agent Runner that coordinates all agents and handles user interactions."""

    def __init__(
        self,
        session: Session,
        update_language_handler: Callable[[str], Awaitable[None]],
        perform_handoff_handler: Callable[[any], Awaitable[None]],
    ):
        """
        Initialize the AI Agent Runner.

        Args:
            session: Initialized user session
            update_language_handler: ConversationRelay handler for changing language
            perform_handoff_handler: ConversationRelay handler for performing handoff
        """
        super().__init__(session)
        self.agent_graph: AgentGraph = AgentGraph()
        self.update_language_handler = update_language_handler
        self.perform_handoff_handler = perform_handoff_handler
        self.config = RunnableConfig(configurable={"thread_id": self.thread_id})
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

    def map_persisted_message(self, message: Message) -> BaseMessage:
        message_builder = AgentMessageBuilder(self.thread_id)
        message_builder.process_persisted_message(message)
        return message_builder.build_langchain_message()

    async def stream_request(
        self, user_input: str
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Process a user request with streaming responses.

        Args:
            user_input: User's input text

        Yields:
            Streaming response chunks
        """
        logger.info("Streaming request:", {"user_input": user_input})
        logger.info("=" * 60)

        try:
            if not self.agent_graph.graph.get_state(self.config).values:
                logger.info("Initializing agent state with defaults")
                self.agent_graph.graph.update_state(
                    self.config,
                    {
                        "session_id": self.session.SessionId,
                        "call_sid": self.session.CallSid,
                        "messages": list(
                            map(self.map_persisted_message, self.state["messages"])
                        ),
                        "dialog_state": self.state["dialog_state"],
                        "user_authenticated": self.session.SessionState.get(
                            "user_authenticated", False
                        ),
                        "username": self.session.SessionState.get("username", None),
                    },
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
                    logger.info(f"[Tool Result] {msg.content}", {"msg": msg})
                    if msg.name == "update_language_tool" and isinstance(
                        msg.content, str
                    ):
                        # Invoke ConversationRelay handler for update_language
                        await self.update_language_handler(msg.content)
                    elif (
                        msg.name == "perform_handoff_tool"
                        or msg.name == "update_hints_tool"
                    ) and isinstance(msg.content, str):
                        # Invoke ConversationRelay handler for perform_handoff
                        handoff_data = json.loads(msg.content)
                        await self.perform_handoff_handler(handoff_data)

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
