"""Editor agent — revises drafts based on review feedback using Clarity methodology."""

from blog_agent.utils import chat

EDITOR_PROMPT = """You are a senior editor using the Clarity editing methodology.
Your job is to revise a draft based on review feedback while preserving factual truth.

## Rules

1. **Truth first.** Never invent, strengthen, or change facts, numbers, names, dates, attributions, or quotes. These are protected.
2. **Fix in Clarity order:**
   a. Substance (what's the real point? Add what's missing)
   b. Development (do paragraphs depend on each other?)
   c. Sentences (remove formulaic machinery, inflate words)
   d. Craft (restore concreteness, rhythm, voice)
3. **Use [TK: specific question]** when you need information the research brief didn't supply.
4. **It is better to cut than invent.** If a passage has no factual support, cut it.

## Input

Research brief (fact source — DO NOT invent beyond this):
{research_brief}

Product website context (from crawled pages):
{product_website_context}

Current draft:
{draft}

Review feedback:
{review}

## How to handle review verdicts

- **keep**: Preserve the passage. Do not rewrite unless there's a clear craft issue.
- **revise**: Rewrite the passage using the suggestion. If the suggestion is weak, improve it yourself using Clarity principles.
- **ask-author**: Replace with `[TK: provide specific question]` or make the best factual guess without inventing.
- **cut**: Remove the passage entirely.

## Specific editing principles

- Replace "important", "crucial", "transformative" with the specific mechanism that makes it important
- Replace vague attributions ("research shows") with specific sources or cut
- Replace stock closers ("In conclusion") with the last concrete thought
- Remove triads that are formulaic, keep ones that are earned
- Remove signpost openers (Moreover, Furthermore) when they just chain paragraphs together
- Ensure every claim has a specific name, number, or example beside it

## Output

Return the full revised draft. Do not explain your changes. Do not keep the review format.
Just return the clean, revised article text.

Now edit the draft.
"""


class Editor:
    def __init__(self, model: str | None = None):
        self.model = model

    def edit(self, draft: str, review: str, research_brief: str = "",
             product_context: str = "") -> str:
        """Revise draft based on review feedback."""
        prompt = EDITOR_PROMPT.format(
            research_brief=research_brief,
            product_website_context=product_context if product_context else "No website context available.",
            draft=draft,
            review=review,
        )
        return chat(prompt, model=self.model, max_tokens=4000)

    def edit_with_iteration(
        self,
        draft: str,
        review: str,
        research_brief: str = "",
        product_context: str = "",
        max_iterations: int = 3,
    ) -> dict:
        """Edit → Review → Edit loop. Returns all iterations."""
        history = []

        for i in range(max_iterations):
            edited = self.edit(draft, review, research_brief, product_context)
            review_again = chat(
                EDITOR_REVIEW_PROMPT.format(draft=edited),
                model=self.model,
                max_tokens=2000,
            )
            history.append({
                "iteration": i,
                "draft": draft,
                "review": review,
                "edited": edited,
                "new_review": review_again,
            })

            # Check if review improved enough to stop early
            if i == max_iterations - 1:
                break

            draft = edited
            review = review_again

        return {"history": history, "final_draft": edited}


EDITOR_REVIEW_PROMPT = """You are reviewing a revised draft. Compare it to the original review.

Did the changes address the main issues? Or are they the same problems in new clothes?

Be brief. One paragraph diagnosis. Focus on the biggest remaining gap.

Draft to review:
{draft}
"""
