"""
Pipeline 04 — Competitor Mapping
Fast version: parallel Google searches + direct HTTP for competitor sites.
"""
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.web_scraper import fast_crawl
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate, clean_text

log = structlog.get_logger()
PIPELINE_ID = "p04_competitor_mapping"

COMPETITOR_IDENTIFY_PROMPT = """Identify up to 4 direct competitors to this company from the search results.
Return ONLY a JSON array: [{"name": "Company", "website": "https://... or null", "reason": "1 sentence why they compete"}]
Only include companies explicitly mentioned in the search results. If fewer than 4 are found, return what you have."""

COMPETITOR_ANALYSE_PROMPT = """You are a competitive intelligence analyst for an experiential marketing agency.
Analyse the competitor data and return ONLY valid JSON:
{
  "competitors": [
    {
      "name": "Company name",
      "brand_positioning": "How they describe themselves (1 sentence)",
      "positioning_style": "Premium | Value | Technical | Community | Bold",
      "marketing_activity_level": "HIGH | MEDIUM | LOW",
      "events_activity": "YES | NO | UNKNOWN",
      "events_description": "What events they've run if any, or UNKNOWN",
      "digital_presence_score": 3,
      "experiential_gap": "What they're missing in experiential marketing",
      "threat_level_to_brand": "HIGH | MEDIUM | LOW"
    }
  ],
  "experiential_white_space": "Which competitor has the biggest gap and why",
  "competitive_urgency": "YES or NO — should StepOneXP mention competitor activity in pitch?",
  "recommended_pitch_angle": "How to use competitor intel in the pitch"
}
If data is limited, use UNKNOWN for uncertain fields. Do not fabricate details."""


class CompetitorMappingPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Competitor Mapping"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"competitor_search": [], "competitor_pages": {}}

        # Search for competitors
        queries = [
            f"top competitors of {n} {self.category} alternatives 2024",
            f"{n} vs similar brands comparison {self.category}",
        ]
        raw["competitor_search"] = run_google_searches_parallel(queries, PIPELINE_ID, num_results=10)
        log.info("p04_competitor_search", results=len(raw["competitor_search"]))

        # Identify competitors from search results using LLM
        comp_names = self._identify_competitors(raw["competitor_search"])
        log.info("p04_competitors_identified", count=len(comp_names), competitors=[c.get("name") for c in comp_names])

        # Crawl top 2 competitor websites
        for comp in comp_names[:2]:
            website = comp.get("website")
            if website and website.startswith("http"):
                try:
                    log.info("p04_crawling_competitor", name=comp.get("name"), url=website)
                    pages = fast_crawl(website, max_pages=2)
                    raw["competitor_pages"][comp["name"]] = {
                        "pages": pages,
                        "reason": comp.get("reason", ""),
                    }
                except Exception as e:
                    log.warning("p04_crawl_failed", name=comp.get("name"), error=str(e))

        raw["identified_competitors"] = comp_names
        return raw

    def _identify_competitors(self, search_results: list) -> list:
        if not search_results:
            return []
        snippets = []
        for r in search_results[:15]:
            t = r.get("title", "")
            s = r.get("snippet", "") or r.get("description", "")
            if t or s:
                snippets.append(f"- {t}: {s}")

        if not snippets:
            return []

        result = synthesise(
            COMPETITOR_IDENTIFY_PROMPT,
            f"COMPANY: {self.company_name}\nCATEGORY: {self.category}\n\nSEARCH RESULTS:\n{chr(10).join(snippets)}",
            max_tokens=500,
        )
        if result:
            parsed = safe_json_parse(result)
            if isinstance(parsed, list) and parsed:
                return parsed
        return []

    def extract(self, raw: dict) -> dict:
        comp_data = []
        for comp in raw.get("identified_competitors", []):
            name  = comp.get("name", "")
            pages = raw.get("competitor_pages", {}).get(name, {}).get("pages", [])
            text_chunks = []
            for page in pages[:2]:
                text = page.get("markdown") or page.get("text", "")
                if text:
                    text_chunks.append(truncate(clean_text(text), 400))
            comp_data.append({
                "name":    name,
                "website": comp.get("website"),
                "reason":  comp.get("reason"),
                "content": "\n".join(text_chunks) if text_chunks else "No website content retrieved.",
            })

        # If no competitors identified from LLM, extract from search result titles
        if not comp_data:
            seen = set([self.company_name.lower()])
            for item in raw.get("competitor_search", [])[:10]:
                t = item.get("title", "")
                # Look for "vs" patterns or brand names
                if " vs " in t.lower():
                    parts = t.lower().split(" vs ")
                    for part in parts:
                        brand = part.strip().split(" ")[0].title()
                        if brand.lower() not in seen and len(brand) > 2:
                            seen.add(brand.lower())
                            comp_data.append({"name": brand, "website": None, "reason": f"Found in 'vs' comparison", "content": ""})
                            if len(comp_data) >= 3: break
                if len(comp_data) >= 3: break

        return {"company_name": self.company_name, "competitors": comp_data}

    def synthesise(self, structured: dict) -> dict:
        competitors = structured.get("competitors", [])

        if not competitors:
            return {
                "competitors": [],
                "experiential_white_space": f"Unable to identify competitors for {self.company_name} from search data",
                "competitive_urgency": "NO",
                "recommended_pitch_angle": "Focus on the brand's own experiential gaps rather than competitor comparison",
            }

        comp_text = ""
        for c in competitors:
            comp_text += f"\n\n--- {c['name']} ---\nWebsite: {c.get('website','N/A')}\nWhy competitor: {c.get('reason','')}\nContent:\n{c.get('content','No content')[:400]}"

        user_data = f"""BRAND: {structured['company_name']}
CATEGORY: {self.category}

COMPETITOR DATA:{comp_text}"""

        result = synthesise(COMPETITOR_ANALYSE_PROMPT, user_data, max_tokens=1200)
        if result:
            parsed = safe_json_parse(result)
            if parsed:
                return parsed

        # Fallback: build basic output from identified competitors
        return {
            "competitors": [{"name": c["name"], "brand_positioning": "Unknown", "events_activity": "UNKNOWN",
                             "experiential_gap": "Unknown", "threat_level_to_brand": "MEDIUM"} for c in competitors],
            "experiential_white_space": "Analysis incomplete — manual review recommended",
            "competitive_urgency": "NO",
            "recommended_pitch_angle": "Manual review needed",
        }
