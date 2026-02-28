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
# LINE NUMBER HELPER
# =========================

def add_line_numbers(code: str) -> str:
    lines = code.split("\n")
    return "\n".join(f"{i+1:4}: {line}" for i, line in enumerate(lines))

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
            combined_code += f"\n\n==== FILE: {name} ====\n{numbered}\n"

        prompt = f"""
You are a Senior Enterprise .NET Architect performing a strict governance-level PR review.

MANDATORY STRUCTURE:

## 1️⃣ What This PR Does
- Explain business purpose clearly.
- Mention architectural impact.

## 2️⃣ Issues Found (Reference exact line numbers)

For EACH issue use:

### 🔴 Issue <number>
Line: <line number>

Problem:
Explain clearly.

Current Code:
```csharp
<copy exact code>