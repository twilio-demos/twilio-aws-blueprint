"""Main AI Agent Runner implementation."""

import uuid
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from src.utils.logger import get_logger

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
        }

    async def stream_request(self, user_input: str) -> AsyncGenerator[str, None]:
        """
        Process a user request with streaming responses.

        Args:
            user_input: User's input text

        Yields:
            Streaming response chunks
        """
        logger.info("Streaming request:", {"user_input": user_input})
        logger.info("=" * 60)

        # Create initial state
        # initial_state = self.graph.create_initial_state(user_input)

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
                    # Skip SupervisorAgent outputs (control messages)
                    if sender == "supervisor":
                        logger.info(f"[Supervisor] {msg.content}")
                        continue

                    # AI can emit text, chunks, or tool_use calls
                    if isinstance(msg.content, str):
                        yield msg.content
                    elif isinstance(msg.content, list):
                        for block in msg.content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text = block["text"]
                                    yield text

            # current_state = self.agent_graph.graph.get_state(self.config)

            # for k in AgentState.__annotations__:
            #     if k in current_state.values:
            #         self.state[k] = current_state.values[k]

        except Exception as e:
            error_msg = f"Streaming error: {str(e)}"
            logger.error(f"❌ {error_msg}")
