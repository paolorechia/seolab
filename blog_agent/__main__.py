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
from blog_agent.persistence import add_audience_segment, get_content_path, _get_conn
from blog_agent.persistence import *

from blog_agent.crawler import crawl_product



def cmd_add_product(name: str, description: str = "", audience: str = "", url: str = "") -> int:
    """Create a product. No audience — audience is part of the plan."""
    product_id = create_product(name, description, audience, url)
    print(f"✓ Created product: {name} (id={product_id})")
    return product_id


def cmd_plan(name: str, description: str = "", audience: str = "", url: str = "") -> dict:
    """Generate content plan for a product.

    Research loop → generates topics, saves to DB.
    """
    # Ensure product exists
    product = get_product(name)
    if product:
        product_id = product["id"]
        # If we have a URL but product has none, update it
        if url and not product.get("url", ""):
            conn = _get_conn()
            conn.execute("UPDATE products SET url = ? WHERE id = ?", (url, product_id))
            conn.commit()
            conn.close()
            product["url"] = url
    else:
        product_id = create_product(name, description, audience, url)

    print(f"\n📊 Researching & Planning for: {name}")

    # Crawl product website if URL provided
    product_context = ""
    product_path = get_content_path(name)
    if url:
        product_context = crawl_product(url, product_path, max_pages=100)
        if product_context:
            print(f"  ✓ Website context saved")

    # Research the product/competitors
    research_brief = research_topic(description if description else name)

    # Generate topics from research + product context
    planner = ProductKeywordPlanner(name, description, audience, product_context)
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

    # Save audience segments
    for seg in plan["audiences"]:
        try:
            add_audience_segment(
                product_id,
                segment=seg.get("segment", ""),
                pain_point=seg.get("pain_point", ""),
                primary_keyword=seg.get("primary_keyword", ""),
                content_format=seg.get("content_format", ""),
            )
        except Exception as e:
            print(f"  ⚠️ Failed to save audience segment: {e}", file=sys.stderr)

    # Save research brief
    slug = name.lower().replace(" ", "-").replace("/", "-")
    content_path = get_content_path(name)
    save_md(content_path, "research_brief", research_brief)

    return plan


def write_article(
    topic: str,
    product: str = "",
    product_description: str = "",
    url: str = "",
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
    product_obj = None
    if product:
        product_obj = get_product(product)
        if product_obj:
            print(f"\n📦 Using product: {product} (id={product_obj['id']})")
            # Update URL if provided and not set
            if url and not product_obj.get("url", ""):
                conn = _get_conn()
                conn.execute("UPDATE products SET url = ? WHERE id = ?", (url, product_obj["id"]))
                conn.commit()
                conn.close()
                product_obj["url"] = url

    # Crawl product website if URL provided
    product_context = ""
    product_name = product or "the product"
    product_audience = ""
    if url:
        product_path = get_content_path(product)
        product_context = crawl_product(url, product_path, max_pages=100)
        if product_context:
            print(f"  ✓ Website context saved")

    # Get audience from product record
    if product:
        product_obj = get_product(product)
        if product_obj and product_obj.get("audience", ""):
            product_audience = product_obj["audience"]

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
    draft = w.write(research_brief, seo_brief["keywords"], seo_brief,
                    product_name=product_name, product_context=product_context,
                    audience=product_audience)

    # Save draft
    if product:
        save_md(content_path, "draft", draft)
        print(f"  ✓ Saved draft.md")

    # 4. Review
    print(f"\n🔎 Reviewing...")
    review = w.review(draft, product_name=product_name, audience=product_audience)

    # Save review
    if product:
        save_md(content_path, "review", review)
        print(f"  ✓ Saved review.md")

    # 5. Edit (auto loop)
    print(f"\n📝 Editing ({iterations} auto-iterations)...")
    e = Editor()
    edit_result = e.edit_with_iteration(
        draft, review, research_brief,
        product_name=product_name,
        product_context=product_context,
        audience=product_audience,
        max_iterations=iterations
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


def cmd_write_all(
    product_name: str,
    url: str = "",
    iterations: int = 2,
    human_loop: bool = False,
    batch: bool = False,
    fast: bool = False,
) -> int:
    """Write all unexplored topics for a product.
    
    Returns:
        Number of articles written.
    """
    product = get_product(product_name)
    if not product:
        print(f"❌ Product '{product_name}' not found.")
        return 0

    topics = get_topics(product["id"])
    if not topics:
        print(f"No topics found for {product_name}.")
        return 0

    # Filter: only topics without an article (no final.md or draft.md)
    unexplored = []
    for t in topics:
        slug = t["title"].lower().replace(" ", "-").replace("/", "-")[:50]
        content_path = get_content_path(product_name, slug)
        if not os.path.exists(os.path.join(content_path, "final.md")) and \
           not os.path.exists(os.path.join(content_path, "draft.md")):
            unexplored.append(t)

    if not unexplored:
        print(f"🎉 All {len(topics)} topics for {product_name} have been written.")
        return 0

    print(f"📝 Writing {len(unexplored)} unexplored topic(s) for {product_name}...")
    print(f"   ({len(topics) - len(unexplored)} already done)\n")

    count = 0
    for i, t in enumerate(unexplored, 1):
        print(f"\n{'=' * 60}")
        print(f"📄 Article {i}/{len(unexplored)}: {t['title']}")
        print(f"   Intent: {t.get('intent', 'N/A')}")
        print(f"   Keyword: {t.get('primary_keyword', 'N/A')}")
        print(f"{'=' * 60}")

        try:
            write_article(
                topic=t["title"],
                product=product_name,
                url=url,
                iterations=iterations,
                human_loop=human_loop,
                batch=batch,
                fast=fast,
            )
            count += 1
        except Exception as e:
            print(f"\n⚠️  Failed to write '{t['title']}': {e}", file=sys.stderr)

    print(f"\n✅ Done: {count}/{len(unexplored)} articles written.")
    return count


def main():
    parser = argparse.ArgumentParser(description="AI Blog Writer")
    subparsers = parser.add_subparsers(dest="cmd", help="Command")

    # add-product subcommand
    add_product_parser = subparsers.add_parser("add-product", help="Create a product")
    add_product_parser.add_argument("name", help="Product name")
    add_product_parser.add_argument("--description", default="", help="Product description")
    add_product_parser.add_argument("--audience", default="", help="Target audience")
    add_product_parser.add_argument("--url", default="", help="Product website URL (for scraping)")

    # plan subcommand
    plan_parser = subparsers.add_parser("plan", help="Research → Topics for a product")
    plan_parser.add_argument("name", help="Product name")
    plan_parser.add_argument("--description", default="", help="Product description")
    plan_parser.add_argument("--audience", default="", help="Target audience (optional)")
    plan_parser.add_argument("--url", default="", help="Product website URL (for scraping)")

    # write subcommand
    write_parser = subparsers.add_parser("write", help="Write a blog post")
    write_parser.add_argument("--topic", required=True, help="The topic to write about")
    write_parser.add_argument("--product", default="", help="Product name")
    write_parser.add_argument("--product-desc", default="", help="Product description")
    write_parser.add_argument("--url", default="", help="Product website URL (for scraping)")
    write_parser.add_argument("--iterations", type=int, default=2, help="Edit iterations")
    write_parser.add_argument("--loop", action="store_true", help="Human review")
    write_parser.add_argument("--print", action="store_true", help="Print to stdout")
    write_parser.add_argument("--batch", action="store_true", help="CI mode")
    write_parser.add_argument("--fast", action="store_true", help="Skip edit loop")

    # write-all subcommand
    write_all_parser = subparsers.add_parser("write-all", help="Write all unexplored topics for a product")
    write_all_parser.add_argument("--product", required=True, help="Product name")
    write_all_parser.add_argument("--url", default="", help="Product website URL (for scraping)")
    write_all_parser.add_argument("--iterations", type=int, default=2, help="Edit iterations")
    write_all_parser.add_argument("--loop", action="store_true", help="Human review")
    write_all_parser.add_argument("--batch", action="store_true", help="CI mode")
    write_all_parser.add_argument("--fast", action="store_true", help="Skip edit loop")

    args = parser.parse_args()

    if args.cmd == "add-product":
        product_id = cmd_add_product(args.name, args.description, args.audience, args.url)
        return

    if args.cmd == "plan":
        plan = cmd_plan(
            args.name,
            args.description,
            args.audience,
            args.url,
        )
        return

    if args.cmd == "write":
        draft = write_article(
            topic=args.topic,
            product=args.product,
            product_description=args.product_desc or "",
            url=args.url,
            iterations=args.iterations,
            human_loop=args.loop,
            batch=args.batch,
            fast=args.fast,
        )

        if args.print:
            print(draft)
        return

    if args.cmd == "write-all":
        cmd_write_all(
            product_name=args.product,
            url=args.url,
            iterations=args.iterations,
            human_loop=args.loop,
            batch=args.batch,
            fast=args.fast,
        )
        return

    # If no subcommand was provided, show help
    parser.print_help()


if __name__ == "__main__":
    main()
