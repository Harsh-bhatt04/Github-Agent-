from langchain_core.messages import SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import GOOGLE_API_KEY
from app.state import AgentState


MUTATING_TOOLS = {
    "git_add",
    "git_commit",
    "git_push",
}


SYSTEM_PROMPT = """
You are a Git assistant working with Git operations through MCP tools.

Available Git operations:
- git_status: read the current Git status
- git_diff: read the current Git diff
- git_add: stage files
- git_commit: create a commit
- git_push: push commits

Rules:

1. ADD / STAGE
- "add all changes", "stage everything", or similar:
  call git_add with files omitted/null.
- If the user specifies files:
  call git_add with exactly those file paths.
- Never stage files the user did not request.

2. COMMIT
- If the user provides a commit message, use that exact message.
- Never invent a commit message.
- If the user asks to commit but does not provide a message,
  call git_commit with message=null.
  The application will ask the human for the message.
- "commit all changes" means make sure the changes are staged
  before committing.

3. PUSH
- A push is a mutating operation.
- Never push without human approval.

4. TOOL USAGE
- Use one MCP tool at a time.
- Do not execute multiple Git mutations in parallel.
- After a successful git_commit or git_push, stop.
- Do not repeat a successful mutation.

5. HUMAN APPROVAL
- The application handles human approval for mutating operations.
- Do not pretend that an operation was executed before the
  application actually executes the MCP tool.
"""


async def build_graph():
    """
    Connect LangGraph to the MCP server and build the agent graph.
    """

    # LangGraph acts as an MCP client.
    mcp_client = MultiServerMCPClient(
        {
            "github": {
                "transport": "stdio",
                "command": "uv",
                "args": [
                    "run",
                    "python",
                    "-m",
                    "app.server",
                ],
            }
        }
    )

    # Get the tools exposed by app/server.py
    mcp_tools = await mcp_client.get_tools()

    # Make MCP tools available to the LLM.
    tool_map = {tool.name: tool for tool in mcp_tools}

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GOOGLE_API_KEY,
    )

    llm_with_tools = llm.bind_tools(mcp_tools)

    async def agent(state: AgentState):
        """
        Ask the LLM what MCP operation should happen next.
        """

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        response = await llm_with_tools.ainvoke(messages)

        return {
            "messages": [response],
        }

    def prepare_tool(state: AgentState):
        """
        Extract the MCP tool call selected by the LLM.
        """

        last_message = state["messages"][-1]

        if not last_message.tool_calls:
            return {}

        tool_call = last_message.tool_calls[0]

        return {
            "action": tool_call["name"],
            "arguments": tool_call["args"],
            "tool_call_id": tool_call["id"],
            "approval": False,
        }

    def route_after_agent(state: AgentState):
        """
        Decide whether the agent wants to call a tool.
        """

        last_message = state["messages"][-1]

        if not last_message.tool_calls:
            return "end"

        return "prepare_tool"

    def route_after_prepare(state: AgentState):
        """
        Decide whether the selected MCP tool needs:
        - commit message
        - human approval
        - direct execution
        """

        action = state["action"]
        arguments = state["arguments"]

        # Commit requested without a message.
        if action == "git_commit" and not arguments.get("message"):
            return "commit_message"

        # Mutating operations require approval.
        if action in MUTATING_TOOLS:
            return "approval"

        # Read-only MCP tools can execute immediately.
        return "execute"

    def request_commit_message(state: AgentState):
        """
        Ask the human for the commit message.
        """

        message = interrupt(
            {
                "type": "commit_message",
                "message": "Enter the commit message:",
            }
        )

        if not isinstance(message, str) or not message.strip():
            return {
                "result": "Commit cancelled: commit message was empty."
            }

        arguments = dict(state["arguments"])
        arguments["message"] = message.strip()

        return {
            "arguments": arguments,
        }

    def route_after_commit_message(state: AgentState):
        """
        Once the commit message is supplied, the commit still
        requires human approval.
        """

        return "approval"

    def request_approval(state: AgentState):
        """
        Ask the human before executing a mutating MCP tool.
        """

        approval = interrupt(
            {
                "type": "approval",
                "action": state["action"],
                "arguments": state["arguments"],
                "message": (
                    f"Approve execution of "
                    f"{state['action']}?"
                ),
            }
        )

        return {
            "approval": approval is True,
        }

    def route_after_approval(state: AgentState):
        if state["approval"]:
            return "execute"

        return "cancelled"

    async def execute_tool(state: AgentState):
        """
        Execute the selected MCP tool only after all required
        HITL checks have passed.
        """

        action = state["action"]
        arguments = state["arguments"]
        tool_call_id = state["tool_call_id"]

        tool = tool_map.get(action)

        if tool is None:
            result = f"MCP tool '{action}' was not found."

            return {
                "messages": [
                    ToolMessage(
                        content=result,
                        tool_call_id=tool_call_id,
                        name=action,
                    )
                ],
                "result": result,
            }

        try:
            tool_result = await tool.ainvoke(arguments)
            result = str(tool_result)

        except Exception as exc:
            result = f"Error executing MCP tool '{action}': {exc}"

        return {
            "messages": [
                ToolMessage(
                    content=result,
                    tool_call_id=tool_call_id,
                    name=action,
                )
            ],
            "result": result,
        }

    def route_after_execute(state: AgentState):
        """
        Stop after final mutations.

        For git_add, return to the agent because the user may
        have asked for a larger operation such as:
        'commit all changes'.
        """

        if state["action"] in {"git_commit", "git_push"}:
            return "end"

        return "agent"

    def cancelled(state: AgentState):
        return {
            "result": f"{state['action']} cancelled by human."
        }

    builder = StateGraph(AgentState)

    builder.add_node("agent", agent)
    builder.add_node("prepare_tool", prepare_tool)
    builder.add_node("commit_message", request_commit_message)
    builder.add_node("approval", request_approval)
    builder.add_node("execute", execute_tool)
    builder.add_node("cancelled", cancelled)

    builder.add_edge(START, "agent")

    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "prepare_tool": "prepare_tool",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "prepare_tool",
        route_after_prepare,
        {
            "commit_message": "commit_message",
            "approval": "approval",
            "execute": "execute",
        },
    )

    builder.add_conditional_edges(
        "commit_message",
        route_after_commit_message,
        {
            "approval": "approval",
        },
    )

    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "execute": "execute",
            "cancelled": "cancelled",
        },
    )

    builder.add_edge("cancelled", END)

    builder.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "agent": "agent",
            "end": END,
        },
    )

    checkpointer = InMemorySaver()

    return builder.compile(
        checkpointer=checkpointer
    )