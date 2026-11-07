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

WRITER_PROMPT = """You are a professional tech writer who produces clear, specific, substance-rich blog posts.
You follow the Clarity writing methodology — substance over style, truth over polish.

## Input

Research brief:
{research_brief}

Target keywords: {keywords}

## ⚠️ CRITICAL: Facts and Evidence

You must ONLY use facts, numbers, names, dates, and claims from the research brief above.

- DO NOT invent test results, studies, benchmarks, or surveys
- DO NOT make up statistics about market share, valuation, or user counts
- DO NOT claim specific performance numbers unless they appear in the research brief
- If you need specific evidence that isn't in the brief, use `[TK: need specific evidence]`
- It is better to be vague but true than specific but fabricated

## Job of the piece

- Medium: Blog post for a tech audience
- Reader: Tech professionals who understand the domain
- Outcome: The reader should understand the landscape, form a position, and know what's worth exploring
- Register: Explanation + argument

## Order of work

1. **Truth and scope** — Use only facts, names, numbers, and claims from the research brief. Do not invent.
2. **Substance** — Find the real point this piece makes. What gap does it fill?
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
- Real company names, product names, tool names
- Direct quotes where available
- Concrete examples or incidents

## Structure

Write a full blog post (800-1200 words). Include:
- A strong opening (one specific fact, scene, or claim — not a definition or generic intro)
- 4-6 body sections with descriptive headings
- An ending that stops on the last useful thought (no recap, no generic send-off)

## SEO integration

Include the target keywords naturally where they fit. Do not force them.

## Self-check before writing

Before you write, think through:
- What is the one thing a reader should carry away?
- What facts, numbers, names are available to support it?
- What could go wrong in the opening?
- What section would make this feel generic? Cut it.

Now write the full blog post.
"""

# ──────────────────────────────────────────────
# Review prompt — Clarity review format
# ──────────────────────────────────────────────

REVIEW_PROMPT = """You are a senior editor using the Clarity review methodology.
Review the following blog post draft against these criteria:

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

    def write(self, research_brief: str, keywords: list[str] = None) -> str:
        """Produce a blog draft from research brief and keywords."""
        keywords_str = " ".join(keywords) if keywords else "No specific keywords"

        prompt = WRITER_PROMPT.format(
            research_brief=research_brief,
            keywords=keywords_str,
        )

        draft = chat(prompt, model=self.model, max_tokens=3000)
        return draft

    def review(self, draft: str) -> str:
        """Self-review a draft using Clarity methodology."""
        prompt = REVIEW_PROMPT.format(draft=draft)
        return chat(prompt, model=self.model, max_tokens=2000)

    def full_pipeline(self, research_brief: str, keywords: list[str] = None) -> dict:
        """Write → Review → return both."""
        draft = self.write(research_brief, keywords)
        review = self.review(draft)
        return {"draft": draft, "review": review}
