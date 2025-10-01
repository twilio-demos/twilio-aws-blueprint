"""Sample Banking Customer Support Agent built using LangGraph."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from ..agents.account_info.account_agent import AccountAgent, account_agent_next_step
from ..agents.account_info.account_tools import account_balance, account_info
from ..agents.auth.auth_agent import AuthAgent, auth_agent_next_step
from ..agents.auth.auth_tools import authenticate_user
from ..agents.supervisor.supervisor_agent import SupervisorAgent
from ..models.state import AgentState


class AgentGraph:
    """Main hierarchical workflow orchestrating specialized agents"""

    def __init__(self):
        # Initialize supervisor
        self.supervisor = SupervisorAgent()

        # Initialize specialists
        self.auth_agent = AuthAgent()
        self.auth_tool_node = ToolNode([authenticate_user])
        self.account_agent = AccountAgent()
        self.account_tool_node = ToolNode([account_info, account_balance])

        # Create the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        graph = StateGraph(AgentState)
        # Add all agent nodes
        graph.add_node("supervisor", self.supervisor)
        graph.add_node("auth_agent", self.auth_agent)
        graph.add_node("account_agent", self.account_agent)

        graph.add_node("auth_tool_node", self.auth_tool_node)
        graph.add_node("account_tool_node", self.account_tool_node)

        # Add coordination edges
        graph.add_edge(START, "supervisor")

        graph.add_conditional_edges(
            "auth_agent",
            auth_agent_next_step,
            {"auth_tool_node": "auth_tool_node", END: END},
        )

        graph.add_conditional_edges(
            "account_agent",
            account_agent_next_step,
            {"account_tool_node": "account_tool_node", END: END},
        )

        graph.add_edge("auth_tool_node", "auth_agent")
        graph.add_edge("account_tool_node", "account_agent")

        memory = MemorySaver()

        return graph.compile(checkpointer=memory)
