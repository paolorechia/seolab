"""
Blog Agent — end-to-end blog writing pipeline.

Usage:
    # Generate a content plan for a product
    uv run python -m blog_agent plan "Product Name" --description "..." --audience "..."

    # Write a blog post (with optional product context)
    uv run python -m blog_agent --topic "topic"
    uv run python -m blog_agent --topic "topic" --product "Product Name"
    uv run python -m blog_agent --topic "topic" --loop --fast --batch
"""

import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blog_agent.research import research_topic
from blog_agent.seo import SEOAnalyzer
from blog_agent.writer import Writer
from blog_agent.editor import Editor
from blog_agent.human_loop import human_approval_loop
from blog_agent.keyword_planner import ProductKeywordPlanner


def generate_plan(product: str, product_description: str = "", audience: str = "") -> dict:
    """Generate a content plan from product context."""
    print(f"\n📦 Product Keyword Planner for: {product}")
    planner = ProductKeywordPlanner(product, product_description, audience)
    plan = planner.full_plan()
    print(planner.plan_to_text(plan))
    return plan


def write_blog(
    topic: str,
    product: str = "",
    product_description: str = "",
    audience: str = "",
    iterations: int = 2,
    human_loop: bool = False,
    batch: bool = False,
    fast: bool = False,
) -> str:
    """Full pipeline: research → SEO → write → review → edit → [human loop]."""
    print(f"\n🔍 Researching: {topic}")
    research_brief = research_topic(topic)

    print(f"\n📊 SEO Analysis...")
    seo = SEOAnalyzer()
    seo_brief = seo.full_analysis(topic, research_brief)

    if product:
        print(f"\n📦 Enriching with product context: {product}")
        seo_brief["product_context"] = {
            "product": product,
            "description": product_description,
            "audience": audience,
        }

    if not batch:
        print(f"\n🔑 Primary keyword: {seo_brief['keywords']['primary']}")
        print(f"🔑 Secondary keywords: {', '.join(seo_brief['keywords']['secondary'][:3])}")
        print(f"🎯 Intent: {seo_brief['intent'].get('intent', 'N/A')}")
        print(f"📰 Titles: {seo_brief['titles'][:2]}")
        print(f"📝 Meta: {seo_brief['meta'][:80]}...")
        print(f"📐 Headings: {len(seo_brief['headings'].get('h2s', []))} H2s")

    print(f"\n✍️ Writing...")
    w = Writer()
    draft = w.write(research_brief, seo_brief["keywords"], seo_brief)

    print(f"\n🔎 Reviewing...")
    review = w.review(draft)

    if fast:
        print(f"\n⏭️ Skipping auto-edit (--fast)")
    else:
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

    safe_topic = topic.lower().replace(" ", "-").replace("/", "-")
    path = os.path.join(os.path.dirname(__file__), "..", f"{safe_topic}.md")
    with open(path, "w") as f:
        f.write(draft)

    if batch:
        sys.exit(0)

    print(f"\n💾 Draft saved to {path}")
    return draft


def main():
    parser = argparse.ArgumentParser(description="AI Blog Writer")

    # Subcommands
    subparsers = parser.add_subparsers(dest="cmd", help="Command")

    # plan subcommand
    plan_parser = subparsers.add_parser("plan", help="Generate content plan")
    plan_parser.add_argument("product", help="Product name")
    plan_parser.add_argument("--description", default="", help="Product description")
    plan_parser.add_argument("--audience", default="", help="Target audience")

    # write subcommand
    write_parser = subparsers.add_parser("write", help="Write a blog post")
    write_parser.add_argument("--topic", required=True, help="The topic to write about")
    write_parser.add_argument("--product", default="", help="Product name")
    write_parser.add_argument("--product-desc", default="", help="Product description")
    write_parser.add_argument("--audience", default="", help="Target audience")
    write_parser.add_argument("--iterations", type=int, default=2, help="Edit iterations")
    write_parser.add_argument("--loop", action="store_true", help="Human review")
    write_parser.add_argument("--print", action="store_true", help="Print to stdout")
    write_parser.add_argument("--batch", action="store_true", help="CI mode")
    write_parser.add_argument("--fast", action="store_true", help="Skip edit loop")

    # Direct mode (no subcommand)
    parser.add_argument("--topic", required=False, help="The topic to write about")
    parser.add_argument("--product", default="", help="Product name")
    parser.add_argument("--product-desc", default="", help="Product description")
    parser.add_argument("--audience", default="", help="Target audience")
    parser.add_argument("--iterations", type=int, default=2, help="Edit iterations")
    parser.add_argument("--loop", action="store_true", help="Human review")
    parser.add_argument("--print", action="store_true", help="Print to stdout")
    parser.add_argument("--batch", action="store_true", help="CI mode")
    parser.add_argument("--fast", action="store_true", help="Skip edit loop")

    args = parser.parse_args()

    if args.cmd == "plan":
        generate_plan(args.product, args.description, args.audience)
        return

    if args.cmd == "write":
        topic = args.topic
        product = args.product
        product_desc = args.product_desc
        audience = args.audience
        iterations = args.iterations
        human_loop = args.loop
        batch_flag = args.batch
        fast_flag = args.fast
    elif args.cmd is None and args.topic:
        topic = args.topic
        product = args.product
        product_desc = args.product_desc
        audience = args.audience
        iterations = args.iterations
        human_loop = args.loop
        batch_flag = args.batch
        fast_flag = args.fast
    else:
        parser.print_help()
        return

    draft = write_blog(
        topic=topic,
        product=product,
        product_description=product_desc,
        audience=audience,
        iterations=iterations,
        human_loop=human_loop,
        batch=batch_flag,
        fast=fast_flag,
    )

    if args.print:
        print(draft)


if __name__ == "__main__":
    main()
