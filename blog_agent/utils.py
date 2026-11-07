from dotenv import load_dotenv
load_dotenv()

import os
from openai import OpenAI


def get_client():
    return OpenAI(
        api_key="not-needed",
        base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:8000/v1"),
        max_retries=0,
    )


def chat(prompt: str, model: str | None = None, max_tokens: int = 3000) -> str:
    """Simple chat helper for Splash's Qwen3.6 (disables reasoning mode)."""
    client = get_client()
    model = model or os.environ.get("OPENAI_MODEL", "")

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        reasoning_effort="none",
    )

    return resp.choices[0].message.content or ""


if __name__ == "__main__":
    resp = chat("Say hello in one word.")
    print(f"Response: {resp}")
