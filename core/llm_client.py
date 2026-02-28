import requests
import time
from core.config import OPENAI_API_KEY, GEMINI_FALLBACK_MODELS

def review_with_ai(diff):

    prompt = f"""
You are a senior .NET architect.

Review this C# diff for:
- SOLID violations
- Async misuse
- Security risks
- Performance concerns

Return:
- Bullet points
- Risk Level
- Score /10

Code:
{diff}
"""

    headers = {"Content-Type": "application/json"}

    body = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    for model in GEMINI_FALLBACK_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={OPENAI_API_KEY}"
            response = requests.post(url, headers=headers, json=body, timeout=60)

            if response.status_code == 200:
                result = response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"]

        except Exception:
            pass

        time.sleep(1)

    return "AI review failed (all models unreachable)."