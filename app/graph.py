from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from app.config import GOOGLE_API_KEY
from app.state import AgentState
from app.tools.git_tools import git_add


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GOOGLE_API_KEY,
)


def inspect_request(state: AgentState):
    """Use the LLM to identify files requested by the user."""

    prompt = f"""
You are a Git assistant.

User request:
{state["user_request"]}

Identify the files the user wants to stage.

Return ONLY a comma-separated list of file paths.
Do not explain anything.

Example:
app/server.py, app/state.py
"""

    response = llm.invoke(prompt)

    files = [
        file.strip()
        for file in response.content.split(",")
        if file.strip()
    ]

    return {
        "files": files,
    }


def ask_approval(state: AgentState):
    """Ask the human before modifying the repository."""

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
    """Execute git add after approval."""

    result = git_add(state["files"])

    return {
        "result": result,
    }


def route_after_approval(state: AgentState):
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