"""
Pipeline 09 — Decision-Maker Identification
=============================================
Layer 1: LinkedIn profile search for 4 target roles + company page scrape
Layer 2: Validate each person — name, title, time in role, activity level
Layer 3: Ranked buying committee with role relevance + pitch priority

Target roles for experiential marketing pitch:
  1. CMO / VP Marketing / Head of Brand (Economic Buyer)
  2. Brand Manager / Senior Marketing Manager (Initiator)
  3. Events Manager / Experiential Lead / Activation Manager (Events Specialist)
  4. Head of HR / People & Culture (for employee experience pitches)
"""
import json, structlog
from pipelines.base import BasePipeline
from utils.apify_client import scrape_linkedin_profiles, run_actor, run_google_search
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate

log = structlog.get_logger()
PIPELINE_ID = "p09_decision_makers"

TARGET_ROLES = [
    ("CMO OR VP Marketing OR Chief Marketing Officer OR Head of Brand OR Head of Marketing", "Economic Buyer"),
    ("Brand Manager OR Senior Marketing Manager OR Marketing Lead", "Initiator"),
    ("Events Manager OR Experiential Manager OR Activation Manager OR Brand Activation", "Events Specialist"),
    ("Head of People OR Head of HR OR People and Culture OR CHRO", "Influencer"),
]

SYSTEM_PROMPT = """You are a B2B sales intelligence analyst. Evaluate these LinkedIn profiles and identify the best contacts for an experiential marketing agency pitch.

Return ONLY valid JSON:
{
  "buying_committee": [
    {
      "name": "Full Name",
      "title": "Exact current title",
      "role_type": "Economic Buyer | Initiator | Events Specialist | Influencer | Gatekeeper",
      "company_tenure_months": 18,
      "linkedin_url": "https://linkedin.com/in/...",
      "linkedin_activity": "ACTIVE | MODERATE | DORMANT | UNKNOWN",
      "previous_company": "Previous employer if available",
      "experiential_familiarity_signal": "Any evidence they've worked on events/experiences",
      "decision_relevance_score": 5,
      "outreach_priority": "PRIMARY | SECONDARY | AVOID",
      "personalisation_hook": "One specific thing to reference in outreach to this person"
    }
  ],
  "primary_contact": "Name of highest priority contact",
  "total_contacts_found": 3,
  "confidence_level": "HIGH | MEDIUM | LOW",
  "committee_gap": "Which role type was NOT found"
}
Decision relevance score 1-5: 5=directly owns events budget, 1=peripheral role."""


class DecisionMakersPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Decision-Maker Identification"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"profiles": [], "google_people": []}

        # LinkedIn search per target role
        for role_query, role_type in TARGET_ROLES:
            query = f"{n} {role_query}"
            profiles = scrape_linkedin_profiles(query, PIPELINE_ID, max_results=2)
            for p in (profiles or []):
                p["_target_role_type"] = role_type
            raw["profiles"].extend(profiles or [])

        # Google search as fallback for public profiles
        google_queries = [
            f'site:linkedin.com/in "{n}" "VP Marketing" OR "CMO" OR "Head of Brand"',
            f'"{n}" "brand manager" OR "events manager" LinkedIn',
        ]
        for q in google_queries:
            raw["google_people"].extend(run_google_search(q, PIPELINE_ID, num_results=5))

        return raw

    def extract(self, raw: dict) -> dict:
        people = []
        seen_names = set()

        for profile in raw.get("profiles", []):
            name  = profile.get("name") or profile.get("fullName", "")
            title = profile.get("headline") or profile.get("title") or profile.get("jobTitle", "")
            url   = profile.get("url") or profile.get("profileUrl", "")
            company_check = profile.get("currentCompanyName") or profile.get("company", "")

            if not name or name in seen_names:
                continue

            # Verify they actually work at the target company
            if self.company_name.lower()[:6] not in company_check.lower() and company_check:
                continue

            seen_names.add(name)
            people.append({
                "name":        name,
                "title":       title,
                "url":         url,
                "role_type":   profile.get("_target_role_type", "Unknown"),
                "location":    profile.get("location", ""),
                "tenure":      profile.get("currentCompanyDuration", ""),
                "previous":    profile.get("previousCompanyName", ""),
                "summary":     truncate(profile.get("summary") or profile.get("about", ""), 200),
            })

        # Add Google results as lower-confidence entries
        for item in raw.get("google_people", [])[:3]:
            title_hint = item.get("title", "")
            snippet    = item.get("snippet", "")
            url        = item.get("link") or item.get("url", "")
            if "linkedin.com/in" in url:
                people.append({
                    "name":     title_hint.split(" - ")[0] if " - " in title_hint else title_hint[:40],
                    "title":    snippet[:80],
                    "url":      url,
                    "role_type":"Unknown (Google result)",
                    "source":   "google",
                })

        return {"company_name": self.company_name, "people": people[:8]}

    def synthesise(self, structured: dict) -> dict:
        people_text = json.dumps(structured.get("people", []), indent=2)
        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}

PROFILES FOUND ({len(structured.get('people', []))} people):
{people_text}
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=1200)
        if result:
            parsed = safe_json_parse(result)
            if parsed: return parsed
        return {
            "buying_committee": [],
            "primary_contact":  None,
            "confidence_level": "LOW",
            "committee_gap":    "All roles — LinkedIn search returned no verified results",
        }
