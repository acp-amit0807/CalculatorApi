import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO = os.getenv("GITHUB_REPOSITORY")
EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")

GEMINI_FALLBACK_MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest",
    "gemini-pro"
]

def validate():
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set")

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set")

    if not REPO:
        raise ValueError("GITHUB_REPOSITORY not set")

    if not EVENT_PATH:
        raise ValueError("GITHUB_EVENT_PATH not set")