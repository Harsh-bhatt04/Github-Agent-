import subprocess

from langchain_core.tools import tool


@tool
def git_status() -> str:
    """Get the current Git repository status."""

    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return f"Git error: {result.stderr.strip()}"

    return result.stdout.strip() or "Working tree is clean."


@tool
def git_diff() -> str:
    """Get the current Git diff."""

    result = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return f"Git error: {result.stderr.strip()}"

    return result.stdout.strip() or "No changes to show."


@tool
def git_add(files: list[str]) -> str:
    """Stage the specified files for the next commit."""

    if not files:
        return "No files provided."

    result = subprocess.run(
        ["git", "add", *files],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return f"Git error: {result.stderr.strip()}"

    return f"Successfully staged: {', '.join(files)}"


@tool
def git_commit(message: str) -> str:
    """Create a Git commit with the specified message."""

    if not message.strip():
        return "Commit message cannot be empty."

    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return f"Git error: {result.stderr.strip()}"

    return result.stdout.strip()