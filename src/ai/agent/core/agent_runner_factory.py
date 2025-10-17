"""Factory for creating different types of agent runners."""

from src.ai.agent.core.base_agent_runner import BaseAgentRunner


class AgentRunnerFactory:
    """Factory for creating different types of agent runners."""

    @staticmethod
    def create_runner(runner_type: str = "langgraph") -> BaseAgentRunner:
        """
        Create an agent runner of the specified type.

        Args:
            runner_type: Type of runner to create ("langgraph" or "simple")

        Returns:
            BaseAgentRunner instance

        Raises:
            ValueError: If unknown runner type is specified
        """
        runner_type = runner_type.lower()

        if runner_type == "langgraph":
            from src.ai.agent.core.langgraph_agent_runner import AIAgentRunner

            return AIAgentRunner()
        elif runner_type == "simple":
            from src.ai.agent.core.example_agent_runner import (
                SimpleEchoAgentRunner,
            )

            return SimpleEchoAgentRunner()
        else:
            raise ValueError(
                f"Unknown runner type: {runner_type}. Supported types: 'langgraph', 'simple'"
            )

    @staticmethod
    def get_available_types() -> list[str]:
        """
        Get list of available agent runner types.

        Returns:
            List of supported runner type names
        """
        return ["langgraph", "simple"]

    @staticmethod
    def get_runner_info(runner_type: str) -> dict[str, str]:
        """
        Get information about a specific runner type.

        Args:
            runner_type: Type of runner to get info for

        Returns:
            Dictionary with runner information

        Raises:
            ValueError: If unknown runner type is specified
        """
        runner_type = runner_type.lower()

        runner_info = {
            "langgraph": {
                "name": "LangGraph Agent Runner",
                "description": "Full-featured agent system using LangGraph with multi-agent orchestration",
                "class": "AIAgentRunner",
                "features": "Complex routing, tool integration, state management",
            },
            "simple": {
                "name": "Simple Echo Runner",
                "description": "Basic echo agent that repeats user input with a prefix",
                "class": "SimpleEchoAgentRunner",
                "features": "Echo responses, minimal overhead, testing/demo purposes",
            },
        }

        if runner_type not in runner_info:
            raise ValueError(
                f"Unknown runner type: {runner_type}. Available types: {list(runner_info.keys())}"
            )

        return runner_info[runner_type]
