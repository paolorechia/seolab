"""
Blog Agent — end-to-end blog writing pipeline.

Commands:
    add-product "Product Name" --description "..." --audience "..."   Create a product
    plan "Product Name" --description "..." --audience "..."          Generate content plan
    write --topic "topic" --product "Product Name"                    Write article

Usage:
    uv run python -m blog_agent add-product Cohearo --description "On-device transcription app" --audience "knowledge workers"
    uv run python -m blog_agent plan Cohearo --description "On-device transcription app" --audience "knowledge workers"
    uv run python -m blog_agent write --topic "Why on-device transcription beats cloud AI" --product "Cohearo" --product-desc "On-device transcription app" --audience "knowledge workers" --fast --batch
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
from blog_agent.persistence import *


def cmd_add_product(name: str, description: str = "", audience: str = "") -> int:
    """Create a product. Returns product id."""
    product_id = create_product(name, description, audience)
    print(f"✓ Created product: {name} (id={product_id})")
    return product_id


def cmd_plan(name: str, description: str = "", audience: str = "") -> dict:
    """Generate content plan for a product.

    Returns plan dict. Saves topics to DB.
    """
    # Ensure product exists
    product = get_product(name)
    if product:
        product_id = product["id"]
    else:
        product_id = create_product(name, description, audience)

    planner = ProductKeywordPlanner(name, description, audience)
    plan = planner.full_plan()

    print(f"\n📦 Product Keyword Planner for: {name}")
    print(planner.plan_to_text(plan))

    # Save topics to DB
    for topic_data in plan["topics"]:
        try:
            add_topic(
                product_id,
                title=topic_data.get("topic_title", ""),
                intent=topic_data.get("intent", ""),
                primary_keyword=topic_data.get("primary_keyword", ""),
                supporting_keywords=topic_data.get("supporting_keywords", []),
                content_angle=topic_data.get("content_angle", ""),
            )
            print(f"  ✓ Added topic: {topic_data.get('topic_title', '')[:60]}...", file=sys.stderr)
        except Exception as e:
            print(f"  ✗ Failed to add topic: {e}", file=sys.stderr)

    # Save comparisons to DB (as topics with special intent)
    for comp in plan["comparisons"][:5]:  # Top 5 comparisons
        try:
            add_topic(
                product_id,
                title=comp.get("topic_title", ""),
                intent="commercial investigation",
                primary_keyword=comp.get("primary_keyword", ""),
                supporting_keywords=comp.get("supporting_keywords", []),
                content_angle=f"Competitive comparison angle for {name}",
            )
        except Exception as e:
            print(f"  ✗ Failed to add comparison: {e}", file=sys.stderr)

    # Save audiences to DB
    plan["audiences"] = []  # Don't save as topics, just return
    return plan


def write_article(
    topic: str,
    product: str = "",
    product_description: str = "",
    audience: str = "",
    product_desc: str = "",
    iterations: int = 2,
    human_loop: bool = False,
    batch: bool = False,
    fast: bool = False,
) -> str:
    """Write a blog article.

    Steps: research → SEO → write → review → edit → [human loop]
    Each step saves artifacts to disk for persistence.
    """
    # Determine product description and audience
    prod_desc = product_desc or product_description
    prod_audience = audience

    # Ensure product exists
    if product:
        product_id = get_product(product)
        if not product_id:
            product_id = create_product(product, prod_desc, prod_audience)
        print(f"\n📦 Using product: {product} (id={product_id})")
    else:
        product_id = None

    # 1. Research
    print(f"\n🔍 Researching: {topic}")
    research_brief = research_topic(topic)

    # Save research
    if product:
        slug = topic.lower().replace(" ", "-").replace("/", "-")[:50]
        content_path = get_content_path(product, slug)
        save_md(content_path, "research", research_brief)
        print(f"  ✓ Saved research.md")

    # 2. SEO Analyst
    print(f"\n📊 SEO Analysis...")
    seo = SEOAnalyzer()
    seo_brief = seo.full_analysis(topic, research_brief)

    # Save SEO brief
    if product:
        save_json(content_path, "seo", seo_brief)
        print(f"  ✓ Saved seo.json")

    if not batch:
        print(f"\n🔑 Primary keyword: {seo_brief['keywords']['primary']}")
        print(f"🔑 Secondary keywords: {', '.join(seo_brief['keywords']['secondary'][:3])}")
        print(f"🎯 Intent: {seo_brief['intent'].get('intent', 'N/A')}")
        print(f"📰 Titles: {seo_brief['titles'][:2]}")
        print(f"📝 Meta: {seo_brief['meta'][:80]}...")
        print(f"📐 Headings: {len(seo_brief['headings'].get('h2s', []))} H2s")

    # 3. Write
    print(f"\n✍️ Writing...")
    w = Writer()
    draft = w.write(research_brief, seo_brief["keywords"], seo_brief)

    # Save draft
    if product:
        save_md(content_path, "draft", draft)
        print(f"  ✓ Saved draft.md")

    # 4. Review
    print(f"\n🔎 Reviewing...")
    review = w.review(draft)

    # Save review
    if product:
        save_md(content_path, "review", review)
        print(f"  ✓ Saved review.md")

    # 5. Edit
    if fast:
        print(f"\n⏭️ Skipping auto-edit (--fast)")
    else:
        print(f"\n📝 Editing ({iterations} auto-iterations)...")
        e = Editor()
        edit_result = e.edit_with_iteration(
            draft, review, research_brief, max_iterations=iterations
        )
        draft = edit_result["final_draft"]

        # Save edit
        if product:
            save_md(content_path, "edit", draft)
            print(f"  ✓ Saved edit.md")

    # 6. Human loop
    if human_loop:
        print("\n👤 Starting human review loop...")
        draft, feedback = human_approval_loop(
            draft, research_brief, review, max_rounds=5
        )

    # Final save
    if product:
        slug = topic.lower().replace(" ", "-").replace("/", "-")[:50]
        final_path = os.path.join(content_path, "final.md")
        save_md(content_path, "final", draft)
        print(f"  ✓ Saved final.md")

        print(f"\n💾 Artifacts saved to: {content_path}")
        return draft
    else:
        print(f"\n💾 Draft saved to: {topic.lower().replace(' ', '-').replace('/', '-')[:50]}.md")
        return draft


def main():
    parser = argparse.ArgumentParser(description="AI Blog Writer")
    subparsers = parser.add_subparsers(dest="cmd", help="Command")

    # add-product subcommand
    add_product_parser = subparsers.add_parser("add-product", help="Create a product")
    add_product_parser.add_argument("name", help="Product name")
    add_product_parser.add_argument("--description", default="", help="Product description")
    add_product_parser.add_argument("--audience", default="", help="Target audience")

    # plan subcommand
    plan_parser = subparsers.add_parser("plan", help="Generate content plan for a product")
    plan_parser.add_argument("name", help="Product name")
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

    args = parser.parse_args()

    if args.cmd == "add-product":
        product_id = cmd_add_product(args.name, args.description, args.audience)
        return

    if args.cmd == "plan":
        plan = cmd_plan(args.name, args.description, args.audience)
        return

    if args.cmd == "write":
        draft = write_article(
            topic=args.topic,
            product=args.product,
            product_description=args.product_desc or "",
            audience=args.audience,
            product_desc=args.product_desc or "",
            iterations=args.iterations,
            human_loop=args.loop,
            batch=args.batch,
            fast=args.fast,
        )

        if args.print:
            print(draft)
        return

    # If no subcommand was provided, show help
    parser.print_help()


if __name__ == "__main__":
    main()
