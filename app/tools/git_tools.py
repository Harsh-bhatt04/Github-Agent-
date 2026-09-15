import subprocess


def git_status() -> str:
    """Return the current Git repository status."""

    result = subprocess.run(
        ["git", "status", "--short"],
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