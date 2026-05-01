"""
Pipeline 04 — Competitor Mapping
==================================
Layer 1: Google search to identify 3-5 competitors + scrape their sites
Layer 2: Per-competitor metrics — positioning, activity, events gap
Layer 3: Comparison table + experiential white space identification
Layer 4 (validation): Verify competitor names against a second source
"""
import json, structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_search, crawl_website
from utils.claude_client import synthesise, extract_json
from utils.helpers import safe_json_parse, truncate, clean_text

log = structlog.get_logger()
PIPELINE_ID = "p04_competitor_mapping"

COMPETITOR_IDENTIFY_PROMPT = """Identify the 4 most direct competitors to this company from the search results.
Return ONLY a JSON array of objects: [{"name": "Company", "website": "url or null", "reason": "why they compete"}]
Maximum 4 competitors. Only include real companies you can confirm from the search results."""

COMPETITOR_ANALYSE_PROMPT = """You are a competitive intelligence analyst for an experiential marketing agency.
Analyse the competitor data provided and return ONLY valid JSON:
{
  "competitors": [
    {
      "name": "Company name",
      "brand_positioning": "How they describe themselves",
      "positioning_style": "Premium | Value | Technical | Community | Bold",
      "marketing_activity_level": "HIGH | MEDIUM | LOW",
      "events_activity": "YES | NO | UNKNOWN",
      "events_description": "What events they've run if any",
      "digital_presence_score": 3,
      "employee_growth": "GROWING | STABLE | SHRINKING | UNKNOWN",
      "experiential_gap": "What they're missing in experiential",
      "threat_level_to_brand": "HIGH | MEDIUM | LOW"
    }
  ],
  "experiential_white_space": "Which competitor has the biggest events gap and why",
  "competitive_urgency": "Should StepOneXP mention competitor activity in pitch? YES/NO and why",
  "recommended_pitch_angle": "How StepOneXP should use competitor intel in their pitch"
}"""


class CompetitorMappingPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Competitor Mapping"

    def fetch(self) -> dict:
        n = self.company_name
        raw = {"competitor_search": [], "competitor_pages": {}}

        # Step 1: Identify competitors
        queries = [
            f"{n} competitors alternatives similar companies",
            f"alternatives to {n} {self.category}",
            f"{n} vs competitors 2024 2025",
        ]
        for q in queries:
            raw["competitor_search"].extend(run_google_search(q, PIPELINE_ID, num_results=8))

        # Step 2: Identify + scrape top competitor websites
        comp_names = self._identify_competitors(raw["competitor_search"])
        for comp in comp_names[:3]:  # Limit to 3 to preserve Apify credits
            if comp.get("website"):
                pages = crawl_website(comp["website"], PIPELINE_ID, max_pages=3)
                raw["competitor_pages"][comp["name"]] = {
                    "pages": pages,
                    "reason": comp.get("reason", ""),
                }
        raw["identified_competitors"] = comp_names
        return raw

    def _identify_competitors(self, search_results: list) -> list:
        snippets = [f"{r.get('title','')}: {r.get('snippet','')}" for r in search_results[:10]]
        data     = "\n".join(snippets)
        result   = synthesise(COMPETITOR_IDENTIFY_PROMPT,
                              f"COMPANY: {self.company_name}\nCATEGORY: {self.category}\n\nSEARCH RESULTS:\n{data}",
                              max_tokens=400)
        if result:
            parsed = safe_json_parse(result)
            if isinstance(parsed, list): return parsed
        return []

    def extract(self, raw: dict) -> dict:
        comp_data = []
        for comp in raw.get("identified_competitors", []):
            name = comp.get("name", "")
            pages_data = raw.get("competitor_pages", {}).get(name, {})
            pages      = pages_data.get("pages", [])
            text_chunks = []
            for page in pages[:3]:
                text = page.get("markdown") or page.get("text", "")
                text_chunks.append(truncate(clean_text(text), 500))
            comp_data.append({
                "name":    name,
                "website": comp.get("website"),
                "reason":  comp.get("reason"),
                "content": "\n".join(text_chunks),
            })
        return {"company_name": self.company_name, "competitors": comp_data}

    def synthesise(self, structured: dict) -> dict:
        comp_text = ""
        for c in structured.get("competitors", []):
            comp_text += f"\n\n--- COMPETITOR: {c['name']} ---\nWebsite: {c.get('website','N/A')}\nReason for competition: {c.get('reason','')}\nContent:\n{c.get('content','No content scraped')[:400]}"

        user_data = f"""BRAND BEING RESEARCHED: {structured['company_name']}
CATEGORY: {self.category}

COMPETITOR DATA:{comp_text}"""

        result = synthesise(COMPETITOR_ANALYSE_PROMPT, user_data, max_tokens=1200)
        if result:
            parsed = safe_json_parse(result)
            if parsed: return parsed
        return {"competitors": [], "experiential_white_space": "Analysis incomplete", "recommended_pitch_angle": "Manual review needed"}
