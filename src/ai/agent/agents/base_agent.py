"""Base agent class for common functionality."""

from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.ai.agent.agents.message_builder import AgentMessageBuilder
from src.services.threadservice import instance as thread_service
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    def __init__(self, runnable, tools=None, agent_name=None):
        self.runnable = runnable
        self.tools = tools or []
        self.agent_name = agent_name

    @property
    def name(self) -> str:
        """Get the agent name, defaulting to class name if not set."""
        return self.agent_name or self.__class__.__name__

    def _save_agent_message(
        self,
        result,
        config: Optional[RunnableConfig] = None,
    ):
        """Save agent message to DynamoDB"""
        # Use instance agent name if no agent_name parameter provided
        agent_name = self.agent_name or "unknown_agent"

        thread_id = config.get("configurable", {}).get("thread_id") if config else None

        if thread_id:
            # Build and save the agent message
            message_builder = AgentMessageBuilder(thread_id)
            message_builder.process_ai_message(result, agent_name)
            message_builder.finalize_streaming_blocks()

            if message_builder.has_content():
                agent_message = message_builder.build()
                logger.info(f"{agent_name} saving message to DynamoDB")
                thread_service.append_rich_message(agent_message)
            else:
                logger.warning(f"{agent_name} has no content to save")
        else:
            logger.warning(
                f"No thread_id found in config for {agent_name}, cannot save message"
            )

    @abstractmethod
    def __call__(self, state, config: RunnableConfig) -> Command:
        pass
