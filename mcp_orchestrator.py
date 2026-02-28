"""
AI C# Pull Request Reviewer

What this script does:
----------------------
This script runs inside GitHub Actions when a Pull Request is opened or updated.

It performs:
1. Fetches changed files from the PR.
2. Filters C# (.cs) files.
3. Performs static code smell detection.
4. Checks whether unit tests are included in the PR.
5. Sends sanitized diffs to Gemini AI for architectural review.
6. Posts a structured enterprise-grade review comment back to the PR.

This acts as an automated governance + AI-assisted review layer.
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

# Gemini fallback models
MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest",
    "gemini-pro"
]

# -------------------------
# Get PR Number
# -------------------------

def get_pr_number():
    event_path = os.getenv("GITHUB_EVENT_PATH")
    with open(event_path, "r") as f:
        event_data = json.load(f)
    return event_data["pull_request"]["number"]

PR_NUMBER = get_pr_number()

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
# Extract C# Diffs
# -------------------------

def extract_csharp_diffs(files):
    return [
        f["patch"]
        for f in files
        if f["filename"].endswith(".cs") and f.get("patch")
    ]

# -------------------------
# Detect Unit Tests
# -------------------------

def detect_unit_tests(files):
    test_files = []

    for file in files:
        name = file["filename"].lower()

        if name.endswith(".cs") and (
            "test" in name or
            "tests" in name or
            name.endswith("tests.cs")
        ):
            test_files.append(file["filename"])

    return test_files

# -------------------------
# Advanced Static Checks
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

    if "TODO" in diff or "FIXME" in diff:
        issues.append("TODO/FIXME found in code.")

    if re.search(r'public class \w+ \{(.|\n){2000,}', diff):
        issues.append("Potential large class detected. Consider refactoring.")

    if diff.count("{") != diff.count("}"):
        issues.append("Brace mismatch detected.")

    if re.search(r'public async Task \w+\(', diff) and "Async" not in diff:
        issues.append("Async method name should end with 'Async'.")

    if "async" in diff and "CancellationToken" not in diff:
        issues.append("Async method missing CancellationToken parameter.")

    if re.search(r'"[^"]{30,}"', diff):
        issues.append("Long hardcoded string detected.")

    if "null" in diff and "?" not in diff:
        issues.append("Potential null-handling issue detected.")

    if "Controller" in diff and "ILogger" not in diff:
        issues.append("Controller without ILogger detected.")

    return issues

# -------------------------
# Sanitize Secrets
# -------------------------

def sanitize_diff(diff):
    diff = re.sub(r'password\s*=\s*".*?"',
                  'password="***REDACTED***"',
                  diff,
                  flags=re.IGNORECASE)

    diff = re.sub(r'PRIVATE KEY.*?END PRIVATE KEY',
                  '***REDACTED KEY***',
                  diff,
                  flags=re.DOTALL)

    return diff

# -------------------------
# Gemini AI Review
# -------------------------

def review_with_ai(diff):

    if "PRIVATE KEY" in diff or "password" in diff.lower():
        return "⚠️ Potential secret detected. Manual review required."

    prompt = f"""
You are a Principal .NET Architect performing enterprise review.

Evaluate:
- SOLID violations
- Clean Architecture compliance
- Thread safety
- Security risks
- Performance concerns
- Dependency Injection usage
- Logging strategy
- Unit testing gaps

Return:
- Structured bullet points
- Risk Level (Low/Medium/High)
- Score /10

Code:
{diff}
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

        except Exception as e:
            print(f"Model {model} failed: {str(e)}")

        time.sleep(1)

    return "AI review unavailable."

# -------------------------
# Main Orchestrator
# -------------------------

def main():

    print(f"Repository: {REPO}")
    print(f"PR Number: {PR_NUMBER}")

    files = get_pr_files()

    csharp_diffs = extract_csharp_diffs(files)
    test_files = detect_unit_tests(files)

    if not csharp_diffs:
        print("No C# changes found.")
        sys.exit(0)

    all_reviews = []

    # Unit test evaluation
    if not test_files:
        all_reviews.append(
            "❌ No unit test files detected in this PR.\n\n"
            "If production code is modified, unit tests should be included "
            "(xUnit / NUnit / MSTest recommended)."
        )
    else:
        all_reviews.append(
            "✅ Unit test files detected:\n" +
            "\n".join([f"- {t}" for t in test_files])
        )

    for diff in csharp_diffs:

        sanitized = sanitize_diff(diff[:15000])
        static_issues = static_checks(sanitized)

        static_section = (
            "\n".join([f"- {issue}" for issue in static_issues])
            if static_issues else
            "No obvious static issues found."
        )

        ai_review = review_with_ai(sanitized)

        combined = f"""
### 🔍 Static Analysis
{static_section}

### 🧠 AI Review
{ai_review}
"""

        all_reviews.append(combined)

    final_review = "\n\n---\n\n".join(all_reviews)

    post_comment(f"## 🤖 AI C# Enterprise Code Review\n\n{final_review}")

    print("Review posted successfully.")

if __name__ == "__main__":
    main()