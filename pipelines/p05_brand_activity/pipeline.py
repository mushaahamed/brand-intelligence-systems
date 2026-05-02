"""
Pipeline 05 — Brand Activity (Last 12-24 Months)
Fast version: 2 parallel Google searches. Instagram actor removed (unreliable + slow).
"""
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate

log = structlog.get_logger()
PIPELINE_ID = "p05_brand_activity"

SYSTEM_PROMPT = """You are a brand activity analyst. Review the news and PR data and produce a structured brand activity report.

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
  "upcoming_opportunity_window": "When is the next likely activation window",
  "activity_summary": "2-3 sentences on their marketing cadence and style"
}
Only include activities confirmed from the data. Never fabricate campaign names."""


class BrandActivityPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Brand Activity (12-24 Months)"

    def fetch(self) -> dict:
        n = self.company_name
        queries = [
            f"{n} campaign launch marketing event 2024 2025",
            f"{n} partnership collaboration advertising PR 2024 2025",
        ]
        return {"news": run_google_searches_parallel(queries, PIPELINE_ID, num_results=10)}

    def extract(self, raw: dict) -> dict:
        activity_items = []
        for item in raw.get("news", []):
            t = item.get("title", "")
            s = item.get("snippet") or item.get("description", "")
            d = item.get("date") or item.get("publishedAt", "")
            if t:
                activity_items.append(f"[{d}] {t}: {s}")
        return {"company_name": self.company_name, "activity_items": activity_items[:20]}

    def synthesise(self, structured: dict) -> dict:
        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}

NEWS & PR ACTIVITY:
{chr(10).join(structured['activity_items']) if structured['activity_items'] else 'No activity data retrieved.'}
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=1000)
        if result:
            parsed = safe_json_parse(result)
            if parsed: return parsed
        return {"activity_summary": "Insufficient data", "budget_signal": "UNKNOWN", "social_content_cadence": "Unknown"}
