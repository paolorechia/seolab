"""
Blog Agent — end-to-end blog writing pipeline.

Commands:
    add-product "Product Name" --description "..."   Create a product
    plan "Product Name" --description "..."           Research → Topics
    write --topic "topic" --product "Product Name"    Write → Review → Edit → Human

Usage:
    uv run python -m blog_agent add-product Cohearo --description "On-device transcription app"
    uv run python -m blog_agent plan Cohearo --description "..."
    uv run python -m blog_agent write --topic "Why on-device beats cloud AI" --product Cohearo
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


def cmd_add_product(name: str, description: str = "") -> int:
    """Create a product. No audience — audience is part of the plan."""
    product_id = create_product(name, description, "")
    print(f"✓ Created product: {name} (id={product_id})")
    return product_id


def cmd_plan(name: str, description: str = "", audience: str = "") -> dict:
    """Generate content plan for a product.

    Research loop → generates topics, saves to DB.
    """
    # Ensure product exists
    product = get_product(name)
    if product:
        product_id = product["id"]
    else:
        product_id = create_product(name, description, audience)

    print(f"\n📊 Researching & Planning for: {name}")

    # Research the product/competitors
    research_brief = research_topic(description if description else name)

    # Generate topics from research + product context
    planner = ProductKeywordPlanner(name, description, audience)
    plan = planner.full_plan()

    print(f"\n📦 Keyword Planner results:")
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
        except Exception as e:
            print(f"  ⚠️ Failed: {e}", file=sys.stderr)

    for comp in plan["comparisons"][:5]:
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
            print(f"  ⚠️ Failed: {e}", file=sys.stderr)

    # Save research brief
    slug = name.lower().replace(" ", "-").replace("/", "-")
    content_path = get_content_path(name)
    save_md(content_path, "research_brief", research_brief)

    plan["audiences"] = []
    return plan


def write_article(
    topic: str,
    product: str = "",
    product_description: str = "",
    iterations: int = 2,
    human_loop: bool = False,
    batch: bool = False,
    fast: bool = False,
) -> str:
    """Write a blog article.

    Pipeline:
      write → review
      review → edit → review (loop)
      edit → human → edit (loop)
      human → approve

    Each step saves artifacts to disk for persistence.
    """
    # Ensure product exists
    if product:
        product_id = get_product(product)
        if product_id:
            print(f"\n📦 Using product: {product} (id={product_id})")

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

    # 5. Edit (auto loop)
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
        save_md(content_path, "final", draft)
        print(f"\n💾 Artifacts saved to: {content_path}")
        return draft
    else:
        return draft


def main():
    parser = argparse.ArgumentParser(description="AI Blog Writer")
    subparsers = parser.add_subparsers(dest="cmd", help="Command")

    # add-product subcommand
    add_product_parser = subparsers.add_parser("add-product", help="Create a product")
    add_product_parser.add_argument("name", help="Product name")
    add_product_parser.add_argument("--description", default="", help="Product description")

    # plan subcommand
    plan_parser = subparsers.add_parser("plan", help="Research → Topics for a product")
    plan_parser.add_argument("name", help="Product name")
    plan_parser.add_argument("--description", default="", help="Product description")
    plan_parser.add_argument("--audience", default="", help="Target audience (optional)")

    # write subcommand
    write_parser = subparsers.add_parser("write", help="Write a blog post")
    write_parser.add_argument("--topic", required=True, help="The topic to write about")
    write_parser.add_argument("--product", default="", help="Product name")
    write_parser.add_argument("--product-desc", default="", help="Product description")
    write_parser.add_argument("--iterations", type=int, default=2, help="Edit iterations")
    write_parser.add_argument("--loop", action="store_true", help="Human review")
    write_parser.add_argument("--print", action="store_true", help="Print to stdout")
    write_parser.add_argument("--batch", action="store_true", help="CI mode")
    write_parser.add_argument("--fast", action="store_true", help="Skip edit loop")

    args = parser.parse_args()

    if args.cmd == "add-product":
        product_id = cmd_add_product(args.name, args.description)
        return

    if args.cmd == "plan":
        plan = cmd_plan(
            args.name,
            args.description,
            args.audience,
        )
        return

    if args.cmd == "write":
        draft = write_article(
            topic=args.topic,
            product=args.product,
            product_description=args.product_desc or "",
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
