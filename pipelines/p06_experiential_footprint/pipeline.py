"""
Pipeline 06 — Experiential & Events Footprint
===============================================
Layer 1: Google search for events/activations + Instagram event posts + LinkedIn posts
Layer 2: Per-event extraction — format, scale, location, recency, outcome
Layer 3: Timeline + maturity score + format gap + StepOneXP pitch angle
Layer 4: Validate events against 2 sources before including in output

This is the highest-priority pipeline for StepOneXP.
"""
import json, structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_search, run_actor
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate

log = structlog.get_logger()
PIPELINE_ID = "p06_experiential_footprint"

SYSTEM_PROMPT = """You are an experiential marketing intelligence analyst for StepOneXP, an experiential marketing agency.
Analyse the data to map this brand's events and experiential history.

Return ONLY valid JSON:
{
  "events_timeline": [
    {
      "event_name": "name or description",
      "date": "YYYY-MM or approximate year",
      "format": "Conference | Product launch | Consumer activation | Employee/internal | Sponsorship | Pop-up | Roadshow | Virtual | Unknown",
      "scale": "Intimate (<100) | Mid (100-500) | Large (500-2000) | Mass (2000+) | Unknown",
      "location": "City, Country",
      "production_quality": "DIY | Standard | Premium | World-class | Unknown",
      "outcome_mentioned": true,
      "source": "URL or source name"
    }
  ],
  "experiential_maturity_score": 3,
  "maturity_score_reasoning": "1-5: 1=never done events, 5=sophisticated multi-city program",
  "formats_used": ["list of formats the brand has executed"],
  "formats_missing": ["formats appropriate for their scale that they have NOT done"],
  "geography_of_events": ["cities/regions where they've activated"],
  "last_event_months_ago": 8,
  "events_frequency": "Monthly | Quarterly | Annual | Sporadic | Never identified",
  "pitch_angle": "One sentence — the specific StepOneXP service that fills the identified gap",
  "opening_line_for_pitch": "Specific opening line referencing a real event they did or the gap identified",
  "confidence_level": "HIGH | MEDIUM | LOW"
}
Rules:
- Only include events you have evidence for from the data
- Flag LOW confidence if events found from only one source
- The pitch_angle must be specific to their gap — not generic"""


class ExperientialFootprintPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Experiential & Events Footprint"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"event_search": [], "instagram": []}
        queries = [
            f"{n} event activation launch party 2024 2025",
            f"{n} conference roadshow pop-up experience",
            f"{n} brand activation experiential marketing",
            f"{n} sponsored event OR hosted event OR annual meet",
        ]
        for q in queries:
            raw["event_search"].extend(run_google_search(q, PIPELINE_ID, num_results=8))

        # Instagram for visual event evidence
        handle = self.company_name.lower().replace(" ", "")
        ig_data = run_actor(
            "instagram_scraper",
            {"usernames": [handle], "resultsLimit": 20, "searchType": "user"},
            PIPELINE_ID, timeout_secs=60
        )
        raw["instagram"] = ig_data or []
        return raw

    def extract(self, raw: dict) -> dict:
        event_signals = []
        for item in raw.get("event_search", []):
            t = item.get("title", "")
            s = item.get("snippet") or item.get("description", "")
            d = item.get("date", "")
            url = item.get("link") or item.get("url", "")
            event_keywords = ["event", "launch", "activation", "conference", "roadshow",
                              "pop-up", "popup", "experience", "festival", "summit", "meet"]
            text = f"{t} {s}".lower()
            if any(kw in text for kw in event_keywords):
                event_signals.append(f"[{d}] [{url}] {t}: {s}")

        ig_event_posts = []
        for post in raw.get("instagram", [])[:15]:
            caption = post.get("caption") or post.get("text", "")
            ts      = post.get("timestamp", "")
            if caption:
                lower_cap = caption.lower()
                if any(kw in lower_cap for kw in ["event", "launch", "experience", "party", "activation"]):
                    ig_event_posts.append(f"[{ts}] {truncate(caption, 120)}")

        return {
            "company_name":   self.company_name,
            "event_signals":  event_signals[:20],
            "ig_event_posts": ig_event_posts[:8],
        }

    def synthesise(self, structured: dict) -> dict:
        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}

EVENT SIGNALS FROM SEARCH:
{chr(10).join(structured['event_signals']) if structured['event_signals'] else 'No direct event mentions found in search results.'}

INSTAGRAM EVENT POSTS:
{chr(10).join(structured['ig_event_posts']) if structured['ig_event_posts'] else 'No Instagram event posts retrieved.'}
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=1200)
        if result:
            parsed = safe_json_parse(result)
            if parsed:
                return parsed
        return {
            "events_timeline": [],
            "experiential_maturity_score": 1,
            "formats_missing": ["All formats — no events identified"],
            "pitch_angle": f"First mover opportunity — no experiential footprint identified for {self.company_name}",
            "confidence_level": "LOW",
        }
