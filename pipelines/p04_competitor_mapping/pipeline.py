"""
Pipeline 04 — Competitor Mapping

Two-source strategy:
  Source A — GPT-4o Knowledge (PRIMARY):
    GPT-4o knows the positioning, marketing style, events activity and
    experiential gaps of major competitors across all categories. Used
    as the primary source for competitor intelligence — always produces
    real, substantive output (not UNKNOWN).

  Source B — Google Search (SUPPLEMENTARY):
    Identifies competitor names from search results and crawls 2 sites
    for recent positioning copy. Used to update GPT knowledge with
    anything new or to find less-known competitors.

  Merge: GPT identifies + analyses competitors using its knowledge,
    supplemented by any website content found via crawling.
"""
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.web_scraper import fast_crawl
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate, clean_text
from config.settings import OPENAI_MODEL_FULL

log = structlog.get_logger()
PIPELINE_ID = "p04_competitor_mapping"

IDENTIFY_PROMPT = """Identify up to 4 direct competitors to this company from the search results.
Return ONLY a JSON array: [{"name": "Company", "website": "https://... or null", "reason": "1 sentence why they compete"}]
Only include companies explicitly mentioned in the search results."""

KNOWLEDGE_ANALYSIS_PROMPT = """You are a competitive intelligence analyst for StepOneXP, an experiential marketing agency in India.

Using your training knowledge, provide a detailed competitive analysis. You know these brands — their positioning, marketing campaigns, events history, and experiential marketing activity.

Be specific. Do not use UNKNOWN for fields where you have knowledge. If a competitor runs events, say which kind. If their positioning is known, state it.

Return ONLY valid JSON, no markdown:
{
  "competitors": [
    {
      "name": "Company name",
      "brand_positioning": "Their actual positioning — how they describe themselves (1 sentence)",
      "positioning_style": "Premium | Value | Technical | Community | Bold | Natural | Playful",
      "marketing_activity_level": "HIGH | MEDIUM | LOW",
      "events_activity": "YES | NO | UNKNOWN",
      "events_description": "What events/activations they run — specific examples if known",
      "digital_presence_score": 4,
      "experiential_gap": "What experiential marketing opportunity they are NOT doing well",
      "threat_level_to_brand": "HIGH | MEDIUM | LOW"
    }
  ],
  "experiential_white_space": "Which competitor has the biggest experiential gap and exactly why",
  "competitive_urgency": "YES or NO — should StepOneXP mention competitor activity in pitch?",
  "recommended_pitch_angle": "Specific angle using competitor intel — e.g. 'Olay is spending big on retail activations, here is how Dove can differentiate'"
}"""

ENRICH_PROMPT = """You have knowledge-based competitor analysis AND real website content below.
Update the analysis with any new information from the website content.
Keep knowledge-based fields where website content is absent or generic.
Return the same JSON structure."""


class CompetitorMappingPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Competitor Mapping"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"competitor_search": [], "competitor_pages": {}, "identified_competitors": []}

        queries = [
            f"top competitors of {n} {self.category} India alternatives 2024",
            f"{n} vs {self.category} brands comparison India",
        ]
        raw["competitor_search"] = run_google_searches_parallel(queries, PIPELINE_ID, num_results=10)
        log.info("     Competitor landscape searched")

        comp_names = self._identify_competitors(raw["competitor_search"])
        if comp_names:
            log.info(f"     Identified: {', '.join(c.get('name','') for c in comp_names)}")

        for comp in comp_names[:2]:
            website = comp.get("website")
            if website and website.startswith("http"):
                try:
                    pages = fast_crawl(website, max_pages=2)
                    raw["competitor_pages"][comp["name"]] = {
                        "pages": pages, "reason": comp.get("reason", "")
                    }
                except Exception:
                    pass

        raw["identified_competitors"] = comp_names
        return raw

    def _identify_competitors(self, search_results: list) -> list:
        if not search_results:
            return []
        snippets = [
            f"- {r.get('title','')}: {r.get('snippet','') or r.get('description','')}"
            for r in search_results[:15]
            if r.get("title") or r.get("snippet")
        ]
        if not snippets:
            return []
        result = synthesise(
            IDENTIFY_PROMPT,
            f"COMPANY: {self.company_name}\nCATEGORY: {self.category}\n\nSEARCH RESULTS:\n" + "\n".join(snippets),
            max_tokens=400,
        )
        parsed = safe_json_parse(result or "")
        return parsed if isinstance(parsed, list) else []

    def extract(self, raw: dict) -> dict:
        comp_data = []
        for comp in raw.get("identified_competitors", []):
            name   = comp.get("name", "")
            pages  = raw.get("competitor_pages", {}).get(name, {}).get("pages", [])
            chunks = [
                truncate(clean_text(p.get("markdown") or p.get("text", "")), 400)
                for p in pages[:2]
                if p.get("markdown") or p.get("text")
            ]
            comp_data.append({
                "name":    name,
                "website": comp.get("website"),
                "reason":  comp.get("reason"),
                "content": "\n".join(chunks) if chunks else "",
            })
        return {
            "company_name": self.company_name,
            "competitors":  comp_data,
        }

    def synthesise(self, structured: dict) -> dict:
        n        = structured["company_name"]
        category = self.category
        comps    = structured.get("competitors", [])

        # ── Source A: GPT-4o knowledge — always gives real competitor intel ──
        # Build competitor list: use search-identified names if available,
        # otherwise let GPT identify them from its own knowledge
        if comps:
            comp_names_str = ", ".join(c["name"] for c in comps)
            knowledge_prompt = f"""BRAND: {n}
CATEGORY: {category}

COMPETITORS IDENTIFIED FROM SEARCH: {comp_names_str}

Analyse these competitors against {n}. Use your training knowledge to fill in their
positioning, events history, and experiential gaps. Be specific — you know these brands."""
        else:
            knowledge_prompt = f"""BRAND: {n}
CATEGORY: {category}
WEBSITE: {self.company_url or 'unknown'}

Identify and analyse the top 4 direct competitors to {n} in {category}.
Use your training knowledge of the Indian market and global brands in this space."""

        knowledge_raw    = synthesise(KNOWLEDGE_ANALYSIS_PROMPT, knowledge_prompt,
                                      model=OPENAI_MODEL_FULL, max_tokens=1400)
        result           = safe_json_parse(knowledge_raw or "") or {}

        # ── Source B: Enrich with real website content if available ──────────
        website_content = "\n\n".join(
            f"--- {c['name']} website ---\n{c['content']}"
            for c in comps
            if c.get("content")
        )
        if website_content:
            enrich_prompt = f"""BRAND: {n}
CATEGORY: {category}

KNOWLEDGE-BASED ANALYSIS:
{knowledge_raw or '(none)'}

REAL WEBSITE CONTENT:
{website_content[:2000]}

Update the analysis with any new positioning copy or evidence from the website content."""

            enriched     = synthesise(ENRICH_PROMPT, enrich_prompt,
                                      model=OPENAI_MODEL_FULL, max_tokens=1400)
            enriched_out = safe_json_parse(enriched or "")
            if enriched_out and enriched_out.get("competitors"):
                result = enriched_out

        comp_count = len((result or {}).get("competitors", []))
        urgency    = (result or {}).get("competitive_urgency", "")
        log.info(f"     {comp_count} competitors mapped · Competitive urgency: {urgency}")

        return result or {
            "competitors":             [],
            "experiential_white_space": f"No competitor data for {n}",
            "competitive_urgency":      "NO",
            "recommended_pitch_angle":  "Focus on brand's own experiential gaps",
        }
