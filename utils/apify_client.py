"""
Apify client — built on the official apify-client Python SDK.
Token rotation: 3 unique tokens spread across 5 pipeline groups.
Fallback: if the primary token fails, tries remaining tokens in order.

KEY DETAIL: apify/google-search-scraper pushes 1 item per query page.
Each item contains { searchQuery: {...}, organicResults: [{title, url, description, ...}] }.
run_google_search() automatically unpacks organicResults so callers get a flat list.
"""
import time
import structlog
from typing import Optional
from apify_client import ApifyClient
from config.settings import APIFY_TOKENS, APIFY_ALL_TOKENS, RATE_LIMIT_DELAY, ACTOR_TIMEOUT
from config.apify_config import ACTORS, TOKEN_GROUP_MAP, ACTOR_DEFAULTS

log = structlog.get_logger()


def _get_token_for_pipeline(pipeline_id: str) -> str:
    for group, pipelines in TOKEN_GROUP_MAP.items():
        if pipeline_id in pipelines:
            return APIFY_TOKENS.get(group, "")
    return APIFY_TOKENS.get("group_1", "")


def _build_token_order(pipeline_id: str) -> list:
    primary = _get_token_for_pipeline(pipeline_id)
    order = [primary] if primary else []
    for t in APIFY_ALL_TOKENS:
        if t not in order:
            order.append(t)
    return order


def run_actor(
    actor_key: str,
    run_input: dict,
    pipeline_id: str,
    timeout_secs: int = None,
    wait_for_finish: bool = True,
) -> Optional[list]:
    """
    Run an Apify actor and return dataset items.
    Tries each available token in order until one works.
    """
    if timeout_secs is None:
        timeout_secs = ACTOR_TIMEOUT

    actor_id = ACTORS.get(actor_key)
    if not actor_id:
        log.error("apify_unknown_actor", actor=actor_key)
        return None

    merged_input = {**ACTOR_DEFAULTS.get(actor_key, {}), **run_input}
    tokens = _build_token_order(pipeline_id)

    if not tokens:
        log.error("apify_no_tokens_configured")
        return None

    for token in tokens:
        try:
            client = ApifyClient(token)
            log.info("apify_run_starting", actor=actor_key, actor_id=actor_id)

            run = client.actor(actor_id).call(
                run_input=merged_input,
                timeout_secs=timeout_secs,
                wait_secs=timeout_secs,
            )

            if not run:
                log.warning("apify_run_returned_none", actor=actor_key)
                continue

            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                log.warning("apify_no_dataset", actor=actor_key)
                return []

            items = list(client.dataset(dataset_id).iterate_items())
            log.info("apify_run_complete", actor=actor_key, items=len(items))
            time.sleep(RATE_LIMIT_DELAY)
            return items

        except Exception as e:
            err = str(e)
            if any(code in err for code in ("402", "403", "429", "Forbidden", "Payment")):
                log.warning("apify_token_limit", actor=actor_key, token_prefix=token[:20], error=err)
                continue
            if "404" in err or "not found" in err.lower():
                log.error("apify_actor_not_found", actor=actor_key, actor_id=actor_id, error=err)
                return None
            if "timeout" in err.lower() or "timed" in err.lower():
                log.warning("apify_timeout", actor=actor_key, timeout_secs=timeout_secs)
                return []
            log.error("apify_error", actor=actor_key, error=err)
            continue

    log.error("apify_all_tokens_exhausted", actor=actor_key)
    return None


def _unwind_google_results(raw_items: list) -> list:
    """
    The Google Search actor pushes 1 item per query with all results nested in 'organicResults'.
    This function unpacks that into a flat list of individual search results.
    Each result gets normalized to {title, url, link, snippet, description, date}.
    """
    if not raw_items:
        return []

    flat = []
    for item in raw_items:
        organic = item.get("organicResults") or item.get("organic_results") or []
        if organic:
            for r in organic:
                flat.append({
                    "title":       r.get("title", ""),
                    "url":         r.get("url", "") or r.get("link", ""),
                    "link":        r.get("url", "") or r.get("link", ""),
                    "snippet":     r.get("description", "") or r.get("snippet", ""),
                    "description": r.get("description", "") or r.get("snippet", ""),
                    "date":        r.get("date", "") or r.get("publishedAt", ""),
                    "position":    r.get("position", 0),
                })
        elif item.get("title") or item.get("url") or item.get("link"):
            # Already a flat result (some actor configs return this way)
            flat.append({
                "title":       item.get("title", ""),
                "url":         item.get("url", "") or item.get("link", ""),
                "link":        item.get("url", "") or item.get("link", ""),
                "snippet":     item.get("description", "") or item.get("snippet", ""),
                "description": item.get("description", "") or item.get("snippet", ""),
                "date":        item.get("date", "") or item.get("publishedAt", ""),
            })

    if flat:
        log.info("apify_google_unwound", raw_items=len(raw_items), flat_results=len(flat))
    else:
        log.warning("apify_google_empty_after_unwind", raw_items=len(raw_items))
    return flat


def run_google_search(query: str, pipeline_id: str, num_results: int = 10) -> list:
    """Run a single Google search query and return a flat list of results."""
    raw = run_actor(
        "google_search",
        {"queries": query, "maxPagesPerQuery": 1, "resultsPerPage": num_results},
        pipeline_id,
    )
    return _unwind_google_results(raw or [])


def crawl_website(url: str, pipeline_id: str, max_pages: int = 4) -> list:
    result = run_actor(
        "website_crawler",
        {"startUrls": [{"url": url}], "maxCrawlPages": max_pages, "saveMarkdown": True},
        pipeline_id,
    )
    return result or []


def scrape_company_employees(company_linkedin_url: str, pipeline_id: str,
                              max_employees: int = 15) -> list:
    """
    Scrape LinkedIn employees for a company using automation-lab/linkedin-company-employees-scraper.
    This actor uses Google SERP discovery — NO LinkedIn cookie required.

    Input:  company_linkedin_url — full URL e.g. https://www.linkedin.com/company/mamaearth/
    Output: list of dicts with keys: name, headline, profileUrl, companySlug, companyName
    """
    result = run_actor(
        "company_employees",
        {"companyUrls": [company_linkedin_url], "maxEmployees": max_employees},
        pipeline_id,
        timeout_secs=60,
    )
    items = result or []
    log.info("apify_employees_returned", url=company_linkedin_url, count=len(items))
    return items


def scrape_reddit(query: str, pipeline_id: str, max_items: int = 20) -> list:
    result = run_actor(
        "reddit_scraper",
        {"searches": [query], "maxItems": max_items, "sort": "relevance", "time": "year"},
        pipeline_id,
        timeout_secs=35,
    )
    return result or []


def run_google_searches_parallel(queries: list, pipeline_id: str, num_results: int = 8) -> list:
    """Run multiple Google search queries in parallel and return combined flat results."""
    from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed
    combined = []
    with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as ex:
        futures = [ex.submit(run_google_search, q, pipeline_id, num_results) for q in queries]
        for f in _as_completed(futures, timeout=90):
            try:
                combined.extend(f.result() or [])
            except Exception as e:
                log.warning("parallel_search_failed", error=str(e))
    return combined
