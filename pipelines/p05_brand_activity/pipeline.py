"""
Pipeline 05 — Brand Activity (Last 12-24 Months)
==================================================
Layer 1: Google News + Instagram scrape + Google search for campaigns/launches
Layer 2: Build chronological activity timeline with type/channel/date classification
Layer 3: Synthesise activity pattern, budget signal, seasonal hooks, silence gaps
"""
import json, structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_search, run_actor
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate, clean_text

log = structlog.get_logger()
PIPELINE_ID = "p05_brand_activity"

SYSTEM_PROMPT = """You are a brand activity analyst. Review the news, social, and PR data and produce a structured brand activity report.

Return ONLY valid JSON:
{
  "recent_campaigns": [
    {"name": "Campaign name", "date": "YYYY-MM or approximate", "channel": "TV|Digital|OOH|Event|PR|Social", "description": "1 sentence"}
  ],
  "product_launches": [{"name": "Product/feature", "date": "YYYY-MM", "description": "1 sentence"}],
  "pr_activity_level": "HIGH | MEDIUM | LOW",
  "social_content_cadence": "Daily | Weekly | Monthly | Sporadic | Unknown",
  "partnerships_collaborations": ["list of notable partnerships found"],
  "seasonal_pattern": "Which seasons/events does the brand activate around",
  "marketing_silence_periods": "Any visible gaps of 60+ days with no activity",
  "budget_signal": "HIGH | MEDIUM | LOW",
  "budget_signal_reasoning": "Evidence for budget assessment",
  "last_major_campaign": "Name and approximate date of most recent campaign",
  "upcoming_opportunity_window": "When is the next likely activation window based on their pattern",
  "activity_summary": "2-3 sentences on their marketing cadence and style"
}
Rules: Only include activities you can confirm from the data. Use approximate dates if exact not available. Never fabricate campaign names."""


class BrandActivityPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Brand Activity (12-24 Months)"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"news": [], "instagram": [], "social": []}
        queries = [
            f"{n} campaign launch marketing 2024 2025",
            f"{n} advertising event activation brand",
            f"{n} partnership collaboration 2024 2025",
            f'"{n}" press release OR award OR recognition',
        ]
        for q in queries:
            raw["news"].extend(run_google_search(q, PIPELINE_ID, num_results=8))

        # Try Instagram scrape for social cadence
        handle_guess = self.company_name.lower().replace(" ", "")
        instagram_data = run_actor(
            "instagram_scraper",
            {"usernames": [handle_guess], "resultsLimit": 15, "searchType": "user"},
            PIPELINE_ID, timeout_secs=60
        )
        raw["instagram"] = instagram_data or []
        return raw

    def extract(self, raw: dict) -> dict:
        activity_items = []
        for item in raw.get("news", []):
            t = item.get("title", "")
            s = item.get("snippet") or item.get("description", "")
            d = item.get("date") or item.get("publishedAt", "")
            if t:
                activity_items.append(f"[{d}] {t}: {s}")

        instagram_info = []
        for post in raw.get("instagram", [])[:10]:
            caption = post.get("caption") or post.get("text", "")
            ts      = post.get("timestamp") or post.get("date", "")
            if caption:
                instagram_info.append(f"[{ts}] {truncate(caption, 100)}")

        return {
            "company_name":    self.company_name,
            "activity_items":  activity_items[:20],
            "instagram_posts": instagram_info[:8],
        }

    def synthesise(self, structured: dict) -> dict:
        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}

NEWS & PR ACTIVITY (chronological):
{chr(10).join(structured['activity_items'])}

INSTAGRAM POSTS:
{chr(10).join(structured['instagram_posts']) if structured['instagram_posts'] else 'No Instagram data retrieved'}
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=1000)
        if result:
            parsed = safe_json_parse(result)
            if parsed: return parsed
        return {"activity_summary": "Insufficient data", "budget_signal": "UNKNOWN", "social_content_cadence": "Unknown"}
