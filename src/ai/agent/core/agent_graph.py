"""Sample Banking Customer Support Agent built using LangGraph."""

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from src.ai.agent.agents.account_info.account_agent import (
    AccountAgent,
    account_agent_next_step,
)
from src.ai.agent.agents.account_info.account_tools import account_balance, account_info
from src.ai.agent.agents.auth.auth_agent import AuthAgent, auth_agent_next_step
from src.ai.agent.agents.auth.auth_tools import authenticate_user
from src.ai.agent.agents.kb.kb_agent import (
    KnowledgeBaseAgent,
    kb_agent_next_step,
    knowledge_base_search,
)
from src.ai.agent.agents.supervisor.supervisor_agent import SupervisorAgent
from src.ai.agent.models.state import AgentState
from src.ai.agent.tools.complete_or_escalate import complete_or_escalate_tool


# This node will be shared for exiting all specialized assistants
def pop_dialog_state(state: AgentState) -> dict:
    """Pop the dialog stack and return to the main assistant.

    This lets the full graph explicitly track the dialog flow and delegate control
    to specific sub-graphs.
    """
    messages = []
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    if tool_calls:
        # Note: Doesn't currently handle the edge case where the llm performs parallel tool calls
        messages.append(
            ToolMessage(
                content="Resuming dialog with the host assistant. Please reflect on the past conversation and assist the user as needed.",
                tool_call_id=tool_calls[0]["id"],
            )
        )
    return {
        "dialog_state": "pop",
        "messages": messages,
    }


class AgentGraph:
    """Main hierarchical workflow orchestrating specialized agents"""

    def __init__(self):
        # Initialize supervisor
        self.supervisor = SupervisorAgent()

        # Initialize specialists
        self.auth_agent = AuthAgent()
        self.auth_tool_node = ToolNode([authenticate_user, complete_or_escalate_tool])
        self.account_agent = AccountAgent()
        self.account_tool_node = ToolNode(
            [account_info, account_balance, complete_or_escalate_tool]
        )

        # Initialize KB agent and tool node
        self.kb_agent = KnowledgeBaseAgent()
        self.kb_tool_node = ToolNode([knowledge_base_search, complete_or_escalate_tool])

        # Create the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        graph = StateGraph(AgentState)  # type: ignore
        # Add all agent nodes
        graph.add_node("supervisor", self.supervisor)
        graph.add_node("auth_agent", self.auth_agent)
        graph.add_node("account_agent", self.account_agent)
        graph.add_node("kb_agent", self.kb_agent)

        graph.add_node("auth_tool_node", self.auth_tool_node)
        graph.add_node("account_tool_node", self.account_tool_node)
        graph.add_node("kb_tool_node", self.kb_tool_node)

        # Add coordination edges
        graph.add_edge(START, "supervisor")

        graph.add_conditional_edges(
            "auth_agent",
            auth_agent_next_step,
            {
                "auth_tool_node": "auth_tool_node",
                "leave_skill": "leave_skill",
                END: END,
            },
        )

        graph.add_conditional_edges(
            "account_agent",
            account_agent_next_step,
            {
                "account_tool_node": "account_tool_node",
                "leave_skill": "leave_skill",
                END: END,
            },
        )

        graph.add_conditional_edges(
            "kb_agent",
            kb_agent_next_step,
            {"kb_tool_node": "kb_tool_node", "leave_skill": "leave_skill", END: END},
        )

        graph.add_edge("auth_tool_node", "auth_agent")
        graph.add_edge("account_tool_node", "account_agent")
        graph.add_edge("kb_tool_node", "kb_agent")

        graph.add_node("leave_skill", pop_dialog_state)
        graph.add_edge("leave_skill", "supervisor")

        memory = MemorySaver()

        return graph.compile(checkpointer=memory)
