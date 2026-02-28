"""
AI C# Pull Request Reviewer – Principal Architect Governance Mode

This script runs inside GitHub Actions when a PR is opened or updated.

It performs:
1. PR clarity and intent validation
2. Unit test presence detection
3. Static code quality checks
4. Principal-level architectural review
5. Maintainability & scalability evaluation
6. Structured actionable feedback

Primary Focus:
Clarity → Maintainability → Technical Soundness → Future Impact
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

if not GITHUB_TOKEN or not OPENAI_API_KEY or not REPO:
    raise ValueError("Missing required environment variables.")

MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest",
    "gemini-pro"
]

# -------------------------
# Load PR Metadata
# -------------------------

def load_event_data():
    event_path = os.getenv("GITHUB_EVENT_PATH")
    with open(event_path, "r") as f:
        return json.load(f)

event_data = load_event_data()
PR_NUMBER = event_data["pull_request"]["number"]
PR_DESCRIPTION = event_data["pull_request"].get("body", "No PR description provided.")

# -------------------------
# GitHub API
# -------------------------

def get_pr_files():
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}/files"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def post_comment(comment):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    body = {"body": comment}
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()

# -------------------------
# Unit Test Detection
# -------------------------

def detect_unit_tests(files):
    return [
        f["filename"]
        for f in files
        if f["filename"].lower().endswith(".cs")
        and "test" in f["filename"].lower()
    ]

# -------------------------
# Static Code Checks
# -------------------------

def static_checks(diff):
    issues = []

    if "async void" in diff:
        issues.append("Avoid async void except for event handlers.")

    if "catch (Exception)" in diff:
        issues.append("Avoid catching generic Exception.")

    if "Console.WriteLine" in diff:
        issues.append("Use ILogger instead of Console.WriteLine.")

    if "DateTime.Now" in diff:
        issues.append("Use DateTime.UtcNow instead of DateTime.Now.")

    if "CancellationToken" not in diff and "async" in diff:
        issues.append("Async method missing CancellationToken parameter.")

    if re.search(r'"[^"]{30,}"', diff):
        issues.append("Long hardcoded string detected.")

    return issues

# -------------------------
# Sanitize Diff
# -------------------------

def sanitize_diff(diff):
    return re.sub(r'password\s*=\s*".*?"',
                  'password="***REDACTED***"',
                  diff,
                  flags=re.IGNORECASE)

# -------------------------
# Principal Architect AI Review
# -------------------------

def review_with_ai(diff):

    prompt = f"""
You are a Principal Software Architect reviewing a Pull Request.

Your responsibility is not just to check correctness,
but to verify whether a new engineer reading this PR clearly understands:

- What problem is being solved
- Why this change was needed
- How the logic works
- What assumptions were made
- What impact this change has

PR Description:
{PR_DESCRIPTION}

Code Diff:
{diff}

🔎 Step 1: Understanding & Clarity Check
Evaluate:
- Purpose clarity
- Is WHY explained?
- Is ticket referenced?
- Can new developer understand in 5–10 minutes?
- Is business logic separated from technical logic?
- Naming & structure quality

🔎 Step 2: Technical Review
Check:
- SOLID principles
- Clean architecture boundaries
- Error handling
- Edge cases
- Performance
- Security
- Scalability

🔎 Step 3: Maintainability & Future Impact
Evaluate:
- Extensibility
- Coupling
- Backward compatibility
- Contract breaking risk

🔎 Step 4: Provide feedback in EXACT format:

1️⃣ Overall Understanding
Is intent clear? (Yes/No + why)

2️⃣ Clarity Issues
Missing explanation:
Confusing logic:
Naming improvements:

3️⃣ Technical Issues (Critical)
Issue:
Why it matters:
Suggested fix:

4️⃣ Improvements (Non-critical)
Refactoring suggestion:
Readability improvement:
Performance suggestion:

5️⃣ Security Concerns
Risk:
Recommendation:

6️⃣ Final Verdict
Approve / Request Changes
Confidence Level (1–10)

Important:
- Do NOT just criticize
- Always give actionable suggestions
- Appreciate good implementation explicitly
- Assume author is mid-level engineer
- Focus on clarity and maintainability first
"""

    headers = {"Content-Type": "application/json"}
    body = {"contents": [{"parts": [{"text": prompt}]}]}

    for model in MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={OPENAI_API_KEY}"
            response = requests.post(url, headers=headers, json=body, timeout=60)

            if response.status_code == 200:
                result = response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]

        except Exception:
            pass

        time.sleep(1)

    return "AI review unavailable."

# -------------------------
# Main Orchestrator
# -------------------------

def main():

    print(f"Repository: {REPO}")
    print(f"PR Number: {PR_NUMBER}")

    files = get_pr_files()
    test_files = detect_unit_tests(files)

    review_sections = []

    # PR Summary
    summary = "## 📦 PR Summary\n\n"
    summary += f"### Description:\n{PR_DESCRIPTION}\n\n"
    summary += "### Files Modified:\n"
    for f in files:
        summary += f"- {f['filename']} (+{f['additions']} / -{f['deletions']})\n"
    review_sections.append(summary)

    # Unit Test Evaluation
    if not test_files:
        review_sections.append(
            "## ❌ Unit Tests Missing\n\n"
            "No test files detected. If business logic changed, "
            "please include unit tests (xUnit/NUnit recommended)."
        )
    else:
        review_sections.append(
            "## ✅ Unit Tests Detected\n\n" +
            "\n".join([f"- {t}" for t in test_files])
        )

    # Per C# File Review
    for f in files:
        if not f["filename"].endswith(".cs") or not f.get("patch"):
            continue

        sanitized = sanitize_diff(f["patch"][:15000])
        static_issues = static_checks(sanitized)

        static_section = (
            "\n".join([f"- {i}" for i in static_issues])
            if static_issues else "No obvious static issues found."
        )

        ai_review = review_with_ai(sanitized)

        review_sections.append(f"""
---

## 📄 Analysis: {f['filename']}

### 🔍 Static Observations
{static_section}

### 🧠 Principal Architect Review
{ai_review}
""")

    final_comment = "\n\n".join(review_sections)

    post_comment(f"## 🤖 AI Enterprise PR Review\n\n{final_comment}")

    print("Review posted successfully.")

if __name__ == "__main__":
    main()