"""Base agent class for common functionality."""

from abc import ABC, abstractmethod

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command


class BaseAgent(ABC):
    def __init__(self, runnable, tools=None):
        self.runnable = runnable
        self.tools = tools or []

    @abstractmethod
    def __call__(self, state, config: RunnableConfig) -> Command:
        pass
