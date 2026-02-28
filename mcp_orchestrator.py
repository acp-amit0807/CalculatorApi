"""
🤖 AI Enterprise C# PR Reviewer (Intelligent Version)

Features:
- Safe GitHub event parsing
- Full file semantic analysis using LLM
- Business-level explanation of code
- Highlights bad practices
- Shows corrected examples
- Generates xUnit tests (positive/negative/edge)
- Auto governance decision
- Defensive error handling
"""

import os
import sys
import json
import base64
import requests
from typing import Dict

# =========================
# ENVIRONMENT VALIDATION
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
# SAFE EVENT LOADER
# =========================

def load_event(path: str) -> Dict:
    if not path or not os.path.exists(path):
        print("⚠️ GitHub event file missing.")
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to parse event: {e}")
        return {}

event = load_event(EVENT_PATH)

PR_NUMBER = (
    event.get("pull_request", {}).get("number")
    or event.get("issue", {}).get("number")
)

PR_DESCRIPTION = (
    event.get("pull_request", {}).get("body")
    or ""
)

if not PR_NUMBER:
    print("⚠️ Not a pull request event. Exiting safely.")
    sys.exit(0)

# =========================
# GITHUB API HELPERS
# =========================

def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

def get_pr_files():
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}/files"
    try:
        response = requests.get(url, headers=github_headers())
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch PR files: {e}")
        return []

def get_file_content(filename: str) -> str:
    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"
    try:
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
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    try:
        requests.post(url, headers=github_headers(), json={"body": comment})
    except Exception as e:
        print(f"❌ Failed to post comment: {e}")

# =========================
# LLM ANALYSIS
# =========================

def analyze_with_llm(filename: str, content: str) -> str:

    if not OPENAI_API_KEY:
        return "⚠️ LLM review skipped (OPENAI_API_KEY not set)."

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
You are a Senior .NET Enterprise Architect.

Review this C# file and respond in structured markdown:

1. Briefly explain what this file is doing (business perspective, 5-8 lines).
2. Identify bad practices or risky patterns.
3. Highlight critical issues (if any).
4. Show improved implementation snippets (only where needed).
5. If unit tests are missing, generate:
   - Positive test cases
   - Negative test cases
   - Edge cases
   Using xUnit best practices.
6. Suggest improvements for readability, scalability, maintainability.
7. Give a final file score (0–10).

File Name: {filename}

Code:
{content}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ LLM analysis failed: {e}"

# =========================
# MAIN REVIEW LOGIC
# =========================

def main():

    files = get_pr_files()
    review_sections = []

    # PR Summary
    summary = "## 📦 PR Summary\n\n"
    summary += f"### Description\n{PR_DESCRIPTION.strip() or '⚠️ No description provided.'}\n\n"
    review_sections.append(summary)

    if not PR_DESCRIPTION.strip():
        review_sections.append(
            "🔴 **PR Description Missing**\n\n"
            "Please explain:\n"
            "- What problem is being solved\n"
            "- Why this change is needed\n"
            "- What impact this has\n"
        )

    test_files_detected = False
    governance_block = False

    # File-level review
    for f in files:
        filename = f.get("filename", "")

        if not filename.endswith(".cs"):
            continue

        if "test" in filename.lower():
            test_files_detected = True

        content = get_file_content(filename)
        if not content:
            continue

        llm_review = analyze_with_llm(filename, content)

        if "Critical" in llm_review:
            governance_block = True

        review_sections.append(f"\n---\n\n## 📄 File: {filename}\n\n{llm_review}")

    # Unit test check
    if not test_files_detected:
        review_sections.append(
            "\n---\n\n## ❌ Unit Tests Missing\n\n"
            "No test project or test files detected.\n\n"
            "Best Practice:\n"
            "- Separate test project (e.g., CalculatorApi.Tests)\n"
            "- Use xUnit\n"
            "- Cover business logic only (not Program.cs)\n"
            "- Add positive, negative and edge case tests\n"
        )
        governance_block = True

    # Final verdict
    review_sections.append("\n---\n\n## 🧾 Final Governance Verdict\n")

    if governance_block or not PR_DESCRIPTION.strip():
        review_sections.append("🔴 **Request Changes – Governance Blocked**")
    else:
        review_sections.append("🟢 **Approved with Suggestions**")

    final_comment = "\n".join(review_sections)

    post_comment(f"## 🤖 AI Enterprise PR Review\n\n{final_comment}")

    print("✅ Intelligent review completed successfully.")

if __name__ == "__main__":
    main()