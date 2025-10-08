"""Main AI Agent Runner implementation."""

import uuid
from decimal import Decimal
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from src.services.threadservice import instance as thread_service
from src.types.models import MessageType
from src.utils.logger import get_logger
from src.utils.message_builder import AgentMessageBuilder, create_user_message

from ..models.state import AgentState
from .agent_graph import AgentGraph

logger = get_logger(__name__)


class AIAgentRunner:
    """Main AI Agent Runner that coordinates all agents and handles user interactions."""

    def __init__(self):
        """
        Initialize the AI Agent Runner.

        Args:
            config: System configuration. If None, uses default config.
        """
        self.config = RunnableConfig(configurable={"thread_id": str(uuid.uuid4())})
        self.agent_graph = AgentGraph()
        self._session_data = {}
        self.state: AgentState = {
            "messages": [],
            "user_authenticated": False,
            "username": None,
            "current_agent": None,
            "next_agent": None,
        }
        self.thread_service = thread_service

    async def stream_request(
        self, user_input: str, thread_id: str | None
    ) -> AsyncGenerator[str, None]:
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

        # Store user message if thread_id is provided
        if thread_id is not None:
            user_message = create_user_message(thread_id, user_input)
            self.thread_service.append_rich_message(user_message)

        # Initialize message builder for agent response
        message_builder = AgentMessageBuilder(thread_id or "unknown")

        try:
            if not self.agent_graph.graph.get_state(self.config).values:
                # Initialize with defaults
                logger.info("Initializing agent state with defaults")
                self.agent_graph.graph.update_state(
                    self.config,
                    {"messages": [], "user_authenticated": False, "username": None},
                )

            # Stream the execution of the agent graph messages
            for msg, metadata in self.agent_graph.graph.stream(
                {"messages": [HumanMessage(content=user_input)]},
                self.config,
                stream_mode="messages",
            ):
                # Handle different message types
                if isinstance(msg, HumanMessage):
                    logger.info(f"[User] {msg.content}")

                elif isinstance(msg, AIMessage):
                    sender = (
                        metadata.get("langgraph_node")
                        if isinstance(metadata, dict)
                        else None
                    )

                    # Process the AI message through the message builder
                    message_builder.process_ai_message(msg, sender)

                    # Add metadata from LangGraph
                    if metadata and isinstance(metadata, dict):
                        # Convert metadata to safe types (avoid Decimal issues)

                        safe_metadata = self.convert_decimals(metadata)
                        message_builder.add_metadata(
                            "langgraph_metadata", safe_metadata
                        )

                    # Skip SupervisorAgent outputs (control messages) from streaming
                    if sender == "supervisor":
                        logger.info(f"[Supervisor] {msg.content}")
                        continue

                    # Stream the content to user
                    if isinstance(msg.content, str):
                        yield msg.content
                    elif isinstance(msg.content, list):
                        for block in msg.content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text = block["text"]
                                    yield text

                elif isinstance(msg, ToolMessage):
                    # Process tool results
                    message_builder.process_tool_message(msg)
                    logger.info(f"[Tool Result] {msg.content}")

            # Store the complete agent message if we have content and a thread_id
            if thread_id is not None and message_builder.has_content():
                agent_message = message_builder.build()
                print("agent_message:", agent_message)

                self.thread_service.append_rich_message(agent_message)
                # tool_count = (
                #     len(agent_message.RichContent.tool_calls)
                #     if agent_message.RichContent
                #     else 0
                # )
                # logger.info(f"Stored agent message with {tool_count} tool calls")

        except Exception as e:
            error_msg = f"Streaming error: {str(e)}"
            logger.error(f"❌ {error_msg}")

            # Store error message if thread_id is provided
            if thread_id is not None:
                error_message = create_user_message(thread_id, f"Error: {error_msg}")
                error_message.Type = MessageType.system
                self.thread_service.append_rich_message(error_message)

    def convert_decimals(self, obj):
        """Convert metadata to DynamoDB-safe types."""
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
