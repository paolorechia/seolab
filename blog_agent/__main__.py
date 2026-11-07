"""
Blog Agent — end-to-end blog writing pipeline.

Usage:
    uv run python -m blog_agent "AI coding assistants"          # interactive + print
    uv run python -m blog_agent "AI coding assistants" --loop   # human-in-the-loop
    uv run python -m blog_agent "AI coding assistants" --batch  # CI mode (no output)
    uv run python -m blog_agent "AI coding assistants" --print  # print to stdout

Steps:
1. Research the topic with DuckDuckGo
2. Extract SEO keywords
3. Write the blog post (Clarity methodology)
4. Self-review against Clarity standards
5. Edit the draft based on review (N iterations)
6. Human review → approve or request changes
"""

import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blog_agent.research import research_topic
from blog_agent.writer import Writer
from blog_agent.editor import Editor
from blog_agent.human_loop import human_approval_loop


def extract_keywords(research_brief: str) -> list[str]:
    """Ask the model to extract 3-5 SEO keywords from the research brief."""
    from blog_agent.utils import chat
    prompt = f"""Extract 3-5 SEO keywords from this research brief.

{research_brief}

Return only a comma-separated list of keywords. No explanation."""
    result = chat(prompt, max_tokens=100)
    keywords = [k.strip() for k in result.replace(",", " ").split()]
    keywords = [k for k in keywords if len(k) > 3]
    return keywords[:5]


def write_blog(
    topic: str,
    product: str = "",
    iterations: int = 3,
    human_loop: bool = False,
    batch: bool = False,
) -> str:
    """Full pipeline: research → write → review → edit → [human loop].

    Returns:
        draft text (so caller can print/save as needed)
    """
    print(f"\n🔍 Researching: {topic}")
    research_brief = research_topic(topic)

    keywords = extract_keywords(research_brief)
    if not batch:
        print(f"🔑 Keywords: {', '.join(keywords)}")

    print(f"\n✍️ Writing...")
    w = Writer()
    draft = w.write(research_brief, keywords)

    print(f"\n🔎 Reviewing...")
    review = w.review(draft)

    print(f"\n📝 Editing ({iterations} auto-iterations)...")
    e = Editor()
    edit_result = e.edit_with_iteration(
        draft, review, research_brief, max_iterations=iterations
    )
    draft = edit_result["final_draft"]

    if human_loop:
        print("\n👤 Starting human review loop...")
        draft, feedback = human_approval_loop(
            draft, research_brief, review, max_rounds=5
        )

    # Save draft to file
    safe_topic = topic.lower().replace(" ", "-").replace("/", "-")
    path = os.path.join(os.path.dirname(__file__), "..", f"{safe_topic}.md")
    with open(path, "w") as f:
        f.write(draft)

    if batch:
        # Silent mode — just save
        sys.exit(0)

    print(f"\n💾 Draft saved to {path}")
    return draft


def main():
    parser = argparse.ArgumentParser(description="AI Blog Writer")
    parser.add_argument("topic", help="The topic to write about")
    parser.add_argument("--product", default="", help="Product name (for SEO context)")
    parser.add_argument(
        "--iterations", type=int, default=3,
        help="Auto-edit iterations before human review",
    )
    parser.add_argument(
        "--loop", action="store_true", help="Interactive human-in-the-loop review"
    )
    parser.add_argument(
        "--print", action="store_true", help="Print draft to stdout (for piping)"
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="CI mode — no output, just save and exit 0",
    )
    args = parser.parse_args()

    draft = write_blog(
        args.topic,
        product=args.product,
        iterations=args.iterations,
        human_loop=args.loop,
        batch=args.batch,
    )

    if args.print:
        print(draft)


if __name__ == "__main__":
    main()
