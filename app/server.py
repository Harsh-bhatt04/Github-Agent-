from mcp.server import MCPServer
from tools.git_tools import git_status,git_diff

mcp = MCPServer("GitHub MCP Server")

@mcp.tool()
def get_git_status() -> str:
    """Get the current Git repository status."""
    return git_status()

@mcp.tool()
def get_git_diff() -> str:
    """Get the current git diff."""
    return git_diff

if __name__ == "__main__":
    mcp.run(transport="stdio")