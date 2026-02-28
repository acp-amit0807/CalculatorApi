import requests
import json
from core.config import GITHUB_TOKEN, REPO, EVENT_PATH

def get_pr_number():
    with open(EVENT_PATH, "r") as f:
        event_data = json.load(f)
    return event_data["pull_request"]["number"]

def get_pr_files(pr_number):
    url = f"https://api.github.com/repos/{REPO}/pulls/{pr_number}/files"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def post_comment(pr_number, comment):
    url = f"https://api.github.com/repos/{REPO}/issues/{pr_number}/comments"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    body = {"body": comment}

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()