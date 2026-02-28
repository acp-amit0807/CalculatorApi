from core.config import validate
from core.github_client import get_pr_number, get_pr_files, post_comment
from core.static_analyzer import static_checks
from core.llm_client import review_with_ai
from core.sanitizer import sanitize_diff

def run_pr_review():

    validate()

    pr_number = get_pr_number()
    files = get_pr_files(pr_number)

    csharp_diffs = [
        f["patch"]
        for f in files
        if f["filename"].endswith(".cs") and f.get("patch")
    ]

    if not csharp_diffs:
        return

    all_reviews = []

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

    post_comment(pr_number, f"## 🤖 AI C# Enterprise Code Review\n\n{final_review}")