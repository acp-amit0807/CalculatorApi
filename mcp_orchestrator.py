"""
🤖 AI Enterprise C# PR Reviewer – Ultimate Governance Version

This version:
- Reads all changed C# files
- Adds line numbers for precise issue reporting
- Explains what PR is doing
- Highlights exact problematic lines
- Shows corrected implementation
- Generates full xUnit test class
- Provides architecture observations
- Provides governance decision
- Never crashes CI if LLM fails
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
# LOAD EVENT
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
    print("⚠️ Not a PR event. Exiting.")
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
    try:
        url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}/files"
        response = requests.get(url, headers=github_headers())
        if response.status_code != 200:
            return []
        return response.json()
    except Exception:
        return []

def get_file_content(filename: str) -> str:
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
        response = requests.get(url, headers=github_headers())
        if response.status_code != 200:
            return ""
        data = response.json()
        if "content" in data:
            return base64.b64decode(data["content"]).decode("utf-8")
        return ""
    except Exception:
        return ""

def post_comment(comment: str):
    try:
        url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
        requests.post(url, headers=github_headers(), json={"body": comment})
    except Exception:
        print("⚠️ Failed to post comment")

# =========================
# LINE NUMBER HELPER
# =========================

def add_line_numbers(code: str) -> str:
    lines = code.split("\n")
    return "\n".join("{:4}: {}".format(i + 1, line) for i, line in enumerate(lines))

# =========================
# LLM REVIEW
# =========================

def analyze_pr_with_llm(pr_description: str, files: Dict[str, str]) -> str:

    if not OPENAI_API_KEY:
        return "⚠️ LLM review skipped (OPENAI_API_KEY not set)."

    try:
        from openai import OpenAI
    except ImportError:
        return "⚠️ openai package not installed."

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        combined_code = ""
        for name, content in files.items():
            numbered = add_line_numbers(content)
            combined_code += "\n\n==== FILE: {} ====\n{}\n".format(name, numbered)

        prompt = """
You are a Senior Enterprise .NET Architect performing a strict governance-level PR review.

MANDATORY STRUCTURE:

1) What This PR Does
- Explain business purpose clearly.
- Mention architectural impact.

2) Issues Found (Reference exact line numbers)

For EACH issue use:

Issue <number>
Line: <line number>

Problem:
Explain clearly.

Current Code:
<copy exact code>

Correct Implementation:
<show corrected version>

3) Architecture Observations
- Separation of concerns
- Dependency injection
- Logging
- Validation
- Scalability

4) Required Unit Tests (xUnit)

Generate a COMPLETE test class based on actual business logic.
Include:
- Positive test
- Negative test
- Edge case test
- Arrange-Act-Assert pattern
- Mock dependencies if needed

5) File Quality Score (0-10)

6) Governance Decision
Approve or Request Changes (with reason)

PR Description:
{desc}

Changed Code:
{code}
""".format(desc=pr_description, code=combined_code)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        return response.choices[0].message.content

    except Exception as e:
        return "⚠️ LLM analysis failed safely: {}".format(str(e))

# =========================
# MAIN
# =========================

def main():

    files = get_pr_files()
    file_contents = {}
    test_project_present = False

    for f in files:
        filename = f.get("filename", "")

        if filename.endswith(".cs"):
            content = get_file_content(filename)
            if content:
                file_contents[filename] = content

        if "test" in filename.lower():
            test_project_present = True

    review_sections = []

    review_sections.append("## 📦 PR Summary\n")
    review_sections.append("### Description\n{}\n".format(
        PR_DESCRIPTION.strip() or "⚠️ No description provided."
    ))

    if not PR_DESCRIPTION.strip():
        review_sections.append(
            "\n🔴 PR Description Missing\n"
            "Please clearly explain the business intent.\n"
        )

    if file_contents:
        llm_review = analyze_pr_with_llm(PR_DESCRIPTION, file_contents)
        review_sections.append("\n---\n\n" + llm_review)
    else:
        review_sections.append("\nNo C# files changed.\n")

    if not test_project_present:
        review_sections.append(
            "\n---\n\n❌ Test Project Missing\n"
            "No test project detected.\n"
            "Best Practice: Create separate ProjectName.Tests using xUnit.\n"
        )

    final_comment = "\n".join(review_sections)

    post_comment("## 🤖 AI Enterprise PR Governance Review\n\n" + final_comment)

    print("✅ Enterprise PR review completed successfully.")

if __name__ == "__main__":
    main()