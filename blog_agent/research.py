import ddgs
from blog_agent.utils import chat


def research_topic(topic: str, max_results: int = 5) -> str:
    """Research a topic using DuckDuckGo with fallback strategies."""
    client = ddgs.DDGS()

    # Try primary search first
    results = _search(client, topic, max_results)

    # Fallback 1: broader keywords
    if not results:
        results = _search(client, _broader_keywords(topic), max_results)

    # Fallback 2: generic LLM brief if all searches fail
    if not results:
        return _fallback_brief(topic)

    # Format results for LLM
    formatted = []
    for i, r in enumerate(results[:max_results], 1):
        formatted.append(f"{i}. [{r['title']}]({r['href']})\n{r['body']}\n")

    prompt = f"""Research the following topic: {topic}

Here are the search results:

{chr(10).join(formatted)}

Based on these results, identify:
1. Key subtopics worth writing about
2. Any angles or perspectives that stand out
3. Notable facts, statistics, or trends mentioned

Return a structured research brief. Be specific and detailed."""

    return chat(prompt, max_tokens=1500)


def _search(client: ddgs.DDGS, query: str, max_results: int) -> list:
    """Attempt a search, return results or empty list."""
    try:
        return list(client.text(query, max_results=max_results))
    except Exception:
        return []


def _broader_keywords(topic: str) -> str:
    """Generate broader search keywords from the topic."""
    return chat(
        f"Convert this topic into 3 broader keyword phrases for search: '{topic}'. "
        "Return them comma-separated. One line only."
    )


def _fallback_brief(topic: str) -> str:
    """Generate a brief from LLM knowledge when search fails."""
    prompt = f"""Topic: {topic}

Search failed to find results. Provide a structured research brief based on your knowledge:
1. Key subtopics worth writing about
2. Angles and perspectives
3. Notable facts, statistics, or trends mentioned

Return a structured research brief. Be specific and detailed."""
    return chat(prompt, max_tokens=1500)


if __name__ == "__main__":
    result = research_topic("AI coding assistants 2025")
    print(result[:500])
