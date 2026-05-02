"""
Pipeline 03 — Market Position
Fast version: 2 parallel Google searches.
"""
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse

log = structlog.get_logger()
PIPELINE_ID = "p03_market_position"

SYSTEM_PROMPT = """You are a brand strategist. Analyse the search results to assess this brand's market position.

Return ONLY valid JSON:
{
  "share_of_voice_level": "HIGH | MEDIUM | LOW",
  "share_of_voice_reasoning": "1-2 sentences",
  "brand_sentiment": "POSITIVE | NEUTRAL | NEGATIVE | MIXED",
  "sentiment_signals": ["up to 3 examples from headlines"],
  "self_positioning_keywords": ["how the brand describes itself"],
  "market_perception_keywords": ["how external sources describe the brand"],
  "perception_gap_score": 1,
  "perception_gap_reasoning": "1-5 scale: 1=fully aligned, 5=major gap",
  "category_leadership_claim": true,
  "leadership_claim_verified": false,
  "recent_sentiment_shift": "IMPROVING | STABLE | DECLINING | UNKNOWN",
  "market_position_summary": "2-3 sentences",
  "pitch_implication": "What this means for StepOneXP pitch"
}"""


class MarketPositionPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Market Position"

    def fetch(self) -> dict:
        n = self.company_name
        queries = [
            f"{n} brand review perception reputation 2024 2025",
            f"{n} vs competitors market news campaign",
        ]
        return {"search_results": run_google_searches_parallel(queries, PIPELINE_ID, num_results=8)}

    def extract(self, raw: dict) -> dict:
        snippets, titles = [], []
        for item in raw.get("search_results", []):
            t = item.get("title", "")
            s = item.get("snippet") or item.get("description", "")
            if t: titles.append(t)
            if s: snippets.append(f"{t}: {s}")
        return {"company_name": self.company_name, "titles": titles[:20], "snippets": snippets[:15]}

    def synthesise(self, structured: dict) -> dict:
        user_data = f"""
COMPANY: {structured['company_name']}
CATEGORY: {self.category}
SEARCH RESULT HEADLINES:
{chr(10).join(structured['titles'][:15])}
FULL SNIPPETS:
{chr(10).join(structured['snippets'][:10])}
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=800)
        if result:
            parsed = safe_json_parse(result)
            if parsed: return parsed
        return {
            "brand_sentiment": "UNKNOWN",
            "market_position_summary": "Insufficient data",
            "pitch_implication": "Manual review needed",
        }
