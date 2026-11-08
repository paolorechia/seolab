"""
Content persistence layer.

Storage:
- SQLite for metadata (products, topics, articles, pipeline status)
- Markdown files for actual content (research, drafts, reviews, edits)
"""

import sqlite3
import json
import os
from typing import Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content.db")


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Initialize the database with required tables."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            audience TEXT DEFAULT '',
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
            draft_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (topic_id) REFERENCES topics(id)
        )
    """)
    conn.commit()
    return conn


def get_or_create_product(conn: sqlite3.Connection, name: str, description: str = "", audience: str = "") -> int:
    """Get or create a product. Returns product id."""
    conn.execute("PRAGMA foreign_keys = ON")
    product = conn.execute(
        "SELECT id FROM products WHERE name = ?", (name,)
    ).fetchone()

    if product:
        return product[0]

    conn.execute(
        "INSERT INTO products (name, description, audience) VALUES (?, ?, ?)",
        (name, description, audience)
    )
    conn.commit()
    return conn.execute("SELECT id FROM products WHERE name = ?", (name,)).fetchone()[0]


def add_topic(conn: sqlite3.Connection, product_id: int, title: str, intent: str = "", primary_keyword: str = "",
              supporting_keywords: list[str] = None, content_angle: str = "") -> int:
    """Add a topic to a product. Returns topic id."""
    conn.execute(
        "INSERT INTO topics (product_id, title, intent, primary_keyword, supporting_keywords, content_angle) VALUES (?, ?, ?, ?, ?, ?)",
        (product_id, title, intent, primary_keyword, json.dumps(supporting_keywords or []), content_angle)
    )
    conn.commit()
    return conn.execute("SELECT id FROM topics ORDER BY id DESC LIMIT 1").fetchone()[0]


def get_product(conn: sqlite3.Connection, name: str) -> dict:
    """Get product details."""
    row = conn.execute("SELECT * FROM products WHERE name = ?", (name,)).fetchone()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "description": row[2], "audience": row[3]}


def get_topics(conn: sqlite3.Connection, product_id: int) -> list[dict]:
    """Get all topics for a product."""
    rows = conn.execute("SELECT * FROM topics WHERE product_id = ?", (product_id,)).fetchall()
    topics = []
    for row in rows:
        topics.append({
            "id": row[0], "product_id": row[1], "title": row[2], "intent": row[3],
            "primary_keyword": row[4], "supporting_keywords": json.loads(row[5]),
            "content_angle": row[6], "status": row[7], "created_at": row[8]
        })
    return topics


def get_article(conn: sqlite3.Connection, topic_id: int) -> Optional[dict]:
    """Get article for a topic if it exists."""
    row = conn.execute("SELECT * FROM articles WHERE topic_id = ?", (topic_id,)).fetchone()
    if not row:
        return None
    return {"id": row[0], "product_id": row[1], "topic_id": row[2], "slug": row[3], "status": row[4]}


def create_article(conn: sqlite3.Connection, product_id: int, topic_id: int, title: str) -> int:
    """Create an article record. Returns article id."""
    slug = title.lower().replace(" ", "-").replace("/", "-")[:50]
    conn.execute(
        "INSERT INTO articles (product_id, topic_id, slug, status) VALUES (?, ?, ?, ?)",
        (product_id, topic_id, slug, "planned")
    )
    conn.commit()
    return conn.execute("SELECT id FROM articles ORDER BY id DESC LIMIT 1").fetchone()[0]


def update_article_status(conn: sqlite3.Connection, article_id: int, status: str, draft_hash: str = ""):
    """Update article status."""
    conn.execute(
        "UPDATE articles SET status = ?, draft_hash = ? WHERE id = ?",
        (status, draft_hash, article_id)
    )
    conn.commit()


def update_topic_status(conn: sqlite3.Connection, topic_id: int, status: str):
    """Update topic status."""
    conn.execute("UPDATE topics SET status = ? WHERE id = ?", (status, topic_id))
    conn.commit()


def init_content_dir(db_path: str = DB_PATH):
    """Create content directories for SQLite."""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)


def get_project_root(db_path: str = DB_PATH) -> str:
    """Get the project root (directory containing content.db)."""
    return os.path.dirname(db_path)


# ──────────────────────────────────────────────
# File persistence helpers
# ──────────────────────────────────────────────


def get_content_base(db_path: str = DB_PATH) -> str:
    """Get the content/ directory path."""
    return os.path.join(os.path.dirname(db_path), "content")


def get_article_dir(content_base: str, product_name: str, slug: str) -> str:
    """Get the article directory path."""
    safe_product = product_name.lower().replace(" ", "-").replace("/", "-")
    return os.path.join(content_base, safe_product, "articles", slug)


def save_artifact(content_base: str, article_slug: str, artifact_name: str, content: str):
    """Save an artifact to markdown file."""
    article_dir = os.path.join(content_base, article_slug)
    os.makedirs(article_dir, exist_ok=True)

    artifact_path = os.path.join(article_dir, f"{artifact_name}.md")
    with open(artifact_path, "w") as f:
        f.write(content)

    return artifact_path


def load_artifact(content_base: str, article_slug: str, artifact_name: str) -> str:
    """Load an artifact from markdown file."""
    artifact_path = os.path.join(content_base, article_slug, f"{artifact_name}.md")
    if os.path.exists(artifact_path):
        with open(artifact_path) as f:
            return f.read()
    return ""


def save_artifact_json(content_base: str, article_slug: str, artifact_name: str, data: dict):
    """Save metadata as JSON."""
    article_dir = os.path.join(content_base, article_slug)
    os.makedirs(article_dir, exist_ok=True)

    artifact_path = os.path.join(article_dir, f"{artifact_name}.json")
    with open(artifact_path, "w") as f:
        json.dump(data, f, indent=2)

    return artifact_path


def load_artifact_json(content_base: str, article_slug: str, artifact_name: str) -> dict:
    """Load metadata from JSON file."""
    artifact_path = os.path.join(content_base, article_slug, f"{artifact_name}.json")
    if os.path.exists(artifact_path):
        with open(artifact_path) as f:
            return json.load(f)
    return {}


if __name__ == "__main__":
    # Test initialization
    init_content_dir()
    conn = init_db()
    print("✓ Database initialized")

    # Test product
    product_id = get_or_create_product(conn, "TestProduct", "Test desc", "Test audience")
    print(f"✓ Product created: id={product_id}")

    # Test topic
    topic_id = add_topic(conn, product_id, "Test topic", "informational", "test keyword", [], "Test angle")
    print(f"✓ Topic created: id={topic_id}")

    # Test article
    article_id = create_article(conn, product_id, topic_id, "Test article")
    print(f"✓ Article created: id={article_id}")

    conn.close()
