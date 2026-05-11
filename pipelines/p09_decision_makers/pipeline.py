"""
Pipeline 09 — Decision-Maker Identification
============================================
Three-source strategy — strongest signal wins:

  Source A — Apify LinkedIn People Search (PRIMARY):
    harvestapi/linkedin-profile-search finds real profiles with job titles,
    LinkedIn URLs, and company affiliation. 3 parallel queries targeting
    CMO / VP Marketing / Brand Manager roles.

  Source B — Apify LinkedIn Company Scraper (SECONDARY):
    harvestapi/linkedin-company-scraper pulls employee list directly from
    the company's LinkedIn page.

  Source C — Google Search (ENRICHMENT):
    2 parallel Google queries find any additional LinkedIn URLs or team
    page mentions. Also used to scrape the company's own team/about page.

  Source D — GPT-4o Knowledge (FALLBACK ONLY):
    Only runs if A+B+C return zero real people. Uses training knowledge for
    major known brands (HUL, Zomato, etc.) — NOT for small/unknown companies.

Merge logic:
  1. LinkedIn profile results (verified URLs) — deduplicated by name
  2. Company scraper employees added if not already seen
  3. Google/team page results added if not already seen
  4. GPT knowledge fills last slots ONLY if total < 2 and company is well-known
  Final result: 2-5 ranked contacts with real LinkedIn URLs where possible.
"""
import re, requests, structlog
from bs4 import BeautifulSoup
from pipelines.base import BasePipeline
from utils.apify_client import (
    run_google_searches_parallel,
    scrape_linkedin_profiles_parallel,
    run_actor,
)
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, normalise_url
from config.settings import OPENAI_MODEL_FULL

log = structlog.get_logger()
PIPELINE_ID = "p09_decision_makers"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# ── System prompt — for synthesising raw LinkedIn + search data ───────────────
SYNTHESIS_SYSTEM_PROMPT = """You are a B2B sales intelligence analyst identifying marketing decision-makers for an experiential marketing pitch.

From the raw LinkedIn profile data and search results provided, build a buying committee of 2-5 people who would own or influence experiential marketing / events / brand activation spend.

For product brands (Dove→HUL, Gillette→P&G, Maggi→Nestlé) — include people at the PARENT COMPANY who manage that brand.

STRICT RULES:
- Only include people explicitly found in the provided data — real names from LinkedIn results or search snippets
- A person is valid if they appear in: LinkedIn profile results, search result titles/snippets, or the team page
- DO NOT invent anyone not found in the data
- If fewer than 2 people are found, that is fine — accuracy over quantity
- Prioritise people with a linkedin_url in the data

Return ONLY valid JSON:
{
  "buying_committee": [
    {
      "name": "Full Name as it appears in the data",
      "title": "Exact title from LinkedIn or search",
      "company": "Company they work at",
      "role_type": "Economic Buyer | Initiator | Events Specialist | Influencer",
      "linkedin_url": "URL from data or null",
      "linkedin_activity": "UNKNOWN",
      "decision_relevance_score": 4,
      "outreach_priority": "PRIMARY | SECONDARY",
      "personalisation_hook": "Specific detail about this person from the data"
    }
  ],
  "primary_contact": "Name of best person or null",
  "parent_company": "Parent company if product brand, else null",
  "confidence_level": "HIGH | MEDIUM | LOW",
  "data_source": "apify_linkedin",
  "committee_gap": "Which role is missing, or None"
}"""

# ── System prompt — GPT knowledge fallback (ONLY for well-known brands) ───────
KNOWLEDGE_FALLBACK_PROMPT = """You are a B2B sales intelligence expert.

ONLY use this prompt if you have GENUINE training knowledge of named individuals at this specific company.

Rules:
- Only include people you genuinely know — real names from training data
- If you don't have real knowledge of specific individuals, return an empty buying_committee
- Empty is correct for small or less-publicly visible companies
- NEVER invent names

Return ONLY valid JSON with same schema as above. Set data_source to "gpt_knowledge"."""


def _scrape_team_page(company_url: str) -> str:
    base = normalise_url(company_url).rstrip("/")
    for path in ["/about-us", "/about", "/team", "/leadership", "/people", "/our-team"]:
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
                log.info(f"     Team page found at {path}")
                return text[:3000]
        except Exception:
            pass
    return ""


def _parse_linkedin_profiles(items: list, company_name: str) -> list:
    """
    Parse raw output from harvestapi/linkedin-profile-search into a
    normalised list of people dicts with name, title, linkedin_url, company.
    Handles multiple field-name formats the actor might return.
    """
    people = []
    company_lower = company_name.lower()

    for item in (items or []):
        # Name — try multiple field names
        name = (
            item.get("fullName") or item.get("name") or
            item.get("firstName", "") + " " + item.get("lastName", "")
        ).strip()
        if not name or name == " ":
            continue

        # Title
        title = (
            item.get("title") or item.get("headline") or
            item.get("currentJobTitle") or item.get("jobTitle") or ""
        ).strip()

        # LinkedIn URL
        li_url = (
            item.get("profileUrl") or item.get("linkedInUrl") or
            item.get("url") or item.get("linkedinUrl") or ""
        ).strip()

        # Company
        company = (
            item.get("currentCompany") or item.get("company") or
            item.get("currentCompanyName") or item.get("companyName") or ""
        ).strip()

        # Filter: keep if company matches (loosely) or if we have a title that looks marketing-related
        marketing_keywords = [
            "marketing", "brand", "cmo", "growth", "events", "experience",
            "communications", "creative", "content", "digital", "commercial",
        ]
        title_lower = title.lower()
        company_match = company_lower in (company or "").lower() or (company or "").lower() in company_lower
        title_match = any(kw in title_lower for kw in marketing_keywords)

        if not (company_match or title_match):
            continue  # Skip clearly irrelevant profiles

        people.append({
            "name":       name,
            "title":      title,
            "company":    company or company_name,
            "linkedin_url": li_url if "linkedin.com/in" in li_url else None,
            "source":     "apify_linkedin",
        })

    return people


def _parse_company_scraper(items: list) -> list:
    """Parse harvestapi/linkedin-company-scraper employee output."""
    people = []
    for item in (items or []):
        # Company scraper may return employees under different keys
        employees = item.get("employees") or item.get("people") or []
        if isinstance(employees, list):
            for emp in employees:
                name = (emp.get("fullName") or emp.get("name") or "").strip()
                title = (emp.get("title") or emp.get("headline") or "").strip()
                li_url = (emp.get("profileUrl") or emp.get("url") or "").strip()
                if name:
                    people.append({
                        "name":       name,
                        "title":      title,
                        "company":    item.get("name", ""),
                        "linkedin_url": li_url if "linkedin.com/in" in li_url else None,
                        "source":     "apify_company",
                    })
        # Sometimes the scraper returns flat employee items
        elif item.get("fullName") or item.get("name"):
            name = (item.get("fullName") or item.get("name") or "").strip()
            title = (item.get("title") or item.get("headline") or "").strip()
            li_url = (item.get("profileUrl") or item.get("url") or "").strip()
            if name:
                people.append({
                    "name":       name,
                    "title":      title,
                    "company":    "",
                    "linkedin_url": li_url if "linkedin.com/in" in li_url else None,
                    "source":     "apify_company",
                })
    return people


def _extract_from_google(google_results: list) -> list:
    """Extract names + LinkedIn URLs from Google search results."""
    people = []
    li_pattern = re.compile(r'(https?://(?:www\.|in\.)?linkedin\.com/in/[a-zA-Z0-9_-]+)', re.I)
    name_pattern = re.compile(r'^([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)')

    for item in (google_results or []):
        url     = item.get("url", "") or item.get("link", "")
        title   = item.get("title", "")
        snippet = item.get("snippet", "") or item.get("description", "")

        if "linkedin.com/in/" in url:
            m = name_pattern.match(title.strip())
            if m:
                name  = m.group(1).strip()
                # Extract role from title (usually "Name - Title at Company | LinkedIn")
                role  = ""
                parts = title.split(" - ")
                if len(parts) > 1:
                    role_part = parts[1].split(" at ")[0].split(" | ")[0].strip()
                    role = role_part
                people.append({
                    "name": name, "title": role,
                    "company": "", "linkedin_url": url, "source": "google",
                })
        else:
            # Scan snippet for inline LinkedIn URLs
            for li_url in li_pattern.findall(snippet + " " + title):
                m = name_pattern.match(title.strip())
                if m:
                    people.append({
                        "name": m.group(1).strip(), "title": "",
                        "company": "", "linkedin_url": li_url, "source": "google",
                    })

    return people


def _merge_people(sources: list[list]) -> list:
    """Deduplicate and merge people from multiple sources."""
    seen = {}

    def _norm(name: str) -> str:
        return re.sub(r'[^a-z]', '', (name or '').lower())

    for source_people in sources:
        for p in (source_people or []):
            key = _norm(p.get("name", ""))
            if not key:
                continue
            if key not in seen:
                seen[key] = p
            else:
                # Enrich existing entry with LinkedIn URL if we now have one
                if p.get("linkedin_url") and not seen[key].get("linkedin_url"):
                    seen[key]["linkedin_url"] = p["linkedin_url"]
                if p.get("title") and not seen[key].get("title"):
                    seen[key]["title"] = p["title"]

    return list(seen.values())[:8]  # Keep top 8 for GPT to rank


class DecisionMakersPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Decision-Maker Identification"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {
            "google_results":    [],
            "team_page":         "",
            "linkedin_profiles": [],
            "company_employees": [],
        }

        # ── Source A: Apify LinkedIn people search (PRIMARY) ──────────────
        li_queries = [
            f"{n} Chief Marketing Officer OR CMO OR VP Marketing",
            f"{n} Head of Marketing OR Marketing Director OR Brand Director",
            f"{n} Brand Manager OR Events Manager OR Head of Brand",
        ]
        log.info("     Searching LinkedIn for decision-makers via Apify...")
        li_profiles = scrape_linkedin_profiles_parallel(li_queries, PIPELINE_ID, max_results=4)
        raw["linkedin_profiles"] = li_profiles or []
        n_li = len(raw["linkedin_profiles"])
        if n_li:
            log.info(f"     LinkedIn returned {n_li} profiles")

        # ── Source B: LinkedIn company scraper (get employees list) ───────
        # Try to find the company's LinkedIn page first via Google
        company_li_results = run_google_searches_parallel(
            [f"{n} linkedin.com/company site:linkedin.com"], PIPELINE_ID, num_results=5
        )
        li_company_url = None
        for r in (company_li_results or []):
            url = r.get("url", "") or r.get("link", "")
            if "linkedin.com/company/" in url:
                li_company_url = url
                break

        if li_company_url:
            company_data = run_actor(
                "linkedin_company",
                {"startUrls": [{"url": li_company_url}], "maxResults": 10},
                PIPELINE_ID,
                timeout_secs=30,
            )
            raw["company_employees"] = company_data or []

        # ── Source C: Google search for extra LinkedIn URLs ────────────────
        google_queries = [
            f"{n} marketing director manager brand head linkedin",
            f"{n} CMO brand manager \"head of\" site:linkedin.com",
        ]
        raw["google_results"] = run_google_searches_parallel(
            google_queries, PIPELINE_ID, num_results=8
        )
        log.info(f"     LinkedIn profiles searched — {len(raw['google_results'])} signals found")

        # ── Source D: Team page ────────────────────────────────────────────
        if self.company_url:
            raw["team_page"] = _scrape_team_page(self.company_url)

        return raw

    def extract(self, raw: dict) -> dict:
        # Parse each source into normalised people list
        li_people      = _parse_linkedin_profiles(raw.get("linkedin_profiles", []), self.company_name)
        company_people = _parse_company_scraper(raw.get("company_employees", []))
        google_people  = _extract_from_google(raw.get("google_results", []))

        # Build Google search text for synthesis prompt
        lines = []
        for item in raw.get("google_results", []):
            t = item.get("title", "")
            s = item.get("snippet", "") or item.get("description", "")
            u = item.get("url", "") or item.get("link", "")
            if t or s:
                lines.append(f"RESULT: {t} | URL: {u} | INFO: {s[:200]}")

        return {
            "company_name":   self.company_name,
            "category":       self.category,
            "li_people":      li_people,
            "company_people": company_people,
            "google_people":  google_people,
            "search_text":    "\n".join(lines),
            "team_page":      raw.get("team_page", "")[:2500],
            "google_results": raw.get("google_results", []),
            "total_li_found": len(li_people),
        }

    def synthesise(self, structured: dict) -> dict:
        n        = structured["company_name"]
        category = structured["category"]

        # Merge all real-data sources
        merged_raw = _merge_people([
            structured["li_people"],
            structured["company_people"],
            structured["google_people"],
        ])

        search_parsed = {}
        final_people  = []

        if merged_raw:
            # We have real data — ask GPT to rank, enrich and structure it
            people_text = "\n".join(
                f"- {p['name']} | {p['title']} | {p.get('company','')} | "
                f"LinkedIn: {p.get('linkedin_url') or 'not found'} | source: {p.get('source','')}"
                for p in merged_raw
            )

            synthesis_prompt = f"""COMPANY: {n}
CATEGORY: {category}

PEOPLE FOUND IN REAL DATA (LinkedIn + Google):
{people_text}

TEAM PAGE EXCERPT:
{structured['team_page'] or '(not found)'}

ADDITIONAL SEARCH SIGNALS:
{structured['search_text'][:800]}

From the people above, identify the 2-5 best marketing/events decision-makers to contact.
Only include people from the data above — do not add anyone not listed."""

            raw_result  = synthesise(SYNTHESIS_SYSTEM_PROMPT, synthesis_prompt, max_tokens=1400)
            search_parsed = safe_json_parse(raw_result or "") or {}
            final_people  = search_parsed.get("buying_committee", [])

        # If no real data found at all → try GPT knowledge as last resort
        if not final_people:
            log.info("     No LinkedIn data found — trying GPT knowledge for known brands...")
            knowledge_prompt = f"""COMPANY: {n}
CATEGORY: {category}
WEBSITE: {self.company_url or 'unknown'}

LinkedIn search and Google search returned no people for this company.
Only proceed if you have genuine training knowledge of named individuals at {n}.
If this is a small or private company you don't have real knowledge of, return an empty buying_committee."""

            kb_raw    = synthesise(KNOWLEDGE_FALLBACK_PROMPT, knowledge_prompt,
                                   model=OPENAI_MODEL_FULL, max_tokens=1200)
            kb_parsed = safe_json_parse(kb_raw or "") or {}
            final_people  = kb_parsed.get("buying_committee", [])
            search_parsed = kb_parsed

        # Determine primary contact
        primary = next(
            (p["name"] for p in final_people if p.get("outreach_priority") == "PRIMARY"),
            final_people[0]["name"] if final_people else None
        )
        confidence    = search_parsed.get("confidence_level", "MEDIUM" if final_people else "LOW")
        committee_gap = search_parsed.get("committee_gap", "None")
        parent_co     = search_parsed.get("parent_company")

        log.info(f"     {len(final_people)} decision-makers identified · Primary: {primary} · Confidence: {confidence}")

        return {
            "buying_committee":     final_people,
            "primary_contact":      primary,
            "parent_company":       parent_co,
            "total_contacts_found": len(final_people),
            "confidence_level":     confidence,
            "committee_gap":        committee_gap,
        }
