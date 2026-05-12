"""
Pipeline 09 — Decision-Maker Identification
============================================
Three-source strategy — strongest signal wins:

  Source A — Apify LinkedIn Company Employees Scraper (PRIMARY):
    automation-lab/linkedin-company-employees-scraper discovers real employees
    via Google SERP — no LinkedIn cookie required. Returns name, headline,
    profileUrl per employee. We call it with the company's LinkedIn URL.

  Source B — Google Search (SUPPLEMENTARY):
    2 parallel queries find extra LinkedIn profile URLs and signals from
    the open web (press releases, team pages, LinkedIn posts).

  Source C — Company Team Page (ENRICHMENT):
    Scrape /about, /team, /leadership pages directly if company URL is known.

  Source D — GPT-4o Knowledge (LAST RESORT):
    Only runs when A + B + C return zero real people.
    Only works for well-known public brands — empty is correct for unknowns.

Merge logic:
  1. Employee scraper results (primary — verified LinkedIn URLs)
  2. Google results added if not already seen
  3. GPT knowledge fills ONLY if total == 0 and brand is well-known
  Final result: 2-5 ranked contacts with real LinkedIn URLs where possible.
"""
import re, requests, structlog
from bs4 import BeautifulSoup
from pipelines.base import BasePipeline
from utils.apify_client import (
    run_google_searches_parallel,
    scrape_company_employees,
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

# ── Synthesis prompt — ranks real scraped data ────────────────────────────────
SYNTHESIS_SYSTEM_PROMPT = """You are a B2B sales intelligence analyst identifying marketing decision-makers for an experiential marketing pitch.

From the raw LinkedIn employee data and search results provided, build a buying committee of 2-5 people who would own or influence experiential marketing / events / brand activation spend.

For product brands (Dove→HUL, Gillette→P&G, Maggi→Nestlé) — include people at the PARENT COMPANY who manage that brand.

STRICT RULES:
- Only include people explicitly found in the provided data
- A person is valid if they appear in: LinkedIn employee results, search result titles/snippets, or the team page
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

# ── GPT knowledge fallback — ONLY for well-known brands ──────────────────────
KNOWLEDGE_FALLBACK_PROMPT = """You are a B2B sales intelligence expert.

ONLY use this prompt if you have GENUINE training knowledge of named individuals at this specific company.

Rules:
- Only include people you genuinely know — real names from training data
- If you don't have real knowledge of specific individuals, return an empty buying_committee
- Empty is correct for small or less-publicly visible companies
- NEVER invent names

Return ONLY valid JSON with same schema as above. Set data_source to "gpt_knowledge"."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_company_linkedin_url(company_name: str) -> str | None:
    """
    Google search to find the company's LinkedIn page URL.
    Returns the first result matching linkedin.com/company/SLUG or None.
    """
    queries = [
        f'"{company_name}" site:linkedin.com/company',
        f"{company_name} linkedin company page",
    ]
    results = run_google_searches_parallel(queries, PIPELINE_ID, num_results=5)
    for r in (results or []):
        url = r.get("url", "") or r.get("link", "")
        if re.search(r'linkedin\.com/company/[a-zA-Z0-9_-]+', url or ""):
            # Normalise to clean profile URL (no trailing query params)
            match = re.search(r'(https?://(?:www\.|in\.)?linkedin\.com/company/[a-zA-Z0-9_-]+)', url)
            if match:
                clean = match.group(1).rstrip("/") + "/"
                log.info("     LinkedIn company URL found", url=clean)
                return clean
    return None


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


def _parse_employees(items: list, company_name: str) -> list:
    """
    Parse output from automation-lab/linkedin-company-employees-scraper.
    Each item has: name, headline, profileUrl, companySlug, companyName, source.

    Filters to keep marketing/brand/events-relevant profiles.
    Returns list of normalised people dicts.
    """
    marketing_keywords = [
        "marketing", "brand", "cmo", "growth", "events", "experience",
        "communications", "creative", "content", "digital", "commercial",
        "activation", "sponsorship", "pr ", "public relations", "campaign",
        "advertising", "media", "partnerships", "community",
    ]

    people     = []
    all_people = []  # full list — used as fallback when filter yields too few

    for item in (items or []):
        name = (item.get("name") or "").strip()
        if not name:
            continue

        headline    = (item.get("headline") or "").strip()
        profile_url = (item.get("profileUrl") or "").strip()
        company     = (item.get("companyName") or company_name).strip()

        person = {
            "name":         name,
            "title":        headline,
            "company":      company,
            "linkedin_url": profile_url if "linkedin.com/in/" in profile_url else None,
            "source":       "apify_linkedin",
        }
        all_people.append(person)

        headline_lower = headline.lower()
        is_marketing = any(kw in headline_lower for kw in marketing_keywords)

        # Also include C-suite / VP / Director even without marketing keyword
        # because they may have budget authority
        is_senior = any(t in headline_lower for t in [
            "chief", "ceo", "coo", "founder", "president", "vice president",
            "vp ", "director", "head of", "head,",
        ])

        if is_marketing or is_senior:
            people.append(person)

    # If strict filter leaves too few, pass all scraped people so the LLM can pick
    if len(people) < 3 and all_people:
        log.info("     Few marketing/senior matches — expanding to all scraped employees",
                 filtered=len(people), total=len(all_people))
        people = all_people[:20]

    log.info("     Employee parse complete",
             total_scraped=len(items or []),
             marketing_relevant=len(people))
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

        if "linkedin.com/in/" in (url or ""):
            m = name_pattern.match(title.strip())
            if m:
                name = m.group(1).strip()
                role = ""
                parts = title.split(" - ")
                if len(parts) > 1:
                    role = parts[1].split(" at ")[0].split(" | ")[0].strip()
                people.append({
                    "name": name, "title": role,
                    "company": "", "linkedin_url": url, "source": "google",
                })
        else:
            for li_url in li_pattern.findall((snippet or "") + " " + title):
                m = name_pattern.match(title.strip())
                if m:
                    people.append({
                        "name": m.group(1).strip(), "title": "",
                        "company": "", "linkedin_url": li_url, "source": "google",
                    })

    return people


def _merge_people(sources: list) -> list:
    """Deduplicate and merge people from multiple sources. Returns top 10."""
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
                if p.get("linkedin_url") and not seen[key].get("linkedin_url"):
                    seen[key]["linkedin_url"] = p["linkedin_url"]
                if p.get("title") and not seen[key].get("title"):
                    seen[key]["title"] = p["title"]

    return list(seen.values())[:10]


class DecisionMakersPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Decision-Maker Identification"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {
            "employee_items":  [],
            "google_results":  [],
            "team_page":       "",
            "company_li_url":  None,
        }

        # ── Step 1: Find company LinkedIn URL via Google ──────────────────
        log.info("     Finding company LinkedIn page...")
        li_url = _find_company_linkedin_url(n)
        raw["company_li_url"] = li_url

        # ── Step 2: Scrape employees via automation-lab actor (PRIMARY) ───
        if li_url:
            log.info(f"     Scraping LinkedIn employees from {li_url}...")
            employee_items = scrape_company_employees(li_url, PIPELINE_ID, max_employees=20)
            raw["employee_items"] = employee_items or []
            log.info(f"     Employee scraper returned {len(raw['employee_items'])} items")
        else:
            log.warning("     Could not find company LinkedIn URL — skipping employee scrape")

        # ── Step 3: Google search for extra LinkedIn profile signals ──────
        google_queries = [
            f"{n} marketing director OR CMO OR brand head site:linkedin.com",
            f"{n} head of marketing OR VP marketing linkedin profile",
        ]
        log.info("     Searching Google for additional LinkedIn signals...")
        raw["google_results"] = run_google_searches_parallel(
            google_queries, PIPELINE_ID, num_results=8
        )
        n_google = len(raw["google_results"])
        log.info(f"     Google returned {n_google} results")

        # ── Step 4: Team page scrape ──────────────────────────────────────
        if self.company_url:
            raw["team_page"] = _scrape_team_page(self.company_url)

        return raw

    def extract(self, raw: dict) -> dict:
        # Parse employee scraper output
        employee_people = _parse_employees(raw.get("employee_items", []), self.company_name)

        # Parse Google results for extra LinkedIn URLs
        google_people = _extract_from_google(raw.get("google_results", []))

        # Build search text for synthesis context
        lines = []
        for item in raw.get("google_results", []):
            t = item.get("title", "")
            s = item.get("snippet", "") or item.get("description", "")
            u = item.get("url", "") or item.get("link", "")
            if t or s:
                lines.append(f"RESULT: {t} | URL: {u} | INFO: {s[:200]}")

        return {
            "company_name":    self.company_name,
            "category":        self.category,
            "company_li_url":  raw.get("company_li_url"),
            "employee_people": employee_people,
            "google_people":   google_people,
            "search_text":     "\n".join(lines),
            "team_page":       raw.get("team_page", "")[:2500],
            "total_scraped":   len(raw.get("employee_items", [])),
        }

    def synthesise(self, structured: dict) -> dict:
        n        = structured["company_name"]
        category = structured["category"]

        # Merge all real-data sources (employee scraper is primary)
        merged_raw = _merge_people([
            structured["employee_people"],
            structured["google_people"],
        ])

        search_parsed = {}
        final_people  = []

        # Always attempt synthesis — even when LinkedIn returns 0 results,
        # the Google search snippets and team page often contain real names/titles.
        people_text = "\n".join(
            f"- {p['name']} | {p['title']} | {p.get('company', '')} | "
            f"LinkedIn: {p.get('linkedin_url') or 'not found'} | source: {p.get('source', '')}"
            for p in merged_raw
        ) if merged_raw else "(none found via LinkedIn scraper)"

        has_any_signal = bool(
            merged_raw
            or structured.get("search_text", "").strip()
            or structured.get("team_page", "").strip()
        )

        if has_any_signal:
            synthesis_prompt = f"""COMPANY: {n}
CATEGORY: {category}
LINKEDIN PAGE: {structured.get('company_li_url') or 'not found'}

EMPLOYEES FOUND VIA LINKEDIN SCRAPER:
{people_text}

TEAM PAGE EXCERPT:
{structured['team_page'] or '(not found)'}

ADDITIONAL SEARCH SIGNALS (Google results — names and titles often appear in snippets):
{structured['search_text'][:1200]}

From ALL sources above (employees list, team page, AND search snippets), identify up to 5
people who are marketing / experiential-marketing / events / brand decision-makers.
If a name appears in a search snippet with a relevant title, include them.
Only include people with at least one piece of evidence in the data above — do not invent."""

            raw_result    = synthesise(SYNTHESIS_SYSTEM_PROMPT, synthesis_prompt, max_tokens=1400)
            search_parsed = safe_json_parse(raw_result or "") or {}
            final_people  = search_parsed.get("buying_committee", [])

        # Last resort: GPT knowledge only if zero from all sources
        if not final_people:
            log.info("     No LinkedIn data found — trying GPT knowledge for known brands...")
            knowledge_prompt = f"""COMPANY: {n}
CATEGORY: {category}
WEBSITE: {self.company_url or 'unknown'}

LinkedIn scraper and Google search returned no people for this company.
Only proceed if you have genuine training knowledge of named individuals at {n}.
If this is a small or private company you don't have real knowledge of, return an empty buying_committee."""

            kb_raw    = synthesise(KNOWLEDGE_FALLBACK_PROMPT, knowledge_prompt,
                                   model=OPENAI_MODEL_FULL, max_tokens=1200)
            kb_parsed = safe_json_parse(kb_raw or "") or {}
            final_people  = kb_parsed.get("buying_committee", [])
            search_parsed = kb_parsed

        primary = next(
            (p["name"] for p in final_people if p.get("outreach_priority") == "PRIMARY"),
            final_people[0]["name"] if final_people else None
        )
        confidence    = search_parsed.get("confidence_level", "MEDIUM" if final_people else "LOW")
        committee_gap = search_parsed.get("committee_gap", "None")
        parent_co     = search_parsed.get("parent_company")

        log.info(
            f"     {len(final_people)} decision-makers identified · "
            f"Primary: {primary} · Confidence: {confidence} · "
            f"Source: {'apify_linkedin' if structured['total_scraped'] > 0 else 'gpt_knowledge'}"
        )

        return {
            "buying_committee":     final_people,
            "primary_contact":      primary,
            "parent_company":       parent_co,
            "total_contacts_found": len(final_people),
            "confidence_level":     confidence,
            "committee_gap":        committee_gap,
        }
