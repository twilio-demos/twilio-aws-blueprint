"""Sample Banking Customer Support Agent built using LangGraph."""

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from src.ai.agent.core.agent_config import agent_config
from src.ai.agent.core.agent_registry import AgentRegistry
from src.ai.agent.models.state import AIAgentState
from src.ai.agent.tools import __all__ as all_custom_tools
from src.utils.logger import get_logger

logger = get_logger(__name__)


# This node will be shared for exiting all specialized assistants
def pop_dialog_state(state: AIAgentState) -> Command:
    """Pop the dialog stack and return to the main assistant.

    This lets the full graph explicitly track the dialog flow and delegate control
    to specific sub-graphs.
    """

    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    if tool_calls:
        # Note: Doesn't currently handle the edge case where the llm performs parallel tool calls
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="Resuming dialog with the supervisor assistant.",
                        tool_call_id=tool_calls[0]["id"],
                    )
                ],
                "dialog_state": "pop",
            }
        )

    return Command(update={"dialog_state": "pop"})


class AgentGraph:
    """Main hierarchical workflow orchestrating specialized agents"""

    LEAVE_SKILL_NODE = "leave_skill"

    def __init__(self):
        # Check if KB is enabled
        self.kb_enabled = bool(agent_config.knowledge_base_id)

        # Initialize agents dynamically using enum
        self.agents = {}
        self.tool_nodes = {}

        self._initialize_agents()

        # Create the graph
        self.graph = self._build_graph()

    def _initialize_agents(self):
        """Initialize all agents and tool nodes based on agent registry."""
        for agent_registry in AgentRegistry:
            # Skip KB agent if not enabled
            if agent_registry == AgentRegistry.KB_AGENT and not self.kb_enabled:
                logger.warning(
                    "Knowledge Base agent disabled: BEDROCK_KB_ID not configured"
                )
                continue

            # Create agent instance
            agent_instance = agent_registry.create_agent_instance()
            if agent_instance:
                self.agents[agent_registry.value] = agent_instance

                # Create tool node if agent has tools
                tools = agent_registry.tools
                if tools:
                    # Add common tools to all agent tool nodes
                    all_tools = tools + all_custom_tools
                    tool_node_name = agent_registry.tool_node_name
                    if tool_node_name:
                        self.tool_nodes[tool_node_name] = ToolNode(all_tools)

    def _build_graph(self) -> CompiledStateGraph:
        graph = StateGraph(AIAgentState)  # type: ignore

        # Add all agent nodes dynamically
        for agent_name, agent_instance in self.agents.items():
            graph.add_node(agent_name, agent_instance)

        # Add all tool nodes dynamically
        for tool_name, tool_node in self.tool_nodes.items():
            graph.add_node(tool_name, tool_node)

        # Add special nodes
        graph.add_node(self.LEAVE_SKILL_NODE, pop_dialog_state)

        # Set entry point
        graph.add_edge(START, AgentRegistry.SUPERVISOR.value)

        # Add conditional edges dynamically based on agent registry configuration
        self._add_conditional_edges(graph)

        # Add tool edges
        self._add_tool_edges(graph)

        # Add leave_skill edge
        graph.add_edge(self.LEAVE_SKILL_NODE, AgentRegistry.SUPERVISOR.value)

        memory = MemorySaver()
        return graph.compile(checkpointer=memory)

    def _add_conditional_edges(self, graph):
        """Add conditional edges based on agent configuration."""
        for agent_registry in AgentRegistry:
            if agent_registry.value not in self.agents:
                continue  # Skip disabled agents

            next_step_func = agent_registry.next_step_function
            if next_step_func:
                # Build routing map
                routing_map = {}

                # Add tool node routing if exists
                tool_node_name = agent_registry.tool_node_name
                if tool_node_name and tool_node_name in self.tool_nodes:
                    routing_map[tool_node_name] = tool_node_name

                # Add leave_skill routing
                routing_map[self.LEAVE_SKILL_NODE] = self.LEAVE_SKILL_NODE
                routing_map[END] = END

                graph.add_conditional_edges(
                    agent_registry.value, next_step_func, routing_map
                )

    def _add_tool_edges(self, graph):
        """Add edges from tool nodes back to their corresponding agents."""
        for agent_registry in AgentRegistry:
            tool_node_name = agent_registry.tool_node_name
            if (
                tool_node_name
                and tool_node_name in self.tool_nodes
                and agent_registry.value in self.agents
            ):
                graph.add_edge(tool_node_name, agent_registry.value)
