from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.state import AgentState
from app.tools.git_tools import git_add, git_commit


def detect_git_action(request: str) -> str:
    """Detect the Git operation requested by the user."""

    request = request.lower()

    if "commit" in request:
        return "commit"

    if "add" in request or "stage" in request:
        return "add"

    return "unknown"


def extract_files(request: str) -> list[str] | None:
    """Extract file paths from a Git add request.

    Returns None when the user wants all files.
    """

    request_lower = request.lower()

    all_keywords = [
        "all files",
        "all changes",
        "everything",
        "all",
    ]

    if any(keyword in request_lower for keyword in all_keywords):
        return None

    words = request.split()

    files = []

    for word in words:
        word = word.strip(",.")

        if "/" in word or "." in word:
            files.append(word)

    return files or None


def request_commit_message(state: AgentState):
    """Ask the user for a commit message."""

    message = interrupt(
        {
            "type": "commit_message",
            "message": "Please provide a commit message.",
        }
    )

    return {
        "messages": [
            HumanMessage(
                content=f"Commit message: {message}"
            )
        ]
    }


def request_approval(state: AgentState):
    """Ask the user before executing a Git mutation."""

    action = state["action"]
    arguments = state["arguments"]

    approval = interrupt(
        {
            "type": "approval",
            "action": action,
            "arguments": arguments,
            "message": f"Approve {action}?",
        }
    )

    return {
        "approval": approval,
    }


def start(state: AgentState):
    request = state["messages"][0].content

    action = detect_git_action(request)

    if action == "add":
        files = extract_files(request)

        return {
            "action": "git_add",
            "arguments": {
                "files": files,
            },
        }

    if action == "commit":
        return {
            "action": "git_commit",
            "arguments": {},
        }

    return {
        "action": "unknown",
        "arguments": {},
    }


def route_after_start(state: AgentState):
    if state["action"] == "git_add":
        return "approval"

    if state["action"] == "git_commit":
        return "commit_message"

    return "end"


def prepare_commit(state: AgentState):
    """Convert the supplied commit message into git_commit arguments."""

    message = state["messages"][-1].content

    message = message.replace("Commit message:", "").strip()

    return {
        "arguments": {
            "message": message,
        }
    }


def route_after_commit_message(state: AgentState):
    return "approval"


def execute_git(state: AgentState):
    """Execute the approved Git operation."""

    action = state["action"]
    arguments = state["arguments"]

    if action == "git_add":
        files = arguments.get("files")

        if files:
            result = git_add.invoke({"files": files})
        else:
            result = git_add.invoke({"files": None})

    elif action == "git_commit":
        result = git_commit.invoke(
            {
                "message": arguments["message"],
            }
        )

    else:
        result = "Unknown Git operation."

    return {
        "result": result,
    }


def route_after_approval(state: AgentState):
    if state["approval"]:
        return "execute"

    return "end"


graph_builder = StateGraph(AgentState)

graph_builder.add_node("start", start)
graph_builder.add_node("commit_message", request_commit_message)
graph_builder.add_node("prepare_commit", prepare_commit)
graph_builder.add_node("approval", request_approval)
graph_builder.add_node("execute", execute_git)

graph_builder.add_edge(START, "start")

graph_builder.add_conditional_edges(
    "start",
    route_after_start,
    {
        "approval": "approval",
        "commit_message": "commit_message",
        "end": END,
    },
)

graph_builder.add_edge(
    "commit_message",
    "prepare_commit",
)

graph_builder.add_conditional_edges(
    "prepare_commit",
    route_after_commit_message,
    {
        "approval": "approval",
    },
)

graph_builder.add_conditional_edges(
    "approval",
    route_after_approval,
    {
        "execute": "execute",
        "end": END,
    },
)

graph_builder.add_edge("execute", END)

checkpointer = InMemorySaver()

graph = graph_builder.compile(
    checkpointer=checkpointer,
)