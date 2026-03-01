from github import Github
from app.config import settings
from app.logger import get_logger

logger = get_logger("GitHubService")


class GitHubService:

    def __init__(self):
        self.client = Github(settings.GITHUB_TOKEN)

    def get_repo(self, full_name: str):
        logger.info(f"Fetching repo: {full_name}")
        return self.client.get_repo(full_name)

    def create_pull_request(
        self,
        repo_name: str,
        source_branch: str,
        target_branch: str,
        title: str,
        body: str,
    ):
        repo = self.get_repo(repo_name)

        pr = repo.create_pull(
            title=title,
            body=body,
            head=source_branch,
            base=target_branch,
        )

        logger.info(f"PR Created: #{pr.number}")

        return {
            "pr_number": pr.number,
            "url": pr.html_url,
            "state": pr.state,
        }

    def get_pull_request(self, repo_name: str, pr_number: int):
        repo = self.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        return {
            "number": pr.number,
            "title": pr.title,
            "state": pr.state,
            "author": pr.user.login,
            "url": pr.html_url,
        }

    def merge_pull_request(self, repo_name: str, pr_number: int):
        repo = self.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        if not pr.mergeable:
            return {"message": "PR not mergeable yet"}

        merge_status = pr.merge()

        return {
            "merged": merge_status.merged,
            "message": merge_status.message,
        }