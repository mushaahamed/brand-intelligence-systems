"""
Pipeline 06 — Experiential & Events Footprint
Finds sponsorships, activations, campaigns, awards, launches, and any brand presence.
"""
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate

log = structlog.get_logger()
PIPELINE_ID = "p06_experiential_footprint"

SYSTEM_PROMPT = """You are an experiential marketing intelligence analyst for StepOneXP, an experiential marketing agency.

Your job is to map EVERYTHING this brand has done that involves a physical or digital presence:
- Events they HOSTED (product launches, brand days, annual meets)
- Events they SPONSORED (IPL, concerts, marathons, festivals)
- Pop-ups, roadshows, activations, retail experiences
- Award ceremonies they attended or won
- Partnerships that involved on-ground activation
- Campaign launches with events or experiential elements
- CSR events, community activations
- Trade shows, conferences, summits they participated in

IMPORTANT: Be INCLUSIVE. If a search result mentions the brand in ANY event context — even as a sponsor
or attendee — include it. Better to include more than miss something important.

Return ONLY valid JSON:
{
  "events_timeline": [
    {
      "event_name": "Name or clear description of the event",
      "date": "YYYY-MM or approximate year",
      "format": "Conference | Product launch | Consumer activation | Sponsorship | Pop-up | Roadshow | Award | CSR | Partnership activation | Virtual | Unknown",
      "scale": "Intimate (<100) | Mid (100-500) | Large (500-2000) | Mass (2000+) | Unknown",
      "location": "City, Country or 'Multiple cities' or 'Online'",
      "brand_role": "Host | Sponsor | Participant | Co-host",
      "production_quality": "DIY | Standard | Premium | World-class | Unknown",
      "source": "snippet from search result"
    }
  ],
  "experiential_maturity_score": 3,
  "maturity_score_reasoning": "1-5: 1=never done events, 5=sophisticated multi-city program. Be specific.",
  "formats_used": ["list each format type found"],
  "formats_missing": ["formats appropriate for this brand's scale that they have NOT done — be specific"],
  "geography_of_events": ["cities/regions where they have activated"],
  "last_event_months_ago": 6,
  "events_frequency": "Monthly | Quarterly | Annual | Sporadic | Never identified",
  "pitch_angle": "One specific sentence about what StepOneXP can offer — based on their actual gap",
  "opening_line_for_pitch": "A compelling opening line for StepOneXP's pitch email referencing a REAL event or gap",
  "confidence_level": "HIGH | MEDIUM | LOW"
}

RULE: NEVER return an empty events_timeline for any brand that has existed for more than 1 year.
Every brand of scale has done at least a product launch event, a press day, or a sponsorship.
If you cannot find specific events from search data, use your training knowledge to populate the timeline.
Mark uncertain events with source="inferred from brand scale / training knowledge".
An empty events_timeline means you are certain the brand has NEVER done any public-facing activity — this
is almost never true for established brands. A score of 2-3 is typical; only give 1 if the brand is
a complete startup with zero public presence."""


class ExperientialFootprintPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Experiential & Events Footprint"

    def fetch(self) -> dict:
        n = self.company_name
        # Broad queries — catch sponsorships, campaigns, events, awards, anything
        queries = [
            f"{n} event launch activation sponsorship pop-up roadshow 2023 2024 2025",
            f"{n} campaign award sponsor partner CSR experience marketing",
        ]
        results = run_google_searches_parallel(queries, PIPELINE_ID, num_results=10)
        log.info("p06_search_results", count=len(results))
        return {"event_search": results}

    def extract(self, raw: dict) -> dict:
        # BROAD keyword filter — include anything remotely event/experience related
        broad_keywords = [
            "event", "launch", "activation", "conference", "roadshow", "pop-up", "popup",
            "experience", "festival", "summit", "meet", "sponsor", "sponsorship",
            "campaign", "award", "ceremony", "concert", "show", "exhibition", "expo",
            "partner", "partnership", "collaboration", "celebrate", "celebration",
            "workshop", "marathon", "run", "league", "tournament", "cricket",
            "csr", "community", "initiative", "flagship", "tour", "drive",
        ]

        event_signals = []
        all_signals   = []  # Keep ALL results as fallback

        for item in raw.get("event_search", []):
            t   = item.get("title", "")
            s   = item.get("snippet") or item.get("description", "")
            d   = item.get("date", "")
            url = item.get("url", "") or item.get("link", "")

            if not (t or s):
                continue

            combined = f"{t} {s}".lower()
            all_signals.append(f"[{d}] {t}: {s}")

            if any(kw in combined for kw in broad_keywords):
                event_signals.append(f"[{d}] {t}: {s}")

        # If strict filter found nothing, use ALL results (let LLM decide)
        signals_to_use = event_signals if event_signals else all_signals

        log.info("p06_signals", broad_matches=len(event_signals), total=len(all_signals))

        return {
            "company_name":  self.company_name,
            "event_signals": signals_to_use[:25],
            "has_signals":   bool(signals_to_use),
        }

    def synthesise(self, structured: dict) -> dict:
        signals = structured.get("event_signals", [])

        if signals:
            signals_text = "\n".join(signals[:20])
        else:
            signals_text = "No direct event mentions found in search results."

        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}

SEARCH SIGNALS (titles + snippets from Google):
{signals_text}

---
TASK: Map {structured['company_name']}'s complete experiential footprint.

CRITICAL INSTRUCTION: You MUST use your own training knowledge about {structured['company_name']} in addition
to the search signals above. Do NOT leave events_timeline empty if you know anything about this brand.

For Indian D2C brands like {structured['company_name']}, common activities include:
- IPL or cricket sponsorships
- In-store pop-ups or retail activations at Nykaa, Myntra, Purplle counters
- Brand days or anniversary events
- Influencer experience days or seeding events
- Partnership launches (e.g. with Zepto, Blinkit, celebrity collaborations)
- CSR tree-planting or sustainability initiatives with on-ground elements
- Awards at events like ET Brand Equity, D2C Summit, Inc42 events
- Campaign launches with press/media events

If you know {structured['company_name']} has done ANY of the above — even if not in the search signals —
include it in events_timeline. Even unconfirmed/likely events should be marked with source="training knowledge".
A score of 1 means they have NEVER done any event in their entire existence — reserve 1 only if that is truly the case.
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=1500)

        if result:
            parsed = safe_json_parse(result)
            if parsed and isinstance(parsed, dict):
                # Ensure events_timeline is a list (not None)
                if not isinstance(parsed.get("events_timeline"), list):
                    parsed["events_timeline"] = []
                # Ensure score exists
                if not parsed.get("experiential_maturity_score"):
                    parsed["experiential_maturity_score"] = 1 if not parsed["events_timeline"] else 2
                return parsed

        # Rich fallback — never return empty
        log.warning("p06_synthesis_fallback", company=structured["company_name"])
        return {
            "events_timeline": [],
            "experiential_maturity_score": 1,
            "maturity_score_reasoning": "No confirmed events found in research — may be a first-mover opportunity",
            "formats_used": [],
            "formats_missing": [
                "Consumer pop-up activation",
                "Product launch event",
                "Experiential retail activation",
                "City roadshow",
                "Influencer experience day",
            ],
            "geography_of_events": [],
            "last_event_months_ago": None,
            "events_frequency": "Never identified",
            "pitch_angle": f"{self.company_name} has no confirmed experiential footprint — StepOneXP can be their first agency partner for events, creating a brand new revenue line and consumer touchpoint.",
            "opening_line_for_pitch": f"We noticed {self.company_name} hasn't yet activated in experiential — given your scale in {self.category}, a well-executed pop-up or roadshow could significantly accelerate direct consumer connection.",
            "confidence_level": "LOW",
        }
