"""
Pipeline 09 — Decision-Maker Identification
============================================
4-tier guarantee: ALWAYS returns at least 1 contact.

Tier 1 — Apify LinkedIn Company Employees Scraper (PRIMARY):
  automation-lab/linkedin-company-employees-scraper discovers real employees
  via Google SERP — no LinkedIn cookie required.

Tier 2 — Google Search supplementary (ENRICHMENT):
  2 parallel queries for LinkedIn profile URLs and signals from open web.

Tier 3 — GPT Brand Knowledge (FALLBACK):
  For well-known brands, GPT knows real people. For FMCG brands it resolves
  the parent company (Dove→HUL, Maggi→Nestlé, Gillette→P&G etc.).

Tier 4 — Universal Inference (ABSOLUTE LAST RESORT):
  GPT generates a realistic contact based on company type + category.
  Guarantees buying_committee is NEVER empty — even for unknown companies.

Tier 5 — Python Safety Net:
  Pure Python fallback if GPT itself fails/returns null.
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
from utils.helpers import safe_json_parse, normalise_url, extract_domain
from config.settings import OPENAI_MODEL_FULL

log = structlog.get_logger()
PIPELINE_ID = "p09_decision_makers"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# ── Tier 1 prompt — ranks real scraped data ───────────────────────────────────
SYNTHESIS_SYSTEM_PROMPT = """You are a B2B sales intelligence analyst identifying marketing decision-makers for an experiential marketing pitch at StepOneXP India.

From the raw LinkedIn employee data, team page, and Google search results provided,
build a buying committee of 2-5 people who would own or influence experiential
marketing / events / brand activation spend.

For product brands (Dove→HUL, Gillette→P&G, Maggi→Nestlé) — include people at
the PARENT COMPANY who manage that brand.

RULES:
- Extract anyone who appears in the data with a name AND a relevant role
- Include people found in search snippets, team pages, OR LinkedIn results
- Prioritise people with a linkedin_url
- If fewer than 2 are found, that is acceptable — accuracy over quantity

Return ONLY valid JSON:
{
  "buying_committee": [
    {
      "name": "Full Name",
      "title": "Exact title from data",
      "company": "Company they work at",
      "role_type": "Economic Buyer | Influencer | Events Specialist | Champion",
      "linkedin_url": "URL or null",
      "linkedin_activity": "UNKNOWN",
      "decision_relevance_score": 4,
      "outreach_priority": "PRIMARY | SECONDARY",
      "personalisation_hook": "Specific detail from the data about this person"
    }
  ],
  "primary_contact": "Name of top person",
  "parent_company": "Parent company if product brand, else null",
  "confidence_level": "HIGH | MEDIUM | LOW",
  "data_source": "apify_linkedin",
  "committee_gap": "Which role is missing, or None"
}"""

# ── Tier 3 prompt — GPT brand intelligence (FMCG / corporate brands) ─────────
KNOWLEDGE_FALLBACK_PROMPT = """You are a senior B2B sales intelligence expert with deep knowledge
of FMCG, consumer brands, corporate companies, and Indian marketing leadership.

CRITICAL — Return 2-5 REAL named individuals from your training knowledge.

Priority rules:
1. Well-known FMCG brands: resolve the parent company and return their marketing leaders
   - Dove, Lux, Lifebuoy, Pears, Surf, Rin, Vim, Closeup → HUL (Hindustan Unilever)
   - Maggi, KitKat, Munch, Nescafé, Milkmaid → Nestlé India
   - Gillette, Ariel, Pampers, Whisper, Olay, Head & Shoulders → P&G India
   - Pepsi, Mountain Dew, Lay's, Kurkure, Tropicana → PepsiCo India
   - Coca-Cola, Sprite, Thums Up, Limca, Maaza → Coca-Cola India
   - Royal Enfield, TVS, Hero, Bajaj → respective two-wheeler companies
   - Tanishq, Westside, Zara India, H&M India → respective parent companies

2. D2C / Indian startups: use your knowledge of CMO, VP Marketing, Growth Head

3. If you don't know real names at this company, return empty array.
   DO NOT return the same person from a different company.
   ONLY real people you have genuine training knowledge of.

Return ONLY valid JSON using the exact same schema. Set data_source to "gpt_knowledge"."""

# ── Tier 4 prompt — universal inference (ABSOLUTE LAST RESORT) ───────────────
UNIVERSAL_INFERENCE_PROMPT = """You are a B2B sales intelligence expert at StepOneXP, an
experiential marketing agency. You MUST return at least 1 contact — this is a hard requirement.

Strategy:
1. If you know real named people at this company → return them (highest priority)
2. If this is a brand subsidiary → identify and return the parent company's marketing lead
3. If the company is unknown to you → generate the MOST LIKELY senior marketing
   decision-maker profile for this company type in India. Use a realistic Indian name
   and an accurate title for the category/industry. Mark confidence_level as "LOW"
   and personalisation_hook as "Contact not verified — search on LinkedIn before outreach"

HARD RULE: buying_committee MUST have at least 1 entry. Empty array is NOT allowed.

Return ONLY valid JSON using the standard schema. Set data_source as appropriate."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_company_linkedin_url(company_name: str) -> str | None:
    """
    Google search to find the company's LinkedIn page URL.
    Returns the first result matching linkedin.com/company/SLUG or None.
    """
    queries = [
        f'"{company_name}" site:linkedin.com/company',
        f"{company_name} linkedin company page India",
    ]
    results = run_google_searches_parallel(queries, PIPELINE_ID, num_results=8)
    for r in (results or []):
        url = r.get("url", "") or r.get("link", "")
        if re.search(r'linkedin\.com/company/[a-zA-Z0-9_-]+', url or ""):
            match = re.search(
                r'(https?://(?:www\.|in\.)?linkedin\.com/company/[a-zA-Z0-9_-]+)', url
            )
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
    Filters to keep marketing/brand/events-relevant profiles.
    If strict filter yields < 3 people, returns all scraped people.
    """
    marketing_keywords = [
        "marketing", "brand", "cmo", "growth", "events", "experience",
        "communications", "creative", "content", "digital", "commercial",
        "activation", "sponsorship", "pr ", "public relations", "campaign",
        "advertising", "media", "partnerships", "community",
    ]
    senior_keywords = [
        "chief", "ceo", "coo", "cfo", "founder", "president", "vice president",
        "vp ", "director", "head of", "head,", "general manager", "gm",
    ]

    people     = []
    all_people = []

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

        hl = headline.lower()
        if any(kw in hl for kw in marketing_keywords) or \
           any(kw in hl for kw in senior_keywords):
            people.append(person)

    # Relax filter if too few marketing/senior matches
    if len(people) < 3 and all_people:
        log.info("     Few filtered matches — using all scraped employees",
                 filtered=len(people), total=len(all_people))
        people = all_people[:20]

    log.info("     Employee parse complete",
             total_scraped=len(items or []), marketing_relevant=len(people))
    return people


def _extract_from_google(google_results: list) -> list:
    """Extract names + LinkedIn URLs from Google search results."""
    people = []
    li_pattern   = re.compile(r'(https?://(?:www\.|in\.)?linkedin\.com/in/[a-zA-Z0-9_-]+)', re.I)
    name_pattern = re.compile(r'^([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)')

    for item in (google_results or []):
        url     = item.get("url", "") or item.get("link", "")
        title   = item.get("title", "")
        snippet = item.get("snippet", "") or item.get("description", "")

        if "linkedin.com/in/" in (url or ""):
            m = name_pattern.match(title.strip())
            if m:
                name  = m.group(1).strip()
                role  = ""
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


def _python_safety_net(company_name: str, category: str) -> list:
    """
    Pure-Python absolute last resort.
    Returns 1 generic but useful contact so P10/P11 always have something to work with.
    This only fires if GPT itself returns None or crashes.
    """
    # Infer a realistic title from category
    category_up = (category or "").upper()
    if "FMCG" in category_up or "CONSUMER" in category_up or "SKINCARE" in category_up:
        title = "VP Marketing"
    elif "TECH" in category_up or "SAAS" in category_up or "D2C" in category_up:
        title = "Head of Marketing"
    elif "RETAIL" in category_up or "E-COMMERCE" in category_up:
        title = "Chief Marketing Officer"
    elif "FINANCE" in category_up or "BANK" in category_up or "FINTECH" in category_up:
        title = "Head of Brand & Marketing"
    else:
        title = "Senior Marketing Manager"

    return [{
        "name":                    f"Marketing Lead — {company_name}",
        "title":                   title,
        "company":                 company_name,
        "role_type":               "Economic Buyer",
        "linkedin_url":            None,
        "linkedin_activity":       "UNKNOWN",
        "decision_relevance_score": 3,
        "outreach_priority":       "PRIMARY",
        "personalisation_hook":    (
            f"Contact not auto-verified — search LinkedIn for '{title}' at "
            f"{company_name} before outreach"
        ),
    }]


class DecisionMakersPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Decision-Maker Identification"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {
            "employee_items": [],
            "google_results": [],
            "team_page":      "",
            "company_li_url": None,
        }

        # ── Step 1: Find company LinkedIn URL ───────────────────────────
        log.info("     Finding company LinkedIn page...")
        li_url = _find_company_linkedin_url(n)
        raw["company_li_url"] = li_url

        # ── Step 2: Scrape LinkedIn employees (PRIMARY) ──────────────────
        if li_url:
            log.info(f"     Scraping LinkedIn employees from {li_url}...")
            employee_items = scrape_company_employees(li_url, PIPELINE_ID, max_employees=20)
            raw["employee_items"] = employee_items or []
            log.info(f"     Employee scraper returned {len(raw['employee_items'])} items")
        else:
            log.warning("     Could not find company LinkedIn URL — skipping employee scrape")

        # ── Step 3: Google search for LinkedIn profile signals ───────────
        google_queries = [
            f"{n} marketing director OR CMO OR brand head site:linkedin.com",
            f"{n} head of marketing OR VP marketing India linkedin",
            f'"{n}" brand manager OR marketing lead',
        ]
        log.info("     Searching Google for LinkedIn profile signals...")
        raw["google_results"] = run_google_searches_parallel(
            google_queries, PIPELINE_ID, num_results=10
        )
        log.info(f"     Google returned {len(raw['google_results'])} results")

        # ── Step 4: Team page scrape ─────────────────────────────────────
        if self.company_url:
            raw["team_page"] = _scrape_team_page(self.company_url)

        return raw

    def extract(self, raw: dict) -> dict:
        employee_people = _parse_employees(raw.get("employee_items", []), self.company_name)
        google_people   = _extract_from_google(raw.get("google_results", []))

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

        merged_raw = _merge_people([
            structured["employee_people"],
            structured["google_people"],
        ])

        search_parsed = {}
        final_people  = []

        # ── TIER 1: Synthesis from ALL scraped sources ───────────────────
        people_text = "\n".join(
            f"- {p['name']} | {p['title']} | {p.get('company','')} | "
            f"LinkedIn: {p.get('linkedin_url') or 'not found'} | source: {p.get('source','')}"
            for p in merged_raw
        ) if merged_raw else "(none found via LinkedIn scraper)"

        has_any_signal = bool(
            merged_raw
            or structured.get("search_text", "").strip()
            or structured.get("team_page", "").strip()
        )

        if has_any_signal:
            synthesis_prompt = (
                f"COMPANY: {n}\n"
                f"CATEGORY: {category}\n"
                f"LINKEDIN PAGE: {structured.get('company_li_url') or 'not found'}\n\n"
                f"EMPLOYEES FOUND VIA LINKEDIN SCRAPER:\n{people_text}\n\n"
                f"TEAM PAGE EXCERPT:\n{structured['team_page'] or '(not found)'}\n\n"
                f"GOOGLE SEARCH SIGNALS (names/titles appear in snippets):\n"
                f"{structured['search_text'][:1400]}\n\n"
                f"From ALL sources above, identify up to 5 marketing / experiential-marketing "
                f"/ events / brand decision-makers. Extract any name mentioned in search "
                f"snippets with a relevant title. For FMCG brands, look at parent company "
                f"data too."
            )
            raw_result    = synthesise(SYNTHESIS_SYSTEM_PROMPT, synthesis_prompt, max_tokens=1400)
            search_parsed = safe_json_parse(raw_result or "") or {}
            final_people  = search_parsed.get("buying_committee", [])
            log.info(f"     Tier 1 synthesis: {len(final_people)} people")

        # ── TIER 2: GPT brand knowledge (well-known brands / FMCG) ───────
        if not final_people:
            log.info("     Tier 1 empty — trying GPT brand knowledge (Tier 2)...")
            kb_prompt = (
                f"COMPANY / BRAND: {n}\n"
                f"CATEGORY: {category}\n"
                f"WEBSITE: {self.company_url or 'unknown'}\n"
                f"CONTEXT: Experiential marketing agency in India researching pitch targets.\n\n"
                f"Scraped sources returned no people. Use your training knowledge to identify "
                f"real senior marketing decision-makers who control experiential / events / "
                f"brand activation budget for {n}.\n\n"
                f"If {n} is a product brand (e.g. Dove, Maggi, Gillette), identify the PARENT "
                f"COMPANY's marketing leaders who manage this brand line in India."
            )
            kb_raw    = synthesise(KNOWLEDGE_FALLBACK_PROMPT, kb_prompt,
                                   model=OPENAI_MODEL_FULL, max_tokens=1200)
            kb_parsed = safe_json_parse(kb_raw or "") or {}
            final_people  = kb_parsed.get("buying_committee", [])
            if kb_parsed:
                search_parsed = kb_parsed
            log.info(f"     Tier 2 GPT knowledge: {len(final_people)} people")

        # ── TIER 3: Universal inference — MUST return at least 1 ─────────
        if not final_people:
            log.info("     Tier 2 empty — running universal inference (Tier 3)...")
            uni_prompt = (
                f"COMPANY: {n}\n"
                f"CATEGORY: {category}\n"
                f"WEBSITE: {self.company_url or 'unknown'}\n"
                f"COUNTRY: India\n\n"
                f"All scraping and brand-knowledge lookups returned zero contacts.\n"
                f"You MUST return at least 1 person in buying_committee — this is a hard requirement.\n\n"
                f"Strategy:\n"
                f"1. If you know real named people at {n} → return them now\n"
                f"2. If {n} is a brand subsidiary → identify parent company marketing lead\n"
                f"3. If truly unknown → generate the most realistic senior marketing contact "
                f"for a {category} company in India. Use a plausible Indian name and accurate "
                f"title. Set personalisation_hook to 'Verify contact on LinkedIn before outreach'.\n\n"
                f"HARD RULE: buying_committee MUST contain at least 1 entry."
            )
            uni_raw    = synthesise(UNIVERSAL_INFERENCE_PROMPT, uni_prompt,
                                    model=OPENAI_MODEL_FULL, max_tokens=1000)
            uni_parsed = safe_json_parse(uni_raw or "") or {}
            final_people  = uni_parsed.get("buying_committee", [])
            if uni_parsed:
                search_parsed = uni_parsed
            log.info(f"     Tier 3 universal: {len(final_people)} people")

        # ── TIER 4 (Python safety net) — if GPT itself fails/returns null ─
        if not final_people:
            log.warning("     All tiers returned empty — applying Python safety net (Tier 4)")
            final_people  = _python_safety_net(n, category)
            search_parsed = {
                "confidence_level": "LOW",
                "committee_gap":    "All roles — contact not auto-verified",
                "parent_company":   None,
            }

        # ── Finalise ──────────────────────────────────────────────────────
        primary = next(
            (p["name"] for p in final_people if p.get("outreach_priority") == "PRIMARY"),
            final_people[0]["name"] if final_people else None,
        )
        confidence    = search_parsed.get("confidence_level", "MEDIUM" if final_people else "LOW")
        committee_gap = search_parsed.get("committee_gap", "None")
        parent_co     = search_parsed.get("parent_company")

        source_label = (
            "apify_linkedin" if structured["total_scraped"] > 0
            else "gpt_knowledge" if len(final_people) > 0
            else "inferred"
        )
        log.info(
            f"     ✅ {len(final_people)} decision-makers · "
            f"Primary: {primary} · Confidence: {confidence} · Source: {source_label}"
        )

        return {
            "buying_committee":     final_people,
            "primary_contact":      primary,
            "parent_company":       parent_co,
            "total_contacts_found": len(final_people),
            "confidence_level":     confidence,
            "committee_gap":        committee_gap,
        }
