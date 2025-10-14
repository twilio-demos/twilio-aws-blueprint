"""Main AI Agent Runner implementation."""

import uuid
from decimal import Decimal
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from src.ai.agent.core.agent_graph import AgentGraph
from src.ai.agent.models.state import AgentState
from src.services.threadservice import instance as thread_service
from src.types.models import MessageType, StreamChunk
from src.utils.logger import get_logger
from src.utils.message_builder import create_user_message

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
            "dialog_state": [],
        }
        self.thread_service = thread_service

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
            logger.info(f"🔗 Updated agent config to use thread_id: {thread_id}")

        # User message saving is handled by the websocket handler
        # Agent runner focuses on AI processing and agent message saving

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
                        f"AIMessage content preview: {str(msg.content)[:200]}..."
                    )
                elif isinstance(msg, ToolMessage):
                    logger.info(f"Processing ToolMessage: {msg.name}")
                else:
                    logger.info(f"Processing {type(msg).__name__}")

                # Write message and metadata to debug file
                self._write_debug_info(msg, metadata)

                # Handle different message types
                if isinstance(msg, HumanMessage):
                    logger.info(f"[User] {msg.content}")
                    logger.info(
                        f"HumanMessage detected - Content: '{msg.content}', NOT saving (already saved)"
                    )

                elif isinstance(msg, AIMessage):
                    sender = None
                    if metadata:
                        if isinstance(metadata, dict):
                            sender = metadata.get("langgraph_node")
                        else:
                            logger.warning(
                                f"Expected metadata to be dict, got {type(metadata)}: {metadata}"
                            )

                    # Skip supervisor messages entirely - they are internal routing decisions
                    if sender == "supervisor":
                        logger.info(f"[Supervisor] {msg.content}")
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

            if thread_id is not None:
                error_message = create_user_message(thread_id, f"Error: {error_msg}")
                error_message.Type = MessageType.system
                # self.thread_service.append_rich_message(error_message)

    def _write_debug_info(self, msg, metadata):
        """Write message and metadata to debug file."""
        import json
        from datetime import datetime

        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "message": {
                "type": type(msg).__name__,
                "content": str(msg.content) if hasattr(msg, "content") else str(msg),
                "tool_calls": getattr(msg, "tool_calls", None),
                "additional_kwargs": getattr(msg, "additional_kwargs", None),
            },
            "metadata": metadata,
        }

        try:
            with open("debug_messages.jsonl", "a") as f:
                f.write(json.dumps(debug_data, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write debug info: {e}")

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
