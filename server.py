from fastmcp import FastMCP
from app.pr_tools import (
    create_pr_tool,
    get_pr_tool,
    merge_pr_tool,
)

mcp = FastMCP("github-pr-agent")


@mcp.tool()
def raise_pull_request(
    repo_name: str,
    source_branch: str,
    target_branch: str,
    title: str,
    description: str,
):
    """
    Raise a new Pull Request in GitHub.
    """
    return create_pr_tool(
        repo_name,
        source_branch,
        target_branch,
        title,
        description,
    )


@mcp.tool()
def get_pull_request_details(repo_name: str, pr_number: int):
    """
    Get Pull Request details.
    """
    return get_pr_tool(repo_name, pr_number)


@mcp.tool()
def merge_pull_request(repo_name: str, pr_number: int):
    """
    Merge Pull Request.
    """
    return merge_pr_tool(repo_name, pr_number)


if __name__ == "__main__":
    mcp.run(transport="stdio")