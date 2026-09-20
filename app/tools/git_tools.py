import subprocess


def git_status() -> str:
    """Return the current Git repository status."""

    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return f"Git error: {result.stderr.strip()}"

    return result.stdout.strip() or "Working tree is clean."


def git_diff() -> str:
    """Return the current Git diff."""

    result = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return f"Git error: {result.stderr.strip()}"

    return result.stdout.strip() or "No changes to show."


def git_add(files: list[str] | None = None) -> str:
    """
    Stage files for the next commit.

    If files are provided, only those files are staged.
    If no files are provided, all changes are staged.
    """

    if files:
        command = ["git", "add", "--", *files]
        description = ", ".join(files)
    else:
        command = ["git", "add", "."]
        description = "all files"

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return f"Git error: {result.stderr.strip()}"

    return f"Successfully staged {description}."


def git_commit(message: str) -> str:
    """Create a Git commit with the specified commit message."""

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


def git_push(
    remote: str = "origin",
    branch: str | None = None,
) -> str:
    """Push commits to the specified Git remote."""

    if branch:
        command = ["git", "push", remote, branch]
    else:
        command = ["git", "push", remote]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return f"Git error: {result.stderr.strip()}"

    return result.stdout.strip() or "Successfully pushed changes."