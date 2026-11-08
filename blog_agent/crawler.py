"""Recursive product page crawler with per-page summarization and aggregate summary.

Crawls a product website starting from the seed URL:
1. Fetches all pages (internal links only, same domain)
2. Summarizes each page via LLM
3. Produces an aggregate summary of all pages

Each page's summary is saved to disk. The aggregate is saved as `product_context.md`.
The aggregate text is returned so it can be passed to LLM prompts without blowing context.
"""

import re
import os
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from blog_agent.utils import chat


def extract_text_from_html(html: str, max_chars: int = 10000) -> str:
    """Extract readable text from HTML, stripping scripts/styles/navigation."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts, styles, nav, footer, sidebar
    for tag in soup(["script", "style", "nav", "footer", "aside", "header", "noscript"]):
        tag.decompose()

    # Also remove common non-content elements
    for selector in ["a", "button", "input"]:
        for el in soup.select(selector):
            el.decompose()

    # Extract text
    text = soup.get_text(separator="\n")

    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    # Truncate
    if len(text) > max_chars:
        cutoff = text[:max_chars]
        last_newline = cutoff.rfind("\n\n")
        if last_newline > 0:
            text = text[:last_newline]
        else:
            text = cutoff + "\n\n[truncated]"

    return text


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract internal links from HTML (same domain, skip anchors/JS)."""
    soup = BeautifulSoup(html, "html.parser")
    parsed = urlparse(base_url)
    domain = parsed.netloc

    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        # Skip anchors, JS, external links
        if href.startswith("#") or href.startswith("javascript:") or "mailto:" in href:
            continue
        # Make absolute
        absolute = urljoin(base_url, href)
        parsed_link = urlparse(absolute)
        # Only internal links (same domain)
        if parsed_link.netloc == domain:
            links.add(absolute)

    return sorted(links)


def fetch_html(url: str) -> str | None:
    """Fetch HTML from a URL using requests."""
    try:
        import requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
        return resp.text
    except Exception as e:
        print(f"  ⚠️ Could not fetch {url}: {e}")
        return None


def extract_title(html: str) -> str:
    """Extract page title from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    return ""


def summarize_text(text: str, title: str = "") -> str:
    """Summarize a page's text via LLM.

    Caps output at 500 chars per page summary to control total context size.
    """
    prompt = f"""Summarize the following webpage content in a concise, structured format.

{title}

Content:
{text}

Return a summary that captures:
- What this page is about (1-2 sentences)
- Key features, capabilities, or offerings mentioned
- Specific product details, pricing, or technical info
- Any target audiences or use cases mentioned
- Notable quotes or unique claims

Be specific. List concrete features, numbers, and names. Do not invent information."""

    return chat(prompt, max_tokens=500)


class PageCrawler:
    """Crawl a website recursively, summarizing each page."""

    def __init__(self, seed_url: str, max_pages: int = 100, max_text_chars: int = 10000):
        self.seed_url = seed_url
        self.max_pages = max_pages
        self.max_text_chars = max_text_chars
        self.visited: set[str] = set()
        self.queue: list[str] = []
        self.results: dict[str, str] = {}  # url -> summary text

    def _get_domain(self) -> str:
        return urlparse(self.seed_url).netloc

    def _is_internal(self, url: str) -> bool:
        """Check if URL is on the same domain and not a non-content path."""
        parsed = urlparse(url)
        # Same domain check
        if parsed.netloc != self._get_domain():
            return False
        # Skip common non-content paths
        path = parsed.path.lower()
        skip_patterns = [
            "/cdn-cgi/",  # Cloudflare stuff
            "email",  # Email protection
            ".js",  # JavaScript files
            ".css",  # Stylesheets
            ".png",  # Images
            ".jpg",  # Images
            ".svg",  # Images
            ".json",  # JSON files
            "/health",  # Health check
            "/robots.txt",  # Robots.txt
        ]
        for pattern in skip_patterns:
            if pattern in path:
                return False
        return True

    def _add_to_queue(self, url: str):
        """Add URL to queue if not visited, not in queue, and domain matches."""
        if url not in self.visited and url not in self.queue and self._is_internal(url) and "?" not in url:
            self.queue.append(url)

    def crawl(self) -> dict:
        """Run the crawl and return {url: summary} dict."""
        self.visited.add(self.seed_url)

        # Seed: fetch and extract links
        html = fetch_html(self.seed_url)
        if html:
            text = extract_text_from_html(html, self.max_text_chars)
            title = extract_title(html) or self.seed_url
            summary = summarize_text(text, title=title)
            self.results[self.seed_url] = summary

            # Queue internal links
            for link in extract_links(html, self.seed_url):
                self._add_to_queue(link)

        # Iterate: fetch remaining pages
        while len(self.results) < self.max_pages and self.queue:
            url = self.queue.pop(0)

            if url in self.visited:
                continue

            self.visited.add(url)

            html = fetch_html(url)
            if not html:
                continue

            text = extract_text_from_html(html, self.max_text_chars)
            if len(text) < 100:
                continue  # Too short, probably not useful

            title = extract_title(html) or url
            summary = summarize_text(text, title=title)
            self.results[url] = summary

            # Queue new internal links
            for link in extract_links(html, url):
                self._add_to_queue(link)

        return self.results


def generate_aggregate_summary(page_summaries: dict[str, str]) -> str:
    """Generate an aggregate summary from all page summaries.

    Caps combined text at ~10k chars to stay within LLM context limits.
    """
    # Combine all summaries, cap total
    combined = ""
    for url, summary in page_summaries.items():
        combined += f"\n---\nURL: {url}\n{summary}"

    combined = combined[:10000]  # cap combined text

    prompt = f"""You are summarizing the complete website content of a product.
You have been given summaries of every page on the website.

Produce a comprehensive product context document that includes:

1. **Product Overview** — What the product does, in clear terms
2. **Key Features** — List every feature mentioned across all pages, with specifics
3. **Pricing & Plans** — Any pricing tiers, plans, or free tier details
4. **Technical Details** — Supported platforms, languages, integrations, specs
5. **Use Cases** — Who uses it and why
6. **Unique Differentiators** — What makes the product different from competitors
7. **Content & Resources** — Links to documentation, blog, etc.

Be exhaustive. If a page mentions a feature, include it. If pricing is stated, include it exactly.
Do not guess or invent anything not present in the summaries above.

Website summaries:
{combined}"""

    return chat(prompt, max_tokens=2000)


def save_crawl_results(results: dict[str, str], aggregate: str, content_path: str) -> str:
    """Save crawl results to disk.

    Returns:
        File path to the aggregate summary file.
    """
    # Save individual page summaries
    os.makedirs(os.path.join(content_path, "pages"), exist_ok=True)
    for url, summary in results.items():
        # Safe filename from URL
        slug = url.replace("https://", "").replace("http://", "").replace("/", "-").replace(":", "_").replace("?", "_").replace("&", "_").replace("=", "_")[:80]
        filename = os.path.join(content_path, "pages", f"{slug}.md")
        with open(filename, "w") as f:
            f.write(f"# Page Summary\n\n")
            f.write(f"URL: {url}\n\n")
            f.write(f"{summary}\n")

    # Save aggregate
    agg_path = os.path.join(content_path, "product_context.md")
    with open(agg_path, "w") as f:
        f.write(f"# Product Website Context\n\n")
        f.write(f"{aggregate}\n")

    return agg_path


def crawl_product(url: str, content_path: str, max_pages: int = 100) -> str:
    """Run a full crawl with summarization.

    Returns:
        The aggregate summary text content (not the file path).
    """
    print(f"\n🕷️ Crawling {url} (up to {max_pages} pages)...")

    crawler = PageCrawler(url, max_pages=max_pages)
    results = crawler.crawl()

    print(f"  ✓ Crawled {len(results)} page(s)")

    for i, (url, summary) in enumerate(results.items(), 1):
        print(f"    {i}. {url[:60]}... ({len(summary)} chars)")

    # Generate aggregate summary
    print("\n📝 Generating aggregate summary...")
    aggregate = generate_aggregate_summary(results)

    # Save to disk (returns file path)
    save_crawl_results(results, aggregate, content_path)
    print(f"  ✓ Saved product_context.md ({len(aggregate)} chars)")

    # Return the aggregate text content (not the file path)
    return aggregate
