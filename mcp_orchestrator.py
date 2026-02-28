import os
import requests
import sys

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = os.getenv("GITHUB_REF").split("/")[-1]

# -----------------------------
# Step 1: Get PR Changed Files
# -----------------------------

def get_pr_files():
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}/files"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# -----------------------------
# Step 2: Extract C# Diffs
# -----------------------------

def extract_csharp_diffs(files):
    diffs = []

    for file in files:
        if file["filename"].endswith(".cs") and file.get("patch"):
            diffs.append(file["patch"])

    return diffs

# -----------------------------
# Step 3: Static Rule Checks (MCP Step 1)
# -----------------------------

def static_checks(diff):
    issues = []

    if "async void" in diff:
        issues.append("Avoid async void except for event handlers.")

    if "catch (Exception)" in diff:
        issues.append("Avoid catching generic Exception.")

    return issues

# -----------------------------
# Step 4: Copilot Review (MCP Step 2)
# -----------------------------

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
    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]

# -----------------------------
# Step 5: Post PR Comment
# -----------------------------

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
    response.raise_for_status()

# -----------------------------
# Orchestrator (MCP Flow)
# -----------------------------

def main():
    print("Fetching PR files...")
    files = get_pr_files()

    print("Extracting C# diffs...")
    csharp_diffs = extract_csharp_diffs(files)

    if not csharp_diffs:
        print("No C# changes found.")
        sys.exit(0)

    all_reviews = []

    for diff in csharp_diffs:

        # Static rules first
        static_issues = static_checks(diff)
        static_section = "\n".join([f"- {issue}" for issue in static_issues])

        # Copilot intelligent review
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