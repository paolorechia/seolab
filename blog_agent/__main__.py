"""
Blog Agent — end-to-end blog writing pipeline.

Usage:
    uv run python -m blog_agent write --topic "AI coding assistants" --product "myproduct"
    uv run python -m blog_agent write --topic "rust error handling" --product "myproduct"

Steps:
1. Research the topic with DuckDuckGo
2. Extract SEO keywords
3. Write the blog post (Clarity methodology)
4. Self-review against Clarity standards
"""

import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blog_agent.research import research_topic
from blog_agent.writer import Writer


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


def write_blog(topic: str, product: str = "") -> None:
    """Full pipeline: research → keywords → write → review."""
    print(f"\n🔍 Researching: {topic}")
    research_brief = research_topic(topic)

    keywords = extract_keywords(research_brief)
    print(f"🔑 Keywords: {', '.join(keywords)}")

    print(f"\n✍️ Writing...")
    w = Writer()
    result = w.full_pipeline(research_brief, keywords)

    print("\n" + "=" * 60)
    print("=== DRAFT ===")
    print("=" * 60)
    print(result["draft"])

    print("\n" + "=" * 60)
    print("=== REVIEW ===")
    print("=" * 60)
    print(result["review"])

    # Save draft to file
    safe_topic = topic.lower().replace(" ", "-").replace("/", "-")
    path = os.path.join(os.path.dirname(__file__), "..", f"{safe_topic}.md")
    with open(path, "w") as f:
        f.write(result["draft"])
    print(f"\n💾 Draft saved to {path}")


def main():
    parser = argparse.ArgumentParser(description="AI Blog Writer")
    parser.add_argument("topic", help="The topic to write about")
    parser.add_argument("--product", default="", help="Product name (for SEO context)")
    args = parser.parse_args()

    write_blog(args.topic, args.product)


if __name__ == "__main__":
    main()
