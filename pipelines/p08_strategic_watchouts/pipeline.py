"""
Pipeline 08 — Strategic Watchouts
====================================
Layer 1: Google search for risk signals — layoffs, controversy, funding gaps, leadership changes
Layer 2: Classify each signal by type and severity
Layer 3: Overall verdict + specific watchouts relevant to StepOneXP pitch
"""
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_search
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse

log = structlog.get_logger()
PIPELINE_ID = "p08_strategic_watchouts"

SYSTEM_PROMPT = """You are a risk intelligence analyst for a B2B agency evaluating whether to pitch a brand.
Review the signals provided and identify risks StepOneXP should know before approaching this company.

Return ONLY valid JSON:
{
  "overall_verdict": "GREEN | AMBER | RED",
  "verdict_reasoning": "1-2 sentences",
  "financial_distress_signals": [],
  "leadership_changes": [{"role": "CMO", "change": "New CMO appointed", "date": "2024-Q3", "implication": "New CMO = new vendor relationships — good timing"}],
  "pr_controversies": [],
  "marketing_freeze_detected": false,
  "marketing_freeze_details": null,
  "existing_agency_signals": [],
  "competitor_dominance_risk": null,
  "seasonality_watchout": null,
  "timing_recommendation": "PURSUE NOW | WAIT 30 DAYS | WAIT 60 DAYS | AVOID",
  "timing_reasoning": "Specific reason",
  "pitch_tone_adjustment": "How StepOneXP should adjust their pitch tone based on these watchouts"
}
GREEN = pursue immediately. AMBER = proceed with caution. RED = do not pitch now.
Only flag signals you found evidence for — do not fabricate risks."""


class StrategicWatchoutsPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Strategic Watchouts"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"risk_signals": []}
        queries = [
            f"{n} layoffs OR restructuring OR cost cutting 2024 2025",
            f"{n} controversy OR scandal OR backlash OR complaint",
            f"{n} CMO OR marketing head OR VP marketing 2024 2025 appointed OR left OR resigned",
            f"{n} funding OR revenue OR financial 2024 2025",
            f"{n} agency OR marketing partner OR campaign partner",
        ]
        for q in queries:
            raw["risk_signals"].extend(run_google_search(q, PIPELINE_ID, num_results=6))
        return raw

    def extract(self, raw: dict) -> dict:
        signals = []
        for item in raw.get("risk_signals", []):
            t = item.get("title", "")
            s = item.get("snippet") or item.get("description", "")
            d = item.get("date", "")
            if t:
                signals.append(f"[{d}] {t}: {s}")
        return {"company_name": self.company_name, "signals": signals[:25]}

    def synthesise(self, structured: dict) -> dict:
        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}

RISK SIGNALS FOUND:
{chr(10).join(structured['signals']) if structured['signals'] else 'No risk signals found in search results.'}
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=800)
        if result:
            parsed = safe_json_parse(result)
            if parsed: return parsed
        return {"overall_verdict": "AMBER", "verdict_reasoning": "Insufficient data for risk assessment", "timing_recommendation": "PURSUE NOW"}
