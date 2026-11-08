"""Product page scraper — fetches and parses product webpages for content context."""

import re
from urllib.parse import urlparse
import os


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    clean = re.compile(r"<[^>]+>")
    return clean.sub("", text)


def extract_text_from_html(html: str, max_chars: int = 8000) -> str:
    """Extract readable text from HTML, stripping scripts/styles/links."""
    # Remove scripts and styles
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--.*?-->', "", html, flags=re.DOTALL | re.IGNORECASE)

    # Replace <br> and <p> with newlines
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</h[1-6]>", "\n", html, flags=re.IGNORECASE)

    # Strip tags
    text = strip_html_tags(html)

    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    # Truncate if too long
    if len(text) > max_chars:
        # Try to cut at a paragraph boundary
        cutoff = text[:max_chars]
        last_newline = cutoff.rfind("\n\n")
        if last_newline > 0:
            text = text[:last_newline]
        else:
            text = cutoff + "\n\n[truncated]"

    return text


def fetch_product_page(url: str, max_chars: int = 8000) -> str | None:
    """Fetch a product webpage and extract readable text.

    Uses standard urllib (no external dependencies). Falls back to None on failure.
    """
    import urllib.request
    import urllib.error

    try:
        # Try a few user agents
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode(resp.headers.get("charset", "utf-8"), errors="replace")
        return extract_text_from_html(html, max_chars)
    except Exception as e:
        print(f"  ⚠️ Could not fetch {url}: {e}")
        return None


def save_product_info(content_path: str, url: str, text: str) -> str:
    """Save scraped product info to disk."""
    path = os.path.join(content_path, "product_info.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(f"# Product Page\n\n")
        f.write(f"Source: {url}\n\n")
        f.write(f"{text}\n")
    return path


def fetch_and_save(url: str, content_path: str) -> str:
    """Fetch a page and save it to the product directory.

    Returns:
        The extracted text (empty string if fetch failed).
    """
    print(f"\n🌐 Fetching product page: {url}")
    text = fetch_product_page(url)
    if text:
        save_product_info(content_path, url, text)
        print(f"  ✓ Saved product_info.md ({len(text)} chars)")
        return text
    return ""
