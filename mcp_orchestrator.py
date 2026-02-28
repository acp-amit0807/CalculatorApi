import os
import requests
import sys
import json
import time

# -------------------------
# Environment Variables
# -------------------------

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Gemini key stored here
REPO = os.getenv("GITHUB_REPOSITORY")

# Fallback models (priority order)
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
# Get PR Files
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
    diffs = []

    for file in files:
        if file["filename"].endswith(".cs") and file.get("patch"):
            diffs.append(file["patch"])

    return diffs


# -------------------------
# Static Checks
# -------------------------

def static_checks(diff):
    issues = []

    if "async void" in diff:
        issues.append("Avoid async void except for event handlers.")

    if "catch (Exception)" in diff:
        issues.append("Avoid catching generic Exception.")

    if "Console.WriteLine" in diff:
        issues.append("Avoid Console.WriteLine in production. Use ILogger.")

    if "DateTime.Now" in diff:
        issues.append("Use DateTime.UtcNow instead of DateTime.Now.")

    return issues


# -------------------------
# Gemini AI Review with Fallback
# -------------------------

def review_with_ai(diff):

    # Secret detection safeguard
    if "PRIVATE KEY" in diff or "password" in diff.lower():
        return "⚠️ Potential secret detected in diff. Manual review required."

    prompt = f"""
You are a senior .NET architect performing enterprise-grade code review.

Review this C# diff for:

- SOLID principle violations
- Async/await misuse
- Security risks
- Performance concerns
- Clean architecture violations
- Logging & exception handling issues
- Dependency injection mistakes
- Thread-safety issues

Return:
1) Structured bullet points
2) Risk Level (Low / Medium / High)
3) Overall score out of 10

Code Diff:
{diff}
"""

    headers = {
        "Content-Type": "application/json"
    }

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    for model in MODELS:
        try:
            print(f"Trying model: {model}")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={OPENAI_API_KEY}"

            response = requests.post(url, headers=headers, json=body, timeout=60)

            if response.status_code == 200:
                result = response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]

            else:
                print(f"Model {model} failed: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"Error with model {model}: {str(e)}")

        time.sleep(1)  # small delay before trying next model

    return "❌ AI review failed. All Gemini models unreachable."


# -------------------------
# Post Comment to PR
# -------------------------

def post_comment(comment):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    body = {
        "body": f"## 🤖 AI C# Enterprise Code Review\n\n{comment}"
    }

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

    if not csharp_diffs:
        print("No C# changes found.")
        sys.exit(0)

    all_reviews = []

    for diff in csharp_diffs:

        static_issues = static_checks(diff)
        static_section = "\n".join([f"- {issue}" for issue in static_issues])

        # Safe truncation for large diffs
        truncated_diff = diff[:15000]

        ai_review = review_with_ai(truncated_diff)

        combined = f"""
### 🔍 Static Analysis
{static_section if static_section else "No obvious static issues found."}

### 🧠 AI Review
{ai_review}
"""

        all_reviews.append(combined)

    final_review = "\n\n---\n\n".join(all_reviews)

    try:
        post_comment(final_review)
        print("Review posted successfully.")
    except Exception as e:
        print("Failed to post comment:", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
