import ddgs
from blog_agent.utils import chat


def research_topic(topic: str, max_results: int = 5) -> str:
    """Research a topic using DuckDuckGo."""
    client = ddgs.DDGS()
    results = list(client.text(topic, max_results=max_results))

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


if __name__ == "__main__":
    result = research_topic("AI coding assistants 2025")
    print(result[:500])
