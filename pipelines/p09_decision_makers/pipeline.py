"""
Pipeline 09 — Decision-Maker Identification
Fast version: Google searches for CMO/Marketing heads — finds real people.
"""
import json, structlog
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate

log = structlog.get_logger()
PIPELINE_ID = "p09_decision_makers"

SYSTEM_PROMPT = """You are a B2B sales intelligence analyst. From the search results, identify the best contacts at this company for an experiential marketing agency pitch.

Return ONLY valid JSON:
{
  "buying_committee": [
    {
      "name": "Full Name",
      "title": "Exact current title",
      "role_type": "Economic Buyer | Initiator | Events Specialist | Influencer",
      "company_tenure_months": 18,
      "linkedin_url": "https://linkedin.com/in/... or null",
      "linkedin_activity": "ACTIVE | MODERATE | DORMANT | UNKNOWN",
      "decision_relevance_score": 4,
      "outreach_priority": "PRIMARY | SECONDARY | AVOID",
      "personalisation_hook": "One specific thing to reference in outreach to this person"
    }
  ],
  "primary_contact": "Name of highest priority contact",
  "total_contacts_found": 3,
  "confidence_level": "HIGH | MEDIUM | LOW",
  "committee_gap": "Which role type was NOT found"
}
Decision relevance 1-5: 5=directly owns events budget, 1=peripheral. Extract real people only."""


class DecisionMakersPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Decision-Maker Identification"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"google_people": []}

        # Strategy: search for leadership/marketing team — broader queries work better than site:linkedin
        queries = [
            f'"{n}" "Chief Marketing Officer" OR "CMO" OR "VP Marketing" OR "Head of Marketing" OR "Head of Brand" linkedin',
            f'"{n}" "Brand Manager" OR "Events Manager" OR "Marketing Director" OR "Head of People" linkedin',
        ]
        raw["google_people"] = run_google_searches_parallel(queries, PIPELINE_ID, num_results=8)

        log.info("p09_google_results", count=len(raw["google_people"]))
        return raw

    def extract(self, raw: dict) -> dict:
        people = []
        seen   = set()

        for item in raw.get("google_people", []):
            title_raw = item.get("title", "")
            snippet   = item.get("snippet", "") or item.get("description", "")
            url       = item.get("url", "") or item.get("link", "")

            # Extract name from title: "FirstName LastName - Title at Company | LinkedIn"
            # or "Name | LinkedIn"
            name = ""
            if " - " in title_raw:
                name = title_raw.split(" - ")[0].strip()
            elif " | " in title_raw:
                name = title_raw.split(" | ")[0].strip()
            else:
                name = title_raw.split(" ·")[0].strip()

            # Clean up name (remove "LinkedIn" etc)
            name = name.replace("LinkedIn", "").replace("Profile", "").strip()
            if len(name.split()) < 2 or len(name) > 50:
                # Try extracting from snippet
                if snippet and " at " in snippet:
                    parts = snippet.split(" at ")[0].strip().split()
                    if 2 <= len(parts) <= 3:
                        name = " ".join(parts)

            # Extract title from the result
            role = ""
            for kw in ["CMO", "Chief Marketing", "VP Marketing", "Head of Marketing", "Head of Brand",
                        "Brand Manager", "Marketing Director", "Events Manager", "Head of People",
                        "Marketing Lead", "Marketing Manager"]:
                if kw.lower() in snippet.lower() or kw.lower() in title_raw.lower():
                    role = kw; break

            if not name or name in seen or len(name) < 4:
                continue
            seen.add(name)

            people.append({
                "name":     name,
                "title":    role or title_raw[:80],
                "url":      url,
                "role_type": "Economic Buyer" if any(k in role for k in ["CMO", "VP", "Chief", "Director", "Head of Marketing", "Head of Brand"]) else "Initiator",
                "snippet":  snippet[:200],
                "source":   "google",
            })

        log.info("p09_people_extracted", count=len(people))
        return {"company_name": self.company_name, "people": people[:8]}

    def synthesise(self, structured: dict) -> dict:
        people = structured.get("people", [])
        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}

PEOPLE FOUND VIA GOOGLE ({len(people)} results):
{json.dumps(people, indent=2)}

Note: Extract real names and titles only. If a result looks like a person at {structured['company_name']},
include them. Infer role_type and outreach_priority from their title.
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=1200)
        if result:
            parsed = safe_json_parse(result)
            if parsed and parsed.get("buying_committee"):
                return parsed

        # If synthesis fails or returns no people, build from extracted data directly
        if people:
            committee = []
            for i, p in enumerate(people[:5]):
                committee.append({
                    "name":                 p["name"],
                    "title":                p.get("title", ""),
                    "role_type":            p.get("role_type", "Initiator"),
                    "company_tenure_months": None,
                    "linkedin_url":         p["url"] if "linkedin.com/in" in p.get("url","") else None,
                    "linkedin_activity":    "UNKNOWN",
                    "decision_relevance_score": 4 if i == 0 else 3,
                    "outreach_priority":    "PRIMARY" if i == 0 else "SECONDARY",
                    "personalisation_hook": p.get("snippet", "")[:100],
                })
            return {
                "buying_committee":    committee,
                "primary_contact":     committee[0]["name"] if committee else None,
                "total_contacts_found": len(committee),
                "confidence_level":    "MEDIUM",
                "committee_gap":       "Events Specialist",
            }

        return {
            "buying_committee": [],
            "primary_contact":  None,
            "confidence_level": "LOW",
            "committee_gap":    "All roles — no results found",
        }
