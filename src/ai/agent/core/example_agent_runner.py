"""Example implementation of a simple echo agent runner."""

from typing import Any, AsyncGenerator, Dict

from src.ai.agent.core.base_agent_runner import BaseAgentRunner
from src.types.models import StreamChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SimpleEchoAgentRunner(BaseAgentRunner):
    """
    Example implementation of a simple echo agent runner.

    This demonstrates how to create alternative agent implementations
    that inherit from BaseAgentRunner. This agent simply echoes back
    what the user said.
    """

    def __init__(self):
        """Initialize the simple echo agent runner."""
        super().__init__()
        self.initialize_agent_system()

    def initialize_agent_system(self) -> None:
        """Initialize the simple echo system."""
        logger.info("Simple echo agent system initialized")

    def get_agent_system_info(self) -> Dict[str, Any]:
        """Get information about the echo system."""
        return {
            "system_type": "SimpleEcho",
            "description": "Echoes back user input",
            "features": "Simple echo response",
        }

    async def stream_request(
        self, user_input: str, thread_id: str | None
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Process user request by echoing it back.

        Args:
            user_input: User's input text
            thread_id: Optional thread ID

        Yields:
            StreamChunk responses
        """
        logger.info(f"Processing echo request: {user_input}")

        if thread_id:
            self.update_thread_config(thread_id)

        # Create echo response
        response = "I heard you say: " + user_input

        # Emit agent type
        yield {"type": "agent", "data": "echo"}

        # Emit response content
        yield {"type": "content", "data": response}

        logger.info("Echo response completed")
