"""
Pipeline 07 — Reputation Research
Fast version: Reddit (30s timeout) + 1 parallel Google search.
"""
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel, scrape_reddit
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate, clean_text
from concurrent.futures import ThreadPoolExecutor, as_completed

log = structlog.get_logger()
PIPELINE_ID = "p07_reputation_research"

SYSTEM_PROMPT = """You are a reputation intelligence analyst. Analyse authentic online conversations about this brand.

Return ONLY valid JSON:
{
  "overall_reputation_score": 72,
  "reputation_label": "STRONG | GOOD | NEUTRAL | MIXED | POOR",
  "reddit_sentiment": "POSITIVE | NEUTRAL | NEGATIVE | MIXED | NO_DATA",
  "reddit_key_themes": ["what Reddit users say — specific themes"],
  "reddit_top_complaints": ["specific complaints from real users"],
  "reddit_top_praise": ["specific praise from real users"],
  "review_platform_sentiment": "POSITIVE | NEUTRAL | NEGATIVE | MIXED | NO_DATA",
  "common_customer_complaints": ["complaints from reviews"],
  "common_customer_praise": ["praise from reviews"],
  "nps_signal": "HIGH | MEDIUM | LOW | UNKNOWN",
  "brand_community_strength": "STRONG | MODERATE | WEAK | NONE",
  "recent_controversy": null,
  "reputation_watchout": "Key reputation risk for StepOneXP to know before pitching",
  "reputation_opportunity": "Positive signal that StepOneXP can reference in pitch"
}
Only reference specific things from the data."""


class ReputationResearchPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Reputation Research"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"reddit": [], "reviews_search": []}

        # Run Reddit and Google search in parallel
        with ThreadPoolExecutor(max_workers=2) as ex:
            reddit_f  = ex.submit(scrape_reddit, f"{n} brand review experience", PIPELINE_ID, 15)
            google_f  = ex.submit(
                run_google_searches_parallel,
                [f"{n} review trustpilot OR reddit customer feedback experience 2024"],
                PIPELINE_ID, 8,
            )
            raw["reddit"]         = reddit_f.result() or []
            raw["reviews_search"] = google_f.result() or []

        return raw

    def extract(self, raw: dict) -> dict:
        reddit_posts = []
        for post in raw.get("reddit", [])[:15]:
            title  = post.get("title") or post.get("name", "")
            body   = post.get("selftext") or post.get("body") or post.get("text", "")
            score  = post.get("score", 0)
            sub    = post.get("subreddit", "")
            if title or body:
                reddit_posts.append(f"[r/{sub} | score:{score}] {title}: {truncate(clean_text(body), 200)}")

        review_snippets = []
        for item in raw.get("reviews_search", [])[:10]:
            t = item.get("title", ""); s = item.get("snippet") or item.get("description", "")
            if t or s: review_snippets.append(f"{t}: {s}")

        return {
            "company_name":    self.company_name,
            "reddit_posts":    reddit_posts,
            "review_snippets": review_snippets,
            "reddit_count":    len(reddit_posts),
        }

    def synthesise(self, structured: dict) -> dict:
        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}
REDDIT POSTS FOUND: {structured['reddit_count']}

REDDIT DISCUSSIONS:
{chr(10).join(structured['reddit_posts']) if structured['reddit_posts'] else 'No Reddit data retrieved.'}

REVIEW PLATFORM DATA:
{chr(10).join(structured['review_snippets']) if structured['review_snippets'] else 'No review data retrieved.'}
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=1000)
        if result:
            parsed = safe_json_parse(result)
            if parsed: return parsed
        return {
            "overall_reputation_score": None,
            "reputation_label": "UNKNOWN",
            "reddit_sentiment": "NO_DATA",
            "reputation_watchout": "Insufficient data — manual review recommended",
            "reputation_opportunity": None,
        }
