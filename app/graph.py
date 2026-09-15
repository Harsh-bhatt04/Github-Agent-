from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from langgraph.checkpoint.memory import InMemorySaver

from app.state import AgentState
from app.tools.git_tools import git_add


def inspect_request(state: AgentState):
    """Determine which files need to be staged."""

    print(f"User request: {state['user_request']}")

    return {
        "files": ["app/tools/git_tools.py"],
    }


def ask_approval(state: AgentState):
    """Pause execution and ask the human for approval."""

    approval = interrupt(
        {
            "action": "git_add",
            "files": state["files"],
            "message": f"Approve staging {state['files']}?",
        }
    )

    return {
        "approval": approval,
    }


def execute_git_add(state: AgentState):
    """Execute git add after human approval."""

    result = git_add(state["files"])

    return {
        "result": result,
    }


def route_after_approval(state: AgentState):
    """Route execution based on human approval."""

    if state["approval"]:
        return "approved"

    return "rejected"


graph_builder = StateGraph(AgentState)

graph_builder.add_node("inspect", inspect_request)
graph_builder.add_node("approval", ask_approval)
graph_builder.add_node("git_add", execute_git_add)

graph_builder.set_entry_point("inspect")

graph_builder.add_edge("inspect", "approval")

graph_builder.add_conditional_edges(
    "approval",
    route_after_approval,
    {
        "approved": "git_add",
        "rejected": END,
    },
)

graph_builder.add_edge("git_add", END)

checkpointer = InMemorySaver()

graph = graph_builder.compile(
    checkpointer=checkpointer
)