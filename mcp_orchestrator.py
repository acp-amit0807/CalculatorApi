import os
import requests
import sys
import json

# --------------------------------------------------
# Environment Variables Provided by GitHub Actions
# --------------------------------------------------

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")


# --------------------------------------------------
# Extract PR Number Correctly (Important Fix)
# --------------------------------------------------

def get_pr_number():
    event_path = os.getenv("GITHUB_EVENT_PATH")

    if not event_path:
        print("GITHUB_EVENT_PATH not found.")
        sys.exit(1)

    with open(event_path, "r") as f:
        event_data = json.load(f)

    return event_data["pull_request"]["number"]


PR_NUMBER = get_pr_number()


# --------------------------------------------------
# Step 1: Get Changed Files from PR
# --------------------------------------------------

def get_pr_files():
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}/files"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("Failed to fetch PR files:", response.text)
        sys.exit(1)

    return response.json()


# --------------------------------------------------
# Step 2: Extract Only C# Diffs
# --------------------------------------------------

def extract_csharp_diffs(files):
    diffs = []

    for file in files:
        if file["filename"].endswith(".cs") and file.get("patch"):
            diffs.append(file["patch"])

    return diffs


# --------------------------------------------------
# Step 3: Static Checks (MCP Step 1)
# --------------------------------------------------

def static_checks(diff):
    issues = []

    if "async void" in diff:
        issues.append("Avoid async void except for event handlers.")

    if "catch (Exception)" in diff:
        issues.append("Avoid catching generic Exception.")

    return issues


# --------------------------------------------------
# Step 4: Copilot Review (GitHub Models API)
# --------------------------------------------------

def review_with_copilot(diff):

    url = "https://api.github.com/models/gpt-4.1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are a senior .NET architect performing enterprise code review.

Review this C# diff for:

- SOLID principle violations
- Async/await misuse
- Security risks
- Performance concerns
- Clean architecture violations
- Logging & exception handling issues

Return structured bullet points.
Also give an overall score out of 10.

Code:
{diff}
"""

    body = {
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 200:
        print("Copilot API error:", response.text)
        sys.exit(1)

    return response.json()["choices"][0]["message"]["content"]


# --------------------------------------------------
# Step 5: Post Comment Back to PR
# --------------------------------------------------

def post_comment(comment):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    body = {
        "body": f"## 🤖 Copilot MCP C# Code Review\n\n{comment}"
    }

    response = requests.post(url, headers=headers, json=body)

    if response.status_code != 201:
        print("Failed to post comment:", response.text)
        sys.exit(1)


# --------------------------------------------------
# MCP Orchestrator Flow
# --------------------------------------------------

def main():
    print(f"Repository: {REPO}")
    print(f"PR Number: {PR_NUMBER}")

    print("Fetching PR files...")
    files = get_pr_files()

    print("Extracting C# diffs...")
    csharp_diffs = extract_csharp_diffs(files)

    if not csharp_diffs:
        print("No C# changes found.")
        sys.exit(0)

    all_reviews = []

    for diff in csharp_diffs:

        # Static rule engine
        static_issues = static_checks(diff)
        static_section = "\n".join([f"- {issue}" for issue in static_issues])

        # Copilot AI review
        copilot_review = review_with_copilot(diff)

        combined_review = f"""
### 🔍 Static Analysis
{static_section if static_section else "No obvious static issues found."}

### 🧠 Copilot AI Review
{copilot_review}
"""

        all_reviews.append(combined_review)

    final_review = "\n\n---\n\n".join(all_reviews)

    print("Posting review comment...")
    post_comment(final_review)

    print("Review posted successfully.")


if __name__ == "__main__":
    main()
