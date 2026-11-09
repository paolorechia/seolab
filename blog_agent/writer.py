"""
Writer agent — produces blog drafts using Clarity methodology.

The writer follows Clarity's order of work:
  1. Truth and scope (inventory claims, attribution, examples)
  2. Substance (find the real point)
  3. Development (paragraphs depend on each other)
  4. Sentences (remove formulaic machinery)
  5. Craft (restore concreteness, rhythm, voice)

It also includes a self-review pass using Clarity's review format.
"""

from blog_agent.utils import chat


# ──────────────────────────────────────────────
# Writer prompt — carries Clarity methodology
# ──────────────────────────────────────────────

WRITER_PROMPT = """You are a professional tech writer who writes **marketing-driven** blog posts.
You follow the Clarity writing methodology — substance over style, truth over polish — but your goal is to **sell {product_name}**, not to be neutral.

{product_name} is the product you are writing about.

## Audience

The target audience for this piece:
{audience}

Write for this audience specifically — use their language, address their pain points, and speak to their situation.

## Input

Research brief:
{research_brief}

Target keywords: {keywords}

Product website context (features, specs, pricing, capabilities from {product_name}'s site):
{product_website_context}

## ⚠️ CRITICAL: Facts and Evidence

You must ONLY use facts, numbers, names, dates, and claims from the research brief above.

- DO NOT invent test results, studies, benchmarks, or surveys
- DO NOT make up statistics about market share, valuation, or user counts
- DO NOT claim specific performance numbers unless they appear in the research brief
- If you need specific evidence that isn't in the brief, use `[TK: need specific evidence]`
- It is better to be vague but true than specific but fabricated

## Product Integration Rules

1. **Name {product_name} in the opening paragraph.** Introduce it as the solution to the problem.
2. **Mention {product_name} at least 6-8 times throughout the piece.** Not once and done.
3. **Use specific features from the website context as proof.** When you claim something works, reference a real feature (e.g., "Cohearo captures audio directly from the app source, no bot needed").
4. **Position {product_name} against competitors.** If the piece compares approaches, make {product_name} the clear winner with specific differentiators.
5. **In the closing**, name {product_name} with a clear call to action.
6. **Never write generic content.** Every paragraph should either advance the argument OR show how {product_name} solves the problem.

## Job of the piece

- Medium: **Marketing blog post** — content that sells {product_name}
- Reader: {audience}
- Outcome: The reader should understand the problem, see why {product_name} is the solution, and want to try it
- Register: **Persuasive explanation** — make the case with specific evidence, not fluff

## Order of work

1. **Truth and scope** — Use only facts, names, numbers, and claims from the research brief. Do not invent.
2. **Substance** — Find the real point this piece makes. What problem does {product_name} solve?
3. **Development** — Each paragraph should answer what the previous raised, or show a consequence.
4. **Sentences** — Remove inflated words (important, crucial, pivotal, transformative) unless a specific mechanism supports them.
5. **Craft** — Add concrete material. Can the reader see, hear, or feel anything?

## Watch for these patterns (remove if formulaic)

- Hedges: may, might, could, arguably, potentially, somewhat
- Boosters: crucial, essential, transformative, groundbreaking, pivotal
- Signpost openers: Moreover, Furthermore, Additionally, Consequently, Ultimately
- Stock closers: In conclusion, Ultimately, The future belongs to...
- Model lexis: delve, tapestry, landscape, showcase, leverage, foster, underscore, navigate, myriad, robust, seamless
- Abstract actors: "data speaks", "the decision drives"
- Formula carrying the argument: triads, "not X but Y", balanced threes

## Anchors you MUST include

- Specific numbers, dates, and names from the research
- {product_name} with specific features/benefits from the website context above (name it early and often)
- Real company names, product names, tool names (for comparison context)
- Direct quotes where available
- Concrete examples or incidents

## SEO Heading Structure

{heading_structure}

Follow this exact heading hierarchy:
- Use the H1 as your opening headline (formatted as markdown # heading)
- Use each H2 as a section heading (formatted as markdown ## heading)
- Use H3s under their parent H2s (formatted as markdown ### heading)
- Do NOT add extra headings not in this structure

## SEO integration

Include the target keywords naturally where they fit. Do not force them.

## Self-check before writing

Before you write, think through:
- What is the one thing a reader should carry away?
- What facts, numbers, names are available to support it?
- **Have I named {product_name} enough? Am I selling it or just describing the topic?**
- What could go wrong in the opening?
- What section would make this feel generic? Cut it.

Now write the full blog post.
"""

# ──────────────────────────────────────────────
# Review prompt — Clarity review format
# ──────────────────────────────────────────────

REVIEW_PROMPT = """You are a senior editor using the Clarity review methodology.
Review the following blog post draft against these criteria.

## Product Mention Check

First, check: **Does this piece mention {product_name} at least 6-8 times?**
- If not, this is the #1 issue to fix.
- List every instance where the product is mentioned.
- Flag sections that are entirely generic and should reference the product.

## Audience Fit

The piece is written for: {audience}
- Does the language and tone match this audience?
- Are the pain points and examples relevant to them?

## Review format

Provide a piece-level diagnosis:
```
Job:          medium, reader, intended outcome
Substance:    what the piece specifically contributes or what is missing
Trust:        factual support, attribution, any gaps
Development:  how material progresses; is it list-like or repetitive?
Voice:        where it reads as authentic vs generic model register
Ending:       does it stop on the last useful thought?
Top fixes:    the 2-3 changes with the largest expected gain
```

Then provide passage-level findings for material issues:
```
Passage:      short quote locating the issue
Verdict:      keep / revise / ask-author / cut
Pattern:      name the issue (e.g., importance-without-mechanism, surface-residue, formulaic)
Why:          what the passage does instead of its intended job
Suggestion:   supported replacement or precise question
```

Do NOT rewrite. Only review and diagnose. Be specific. Quote passages when locating issues.

## Draft to review:
{draft}
"""


# ──────────────────────────────────────────────
# Writer class
# ──────────────────────────────────────────────


class Writer:
    def __init__(self, model: str | None = None):
        self.model = model

    def write(self, research_brief: str, keywords: list[str] = None, seo_brief: dict = None,
              product_name: str = "", product_context: str = "", audience: str = "") -> str:
        """Produce a blog draft from research brief and keywords.

        Args:
            research_brief: Raw research from DuckDuckGo
            keywords: List of target keywords
            seo_brief: Optional SEO analysis (headings, titles, meta)
            product_name: Product name (for anchoring)
            product_context: Full website crawl context
            audience: Target audience description
        """
        keywords_str = " ".join(keywords) if keywords else "No specific keywords"
        product_context_str = product_context if product_context else "No website context available."
        product_name_str = product_name if product_name else "the product"
        audience_str = audience if audience else "Tech professionals"

        # Build heading structure string
        if seo_brief and "headings" in seo_brief:
            headings = seo_brief["headings"]
            structure = f"""
H1: {headings.get('h1', '')}

"""
            for h2 in headings.get("h2s", []):
                structure += f"## {h2}\n"
                for h3 in headings.get("h3s", {}).get(h2, []):
                    structure += f"  - {h3}\n"
        else:
            structure = "No specific heading structure provided. Create your own."

        prompt = WRITER_PROMPT.format(
            research_brief=research_brief,
            keywords=keywords_str,
            product_website_context=product_context_str,
            product_name=product_name_str,
            audience=audience_str,
            heading_structure=structure,
        )

        draft = chat(prompt, model=self.model, max_tokens=3000)
        return draft

    def review(self, draft: str, product_name: str = "", audience: str = "") -> str:
        """Self-review a draft using Clarity methodology."""
        prompt = REVIEW_PROMPT.format(draft=draft, product_name=product_name, audience=audience)
        return chat(prompt, model=self.model, max_tokens=2000)

    def full_pipeline(self, research_brief: str, keywords: list[str] = None, seo_brief: dict = None) -> dict:
        """Write → Review → return both."""
        draft = self.write(research_brief, keywords, seo_brief)
        review = self.review(draft)
        return {"draft": draft, "review": review}
