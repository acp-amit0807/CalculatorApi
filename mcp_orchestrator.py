"""
🤖 AI Enterprise C# PR Reviewer – Full Governance Mode

This version:
- Reads ALL changed C# files
- Understands full PR context
- Explains what the PR is doing
- Identifies real issues
- Shows corrected implementations
- Generates full xUnit test classes
- Provides architectural suggestions
- Returns governance decision
"""

import os
import sys
import json
import base64
import requests
from typing import Dict, List

# =========================
# ENV VALIDATION
# =========================

def get_env(name: str, required: bool = True, default: str = "") -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or default

GITHUB_TOKEN = get_env("GITHUB_TOKEN")
REPO = get_env("GITHUB_REPOSITORY")
EVENT_PATH = get_env("GITHUB_EVENT_PATH")
OPENAI_API_KEY = get_env("OPENAI_API_KEY", required=False)

# =========================
# LOAD EVENT SAFELY
# =========================

def load_event(path: str) -> Dict:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

event = load_event(EVENT_PATH)

PR_NUMBER = (
    event.get("pull_request", {}).get("number")
    or event.get("issue", {}).get("number")
)

PR_DESCRIPTION = event.get("pull_request", {}).get("body") or ""

if not PR_NUMBER:
    print("⚠️ Not a PR event. Exiting safely.")
    sys.exit(0)

# =========================
# GITHUB API
# =========================

def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

def get_pr_files() -> List[Dict]:
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}/files"
    response = requests.get(url, headers=github_headers())
    if response.status_code != 200:
        return []
    return response.json()

def get_file_content(filename: str) -> str:
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    response = requests.get(url, headers=github_headers())
    if response.status_code != 200:
        return ""
    data = response.json()
    if "content" in data:
        return base64.b64decode(data["content"]).decode("utf-8")
    return ""

def post_comment(comment: str):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    requests.post(url, headers=github_headers(), json={"body": comment})

# =========================
# LLM FULL PR ANALYSIS
# =========================

def analyze_pr_with_llm(pr_description: str, file_contents: Dict[str, str]) -> str:

    if not OPENAI_API_KEY:
        return "⚠️ LLM review skipped (OPENAI_API_KEY missing)."

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    combined_code = ""
    for name, content in file_contents.items():
        combined_code += f"\n\n==== FILE: {name} ====\n{content}\n"

    prompt = f"""
You are a Senior Enterprise .NET Architect performing a governance-level PR review.

STRICT INSTRUCTIONS:

STEP 1 – Explain the PR
- Explain clearly what this PR is doing.
- Explain business intent.
- Mention if architecture changed.

STEP 2 – Identify Issues
For each issue:
- Explain what is wrong
- Why it is wrong
- Show corrected implementation

STEP 3 – Architecture Review
- Is separation of concerns respected?
- Is business logic inside controllers?
- Is dependency injection used properly?
- Suggest proper layering if needed.

STEP 4 – Unit Test Generation
If business logic exists:
- Generate a full xUnit test class
- Include positive tests
- Include negative tests
- Include edge case tests
- Use best practices (Arrange-Act-Assert)
- Mock dependencies if needed

STEP 5 – Code Quality Score
Provide:
- File quality score (0–10)
- PR governance decision (Approve / Request Changes)

PR Description:
{pr_description}

Changed Code:
{combined_code}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content

# =========================
# MAIN
# =========================

def main():

    files = get_pr_files()
    file_contents = {}
    test_files_present = False

    for f in files:
        filename = f.get("filename", "")
        if filename.endswith(".cs"):
            content = get_file_content(filename)
            if content:
                file_contents[filename] = content
        if "test" in filename.lower():
            test_files_present = True

    review_sections = []

    review_sections.append("## 📦 PR Summary\n")
    review_sections.append(f"### Description\n{PR_DESCRIPTION.strip() or '⚠️ No description provided.'}\n")

    if not PR_DESCRIPTION.strip():
        review_sections.append(
            "🔴 **PR Description Missing**\n"
            "Please explain business intent clearly.\n"
        )

    llm_review = analyze_pr_with_llm(PR_DESCRIPTION, file_contents)
    review_sections.append("\n---\n\n" + llm_review)

    if not test_files_present:
        review_sections.append(
            "\n---\n\n## ❌ Test Project Missing\n"
            "No test project detected.\n"
            "Recommended: Create `ProjectName.Tests` using xUnit.\n"
        )

    final_comment = "\n".join(review_sections)

    post_comment(f"## 🤖 AI Enterprise PR Governance Review\n\n{final_comment}")

    print("✅ Full PR review completed.")

if __name__ == "__main__":
    main()