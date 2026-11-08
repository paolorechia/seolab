# Blog Agent — AI Content Pipeline

End-to-end blog writing system with persistence, product-aware content planning, and human-in-the-loop review.

## Quick Start

```bash
# 1. Create a product
uv run python -m blog_agent add-product Cohearo --description "On-device transcription app" --audience "knowledge workers"

# 2. Generate content plan
uv run python -m blog_agent plan Cohearo --description "..." --audience "..."

# 3. Write an article
uv run python -m blog_agent write --topic "Why on-device transcription beats cloud AI" \
  --product Cohearo --product-desc "..." --audience "..." --fast --batch

# 4. Interactive review (with human loop)
uv run python -m blog_agent write --topic "..." --product Cohearo --loop
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
│  add-product → create product + audience         │
│  plan → generate topics + angles + comparisons   │
│  write → research → SEO → write → review → edit  │
│  human-loop → approve | change | rewrite | lint  │
└─────────────────────────────────────────────────┘
```

## Components

### 1. Persistence (`blog_agent/persistence.py`)

**SQLite Tables:**
- `products` - product name, description, audience
- `topics` - title, intent, keywords, content angle
- `articles` - links to topics, pipeline status

**File Structure:**
```
content/
  cohearo/
    articles/
      why-on-device-transcription-beats-cloud-ai-for-pri/
        research.md    ← DuckDuckGo research brief
        seo.json       ← SEO brief (keywords, SERP, headings)
        draft.md       ← initial draft
        review.md      ← Clarity review
        edit.md        ← edited version
        final.md       ← final draft
```

### 2. Keyword Planner (`blog_agent/keyword_planner.py`)

Generates topic clusters from product context:
- **Content topics** (5-8) with intent, keywords, angles
- **Comparisons** (product vs competitors)
- **Audience segments** with pain points

### 3. Pipeline Steps

| Step | Command | Artifacts Saved |
|------|---------|----------------|
| Research | DuckDuckGo | `research.md` |
| SEO Analysis | Intent + keywords + SERP | `seo.json` |
| Write | Clarity methodology | `draft.md` |
| Review | Clarity review | `review.md` |
| Edit | Auto-revision loop | `edit.md`, `final.md` |
| Human Review | Interactive CLI | feedback loop |

## Pipeline Commands

```bash
# Step 1: Add product (one-time setup)
uv run python -m blog_agent add-product ProductName --description "..." --audience "..."

# Step 2: Generate content plan
uv run python -m blog_agent plan ProductName --description "..." --audience "..."

# Step 3: Write article (with product context)
uv run python -m blog_agent write --topic "topic" --product "Product" --product-desc "..." --audience "..."

# Step 4: Write without product context
uv run python -m blog_agent write --topic "topic" --fast --batch

# Step 5: Write with human loop
uv run python -m blog_agent write --topic "topic" --product "Product" --loop
```

## Modes

| Mode | Flag | Description |
|------|------|-------------|
| Default | None | Interactive with output |
| Fast | `--fast` | Skip auto-edit loop |
| Batch | `--batch` | CI mode, no output |
| Print | `--print` | Print to stdout |
| Loop | `--loop` | Human-in-the-loop |

## Example: Cohearo (On-Device Transcription App)

```bash
# Create product
uv run python -m blog_agent add-product Cohearo --description "On-device transcription app" --audience "knowledge workers"

# Generate plan
uv run python -m blog_agent plan Cohearo --description "..." --audience "..."

# Output:
# ✓ Created product: Cohearo (id=1)
# 📦 Content Plan for: Cohearo
# 
# 📚 Topics (7):
#   1. Why On-Device Transcription Is Critical for Enterprise Compliance...
#   2. How to Create a Second Brain: Offloading Meeting Notes...
#   3. The Hidden Cost of Cloud Transcription: Security Risks...
#   4. Best On-Device AI Transcription Apps...
#   5. Boosting Productivity with Offline Meeting Transcription...
#   6. Reducing Cloud Storage Costs: The Case for Local AI...
#   7. What Is On-Device AI? A Guide for Knowledge Workers...
# 
# 🔍 Comparisons (5):
#   - Cohearo vs Otter.ai
#   - Cohearo vs Rev Transcription...
#   - Cohearo vs Whisper App...
#   - Cohearo vs Notion AI
#   - Best on-device transcription apps for iOS
# 
# 👥 Audience Segments (4):
#   - Journalists and Interviewers
#   - Academic Researchers
#   - Legal Professionals
#   - Remote Knowledge Workers

# Write article
uv run python -m blog_agent write --topic "Why on-device transcription beats cloud AI" \
  --product Cohearo --product-desc "..." --audience "..." --fast --batch
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
