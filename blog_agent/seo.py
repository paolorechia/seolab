"""SEO Analyst — keyword and intent research module.

Takes a topic and research brief, then produces:
- Primary keyword + secondary keywords
- Search intent classification
- SERP landscape (what ranks)
- Title suggestions (3 options)
- Meta description
- SEO heading outline (H1 + 4-6 H2s)
"""

from blog_agent.utils import chat


INTENT_PROMPT = """You are an SEO analyst classifying search intent for a given topic.

Classify the search intent into ONE of these categories:
- informational: user wants to learn (overview, guide, explanation)
- commercial investigation: user is researching before buying (comparison, best of, alternatives)
- transactional: user is ready to buy/try (product page, review, tutorial with CTA)
- navigational: user is looking for a specific tool/site

For each, return:
- intent: the classification (informational | commercial investigation | transactional | navigational)
- angle: a one-sentence description of what the user is really looking for
- format: what article type would serve them best (guide, comparison, overview, listicle, how-to, etc.)

Topic: {topic}

Respond in this exact format:
intent: <type>
angle: <description>
format: <article type>"""

KEYWORDS_PROMPT = """You are an SEO keyword analyst. Given the research topic and brief, extract keywords.

Research topic: {topic}

Research brief:
{research_brief}

Return:
- primary keyword: the main SEO target (one phrase, the highest intent/traffic)
- secondary keywords: comma-separated list of 3-5 supporting keywords

Respond in this exact format:
primary: <keyword>
secondary: <comma-separated keywords>"""

SERP_PROMPT = """You are an SEO analyst analyzing the SERP landscape for a topic.

Research topic: {topic}

Research brief:
{research_brief}

Based on the research results (which come from real search results), describe:
- What types of results currently rank for this topic (guide, listicle, product page, news, blog, comparison, opinion piece, etc.)
- The typical content length of top results (short, medium, long)
- What angle top results take (technical, beginner, opinion, list of tools, how-to, etc.)
- Any obvious content gaps (what's missing from top results that a good article could cover)

Respond in this exact format:
result_types: <comma-separated types of top results>
typical_length: <short (~500w) | medium (~1000w) | long (~1500w+)>
common_angle: <what approach top results use>
content_gaps: <what a good article could cover that top results miss>"""

TITLE_PROMPT = """You are a headline writer. Generate 3 SEO-friendly title options for this topic.

Research topic: {topic}
Primary keyword: {primary_keyword}
Search intent: {intent_type}
Common angle from top results: {common_angle}

Titles should:
- Contain the primary keyword
- Match the search intent and audience expectation
- Be specific and benefit-driven (not vague or clickbaity)
- Be 50-70 characters

Respond with exactly 3 numbered options. Each on its own line."""

META_PROMPT = """You are an SEO copywriter. Write a meta description for this topic.

Research topic: {topic}
Primary keyword: {primary_keyword}
Secondary keywords: {secondary_keywords}
Search intent: {intent_type}
Angle: {angle}

Requirements:
- 150-160 characters
- Start with the primary keyword or a variation
- Clearly state the benefit or what the reader will learn
- Include a call to action or hook at the end
- No keyword stuffing

Return only the meta description text."""

HEADING_PROMPT = """You are a content strategist creating an SEO heading outline.

Research topic: {topic}
Primary keyword: {primary_keyword}
Secondary keywords: {secondary_keywords}
Search intent: {intent_type}
Article format: {format}

Create a heading structure:
- H1: the main title (should contain primary keyword)
- H2s: 4-6 main section headings (include secondary keywords where natural)
- H3s: optional sub-sections under key H2s

Requirements:
- H1 should be a clear, benefit-driven headline
- Each H2 should represent a distinct section
- Include primary keyword in H1 and at least one H2
- Secondary keywords should be distributed across 2-3 H2s
- Avoid generic headings like "Introduction" or "Conclusion"

Respond in this format:
H1: <heading>
H2: <heading>
H2: <heading>
...
"""


class SEOAnalyzer:
    def __init__(self, model: str | None = None):
        self.model = model

    def analyze_intent(self, topic: str) -> dict:
        """Classify search intent and determine article angle."""
        result = chat(INTENT_PROMPT.format(topic=topic), model=self.model, max_tokens=200)
        lines = result.strip().split("\n")
        parsed = {}
        for line in lines:
            if ":" in line:
                key, val = line.split(":", 1)
                parsed[key.strip()] = val.strip()
        return parsed

    def extract_keywords(self, topic: str, research_brief: str) -> dict:
        """Extract primary and secondary keywords."""
        result = chat(
            KEYWORDS_PROMPT.format(topic=topic, research_brief=research_brief),
            model=self.model,
            max_tokens=200,
        )
        lines = result.strip().split("\n")
        parsed = {}
        for line in lines:
            if ":" in line:
                key, val = line.split(":", 1)
                parsed[key.strip()] = val.strip()

        # Parse secondary keywords
        secondary = []
        if "secondary" in parsed:
            secondary = [k.strip() for k in parsed["secondary"].split(",")]

        return {
            "primary": parsed.get("primary", ""),
            "secondary": [k for k in secondary if len(k) > 2],
        }

    def analyze_serp(self, topic: str, research_brief: str) -> dict:
        """Analyze SERP landscape from research results."""
        result = chat(
            SERP_PROMPT.format(topic=topic, research_brief=research_brief),
            model=self.model,
            max_tokens=300,
        )
        lines = result.strip().split("\n")
        parsed = {}
        for line in lines:
            if ":" in line:
                key, val = line.split(":", 1)
                parsed[key.strip()] = val.strip()
        return parsed

    def generate_titles(self, topic: str, primary: str, intent: str, common_angle: str) -> list[str]:
        """Generate 3 title options."""
        result = chat(
            TITLE_PROMPT.format(topic=topic, primary_keyword=primary, intent_type=intent, common_angle=common_angle),
            model=self.model,
            max_tokens=300,
        )
        titles = [line.strip() for line in result.strip().split("\n") if line.strip() and len(line.strip()) > 10][:3]
        return titles

    def generate_meta(self, topic: str, primary: str, secondary: str, intent: str, angle: str) -> str:
        """Generate meta description."""
        return chat(
            META_PROMPT.format(topic=topic, primary_keyword=primary, secondary_keywords=secondary, intent_type=intent, angle=angle),
            model=self.model,
            max_tokens=200,
        )

    def generate_headings(self, topic: str, primary: str, secondary: str, intent: str, format: str) -> dict:
        """Generate H1/H2 heading outline."""
        result = chat(
            HEADING_PROMPT.format(topic=topic, primary_keyword=primary, secondary_keywords=secondary, intent_type=intent, format=format),
            model=self.model,
            max_tokens=300,
        )
        lines = result.strip().split("\n")
        h1 = ""
        h2s = []
        h3s = {}

        for line in lines:
            line = line.strip()
            if line.startswith("H1:"):
                h1 = line[3:].strip()
            elif line.startswith("H2:"):
                h2s.append(line[3:].strip())
            elif line.startswith("H3:") and h2s:
                h2_key = h2s[-1]
                if h2_key not in h3s:
                    h3s[h2_key] = []
                h3s[h2_key].append(line[3:].strip())

        return {"h1": h1, "h2s": h2s, "h3s": h3s}

    def full_analysis(self, topic: str, research_brief: str) -> dict:
        """Run complete keyword + intent analysis.

        Returns a dict with all SEO analysis outputs.
        """
        print(f"\n🔎 Analyzing search intent...")
        intent = self.analyze_intent(topic)

        print(f"\n🔑 Extracting keywords...")
        keywords = self.extract_keywords(topic, research_brief)

        print(f"\n🌐 Analyzing SERP landscape...")
        serp = self.analyze_serp(topic, research_brief)

        intent_type = intent.get("intent", "informational")
        angle = intent.get("angle", "Overview")
        common_angle = serp.get("common_angle", "General overview")
        primary = keywords["primary"]
        secondary = keywords["secondary"]

        print(f"\n📝 Generating titles...")
        titles = self.generate_titles(topic, primary, intent_type, common_angle)

        print(f"\n📝 Generating meta description...")
        meta = self.generate_meta(topic, primary, ", ".join(secondary), intent_type, angle)

        print(f"\n📝 Generating heading outline...")
        headings = self.generate_headings(topic, primary, ", ".join(secondary), intent_type, serp.get("format", "guide"))

        return {
            "intent": intent,
            "keywords": keywords,
            "serp": serp,
            "titles": titles,
            "meta": meta,
            "headings": headings,
        }
