"""
AI C# Pull Request Reviewer – Human Readable Governance Mode

Focus:
- Clarity
- Maintainability
- Severity-based issue grouping
- Human-readable structured output
"""

import os
import requests
import sys
import json
import time
import re

# -------------------------
# Environment Variables
# -------------------------

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO = os.getenv("GITHUB_REPOSITORY")

if not GITHUB_TOKEN or not REPO:
    raise ValueError("Missing required environment variables.")

# Ignore noise files
IGNORE_PATTERNS = [
    ".vs/",
    ".suo",
    ".v2",
    ".vsidx",
    ".dtbcache"
]

# -------------------------
# Load PR Metadata
# -------------------------

def load_event():
    with open(os.getenv("GITHUB_EVENT_PATH"), "r") as f:
        return json.load(f)

event = load_event()
PR_NUMBER = event["pull_request"]["number"]
PR_DESCRIPTION = event["pull_request"].get("body", "No description provided.")

# -------------------------
# GitHub API
# -------------------------

def get_pr_files():
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}/files"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    return requests.get(url, headers=headers).json()

def post_comment(comment):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    requests.post(url, headers=headers, json={"body": comment})

# -------------------------
# Utility
# -------------------------

def should_ignore(filename):
    return any(pattern in filename for pattern in IGNORE_PATTERNS)

# -------------------------
# Static Analysis with Severity
# -------------------------

def analyze_diff(diff):

    critical = []
    must = []
    good = []

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

    if "CancellationToken" not in diff and "async" in diff:
        must.append("Async method missing CancellationToken.")

    return critical, must, good

# -------------------------
# Main
# -------------------------

def main():

    files = get_pr_files()
    review = []

    # -------------------------
    # PR Summary
    # -------------------------

    summary = "## 📦 PR Summary\n\n"
    summary += f"### Description\n{PR_DESCRIPTION}\n\n"
    summary += "### Relevant Files\n"

    relevant_files = []

    for f in files:
        if not should_ignore(f["filename"]):
            relevant_files.append(f["filename"])
            summary += f"- {f['filename']}\n"

    review.append(summary)

    # -------------------------
    # Unit Test Check
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

        if should_ignore(f["filename"]):
            continue

        if not f["filename"].endswith(".cs"):
            continue

        if not f.get("patch"):
            continue

        critical, must, good = analyze_diff(f["patch"])

        explanation = f"""
---

## 📄 File: {f['filename']}

### 🔎 What This File Appears To Do
Based on changes, this file modifies C# logic.
If this introduces business logic or API endpoints,
please ensure the PR description explains:
- What problem is being solved
- Why this change was required
- What impact it has

"""

        issues = ""

        if critical:
            issues += "### 🔴 Critical Issues (Must Fix Before Merge)\n"
            for i in critical:
                issues += f"- {i}\n"

        if must:
            issues += "\n### 🟠 Must Fix\n"
            for i in must:
                issues += f"- {i}\n"

        if good:
            issues += "\n### 🟢 Good To Have Improvements\n"
            for i in good:
                issues += f"- {i}\n"

        if not critical and not must and not good:
            issues += "\nNo major issues detected. 👍"

        review.append(explanation + issues)

    # -------------------------
    # Final Verdict
    # -------------------------

    verdict = "\n---\n\n## 🧾 Final Verdict\n"

    if "No description provided." in PR_DESCRIPTION:
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

    print("Review posted successfully.")

if __name__ == "__main__":
    main()