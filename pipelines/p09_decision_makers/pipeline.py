"""
Pipeline 09 — Decision-Maker Identification

Two-source strategy so it ALWAYS finds contacts:

  Source A — GPT-4o Knowledge (PRIMARY, always runs):
    GPT-4o has deep training knowledge of Indian brands, global brands, parent
    companies (Dove→HUL, Gillette→P&G, Maggi→Nestlé). It knows who the CMO /
    VP Marketing / Brand Head is at virtually every major company. This runs
    first and gives us a guaranteed baseline.

  Source B — Google Search (SUPPLEMENTARY, enriches Source A):
    4 parallel Google searches find LinkedIn URLs and recent title changes.
    These URLs get stitched onto the people GPT already identified.

  Merge:
    Deduplicate by name. Search contacts (with LinkedIn URLs) take priority.
    GPT knowledge fills any gaps. Final result: 2-5 ranked contacts.

This approach works for: standalone brands, product brands (parent company),
small startups, large conglomerates — anything.
"""
import re, requests, structlog
from bs4 import BeautifulSoup
from pipelines.base import BasePipeline
from utils.apify_client import run_google_searches_parallel
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse, normalise_url
from config.settings import OPENAI_MODEL_FULL

log = structlog.get_logger()
PIPELINE_ID = "p09_decision_makers"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# ── System prompt for search-based extraction ─────────────────────────────────
SEARCH_SYSTEM_PROMPT = """You are a B2B sales intelligence analyst for StepOneXP, an experiential marketing agency in India.

From the raw Google search results and company page text, identify marketing decision-makers to contact for an experiential marketing pitch.

IMPORTANT: Some brands are product lines of larger companies (Dove→HUL, Gillette→P&G, Maggi→Nestlé India, Horlicks→HUL). Include people at the parent company if they manage this brand.

Return ONLY valid JSON, no markdown:
{
  "buying_committee": [
    {
      "name": "Full Name",
      "title": "Exact title",
      "company": "Company they work at",
      "role_type": "Economic Buyer | Initiator | Events Specialist | Influencer",
      "linkedin_url": "https://linkedin.com/in/... or null",
      "linkedin_activity": "UNKNOWN",
      "decision_relevance_score": 4,
      "outreach_priority": "PRIMARY | SECONDARY",
      "personalisation_hook": "One specific, verifiable detail to reference in outreach"
    }
  ],
  "primary_contact": "Name of best person to contact first",
  "parent_company": "Parent company name if applicable, else null",
  "confidence_level": "HIGH | MEDIUM | LOW",
  "data_source": "google_search",
  "committee_gap": "Which role is missing, or None"
}

Rules:
- 2-5 people max. Quality over quantity.
- PRIMARY = most senior marketing person (CMO / VP / Head of Marketing)
- SECONDARY = Brand Managers, Events Managers, Growth leads
- Extract LinkedIn URLs from RESULT lines if visible
- Only include people who genuinely appear to work at this company or its parent"""

# ── System prompt for knowledge-based extraction ──────────────────────────────
KNOWLEDGE_SYSTEM_PROMPT = """You are a senior B2B sales intelligence expert with deep knowledge of Indian brands, FMCG companies, D2C brands, fintech, edtech, and all major consumer categories.

Your task: Use your training knowledge to identify the marketing decision-makers at the given company who would own or influence experiential marketing spend.

Key rules:
- For product brands (Dove, Gillette, Ariel, Maggi, Horlicks, etc.) → identify people at the PARENT COMPANY (HUL, P&G India, Nestlé India) who manage that category/brand
- For standalone companies (Mamaearth, Razorpay, Zomato, etc.) → identify their direct marketing leadership
- ONLY include people you genuinely know from your training data — real names, real titles, real companies
- If you do not have real knowledge of specific individuals at this company, return an empty buying_committee — DO NOT guess or invent names
- An empty list is correct and honest for small, private, or less publicly visible companies
- NEVER fabricate names. Wrong names are worse than no names.

Return ONLY valid JSON, no markdown:
{
  "buying_committee": [
    {
      "name": "Full Name",
      "title": "Their title",
      "company": "Company they work at",
      "role_type": "Economic Buyer | Initiator | Events Specialist | Influencer",
      "linkedin_url": null,
      "linkedin_activity": "UNKNOWN",
      "decision_relevance_score": 4,
      "outreach_priority": "PRIMARY | SECONDARY",
      "personalisation_hook": "A specific fact about this person or their brand work"
    }
  ],
  "primary_contact": "Name of best person to contact first or null",
  "parent_company": "Parent company if product brand, else null",
  "confidence_level": "HIGH | MEDIUM | LOW",
  "data_source": "gpt_knowledge",
  "committee_gap": "Which role is missing, or None"
}"""


def _scrape_team_page(company_url: str) -> str:
    """Try common team/about paths on the company website."""
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


def _extract_linkedin_map(google_results: list) -> dict:
    """
    Build a name→linkedin_url map from Google search results.
    Used to enrich GPT-knowledge contacts with real LinkedIn URLs.
    """
    li_map = {}
    li_pattern = re.compile(
        r'(https?://(?:www\.|in\.)?linkedin\.com/in/[a-zA-Z0-9_-]+)',
        re.I
    )
    name_pattern = re.compile(r'^([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)')

    for item in google_results:
        url     = item.get("url", "") or item.get("link", "")
        title   = item.get("title", "")
        snippet = item.get("snippet", "") or item.get("description", "")

        # If this is a LinkedIn profile URL, try to extract the name from title
        if "linkedin.com/in/" in url:
            m = name_pattern.match(title.strip())
            if m:
                name = m.group(1).strip()
                li_map[name.lower()] = url

        # Also scan snippets for inline LinkedIn URLs
        for text in [title, snippet]:
            for li_url in li_pattern.findall(text):
                m = name_pattern.match(title.strip())
                if m:
                    li_map[m.group(1).strip().lower()] = li_url

    return li_map


def _merge_committees(search_people: list, knowledge_people: list,
                      li_map: dict) -> list:
    """
    Merge search-found and knowledge-found contacts.
    - Deduplicates by normalised name
    - Search contacts take priority (they have LinkedIn URLs)
    - Knowledge contacts fill gaps up to 5 total
    - Attaches LinkedIn URLs from li_map to knowledge contacts where name matches
    """
    seen = {}

    def _norm(name: str) -> str:
        return re.sub(r'[^a-z]', '', (name or '').lower())

    # Search contacts first — they have LinkedIn URLs
    for p in search_people:
        key = _norm(p.get("name", ""))
        if key and key not in seen:
            seen[key] = p

    # Knowledge contacts fill gaps
    for p in knowledge_people:
        key = _norm(p.get("name", ""))
        if not key or key in seen:
            continue
        # Try to attach LinkedIn URL from li_map
        for li_name, li_url in li_map.items():
            if _norm(li_name) == key:
                p["linkedin_url"] = li_url
                break
        seen[key] = p

    merged = list(seen.values())[:5]

    # Attach any remaining LinkedIn URLs by fuzzy name match
    for p in merged:
        if p.get("linkedin_url"):
            continue
        pkey = _norm(p.get("name", ""))
        for li_name, li_url in li_map.items():
            if pkey and pkey in _norm(li_name):
                p["linkedin_url"] = li_url
                break

    return merged


class DecisionMakersPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Decision-Maker Identification"

    def fetch(self) -> dict:
        n   = self.company_name
        raw = {"google_results": [], "team_page": ""}

        # 4 parallel Google searches — find LinkedIn URLs to enrich GPT knowledge
        queries = [
            f"{n} CMO \"VP Marketing\" OR \"Head of Marketing\" OR \"SVP\" OR \"AVP\" site:linkedin.com",
            f"{n} \"brand manager\" OR \"marketing manager\" OR \"events manager\" OR \"head of marketing\" linkedin",
            f"{n} marketing director manager brand linkedin profile India",
            f"{n} brand marketing \"category manager\" OR \"brand head\" OR \"portfolio\" linkedin",
        ]
        raw["google_results"] = run_google_searches_parallel(queries, PIPELINE_ID, num_results=8)
        log.info(f"     LinkedIn profiles searched — {len(raw['google_results'])} signals found")

        if self.company_url:
            raw["team_page"] = _scrape_team_page(self.company_url)

        return raw

    def extract(self, raw: dict) -> dict:
        lines = []
        for item in raw.get("google_results", []):
            title   = item.get("title", "")
            snippet = item.get("snippet", "") or item.get("description", "")
            url     = item.get("url", "") or item.get("link", "")
            if title or snippet:
                lines.append(f"RESULT: {title} | URL: {url} | INFO: {snippet[:200]}")

        return {
            "company_name":   self.company_name,
            "category":       self.category,
            "search_text":    "\n".join(lines),
            "team_page":      raw.get("team_page", "")[:2500],
            "result_count":   len(raw.get("google_results", [])),
            "google_results": raw.get("google_results", []),
        }

    def synthesise(self, structured: dict) -> dict:
        n        = structured["company_name"]
        category = structured["category"]

        # ── Source A: GPT-4o knowledge (PRIMARY — always gives results) ───────
        knowledge_prompt = f"""COMPANY: {n}
CATEGORY: {category}
WEBSITE: {self.company_url or 'unknown'}

Use your training knowledge to identify the marketing decision-makers at {n} who would own experiential marketing / brand events / consumer activations.

Remember: if {n} is a product brand (e.g. a personal care, food, beverage, or consumer brand), identify people at the parent company who manage this brand portfolio."""

        knowledge_raw    = synthesise(KNOWLEDGE_SYSTEM_PROMPT, knowledge_prompt,
                                      model=OPENAI_MODEL_FULL, max_tokens=1500)
        knowledge_parsed = safe_json_parse(knowledge_raw or "") or {}
        knowledge_people = knowledge_parsed.get("buying_committee", [])

        # ── Source B: Extract from Google search results ───────────────────────
        search_people  = []
        search_parsed  = {}
        if structured["search_text"].strip():
            search_prompt = f"""COMPANY: {n}
CATEGORY: {category}
WEBSITE: {self.company_url}

GOOGLE SEARCH RESULTS ({structured['result_count']} results):
{structured['search_text']}

TEAM PAGE:
{structured['team_page'] or '(not found)'}

Extract people from these search results only. Do not invent anyone not found in the results."""

            search_raw    = synthesise(SEARCH_SYSTEM_PROMPT, search_prompt, max_tokens=1200)
            search_parsed = safe_json_parse(search_raw or "") or {}
            search_people = search_parsed.get("buying_committee", [])

        # ── Build LinkedIn URL map from raw Google results ────────────────────
        li_map = _extract_linkedin_map(structured.get("google_results", []))

        # ── Merge both sources ────────────────────────────────────────────────
        merged = _merge_committees(search_people, knowledge_people, li_map)

        # Do NOT add a fallback that invents names — empty is better than wrong

        # Determine primary contact (highest decision_relevance_score among PRIMARY)
        primary = next(
            (p["name"] for p in merged if p.get("outreach_priority") == "PRIMARY"),
            merged[0]["name"] if merged else None
        )

        # Use knowledge metadata as ground truth for parent company etc.
        parent_company    = (knowledge_parsed.get("parent_company") or
                             (search_parsed.get("parent_company") if search_people else None))
        confidence        = (knowledge_parsed.get("confidence_level") or
                             "MEDIUM" if merged else "LOW")
        committee_gap     = knowledge_parsed.get("committee_gap") or "None"

        log.info(f"     {len(merged)} decision-makers identified · Primary: {primary} · Confidence: {confidence}")

        return {
            "buying_committee":     merged,
            "primary_contact":      primary,
            "parent_company":       parent_company,
            "total_contacts_found": len(merged),
            "confidence_level":     confidence,
            "committee_gap":        committee_gap,
        }
