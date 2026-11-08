"""Product Keyword Planner — generates keyword topics from product context.

Takes a product and optionally a description, then produces:
- Content topics (clusters around the product)
- Product-aware keywords (informational + commercial intent)
- Content angles (based on product positioning vs competitors)
- Target audience segments
"""

from blog_agent.utils import chat


TOPIC_GENERATOR_PROMPT = """You are a content strategist generating blog topics for a product.

Product: {product}
{product_description}
Target audience: {audience}

Based on this product, generate 5-8 blog topic ideas that would drive relevant organic traffic.
For each topic, provide:
- topic_title: a clear topic title
- search_intent: the likely search intent (informational | commercial investigation | transactional)
- primary_keyword: the main keyword phrase for this topic
- supporting_keywords: 3-4 related keywords (comma-separated)
- content_angle: the unique angle from the product's perspective

Requirements:
- Mix of informational (top-funnel) and commercial (mid-funnel) topics
- Topics should be specific enough to write about, broad enough to drive traffic
- Angles should leverage the product's unique positioning (not generic content)
- Target audience context should inform which topics to prioritize

Return in this exact format for each topic:
topic: <title>
intent: <type>
primary_keyword: <keyword>
supporting_keywords: <comma-separated>
content_angle: <description>
"""


COMPARISON_KEYWORDS_PROMPT = """You are an SEO analyst identifying comparison opportunities for a product.

Product: {product}
{product_description}

Identify relevant comparison/alternative topics where our product should compete:
- Direct product-vs-product comparisons
- "Best of" roundups where we compete
- Alternatives-to comparisons
- Feature-specific comparisons

Return in this exact format:
1. <comparison topic title> | primary: <keyword> | secondary: <comma-separated>
2. ...

Only include comparisons where our product is a legitimate competitor."""


AUDIENCE_KEYWORDS_PROMPT = """You are an SEO analyst mapping audience segments to keyword clusters.

Product: {product}
{product_description}
Target audience: {audience}

Identify which audience segments are most valuable and their corresponding keyword clusters:
- Audience segment: the specific user persona
- Pain points: what they're trying to solve
- Primary keyword: their main search intent
- Content format: what content type serves them best (guide, comparison, tutorial, etc.)

Return in this format:
segment: <audience description>
pain_point: <what they're trying to solve>
primary_keyword: <their main keyword>
content_format: <guide|comparison|tutorial|overview>
"""


class ProductKeywordPlanner:
    def __init__(self, product: str, product_description: str = "", audience: str = ""):
        self.product = product
        self.product_description = product_description
        self.audience = audience

    def generate_topics(self) -> list[dict]:
        """Generate blog topic clusters around the product."""
        desc = f"Product description: {self.product_description}\n" if self.product_description else ""
        result = chat(
            TOPIC_GENERATOR_PROMPT.format(
                product=self.product,
                product_description=desc,
                audience=self.audience,
            ),
            max_tokens=2000,
        )

        topics = []
        current = {}
        for line in result.strip().split("\n"):
            line = line.strip()
            if line.startswith("topic:"):
                if current:
                    topics.append(current)
                current = {"topic_title": line[6:].strip()}
            elif line.startswith("intent:"):
                current["intent"] = line[7:].strip()
            elif line.startswith("primary_keyword:"):
                current["primary_keyword"] = line[16:].strip()
            elif line.startswith("supporting_keywords:"):
                current["supporting_keywords"] = [
                    k.strip() for k in line[20:].split(",") if len(k.strip()) > 3
                ]
            elif line.startswith("content_angle:"):
                current["content_angle"] = line[16:].strip()

        if current:
            topics.append(current)

        return topics[:8]

    def comparison_keywords(self) -> list[dict]:
        """Generate competitor comparison opportunities."""
        desc = f"Product description: {self.product_description}\n" if self.product_description else ""
        result = chat(
            COMPARISON_KEYWORDS_PROMPT.format(
                product=self.product,
                product_description=desc,
            ),
            max_tokens=1500,
        )

        comparisons = []
        for line in result.strip().split("\n"):
            line = line.strip()
            if not line or (line[0].isdigit() and '.' not in line and ':' not in line):
                continue

            # Parse "1. <topic> | primary: <kw> | secondary: <kw>"
            import re
            match = re.match(r"\d+\.\s*(.+?)\s*\|\s*primary:\s*(.+?)\s*\|\s*secondary:\s*(.+)", line)
            if match:
                comparisons.append({
                    "topic_title": match.group(1).strip(),
                    "primary_keyword": match.group(2).strip(),
                    "supporting_keywords": [
                        k.strip() for k in match.group(3).split(",") if len(k.strip()) > 3
                    ],
                })

        return comparisons

    def audience_mapping(self) -> list[dict]:
        """Map audience segments to keyword clusters."""
        desc = f"Product description: {self.product_description}\n" if self.product_description else ""
        result = chat(
            AUDIENCE_KEYWORDS_PROMPT.format(
                product=self.product,
                product_description=desc,
                audience=self.audience,
            ),
            max_tokens=1500,
        )

        segments = []
        current = {}
        for line in result.strip().split("\n"):
            line = line.strip()
            if not line:
                if current:
                    segments.append(current)
                current = {}
                continue

            if line.startswith("segment:"):
                current["segment"] = line[8:].strip()
            elif line.startswith("pain_point:"):
                current["pain_point"] = line[11:].strip()
            elif line.startswith("primary_keyword:"):
                current["primary_keyword"] = line[16:].strip()
            elif line.startswith("content_format:"):
                current["content_format"] = line[17:].strip()

        if current:
            segments.append(current)

        return segments

    def full_plan(self) -> dict:
        """Generate complete product content plan.

        Returns:
            {
                "product": product_name,
                "topics": [...],
                "comparisons": [...],
                "audiences": [...],
            }
        """
        topics = self.generate_topics()
        comparisons = self.comparison_keywords()
        audiences = self.audience_mapping()

        return {
            "product": self.product,
            "topics": topics,
            "comparisons": comparisons,
            "audiences": audiences,
        }

    def plan_to_text(self, plan: dict) -> str:
        """Format the plan for display."""
        lines = [
            f"Content Plan for: {plan['product']}\n",
            "",
            f"📚 Topics ({len(plan['topics'])}):",
        ]
        for i, t in enumerate(plan["topics"], 1):
            lines.append(f"\n{i}. {t['topic_title']}")
            lines.append(f"   Intent: {t['intent']}")
            lines.append(f"   Primary keyword: {t['primary_keyword']}")
            lines.append(f"   Supporting: {', '.join(t['supporting_keywords'][:2])}")
            lines.append(f"   Angle: {t['content_angle'][:80]}...")

        lines.append(f"\n🔍 Comparisons ({len(plan['comparisons'])}):\n")
        for c in plan["comparisons"][:5]:
            lines.append(f"  - {c['topic_title']}")

        lines.append(f"\n👥 Audience Segments ({len(plan['audiences'])}):\n")
        for a in plan["audiences"][:3]:
            lines.append(f"  - {a['segment']}: {a['pain_point']}")

        return "\n".join(lines)
