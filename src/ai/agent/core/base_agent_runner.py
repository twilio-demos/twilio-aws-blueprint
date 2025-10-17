"""Base abstract class for Agent Runner implementations."""

import uuid
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional

from langchain_core.runnables import RunnableConfig

from src.ai.agent.models.state import AgentState
from src.types.models import StreamChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgentRunner(ABC):
    """Abstract base class for AI Agent Runners that coordinate agents and handle user interactions."""

    def __init__(self, config: Optional[RunnableConfig] = None):
        """
        Initialize the Base Agent Runner.

        Args:
            config: System configuration. If None, creates default config.
        """
        self.config = config or RunnableConfig(
            configurable={"thread_id": str(uuid.uuid4())}
        )
        self.state: AgentState = {
            "messages": [],
            "user_authenticated": False,
            "username": None,
            "dialog_state": [],
        }

    @abstractmethod
    def stream_request(
        self, user_input: str, thread_id: str | None
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Process a user request with streaming responses.

        Args:
            user_input: User's input text
            thread_id: Optional thread ID for conversation tracking

        Yields:
            Streaming response chunks

        This method must be implemented by concrete agent runner classes.
        """
        pass

    @abstractmethod
    def initialize_agent_system(self) -> None:
        """
        Initialize the agent system (graph, registry, etc.).

        This method should set up whatever agent architecture the
        concrete implementation uses (LangGraph, custom routing, etc.).
        """
        pass

    @abstractmethod
    def get_agent_system_info(self) -> Dict[str, Any]:
        """
        Get information about the current agent system.

        Returns:
            Dict containing information about agents, tools, etc.
        """
        pass

    def update_thread_config(self, thread_id: str) -> None:
        """
        Update the runner configuration with a new thread ID.

        Args:
            thread_id: The thread ID to use for agent interactions
        """
        self.config = RunnableConfig(configurable={"thread_id": thread_id})
        logger.info(f"Updated agent config to use thread_id: {thread_id}")

    @property
    def thread_id(self) -> Optional[str]:
        """Get the current thread ID from config."""
        return (
            self.config.get("configurable", {}).get("thread_id")
            if self.config
            else None
        )
