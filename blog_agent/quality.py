"""Quality linting using Clarity methodology."""

import subprocess
import tempfile
import sys
import os

def lint(text: str) -> str:
    """Run prose_stats.py diagnostics on the draft text."""
    # Use the Clarity linting scripts
    import subprocess
    import tempfile
    
    # Resolve script paths relative to this file
    this_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(this_dir)
    strip_script = os.path.join(project_dir, "scripts", "strip_markdown.py")
    stats_script = os.path.join(project_dir, "scripts", "prose_stats.py")

    if os.path.exists(strip_script) and os.path.exists(stats_script):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(text)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, stats_script, tmp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout
        finally:
            os.unlink(tmp_path)
    else:
        # Fallback: just count basic metrics
        words = len(text.split())
        sentences = max(text.count(". ") + text.count("\n"), 1)
        paras = max(text.count("\n\n"), 1)
        return f"Size: {words} words, ~{sentences} sentences, ~{paras} paragraphs\n\nNo Clarity scripts found. Install scripts/strip_markdown.py and scripts/prose_stats.py for full diagnostics."


def review_quality(draft: str) -> str:
    """Ask the LLM to review the draft using Clarity review methodology."""
    from blog_agent.utils import chat

    prompt = f"""You are reviewing this draft using the Clarity review methodology.
Apply the full review format:

- Piece-level diagnosis (Job, Substance, Trust, Development, Voice, Ending, Top fixes)
- Passage-level findings (Passage, Verdict, Pattern, Why, Suggestion)

Here is the draft:

{draft}
"""
    return chat(prompt, max_tokens=2000)


def full_quality_check(draft: str) -> dict:
    """Lint + review."""
    lint_output = lint(draft)
    review = review_quality(draft)
    return {"lint": lint_output, "review": review}


if __name__ == "__main__":
    # Quick test
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            text = f.read()
    else:
        text = """In 2025, AI coding assistants have become a transformative landscape that plays a crucial role in the ever-evolving technology space. Delve into the groundbreaking advancements that underscore the importance of leveraging these seamless solutions. It is important to note that the future belongs to those who unlock the power of AI."""

    check = full_quality_check(text)
    print("=== LINT ===")
    print(check["lint"])
    print("\n=== REVIEW ===")
    print(check["review"])
