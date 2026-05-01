"""
Pipeline 01 — Company Overview
================================
Layer 1: Crawl company website + LinkedIn company page + Google search
Layer 2: Extract business model, scale, funding, geography, marketing maturity
Layer 3: Claude synthesises → ICP fit score + recommended service + narrative

Data sources:
  - apify/website-content-crawler  → About page, team page, press page
  - harvestapi/linkedin-company-scraper → Employee count, founding year, industry
  - apify/google-search-scraper → Funding news, revenue signals
"""
import json
import structlog
from pipelines.base import BasePipeline
from utils.apify_client import crawl_website, run_google_search, run_actor
from utils.claude_client import synthesise, extract_json
from utils.helpers import (
    extract_domain, normalise_url, truncate, clean_text,
    safe_json_parse, calculate_icp_score, score_to_label
)

log = structlog.get_logger()
PIPELINE_ID = "p01_company_overview"


class CompanyOverviewPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Company Overview"

    # ── LAYER 1: FETCH ────────────────────────────────────────────────────────

    def fetch(self) -> dict:
        url    = normalise_url(self.company_url)
        domain = extract_domain(url)
        name   = self.company_name

        raw = {"website_pages": [], "linkedin": [], "news": [], "domain": domain}

        # 1a. Crawl company website (About, Team, Press, Investors pages)
        log.info("p01_fetch_website", url=url)
        pages = crawl_website(url, PIPELINE_ID, max_pages=8)
        raw["website_pages"] = pages

        # 1b. LinkedIn company search
        log.info("p01_fetch_linkedin")
        linkedin = run_actor(
            "linkedin_company",
            {"searchQuery": name, "maxResults": 1},
            PIPELINE_ID
        )
        raw["linkedin"] = linkedin or []

        # 1c. Google: funding, revenue, about
        queries = [
            f"{name} funding series raised investors",
            f"{name} revenue employees founded about company",
        ]
        for q in queries:
            results = run_google_search(q, PIPELINE_ID, num_results=5)
            raw["news"].extend(results)

        return raw

    # ── LAYER 2: EXTRACT ─────────────────────────────────────────────────────

    def extract(self, raw: dict) -> dict:
        structured = {
            "company_name": self.company_name,
            "company_url":  self.company_url,
            "domain":       raw.get("domain", ""),
            "website_text": "",
            "linkedin_data": {},
            "news_snippets": [],
        }

        # Extract website text (About, Team, Investors sections prioritised)
        priority_pages = []
        other_pages    = []
        for page in raw.get("website_pages", []):
            url_lower = page.get("url", "").lower()
            if any(kw in url_lower for kw in ["about", "team", "investor", "press", "story"]):
                priority_pages.append(page)
            else:
                other_pages.append(page)

        all_pages = priority_pages + other_pages
        website_chunks = []
        for page in all_pages[:6]:
            text = page.get("markdown") or page.get("text") or ""
            if text:
                website_chunks.append(f"[PAGE: {page.get('url', '')}]\n{clean_text(text)[:800]}")

        structured["website_text"] = "\n\n".join(website_chunks)

        # Extract LinkedIn data
        if raw.get("linkedin"):
            li = raw["linkedin"][0]
            structured["linkedin_data"] = {
                "employee_count": li.get("employeeCount", li.get("employees")),
                "founded":        li.get("foundedYear", li.get("founded")),
                "headquarters":   li.get("headquarters", li.get("location")),
                "industry":       li.get("industry"),
                "description":    truncate(li.get("description", ""), 300),
                "followers":      li.get("followersCount"),
            }

        # Extract news snippets
        for item in raw.get("news", [])[:10]:
            snippet = item.get("snippet") or item.get("description") or ""
            title   = item.get("title", "")
            if snippet or title:
                structured["news_snippets"].append(f"{title}: {snippet}")

        return structured

    # ── LAYER 3: SYNTHESISE ───────────────────────────────────────────────────

    def synthesise(self, structured: dict) -> dict:
        # Load system prompt
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
        with open(prompt_path) as f:
            system_prompt = f.read()

        # Build user data for Claude
        user_data = f"""
COMPANY: {structured['company_name']}
URL: {structured['company_url']}
CATEGORY: {self.category}

WEBSITE CONTENT:
{structured['website_text'][:2000]}

LINKEDIN DATA:
{json.dumps(structured['linkedin_data'], indent=2)}

NEWS & FUNDING SIGNALS:
{chr(10).join(structured['news_snippets'][:8])}
"""
        result_str = synthesise(system_prompt, user_data, max_tokens=1500)

        if result_str:
            output = safe_json_parse(result_str)
            if output:
                # Compute ICP score from extracted fields if not present
                if not output.get("icp_fit_score"):
                    output["icp_fit_score"] = calculate_icp_score(output)
                # Compute readiness label
                if not output.get("experiential_readiness"):
                    output["experiential_readiness"] = score_to_label(
                        output.get("icp_fit_score", 0),
                        {40: "LOW", 70: "MEDIUM", 100: "HIGH"}
                    )
                return output

        # Fallback: return structured data with nulls
        log.warning("p01_synthesis_failed", company=structured["company_name"])
        return {
            "business_model":         None,
            "industry_vertical":      self.category,
            "employee_count_range":   structured["linkedin_data"].get("employee_count"),
            "funding_status":         "Unknown",
            "icp_fit_score":          0,
            "experiential_readiness": "LOW",
            "company_narrative":      f"{self.company_name} — research incomplete",
            "key_facts":              [],
            "sources_used":           [self.company_url],
        }
