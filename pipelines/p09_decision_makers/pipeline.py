"""
Pipeline 09 — Decision-Maker Identification

Simple, reliable approach:
1. 3 parallel Google searches → raw results (title + snippet + URL)
2. Company team/about page scrape
3. GPT-4o-mini reads ALL raw text and extracts the buying committee

No pre-filtering. The old approach dropped "SVP Marketing", "AVP Brand" etc.
because they weren't in the keyword list. GPT understands all titles natively.
"""
import re, requests, structlog
from bs4 import BeautifulSoup
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, normalise_url

log = structlog.get_logger()
PIPELINE_ID = "p09_decision_makers"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

SYSTEM_PROMPT = """You are a B2B sales intelligence analyst for StepOneXP, an experiential marketing agency in India.

From the raw Google search results and company page text below, identify the best people to contact for an experiential marketing pitch.

Focus on: CMO, VP/SVP/AVP Marketing, Head of Marketing, Brand Director/Manager, Events Manager, CEO/Founder, Head of Growth, Head of Brand, Category Manager, Head of Consumer Marketing — anyone who could approve or influence experiential marketing spend.

Return ONLY valid JSON, no markdown fences:
{
  "buying_committee": [
    {
      "name": "Full Name",
      "title": "Their exact title",
      "role_type": "Economic Buyer | Initiator | Events Specialist | Influencer",
      "company_tenure_months": null,
      "linkedin_url": "https://linkedin.com/in/... or null",
      "linkedin_activity": "UNKNOWN",
      "decision_relevance_score": 4,
      "outreach_priority": "PRIMARY | SECONDARY",
      "personalisation_hook": "One specific detail from their profile or work to reference in outreach"
    }
  ],
  "primary_contact": "Name of single best person to contact first",
  "total_contacts_found": 3,
  "confidence_level": "HIGH | MEDIUM | LOW",
  "committee_gap": "Which role is missing, or None"
}

Rules:
- Include 2-5 people. Quality over quantity.
- PRIMARY = CMO / VP Marketing / Head of Marketing (whoever is most senior in marketing)
- SECONDARY = Brand Managers, Events Managers, Growth leads
- decision_relevance_score: 5 = owns events budget, 1 = peripheral
- linkedin_url: extract the full URL if visible in the search result
- If a result is from LinkedIn (in.linkedin.com or www.linkedin.com), the person IS at or was at the company
- Only include people who genuinely appear to be at this company"""


def _scrape_team_page(company_url: str) -> str:
    """Try common team/about paths on the company website."""
    base = normalise_url(company_url).rstrip("/")
    for path in ["/about-us", "/about", "/team", "/leadership", "/people", "/our-team", "/who-we-are"]:
        try:
            r = requests.get(base + path, headers=HEADERS, timeout=7, allow_redirects=True)
            if r.status_code != 200:
                continue
            if "text/html" not in r.headers.get("content-type", ""):
                continue
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = re.sub(r'\s+', ' ', soup.get_text(separator=" ", strip=True))
            if len(text) > 300:
                log.info("p09_team_page_found", path=path, chars=len(text))
                return text[:3000]
        except Exception:
            pass
    return ""


class DecisionMakersPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Decision-Maker Identification"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"google_results": [], "team_page": ""}

        # 3 parallel Google searches — broad enough to catch any title format
        queries = [
            f"{n} marketing leadership CMO \"head of\" OR \"VP\" OR \"SVP\" OR \"AVP\" site:linkedin.com",
            f"{n} \"brand manager\" OR \"marketing manager\" OR \"events manager\" OR \"head of marketing\" linkedin",
            f"{n} marketing team director manager linkedin profile",
        ]
        raw["google_results"] = run_google_searches_parallel(queries, PIPELINE_ID, num_results=8)
        log.info("p09_google_done", results=len(raw["google_results"]))

        # Team page scrape
        if self.company_url:
            raw["team_page"] = _scrape_team_page(self.company_url)

        return raw

    def extract(self, raw: dict) -> dict:
        """
        Don't filter anything — collect raw text and pass it all to GPT.
        Previous approach dropped 'SVP Marketing', 'AVP Brand' etc. because
        they weren't in a static keyword list. GPT handles all title variants.
        """
        lines = []
        for item in raw.get("google_results", []):
            title   = item.get("title", "")
            snippet = item.get("snippet", "") or item.get("description", "")
            url     = item.get("url", "") or item.get("link", "")
            if title or snippet:
                lines.append(f"RESULT: {title} | URL: {url} | INFO: {snippet[:200]}")

        return {
            "company_name": self.company_name,
            "category":     self.category,
            "search_text":  "\n".join(lines),
            "team_page":    raw.get("team_page", "")[:2500],
            "result_count": len(raw.get("google_results", [])),
        }

    def synthesise(self, structured: dict) -> dict:
        n = structured["company_name"]

        user_prompt = f"""COMPANY: {n}
CATEGORY: {structured['category']}
WEBSITE: {self.company_url}

GOOGLE SEARCH RESULTS ({structured['result_count']} results across 3 queries about {n}'s marketing team):
{structured['search_text']}

COMPANY TEAM/ABOUT PAGE TEXT:
{structured['team_page'] or '(not found)'}

Extract the buying committee for {n}. Focus on marketing, brand, events, and growth leadership.
LinkedIn URLs are in the RESULT lines — extract them if present."""

        result = synthesise(SYSTEM_PROMPT, user_prompt, max_tokens=1500)
        if result:
            parsed = safe_json_parse(result)
            if parsed and parsed.get("buying_committee"):
                parsed["total_contacts_found"] = len(parsed["buying_committee"])
                log.info("p09_done", contacts=parsed["total_contacts_found"],
                         confidence=parsed.get("confidence_level"))
                return parsed

        log.warning("p09_gpt_returned_empty", company=n)
        return {
            "buying_committee":     [],
            "primary_contact":      None,
            "total_contacts_found": 0,
            "confidence_level":     "LOW",
            "committee_gap":        "All roles — GPT synthesis failed",
        }
