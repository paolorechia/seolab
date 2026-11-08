# Blog Agent — AI Content Pipeline

End-to-end blog writing system with persistence, product-aware content planning, and human-in-the-loop review.

## Quick Start

```bash
# 1. Create a product
uv run python -m blog_agent add-product Cohearo --description "On-device transcription app"

# 2. Research → Topics
uv run python -m blog_agent plan Cohearo --description "..." --audience "knowledge workers"

# 3. Write an article
uv run python -m blog_agent write --topic "Why on-device beats cloud AI" \
  --product Cohearo --fast --batch
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Persistence Layer                    │
│  SQLite: products, topics, articles, status       │
│  Markdown: research, seo, draft, review, edit     │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│              Content Pipeline                     │
│                                                   │
│  add-product → product                           │
│  plan → research → topics                        │
│  write → review → edit → human → approve         │
└─────────────────────────────────────────────────┘
```

## Commands

### 1. Add Product

```bash
uv run python -m blog_agent add-product Cohearo --description "On-device transcription app"
```

Creates a product with no audience. Audience is added during planning.

### 2. Plan (Research → Topics)

```bash
uv run python -m blog_agent plan Cohearo --description "..." --audience "knowledge workers"
```

**Flow:**
- Researches product + competitors
- Generates topic clusters (5-8 topics)
- Identifies comparison opportunities (product vs competitors)
- Maps audience segments
- Saves topics to SQLite + research brief to `content/`
- Saves research brief to `content/<product>/research_brief.md`

**Output:**
```
📦 Keyword Planner results:
📚 Topics (7):
  1. Why On-Device Transcription is Critical for Enterprise...
  2. Reducing API Costs with Edge AI Transcription for Teams...
  3. Offline Meeting Transcription: How to Work Without Internet...
  4. Best Privacy-Friendly Transcription Alternatives...
  5. Integrating On-Device Transcription into Local Workflows...
  6. Latency vs. Accuracy: Why Local Transcription is Catching Up...
  7. How to Prepare Your Device for On-Device AI Workloads...

🔍 Comparisons (8):
  - Cohearo vs Otter.ai
  - Best on-device transcription apps 2024
  - Alternatives to cloud-based transcription services

👥 Audience Segments (3):
  - Academic researchers and interview journalists...
  - Remote software engineers...
  - Freelance content creators and podcasters...
```

### 3. Write Article

```bash
uv run python -m blog_agent write --topic "Why on-device beats cloud AI" --product Cohearo --fast --batch
```

**Pipeline:**
```
write → review
review → edit → review (loop)
edit → human → edit (loop)
human → approve
```

**Steps:**
1. **Research** → DuckDuckGo → research brief → `research.md`
2. **SEO** → keywords + SERP + headings → `seo.json`
3. **Write** → draft → `draft.md`
4. **Review** → Clarity review → `review.md`
5. **Edit** → revise (auto loop) → `edit.md`
6. **Human** → approve / change → `final.md`

## Modes

| Mode | Flag | Description |
|------|------|-------------|
| Default | None | Interactive with output |
| Fast | `--fast` | Skip auto-edit loop |
| Batch | `--batch` | CI mode, no output |
| Print | `--print` | Print to stdout |
| Loop | `--loop` | Human-in-the-loop |

## File Structure

```
content.db          ← SQLite for metadata
content/
  cohearo/          ← product directory
    research_brief.md ← Plan research brief
    articles/
      local-vs-cloud-transcription/
        research.md     ← DuckDuckGo research
        seo.json        ← SEO brief
        draft.md        ← initial draft
        review.md       ← Clarity review
        edit.md         ← edited version
        final.md        ← final draft
```

## Example Flow

```bash
# Step 1: Create product
$ uv run python -m blog_agent add-product Cohearo --description "On-device transcription app"
✓ Created product: Cohearo (id=1)

# Step 2: Research & plan
$ uv run python -m blog_agent plan Cohearo --description "..." --audience "knowledge workers"
📊 Researching & Planning for: Cohearo
📦 Keyword Planner results:
📚 Topics (7): ...
🔍 Comparisons (8): ...
👥 Audience Segments (3): ...

# Step 3: Write article (fast mode)
$ uv run python -m blog_agent write --topic "Why on-device beats cloud AI" --product Cohearo --fast --batch
🔍 Researching: Why on-device beats cloud AI
  ✓ Saved research.md
📊 SEO Analysis...
  ✓ Saved seo.json
✍️ Writing...
  ✓ Saved draft.md
🔎 Reviewing...
  ✓ Saved review.md
⏭️ Skipping auto-edit (--fast)
  ✓ Saved edit.md
💾 Artifacts saved to: content/cohearo/articles/why-on-device-beats-cloud-ai
```

## Persistence Benefits

- **No duplicate generation** — pipeline checks status before running steps
- **Step decoupling** — research/SEO/write/review/edit can run independently
- **Product context** — topics inherit product audience, keywords, angles
- **Audit trail** — SQLite stores metadata, markdown stores content

## Next Steps

1. Content publishing to CMS (WordPress, MDX, etc.)
2. Competitor content analysis (SERP monitoring)
3. Internal linking suggestions from site sitemap
4. Readability optimization (Flesch-Kincaid, Hemingway)
5. A/B testing title variants
6. Topic cluster expansion (related topics, PBN links)
