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

MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest",
    "gemini-pro"
]

if not GITHUB_TOKEN or not OPENAI_API_KEY or not REPO:
    raise ValueError("Required environment variables missing.")

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
# GitHub PR Files
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
# Detect Unit Test Presence
# -------------------------

def detect_unit_tests(files):
    for file in files:
        name = file["filename"].lower()
        if "test" in name and name.endswith(".cs"):
            return True
    return False

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
        issues.append("Avoid Console.WriteLine. Use ILogger.")

    if "DateTime.Now" in diff:
        issues.append("Use DateTime.UtcNow instead of DateTime.Now.")

    if "TODO" in diff or "FIXME" in diff:
        issues.append("TODO/FIXME found in code.")

    if re.search(r'public class \w+ \{(.|\n){2000,}', diff):
        issues.append("Potential large class detected. Consider refactoring.")

    if diff.count("{") - diff.count("}") != 0:
        issues.append("Potential brace mismatch detected.")

    if re.search(r'public async Task \w+\(', diff) and "Async" not in diff:
        issues.append("Async method name should end with 'Async'.")

    if "CancellationToken" not in diff and "async" in diff:
        issues.append("Async method missing CancellationToken parameter.")

    if re.search(r'"[^"]{20,}"', diff):
        issues.append("Long hardcoded string detected. Consider configuration or constants.")

    if "null" in diff and "?" not in diff:
        issues.append("Potential null handling issue detected.")

    if "ILogger" not in diff and "Controller" in diff:
        issues.append("Controller without ILogger detected.")

    return issues

# -------------------------
# Secret Sanitization
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
You are a principal .NET architect performing enterprise review.

Evaluate:
- SOLID violations
- Clean Architecture
- Thread safety
- Performance
- Security
- Dependency Injection
- Logging strategy
- Unit testing gaps

Return:
- Bullet points
- Risk Level (Low/Medium/High)
- Score /10

Code:
{diff}
"""

    headers = {"Content-Type": "application/json"}

    body = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

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
# Post Comment
# -------------------------

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
# Orchestrator
# -------------------------

def main():

    print(f"Repository: {REPO}")
    print(f"PR Number: {PR_NUMBER}")

    files = get_pr_files()

    csharp_diffs = extract_csharp_diffs(files)
    has_tests = detect_unit_tests(files)

    if not csharp_diffs:
        print("No C# changes found.")
        sys.exit(0)

    all_reviews = []

    if not has_tests:
        all_reviews.append("⚠️ No unit test files detected in this PR.")

    for diff in csharp_diffs:

        sanitized = sanitize_diff(diff[:15000])

        static_issues = static_checks(sanitized)
        static_section = "\n".join([f"- {i}" for i in static_issues]) \
            if static_issues else "No obvious static issues found."

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