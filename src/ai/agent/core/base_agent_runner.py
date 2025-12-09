"""Base abstract class for Agent Runner implementations."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict

from src.ai.agent.models.state import BaseAgentState
from src.services.threadservice import instance as thread_service
from src.types.models import Session, StreamChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgentRunner(ABC):
    """Abstract base class for AI Agent Runners that coordinate agents and handle user interactions."""

    def __init__(self, session: Session):
        """
        Initialize the Base Agent Runner.

        Args:
            session: Initialized user session
        """
        self.session = session
        self.state: BaseAgentState = {
            "messages": thread_service.get(self.session),
            "dialog_state": [],
        }

    @abstractmethod
    def stream_request(self, user_input: str) -> AsyncGenerator[StreamChunk, None]:
        """
        Process a user request with streaming responses.

        Args:
            user_input: User's input text

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

    @property
    def thread_id(self) -> str:
        """Get the current thread ID from config."""
        return self.session.ThreadId
