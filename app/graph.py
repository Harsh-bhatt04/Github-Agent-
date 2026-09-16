from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt

from app.config import GOOGLE_API_KEY
from app.state import AgentState
from app.tools.git_tools import git_add, git_commit, git_diff, git_status


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GOOGLE_API_KEY,
)

tools = [git_status, git_diff, git_add, git_commit]

llm_with_tools = llm.bind_tools(tools)


def agent(state: AgentState):
    messages = [
        SystemMessage(
            content=(
                "You are a Git assistant.\n\n"
                "Git add rules:\n"
                "- If the user asks to add or stage all files, call git_add "
                "without specifying files.\n"
                "- If the user specifies file paths, call git_add with only "
                "those files.\n"
                "- Never stage unspecified files.\n\n"
                "Git commit rules:\n"
                "- If the user asks to commit and provides a commit message, "
                "call git_commit with that message.\n"
                "- If the user asks to commit but does not provide a message, "
                "do not invent one."
            )
        ),
        *state["messages"],
    ]

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response],
    }


def request_commit_message(state: AgentState):
    commit_message = interrupt(
        {
            "type": "commit_message",
            "message": "Please provide a commit message.",
        }
    )

    return {
        "messages": [
            HumanMessage(
                content=f"Use this commit message: {commit_message}"
            )
        ]
    }


def approval(state: AgentState):
    last_message = state["messages"][-1]

    tool_call = last_message.tool_calls[0]

    approval_result = interrupt(
        {
            "type": "approval",
            "action": tool_call["name"],
            "arguments": tool_call["args"],
            "message": f"Approve {tool_call['name']}?",
        }
    )

    return {
        "approval": approval_result,
    }


def route_after_agent(state: AgentState):
    last_message = state["messages"][-1]

    if not last_message.tool_calls:
        original_request = state["messages"][0].content.lower()

        if "commit" in original_request:
            return "commit_message"

        return "end"

    tool_name = last_message.tool_calls[0]["name"]

    if tool_name in {"git_add", "git_commit"}:
        return "approval"

    return "tools"


def route_after_approval(state: AgentState):
    if state["approval"]:
        return "tools"

    return "end"


tool_node = ToolNode(tools)

graph_builder = StateGraph(AgentState)

graph_builder.add_node("agent", agent)
graph_builder.add_node("commit_message", request_commit_message)
graph_builder.add_node("approval", approval)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "agent")

graph_builder.add_conditional_edges(
    "agent",
    route_after_agent,
    {
        "commit_message": "commit_message",
        "approval": "approval",
        "tools": "tools",
        "end": END,
    },
)

graph_builder.add_edge("commit_message", "agent")

graph_builder.add_conditional_edges(
    "approval",
    route_after_approval,
    {
        "tools": "tools",
        "end": END,
    },
)

graph_builder.add_edge("tools", "agent")

checkpointer = InMemorySaver()

graph = graph_builder.compile(
    checkpointer=checkpointer,
)