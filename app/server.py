
from typing import Annotated

from pydantic import BaseModel, Field

from mcp.server import MCPServer
from mcp.server.mcpserver import Elicit, Resolve

from app.tools.git_tools import (
    git_add as run_git_add,
    git_commit as run_git_commit,
    git_diff as run_git_diff,
    git_push as run_git_push,
    git_status as run_git_status,
)


mcp = MCPServer("GitHub MCP Server")

class CommitMessage(BaseModel):
    message: str = Field(
        description="The commit message to use."
    )


class Approval(BaseModel):
    approved: bool = Field(
        description="Approve or reject the Git operation."
    )


@mcp.tool()
def git_status() -> str:
    """Get the current Git repository status."""

    return run_git_status()

@mcp.tool()
def git_diff() -> str:
    """Get the current Git diff."""

    return run_git_diff()


async def ask_add_approval(
    files: list[str] | None,
) -> Elicit[Approval]:
    """Ask the user to approve staging files."""

    if files:
        description = ", ".join(files)
    else:
        description = "all changes"

    return Elicit(
        f"Approve staging {description}?",
        Approval,
    )


@mcp.tool()
async def git_add(
    approval: Annotated[
        Approval,
        Resolve(ask_add_approval),
    ],
    files: list[str] | None = None,
) -> str:
    """
    Stage Git files.

    Provide specific file paths to stage only those files.
    Leave files empty to stage all changes.
    """

    if not approval.approved:
        return "Git add cancelled by user."

    return run_git_add(files)


async def ask_commit_message() -> Elicit[CommitMessage]:
    """Ask the user for the commit message."""

    return Elicit(
        "What commit message should be used?",
        CommitMessage,
    )


async def ask_commit_approval(
    message: Annotated[
        CommitMessage,
        Resolve(ask_commit_message),
    ],
) -> Elicit[Approval]:
    """Ask the user to approve the commit."""

    return Elicit(
        f"Approve creating this commit?\n\n"
        f"Commit message: {message.message}",
        Approval,
    )


@mcp.tool()
async def git_commit(
    message: Annotated[
        CommitMessage,
        Resolve(ask_commit_message),
    ],
    approval: Annotated[
        Approval,
        Resolve(ask_commit_approval),
    ],
) -> str:
    """
    Create a Git commit.

    The user is asked for a commit message and must
    approve the commit before it is executed.
    """

    if not approval.approved:
        return "Git commit cancelled by user."

    return run_git_commit(message.message)

async def ask_push_approval(
    remote: str,
    branch: str | None,
) -> Elicit[Approval]:
    """Ask the user to approve pushing commits."""

    destination = remote

    if branch:
        destination = f"{remote}/{branch}"

    return Elicit(
        f"Approve pushing commits to {destination}?",
        Approval,
    )


@mcp.tool()
async def git_push(
    approval: Annotated[
        Approval,
        Resolve(ask_push_approval),
    ],
    remote: str = "origin",
    branch: str | None = None,
) -> str:
    """
    Push Git commits to a remote repository.

    The user must approve the push before it executes.
    """

    if not approval.approved:
        return "Git push cancelled by user."

    return run_git_push(remote, branch)


if __name__ == "__main__":
    mcp.run(transport="stdio")

