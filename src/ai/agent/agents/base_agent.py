"""Base agent class for common functionality."""

from abc import ABC, abstractmethod

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from src.services.threadservice import instance as thread_service
from src.utils.logger import get_logger
from src.utils.message_builder import AgentMessageBuilder

logger = get_logger(__name__)


class BaseAgent(ABC):
    def __init__(self, runnable, tools=None):
        self.runnable = runnable
        self.tools = tools or []

    def _save_agent_message(self, result, agent_name: str, config: RunnableConfig):
        """Save agent message to DynamoDB"""
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
