"""
AI C# Pull Request Reviewer – Enterprise Hardened Version

Enhancements:
- Full None safety
- GitHub event defensive parsing
- API failure handling
- Clean validation helpers
- Testable functions
"""

import os
import requests
import sys
import json
import re
from typing import Tuple, List

# -------------------------
# Environment Validation
# -------------------------

def get_env(name: str, required: bool = True, default: str = "") -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or default

GITHUB_TOKEN = get_env("GITHUB_TOKEN")
REPO = get_env("GITHUB_REPOSITORY")
EVENT_PATH = get_env("GITHUB_EVENT_PATH")

# -------------------------
# Ignore Patterns
# -------------------------

IGNORE_PATTERNS = [
    ".vs/",
    ".suo",
    ".v2",
    ".vsidx",
    ".dtbcache"
]

# -------------------------
# Safe Event Loader
# -------------------------

def load_event(path: str) -> dict:
    if not path or not os.path.exists(path):
        print("⚠️ GitHub event file missing.")
        return {}

    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to parse GitHub event: {e}")
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
    print("⚠️ No PR number found. Exiting safely.")
    sys.exit(0)

# -------------------------
# GitHub API (Safe)
# -------------------------

def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

def get_pr_files() -> list:
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}/files"
    try:
        response = requests.get(url, headers=github_headers())
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Failed to fetch PR files: {e}")
        return []

def post_comment(comment: str):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    try:
        response = requests.post(
            url,
            headers=github_headers(),
            json={"body": comment}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Failed to post comment: {e}")

# -------------------------
# Utility
# -------------------------

def should_ignore(filename: str) -> bool:
    return any(pattern in filename for pattern in IGNORE_PATTERNS)

def is_pr_description_missing(desc: str) -> bool:
    return not desc.strip()

# -------------------------
# Static Analysis
# -------------------------

def analyze_diff(diff: str) -> Tuple[List[str], List[str], List[str]]:
    critical = []
    must = []
    good = []

    if not diff:
        return critical, must, good

    if "async void" in diff:
        critical.append("Avoid async void (can crash process).")

    if "catch (Exception)" in diff:
        must.append("Avoid catching generic Exception.")

    if "Console.WriteLine" in diff:
        must.append("Replace Console.WriteLine with ILogger.")

    if "DateTime.Now" in diff:
        good.append("Use DateTime.UtcNow for timezone safety.")

    if re.search(r'"[^"]{40,}"', diff):
        good.append("Long hardcoded string detected (consider constant/config).")

    if "async" in diff and "CancellationToken" not in diff:
        must.append("Async method missing CancellationToken.")

    return critical, must, good

# -------------------------
# Main
# -------------------------

def main():

    files = get_pr_files()
    review = []

    summary = "## 📦 PR Summary\n\n"
    summary += f"### Description\n{PR_DESCRIPTION or '⚠️ No description provided.'}\n\n"
    summary += "### Relevant Files\n"

    relevant_files = []

    for f in files:
        filename = f.get("filename", "")
        if filename and not should_ignore(filename):
            relevant_files.append(filename)
            summary += f"- {filename}\n"

    review.append(summary)

    # -------------------------
    # Unit Test Detection
    # -------------------------

    test_files = [f for f in relevant_files if "test" in f.lower()]

    if not test_files:
        review.append(
            "## ❌ Unit Test Coverage\n\n"
            "No test files detected.\n"
            "If business logic changed, unit tests must be added."
        )
    else:
        review.append(
            "## ✅ Unit Tests Present\n\n" +
            "\n".join(test_files)
        )

    # -------------------------
    # File Analysis
    # -------------------------

    for f in files:

        filename = f.get("filename", "")
        patch = f.get("patch")

        if not filename or should_ignore(filename):
            continue

        if not filename.endswith(".cs"):
            continue

        if not patch:
            continue

        critical, must, good = analyze_diff(patch)

        explanation = f"""
---

## 📄 File: {filename}

### 🔎 Clarity Check
Ensure:
- PR description explains intent
- Complex logic is commented
- Method names reflect business purpose
"""

        issues = ""

        if critical:
            issues += "### 🔴 Critical Issues\n"
            for i in critical:
                issues += f"- {i}\n"

        if must:
            issues += "\n### 🟠 Must Fix\n"
            for i in must:
                issues += f"- {i}\n"

        if good:
            issues += "\n### 🟢 Improvements\n"
            for i in good:
                issues += f"- {i}\n"

        if not (critical or must or good):
            issues += "\nNo major issues detected. 👍"

        review.append(explanation + issues)

    # -------------------------
    # Final Verdict
    # -------------------------

    verdict = "\n---\n\n## 🧾 Final Verdict\n"

    if is_pr_description_missing(PR_DESCRIPTION):
        verdict += "🔴 Request Changes\n"
        verdict += "PR description is missing. Please explain:\n"
        verdict += "- What problem is being solved\n"
        verdict += "- Why this change is needed\n"
        verdict += "- What impact this has\n"
    else:
        verdict += "🟠 Needs Improvement\n"
        verdict += "Please address highlighted issues."

    review.append(verdict)

    final_comment = "\n".join(review)

    post_comment(f"## 🤖 AI Enterprise PR Review\n\n{final_comment}")

    print("✅ Review completed successfully.")

if __name__ == "__main__":
    main()