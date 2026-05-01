"""
Pipeline 07 — Reputation Research
====================================
Layer 1: Reddit scrape + Google reviews + Trustpilot + Twitter/news for brand mentions
Layer 2: Sentiment classification per source, extract specific complaints/praise
Layer 3: Reputation scorecard — what people say vs what brand claims

Reddit is the highest-signal source for authentic brand perception.
"""
import json, structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_search, scrape_reddit, run_actor
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate, clean_text

log = structlog.get_logger()
PIPELINE_ID = "p07_reputation_research"

SYSTEM_PROMPT = """You are a reputation intelligence analyst. Analyse authentic online conversations about this brand.

Return ONLY valid JSON:
{
  "overall_reputation_score": 72,
  "reputation_label": "STRONG | GOOD | NEUTRAL | MIXED | POOR",
  "reddit_sentiment": "POSITIVE | NEUTRAL | NEGATIVE | MIXED | NO_DATA",
  "reddit_key_themes": ["what Reddit users say about the brand — specific themes"],
  "reddit_top_complaints": ["specific complaints mentioned by real users"],
  "reddit_top_praise": ["specific praise mentioned by real users"],
  "review_platform_sentiment": "POSITIVE | NEUTRAL | NEGATIVE | MIXED | NO_DATA",
  "common_customer_complaints": ["complaints from reviews"],
  "common_customer_praise": ["praise from reviews"],
  "twitter_sentiment": "POSITIVE | NEUTRAL | NEGATIVE | MIXED | NO_DATA",
  "recent_controversy": null,
  "controversy_details": null,
  "nps_signal": "HIGH | MEDIUM | LOW | UNKNOWN",
  "brand_community_strength": "STRONG | MODERATE | WEAK | NONE",
  "reputation_vs_brand_claim_gap": "1-5 scale: 1=fully aligned, 5=major gap between what brand says and what people say",
  "reputation_watchout": "Key reputation risk for StepOneXP to be aware of before pitching",
  "reputation_opportunity": "Positive reputation signal that StepOneXP can reference in pitch"
}
Rules: Only reference specific things from the data. If no data found for a source, use NO_DATA."""


class ReputationResearchPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Reputation Research"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"reddit": [], "reviews_search": [], "twitter_search": []}

        # Reddit — highest signal source
        log.info("p07_fetch_reddit", company=n)
        raw["reddit"] = scrape_reddit(f"{n} brand OR product OR review OR experience", PIPELINE_ID, max_items=30)

        # Google search for reviews (Trustpilot, G2, Glassdoor etc.)
        review_queries = [
            f"{n} review site:reddit.com OR site:trustpilot.com OR site:g2.com",
            f"{n} customer experience feedback",
        ]
        for q in review_queries:
            raw["reviews_search"].extend(run_google_search(q, PIPELINE_ID, num_results=8))

        # Twitter/social search via Google
        raw["twitter_search"] = run_google_search(
            f"{n} site:twitter.com OR site:x.com reviews experience 2024 2025",
            PIPELINE_ID, num_results=5
        )
        return raw

    def extract(self, raw: dict) -> dict:
        reddit_posts = []
        for post in raw.get("reddit", [])[:20]:
            title   = post.get("title") or post.get("name", "")
            body    = post.get("selftext") or post.get("body") or post.get("text", "")
            score   = post.get("score", 0)
            sub     = post.get("subreddit", "")
            comments = post.get("numComments") or post.get("num_comments", 0)
            if title or body:
                reddit_posts.append(
                    f"[r/{sub} | score:{score} | comments:{comments}] {title}: {truncate(clean_text(body), 200)}"
                )

        review_snippets = []
        for item in raw.get("reviews_search", [])[:10]:
            t = item.get("title", "")
            s = item.get("snippet") or item.get("description", "")
            if t or s:
                review_snippets.append(f"{t}: {s}")

        twitter_snippets = [
            f"{i.get('title','')}: {i.get('snippet','')}"
            for i in raw.get("twitter_search", [])[:5] if i.get("title")
        ]

        return {
            "company_name":      self.company_name,
            "reddit_posts":      reddit_posts,
            "review_snippets":   review_snippets,
            "twitter_snippets":  twitter_snippets,
            "reddit_count":      len(reddit_posts),
        }

    def synthesise(self, structured: dict) -> dict:
        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}
REDDIT POSTS FOUND: {structured['reddit_count']}

REDDIT DISCUSSIONS:
{chr(10).join(structured['reddit_posts']) if structured['reddit_posts'] else 'No Reddit data retrieved — brand may have low Reddit presence.'}

REVIEW PLATFORM DATA:
{chr(10).join(structured['review_snippets']) if structured['review_snippets'] else 'No review data retrieved.'}

TWITTER/SOCIAL SIGNALS:
{chr(10).join(structured['twitter_snippets']) if structured['twitter_snippets'] else 'No Twitter data.'}
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
