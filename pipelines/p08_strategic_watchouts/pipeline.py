"""
Pipeline 08 — Strategic Watchouts
Fast version: 2 parallel Google searches.
"""
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse

log = structlog.get_logger()
PIPELINE_ID = "p08_strategic_watchouts"

SYSTEM_PROMPT = """You are a risk intelligence analyst for a B2B agency evaluating whether to pitch a brand.
Review the signals and identify risks StepOneXP should know before approaching this company.

Return ONLY valid JSON:
{
  "overall_verdict": "GREEN | AMBER | RED",
  "verdict_reasoning": "1-2 sentences",
  "financial_distress_signals": [],
  "leadership_changes": [{"role": "CMO", "change": "New CMO appointed", "date": "2024-Q3", "implication": "Good timing for new vendor relationships"}],
  "pr_controversies": [],
  "marketing_freeze_detected": false,
  "marketing_freeze_details": null,
  "existing_agency_signals": [],
  "timing_recommendation": "PURSUE NOW | WAIT 30 DAYS | WAIT 60 DAYS | AVOID",
  "timing_reasoning": "Specific reason",
  "pitch_tone_adjustment": "How StepOneXP should adjust pitch tone based on these watchouts"
}
GREEN = pursue immediately. AMBER = proceed with caution. RED = do not pitch now.
Only flag signals you found evidence for."""


class StrategicWatchoutsPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Strategic Watchouts"

    def fetch(self) -> dict:
        n = self.company_name
        queries = [
            f"{n} layoffs restructuring controversy CMO marketing head 2024 2025",
            f"{n} funding revenue financial agency partner campaign 2024 2025",
        ]
        return {"risk_signals": run_google_searches_parallel(queries, PIPELINE_ID, num_results=8)}

    def extract(self, raw: dict) -> dict:
        signals = []
        for item in raw.get("risk_signals", []):
            t = item.get("title", ""); s = item.get("snippet") or item.get("description", ""); d = item.get("date", "")
            if t: signals.append(f"[{d}] {t}: {s}")
        return {"company_name": self.company_name, "signals": signals[:25]}

    def synthesise(self, structured: dict) -> dict:
        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}

RISK SIGNALS:
{chr(10).join(structured['signals']) if structured['signals'] else 'No risk signals found.'}
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=800)
        if result:
            parsed = safe_json_parse(result)
            if parsed: return parsed
        return {"overall_verdict": "AMBER", "verdict_reasoning": "Insufficient data", "timing_recommendation": "PURSUE NOW"}
