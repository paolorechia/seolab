"""
Blog Agent — end-to-end blog writing pipeline.

Usage:
    uv run python -m blog_agent write --topic "AI coding assistants" --product "myproduct"
    uv run python -m blog_agent "AI coding assistants"

Steps:
1. Research the topic with DuckDuckGo
2. Extract SEO keywords
3. Write the blog post (Clarity methodology)
4. Self-review against Clarity standards
5. Edit the draft based on review
6. (optional) Re-review the edited draft
"""

import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blog_agent.research import research_topic
from blog_agent.writer import Writer
from blog_agent.editor import Editor


def extract_keywords(research_brief: str) -> list[str]:
    """Ask the model to extract 3-5 SEO keywords from the research brief."""
    from blog_agent.utils import chat
    prompt = f"""Extract 3-5 SEO keywords from this research brief.

{research_brief}

Return only a comma-separated list of keywords. No explanation."""
    result = chat(prompt, max_tokens=100)
    # Clean up the output
    keywords = [k.strip() for k in result.replace(",", " ").split()]
    keywords = [k for k in keywords if len(k) > 3]
    return keywords[:5]


def write_blog(topic: str, product: str = "", iterations: int = 3) -> None:
    """Full pipeline: research → write → review → edit."""
    print(f"\n🔍 Researching: {topic}")
    research_brief = research_topic(topic)

    keywords = extract_keywords(research_brief)
    print(f"🔑 Keywords: {', '.join(keywords)}")

    print(f"\n✍️ Writing...")
    w = Writer()
    draft = w.write(research_brief, keywords)

    print(f"\n🔎 Reviewing...")
    review = w.review(draft)

    print(f"\n📝 Editing (up to {iterations} iterations)...")
    e = Editor()
    edit_result = e.edit_with_iteration(draft, review, research_brief, max_iterations=iterations)

    best_draft = edit_result["final_draft"]

    # Print results
    print("\n" + "=" * 60)
    print("=== DRAFT ===")
    print("=" * 60)
    print(best_draft)

    print("\n" + "=" * 60)
    print("=== REVIEW ===")
    print("=" * 60)
    print(review)

    # Save draft to file
    safe_topic = topic.lower().replace(" ", "-").replace("/", "-")
    path = os.path.join(os.path.dirname(__file__), "..", f"{safe_topic}.md")
    with open(path, "w") as f:
        f.write(best_draft)
    print(f"\n💾 Draft saved to {path}")


def main():
    parser = argparse.ArgumentParser(description="AI Blog Writer")
    parser.add_argument("topic", help="The topic to write about")
    parser.add_argument("--product", default="", help="Product name (for SEO context)")
    parser.add_argument("--iterations", type=int, default=3, help="Max edit iterations")
    args = parser.parse_args()

    write_blog(args.topic, args.product, iterations=args.iterations)


if __name__ == "__main__":
    main()
