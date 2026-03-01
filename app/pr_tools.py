from app.github_service import GitHubService

service = GitHubService()


def create_pr_tool(
    repo_name: str,
    source_branch: str,
    target_branch: str,
    title: str,
    description: str,
):
    return service.create_pull_request(
        repo_name,
        source_branch,
        target_branch,
        title,
        description,
    )


def get_pr_tool(repo_name: str, pr_number: int):
    return service.get_pull_request(repo_name, pr_number)


def merge_pr_tool(repo_name: str, pr_number: int):
    return service.merge_pull_request(repo_name, pr_number)