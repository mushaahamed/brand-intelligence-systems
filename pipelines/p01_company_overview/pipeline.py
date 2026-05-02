"""
Pipeline 01 — Company Overview
================================
Fast version: direct HTTP crawl + parallel Google searches.
"""
import json
import structlog
from pipelines.base import BasePipeline
from utils.web_scraper import fast_crawl
from utils.apify_client import run_google_searches_parallel
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

    def fetch(self) -> dict:
        url  = normalise_url(self.company_url)
        name = self.company_name
        raw  = {"website_pages": [], "news": [], "domain": extract_domain(url)}

        log.info("p01_fetch_website", url=url)
        raw["website_pages"] = fast_crawl(url, max_pages=4)

        queries = [
            f"{name} employees founded funding revenue about company",
            f"{name} headquarters investors series funding LinkedIn",
        ]
        raw["news"] = run_google_searches_parallel(queries, PIPELINE_ID, num_results=8)
        return raw

    def extract(self, raw: dict) -> dict:
        structured = {
            "company_name": self.company_name,
            "company_url":  self.company_url,
            "domain":       raw.get("domain", ""),
            "website_text": "",
            "linkedin_data": {},
            "news_snippets": [],
        }

        priority_pages, other_pages = [], []
        for page in raw.get("website_pages", []):
            url_lower = page.get("url", "").lower()
            if any(kw in url_lower for kw in ["about", "team", "investor", "press", "story"]):
                priority_pages.append(page)
            else:
                other_pages.append(page)

        website_chunks = []
        for page in (priority_pages + other_pages)[:6]:
            text = page.get("markdown") or page.get("text") or ""
            if text:
                website_chunks.append(f"[PAGE: {page.get('url', '')}]\n{clean_text(text)[:800]}")
        structured["website_text"] = "\n\n".join(website_chunks)

        for item in raw.get("news", [])[:10]:
            snippet = item.get("snippet") or item.get("description") or ""
            title   = item.get("title", "")
            if snippet or title:
                structured["news_snippets"].append(f"{title}: {snippet}")

        return structured

    def synthesise(self, structured: dict) -> dict:
        import os
        prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
        with open(prompt_path) as f:
            system_prompt = f.read()

        user_data = f"""
COMPANY: {structured['company_name']}
URL: {structured['company_url']}
CATEGORY: {self.category}

WEBSITE CONTENT:
{structured['website_text'][:2000]}

NEWS & FUNDING SIGNALS:
{chr(10).join(structured['news_snippets'][:8])}
"""
        result_str = synthesise(system_prompt, user_data, max_tokens=1500)

        if result_str:
            output = safe_json_parse(result_str)
            if output:
                if not output.get("icp_fit_score"):
                    output["icp_fit_score"] = calculate_icp_score(output)
                if not output.get("experiential_readiness"):
                    output["experiential_readiness"] = score_to_label(
                        output.get("icp_fit_score", 0),
                        {40: "LOW", 70: "MEDIUM", 100: "HIGH"}
                    )
                return output

        log.warning("p01_synthesis_failed", company=structured["company_name"])
        return {
            "business_model":         None,
            "industry_vertical":      self.category,
            "employee_count_range":   None,
            "funding_status":         "Unknown",
            "icp_fit_score":          0,
            "experiential_readiness": "LOW",
            "company_narrative":      f"{self.company_name} — research incomplete",
            "key_facts":              [],
            "sources_used":           [self.company_url],
        }
