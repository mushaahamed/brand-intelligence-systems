"""
Pipeline 09 — Decision-Maker Identification
Finds real people at the company who can approve experiential marketing spend.

Layer 1: Google searches for LinkedIn profiles (3 query variants)
Layer 2: Scrape company team/about/leadership page for names
Layer 3: GPT-4o synthesises buying committee from all raw data
"""
import re, json, structlog, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, truncate, normalise_url

log = structlog.get_logger()
PIPELINE_ID = "p09_decision_makers"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

SENIORITY_KW = [
    "CMO", "Chief Marketing Officer", "VP Marketing", "Vice President Marketing",
    "Head of Marketing", "Head of Brand", "Marketing Director", "Brand Director",
    "Marketing Manager", "Brand Manager", "Senior Brand Manager", "Events Manager",
    "Head of Events", "Experiential Manager", "Head of Growth", "Growth Lead",
    "Marketing Lead", "Category Manager", "CEO", "Founder", "Co-Founder",
    "Managing Director", "Director of Marketing", "Head of People",
]

LI_URL_RE = re.compile(r'linkedin\.com/in/[\w\-]+', re.I)

SYSTEM_PROMPT = """You are a B2B sales intelligence analyst. From the search results and team page data, identify the best contacts at this company for an experiential marketing agency pitch.

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
      "personalisation_hook": "One specific detail to reference in outreach — a campaign, achievement, or career transition"
    }
  ],
  "primary_contact": "Name of highest priority contact",
  "total_contacts_found": 3,
  "confidence_level": "HIGH | MEDIUM | LOW",
  "committee_gap": "Which role type was NOT found (or 'None — all roles covered')"
}

Decision relevance 1-5: 5=directly owns events budget, 1=peripheral.
outreach_priority: PRIMARY for CMO/Marketing head, SECONDARY for brand managers and others.
Extract REAL people only — verify they work at this company from their title/profile data."""


def _scrape_team_page(company_url: str) -> str:
    """
    Fetch the company's team/about/leadership page and extract raw text
    that likely contains staff names and titles.
    """
    base_url = normalise_url(company_url)
    candidate_paths = [
        "/team", "/about", "/about-us", "/leadership", "/people",
        "/who-we-are", "/company/team", "/about/team", "/our-team",
    ]
    for path in candidate_paths:
        try:
            url = base_url.rstrip("/") + path
            r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
            if r.status_code != 200:
                continue
            if "text/html" not in r.headers.get("content-type", ""):
                continue
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) < 200:
                continue
            log.info("p09_team_page_found", url=url, chars=len(text))
            return text[:3000]
        except Exception:
            pass
    return ""


def _extract_linkedin_url(text: str) -> str | None:
    """Extract a clean LinkedIn profile URL from a string."""
    m = LI_URL_RE.search(text)
    if m:
        return "https://www." + m.group(0)
    return None


def _parse_google_results(items: list, company_name: str) -> list:
    """
    Parse Google search result items and extract candidate people.
    Returns list of {name, title, url, snippet, role_type, linkedin_url}.
    """
    people = []
    seen   = set()
    company_lower = company_name.lower()

    for item in items:
        title_raw = item.get("title", "")
        snippet   = item.get("snippet", "") or item.get("description", "")
        url       = item.get("url", "") or item.get("link", "")
        combined  = f"{title_raw} {snippet}"

        # ── Extract name ─────────────────────────────────────────────
        name = ""
        # Pattern: "First Last - Title at Company | LinkedIn"
        if " - " in title_raw:
            candidate = title_raw.split(" - ")[0].strip()
            # Clean up common suffixes
            candidate = re.sub(r'\s*[|·,].*$', '', candidate).strip()
            if 2 <= len(candidate.split()) <= 4 and len(candidate) <= 50:
                name = candidate
        # Pattern: "First Last | Company | LinkedIn"
        if not name and " | " in title_raw:
            candidate = title_raw.split(" | ")[0].strip()
            if 2 <= len(candidate.split()) <= 4 and len(candidate) <= 50:
                name = candidate
        # Pattern: "First Last · Title · LinkedIn"
        if not name and " · " in title_raw:
            candidate = title_raw.split(" · ")[0].strip()
            if 2 <= len(candidate.split()) <= 4 and len(candidate) <= 50:
                name = candidate
        # Try snippet: "Sarah joined [Company] as Head of Marketing"
        if not name and snippet:
            sm = re.search(
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s+(?:is|joined|leads|heads|manages|serves)',
                snippet
            )
            if sm:
                name = sm.group(1).strip()

        # Filter out non-names
        if not name:
            continue
        name = re.sub(r'\s*(LinkedIn|Profile|Page).*', '', name, flags=re.I).strip()
        words = name.split()
        if len(words) < 2 or len(words) > 4:
            continue
        if any(w.lower() in ('the', 'and', 'for', 'of', 'at', 'in', 'on', 'company', 'marketing', 'brand') for w in words):
            continue
        if name in seen:
            continue

        # ── Verify company association ──────────────────────────────
        if company_lower not in combined.lower() and not ("linkedin.com" in url.lower()):
            continue

        # ── Extract role ────────────────────────────────────────────
        role = ""
        for kw in SENIORITY_KW:
            if kw.lower() in combined.lower():
                role = kw; break

        if not role:
            continue  # Skip results with no recognisable seniority keyword

        # ── LinkedIn URL ─────────────────────────────────────────────
        li_url = None
        if "linkedin.com/in" in url.lower():
            li_url = _extract_linkedin_url(url)
        elif "linkedin.com/in" in snippet.lower():
            li_url = _extract_linkedin_url(snippet)

        # ── Role type ────────────────────────────────────────────────
        senior = any(k in role for k in [
            "CMO", "VP", "Chief", "Director", "Head of Marketing",
            "Head of Brand", "CEO", "Founder", "Managing Director"
        ])
        role_type = "Economic Buyer" if senior else "Initiator"

        seen.add(name)
        people.append({
            "name":         name,
            "title":        role,
            "url":          url,
            "linkedin_url": li_url,
            "role_type":    role_type,
            "snippet":      snippet[:200],
            "source":       "google",
        })

    return people


class DecisionMakersPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Decision-Maker Identification"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"google_people": [], "team_page_text": ""}

        # ── 3 query variants — broad to narrow ──────────────────────
        queries = [
            # Unquoted company name is more forgiving (catches brand name variants)
            f'{n} "Head of Marketing" OR "CMO" OR "VP Marketing" OR "Marketing Director" linkedin',
            f'{n} "Brand Manager" OR "Brand Director" OR "Events Manager" OR "Head of Brand" linkedin',
            f'{n} "Chief Marketing" OR "Marketing Lead" OR "Growth" OR "CEO" OR "Founder" linkedin profile',
        ]
        raw["google_people"] = run_google_searches_parallel(queries, PIPELINE_ID, num_results=8)

        # ── Scrape company team page as fallback/supplement ──────────
        if self.company_url:
            try:
                raw["team_page_text"] = _scrape_team_page(self.company_url)
            except Exception as e:
                log.warning("p09_team_page_error", error=str(e))

        log.info("p09_google_results", count=len(raw["google_people"]),
                 team_page_chars=len(raw.get("team_page_text", "")))
        return raw

    def extract(self, raw: dict) -> dict:
        people = _parse_google_results(raw.get("google_people", []), self.company_name)
        log.info("p09_people_extracted", count=len(people))
        return {
            "company_name": self.company_name,
            "people":       people[:10],
            "team_page":    raw.get("team_page_text", "")[:2000],
        }

    def synthesise(self, structured: dict) -> dict:
        people    = structured.get("people", [])
        team_page = structured.get("team_page", "")

        user_data = f"""COMPANY: {structured['company_name']}
CATEGORY: {self.category}
COMPANY URL: {self.company_url}

PEOPLE FOUND VIA GOOGLE SEARCH ({len(people)} results):
{json.dumps(people, indent=2)}

TEAM PAGE TEXT (scraped from company website — may contain names/titles):
{team_page[:1500] if team_page else 'Not found'}

INSTRUCTIONS:
- Extract all real people who work at {structured['company_name']}
- If the team page contains names with titles, include them
- Focus on marketing, brand, events, growth, and leadership roles
- If confidence is LOW (very few results), still return whatever you found
- For personalisation_hook: reference a specific campaign, award, career move, or public project
"""
        result = synthesise(SYSTEM_PROMPT, user_data, max_tokens=1500)
        if result:
            parsed = safe_json_parse(result)
            if parsed and parsed.get("buying_committee"):
                # Ensure total_contacts_found is accurate
                parsed["total_contacts_found"] = len(parsed["buying_committee"])
                return parsed

        # ── Fallback: build committee directly from extracted data ────
        if people:
            committee = []
            for i, p in enumerate(people[:5]):
                priority = "PRIMARY" if i == 0 else "SECONDARY"
                committee.append({
                    "name":                  p["name"],
                    "title":                 p.get("title", ""),
                    "role_type":             p.get("role_type", "Initiator"),
                    "company_tenure_months": None,
                    "linkedin_url":          p.get("linkedin_url"),
                    "linkedin_activity":     "UNKNOWN",
                    "decision_relevance_score": 4 if i == 0 else 3,
                    "outreach_priority":     priority,
                    "personalisation_hook":  p.get("snippet", "")[:120],
                })
            return {
                "buying_committee":    committee,
                "primary_contact":     committee[0]["name"],
                "total_contacts_found": len(committee),
                "confidence_level":    "MEDIUM",
                "committee_gap":       "Events Specialist",
            }

        # ── Hard fallback: team page parsing ─────────────────────────
        if team_page:
            # Try to extract name + title pairs from team page text
            name_title_re = re.compile(
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b[^\n]{0,30}'
                r'(?:' + '|'.join(re.escape(k) for k in SENIORITY_KW[:12]) + r')',
                re.I
            )
            matches = name_title_re.findall(team_page)
            if matches:
                committee = [{
                    "name":  m.strip(),
                    "title": "Marketing Team",
                    "role_type": "Initiator",
                    "company_tenure_months": None,
                    "linkedin_url": None,
                    "linkedin_activity": "UNKNOWN",
                    "decision_relevance_score": 3,
                    "outreach_priority": "SECONDARY",
                    "personalisation_hook": "",
                } for m in matches[:3]]
                return {
                    "buying_committee":     committee,
                    "primary_contact":      committee[0]["name"],
                    "total_contacts_found": len(committee),
                    "confidence_level":     "LOW",
                    "committee_gap":        "Economic Buyer",
                }

        return {
            "buying_committee":     [],
            "primary_contact":      None,
            "total_contacts_found": 0,
            "confidence_level":     "LOW",
            "committee_gap":        "All roles — insufficient public data found",
        }
