"""
Content persistence layer.

Stores:
- Products (name, description, audience)
- Topics (title, intent, keywords, angle, status)
- Articles (topic link, slug, status)
- Content artifacts (research, SEO brief, drafts, reviews, edits) as markdown files

Directory structure:
  content.db          ← SQLite for metadata
  content/
    product-name/     ← product directory
      articles/
        article-slug/ ← article directory
          research.md ← DuckDuckGo research
          seo.json    ← SEO brief
          draft.md    ← initial draft
          review.md   ← review feedback
          edit.md     ← edited version
"""

import sqlite3
import json
import os
import sys
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime

# ──────────────────────────────────────────────
# Database paths
# ──────────────────────────────────────────────

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_DIR, "content.db")
CONTENT_DIR = os.path.join(PROJECT_DIR, "content")


# ──────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────


def _get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Get database connection."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DB_PATH):
    """Create tables if they don't exist."""
    conn = _get_conn(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            audience TEXT DEFAULT '',
            url TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            intent TEXT,
            primary_keyword TEXT,
            supporting_keywords TEXT DEFAULT '[]',
            content_angle TEXT,
            status TEXT DEFAULT 'planned',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL,
            slug TEXT NOT NULL,
            status TEXT DEFAULT 'planned',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (topic_id) REFERENCES topics(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audience_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            segment TEXT NOT NULL,
            pain_point TEXT DEFAULT '',
            primary_keyword TEXT DEFAULT '',
            content_format TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    conn.commit()
    conn.close()


def create_product(name: str, description: str = "", audience: str = "", url: str = "") -> int:
    """Create a product. Returns product id."""
    conn = _get_conn()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT OR IGNORE INTO products (name, description, audience, url) VALUES (?, ?, ?, ?)",
                 (name, description, audience, url))
    product_id = conn.execute("SELECT id FROM products WHERE name = ?", (name,)).fetchone()[0]
    conn.commit()
    conn.close()
    return product_id


def get_product(name: str) -> Optional[dict]:
    """Get product by name."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM products WHERE name = ?", (name,)).fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "description": row[2], "audience": row[3], "url": row[4]}


def add_topic(product_id: int, title: str, intent: str = "", primary_keyword: str = "",
              supporting_keywords: list = None, content_angle: str = "") -> int:
    """Add a topic to a product. Returns topic id."""
    conn = _get_conn()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT INTO topics (product_id, title, intent, primary_keyword, supporting_keywords, content_angle) VALUES (?, ?, ?, ?, ?, ?)",
                 (product_id, title, intent, primary_keyword, json.dumps(supporting_keywords or []), content_angle))
    topic_id = conn.execute("SELECT id FROM topics ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.commit()
    conn.close()
    return topic_id


def get_topics(product_id: int) -> list:
    """Get all topics for a product."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM topics WHERE product_id = ?", (product_id,)).fetchall()
    conn.close()
    return [{"id": r[0], "product_id": r[1], "title": r[2], "intent": r[3],
             "primary_keyword": r[4], "supporting_keywords": json.loads(r[5] or "[]"),
             "content_angle": r[6], "status": r[7]} for r in rows]


def create_article(product_id: int, topic_id: int, slug: str) -> int:
    """Create an article record. Returns article id."""
    conn = _get_conn()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT INTO articles (product_id, topic_id, slug, status) VALUES (?, ?, ?, ?)",
                 (product_id, topic_id, slug, "planned"))
    article_id = conn.execute("SELECT id FROM articles ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.commit()
    conn.close()
    return article_id


def add_audience_segment(product_id: int, segment: str, pain_point: str = "",
                         primary_keyword: str = "", content_format: str = "") -> int:
    """Add an audience segment to a product. Returns segment id."""
    conn = _get_conn()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT INTO audience_segments (product_id, segment, pain_point, primary_keyword, content_format) VALUES (?, ?, ?, ?, ?)",
        (product_id, segment, pain_point, primary_keyword, content_format)
    )
    segment_id = conn.execute(
        "SELECT id FROM audience_segments ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    conn.commit()
    conn.close()
    return segment_id


def get_audience_segments(product_id: int) -> list:
    """Get all audience segments for a product."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM audience_segments WHERE product_id = ?",
        (product_id,)
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "product_id": r[1], "segment": r[2],
         "pain_point": r[3], "primary_keyword": r[4],
         "content_format": r[5]}
        for r in rows
    ]


def get_article(topic_id: int) -> Optional[dict]:
    """Get article for a topic id."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM articles WHERE topic_id = ?", (topic_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "product_id": row[1], "topic_id": row[2], "slug": row[3], "status": row[4]}


def update_article_status(article_id: int, status: str, draft_hash: str = ""):
    """Update article pipeline status."""
    conn = _get_conn()
    conn.execute("UPDATE articles SET status = ?, draft_hash = ? WHERE id = ?",
                 (status, draft_hash, article_id))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# File persistence (markdown + JSON)
# ──────────────────────────────────────────────


def get_content_path(product_name: str, slug: str = None) -> str:
    """Get content directory path.

    Args:
        product_name: Product name
        slug: Article slug (optional for product-level files)

    Returns:
        Full path to product or article directory
    """
    safe_product = product_name.lower().replace(" ", "-").replace("/", "-")
    if slug:
        return os.path.join(CONTENT_DIR, safe_product, "articles", slug)
    return os.path.join(CONTENT_DIR, safe_product)


def save_md(content_path: str, filename: str, content: str) -> str:
    """Save content to markdown file."""
    path = os.path.join(content_path, f"{filename}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return path


def load_md(content_path: str, filename: str) -> str:
    """Load content from markdown file."""
    path = os.path.join(content_path, f"{filename}.md")
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""


def save_json(content_path: str, filename: str, data: dict) -> str:
    """Save data to JSON file."""
    path = os.path.join(content_path, f"{filename}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_json(content_path: str, filename: str) -> dict:
    """Load data from JSON file."""
    path = os.path.join(content_path, f"{filename}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def compute_hash(content: str) -> str:
    """Compute content hash for change detection."""
    return hashlib.md5(content.encode()).hexdigest()[:8]


# ──────────────────────────────────────────────
# Pipeline helpers
# ──────────────────────────────────────────────


def is_research_done(product_name: str, slug: str) -> bool:
    """Check if research has already been generated."""
    return bool(load_md(get_content_path(product_name, slug), "research"))


def is_seo_done(product_name: str, slug: str) -> bool:
    """Check if SEO brief has been generated."""
    return bool(load_json(get_content_path(product_name, slug), "seo"))


def is_draft_done(product_name: str, slug: str) -> bool:
    """Check if draft has been generated."""
    return bool(load_md(get_content_path(product_name, slug), "draft"))


def is_review_done(product_name: str, slug: str) -> bool:
    """Check if review has been generated."""
    return bool(load_md(get_content_path(product_name, slug), "review"))


def is_edit_done(product_name: str, slug: str) -> bool:
    """Check if edit has been generated."""
    return bool(load_md(get_content_path(product_name, slug), "edit"))


def get_pipeline_status(product_name: str, slug: str) -> dict:
    """Get current pipeline status for an article."""
    return {
        "research": is_research_done(product_name, slug),
        "seo": is_seo_done(product_name, slug),
        "draft": is_draft_done(product_name, slug),
        "review": is_review_done(product_name, slug),
        "edit": is_edit_done(product_name, slug),
    }


def step_exists(product_name: str, slug: str, step: str) -> bool:
    """Check if a specific pipeline step exists."""
    if step == "research":
        return is_research_done(product_name, slug)
    if step == "seo":
        return is_seo_done(product_name, slug)
    if step == "draft":
        return is_draft_done(product_name, slug)
    if step == "review":
        return is_review_done(product_name, slug)
    if step == "edit":
        return is_edit_done(product_name, slug)
    return False


# ──────────────────────────────────────────────
# Initialization
# ──────────────────────────────────────────────


init_db()

if __name__ == "__main__":
    print("✓ Database initialized:", DB_PATH)
    print("✓ Content directory:", CONTENT_DIR)
