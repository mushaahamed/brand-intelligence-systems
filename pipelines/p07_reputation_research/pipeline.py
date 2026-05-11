"""
Pipeline 07 — Reputation Research

Two-source strategy (same pattern as P09):
  Source A — GPT-4o Knowledge (PRIMARY):
    GPT-4o knows the real reputation of virtually every major brand —
    customer sentiment, controversies, NPS signals, community strength.
    Runs first, always returns substantive data.

  Source B — Reddit + Google Search (SUPPLEMENTARY):
    Adds real, recent user discussions and review snippets to validate
    or update GPT's knowledge with anything from the last 12 months.

  Merge: GPT knowledge is the baseline. Search data overrides specific
    fields (reddit_sentiment, recent_controversy) when found.
"""
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel, scrape_reddit
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate, clean_text
from config.settings import OPENAI_MODEL_FULL
from concurrent.futures import ThreadPoolExecutor

log = structlog.get_logger()
PIPELINE_ID = "p07_reputation_research"

KNOWLEDGE_SYSTEM_PROMPT = """You are a senior brand reputation analyst with deep knowledge of Indian and global consumer brands.

Using your training knowledge, provide an honest reputation assessment of this brand. Base it on:
- Known customer sentiment and brand perception
- Major controversies or PR crises (if any)
- Brand community strength and advocacy
- NPS and loyalty signals from your training data
- Typical review platform ratings for this category

Return ONLY valid JSON, no markdown:
{
  "overall_reputation_score": 72,
  "reputation_label": "STRONG | GOOD | NEUTRAL | MIXED | POOR",
  "reddit_sentiment": "POSITIVE | NEUTRAL | NEGATIVE | MIXED | NO_DATA",
  "reddit_key_themes": ["specific themes customers discuss about this brand"],
  "reddit_top_complaints": ["real known complaints about this brand"],
  "reddit_top_praise": ["real known praise about this brand"],
  "review_platform_sentiment": "POSITIVE | NEUTRAL | NEGATIVE | MIXED | NO_DATA",
  "common_customer_complaints": ["known complaints from reviews/forums"],
  "common_customer_praise": ["known praise from reviews/forums"],
  "nps_signal": "HIGH | MEDIUM | LOW | UNKNOWN",
  "brand_community_strength": "STRONG | MODERATE | WEAK | NONE",
  "recent_controversy": "Any known controversy or null",
  "reputation_watchout": "Key reputation risk StepOneXP should know before pitching",
  "reputation_opportunity": "Positive signal StepOneXP can reference in pitch"
}

Be specific and accurate. If you know this brand well, use that knowledge. Do NOT return generic placeholder text."""

ENRICH_SYSTEM_PROMPT = """You are a reputation intelligence analyst. Real user data is provided below.
Update the reputation assessment based on this ACTUAL data from Reddit and review sites.

Return ONLY valid JSON with the same structure as before, but now use the real data to fill:
- reddit_sentiment: based on actual post tone
- reddit_key_themes: actual topics discussed
- reddit_top_complaints: actual complaints found
- reddit_top_praise: actual praise found
- recent_controversy: any controversy mentioned

Keep knowledge-based fields intact if real data doesn't contradict them."""


class ReputationResearchPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Reputation Research"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"reddit": [], "reviews_search": []}

        with ThreadPoolExecutor(max_workers=2) as ex:
            reddit_f = ex.submit(scrape_reddit, f"{n} brand review experience", PIPELINE_ID, 15)
            google_f = ex.submit(
                run_google_searches_parallel,
                [f"{n} customer review complaints feedback reddit 2024",
                 f"{n} brand reputation controversy OR scandal OR award 2024"],
                PIPELINE_ID, 8,
            )
            raw["reddit"]         = reddit_f.result() or []
            raw["reviews_search"] = google_f.result() or []

        return raw

    def extract(self, raw: dict) -> dict:
        reddit_posts = []
        for post in raw.get("reddit", [])[:15]:
            title = post.get("title") or post.get("name", "")
            body  = post.get("selftext") or post.get("body") or post.get("text", "")
            score = post.get("score", 0)
            sub   = post.get("subreddit", "")
            if title or body:
                reddit_posts.append(
                    f"[r/{sub} | score:{score}] {title}: {truncate(clean_text(body), 200)}"
                )

        review_snippets = []
        for item in raw.get("reviews_search", [])[:10]:
            t = item.get("title", "")
            s = item.get("snippet") or item.get("description", "")
            if t or s:
                review_snippets.append(f"{t}: {s}")

        return {
            "company_name":    self.company_name,
            "reddit_posts":    reddit_posts,
            "review_snippets": review_snippets,
            "reddit_count":    len(reddit_posts),
            "has_real_data":   len(reddit_posts) > 0 or len(review_snippets) > 3,
        }

    def synthesise(self, structured: dict) -> dict:
        n        = structured["company_name"]
        category = self.category

        # ── Source A: GPT-4o knowledge (always gives real brand insight) ─────
        knowledge_prompt = f"""BRAND: {n}
CATEGORY: {category}
WEBSITE: {self.company_url or 'unknown'}

Provide a reputation assessment for {n} based on your training knowledge.
Consider: Is this a beloved brand or does it have issues? What do customers say?
What controversies has it faced? What is its community like?"""

        knowledge_raw    = synthesise(KNOWLEDGE_SYSTEM_PROMPT, knowledge_prompt,
                                      model=OPENAI_MODEL_FULL, max_tokens=1000)
        result           = safe_json_parse(knowledge_raw or "") or {}

        # ── Source B: Enrich with real Reddit/search data if found ───────────
        if structured["has_real_data"]:
            real_data_text = ""
            if structured["reddit_posts"]:
                real_data_text += f"\nREDDIT DISCUSSIONS ({structured['reddit_count']} posts):\n"
                real_data_text += "\n".join(structured["reddit_posts"])
            if structured["review_snippets"]:
                real_data_text += f"\n\nREVIEW/NEWS SNIPPETS:\n"
                real_data_text += "\n".join(structured["review_snippets"])

            enrich_prompt = f"""BRAND: {n}
CATEGORY: {category}

KNOWLEDGE-BASED ASSESSMENT (baseline):
{knowledge_raw or '(none)'}

REAL DATA FOUND:
{real_data_text}

Update the assessment using the real data. Keep knowledge fields where real data is absent."""

            enriched_raw    = synthesise(ENRICH_SYSTEM_PROMPT, enrich_prompt,
                                         model=OPENAI_MODEL_FULL, max_tokens=1000)
            enriched_parsed = safe_json_parse(enriched_raw or "")
            if enriched_parsed:
                result = enriched_parsed
                log.info(f"     Community data incorporated — {structured['reddit_count']} discussions analysed")

        rep_label = result.get("reputation_label", "")
        rep_score = result.get("overall_reputation_score", "")
        log.info(f"     Reputation: {rep_label} · Score: {rep_score}/100")

        return result or {
            "overall_reputation_score": None,
            "reputation_label":         "UNKNOWN",
            "reddit_sentiment":         "NO_DATA",
            "reputation_watchout":      "Insufficient data",
            "reputation_opportunity":   None,
        }
