"""
Apify client wrapper with:
- Token rotation by pipeline group
- Automatic retries with exponential backoff
- Rate limiting to protect free tier credits
- Structured error handling — never crashes the pipeline
"""
import time
import requests
import structlog
from typing import Any, Optional
from config.settings import APIFY_TOKENS, MAX_RETRIES, REQUEST_TIMEOUT, RATE_LIMIT_DELAY, ACTOR_TIMEOUT
from config.apify_config import ACTORS, TOKEN_GROUP_MAP, ACTOR_DEFAULTS

log = structlog.get_logger()

BASE_URL = "https://api.apify.com/v2"


def _get_token_for_pipeline(pipeline_id: str) -> str:
    """Returns the correct Apify token for a given pipeline."""
    for group, pipelines in TOKEN_GROUP_MAP.items():
        if pipeline_id in pipelines:
            return APIFY_TOKENS.get(group, "")
    return APIFY_TOKENS.get("group_1", "")


def run_actor(
    actor_key: str,
    run_input: dict,
    pipeline_id: str,
    timeout_secs: int = None,
    wait_for_finish: bool = True,
) -> Optional[list[dict]]:
    if timeout_secs is None:
        timeout_secs = ACTOR_TIMEOUT
    """
    Run an Apify actor and return its dataset items.

    Args:
        actor_key:      Key from ACTORS dict (e.g. 'google_search')
        run_input:      Input payload for the actor
        pipeline_id:    Which pipeline is calling this (for token rotation)
        timeout_secs:   Max seconds to wait for actor completion
        wait_for_finish: If True, poll until done; else return run ID

    Returns:
        List of result dicts, or None on failure
    """
    token    = _get_token_for_pipeline(pipeline_id)
    actor_id = ACTORS.get(actor_key)

    if not token:
        log.error("apify_no_token", pipeline=pipeline_id)
        return None
    if not actor_id:
        log.error("apify_unknown_actor", actor=actor_key)
        return None

    # Merge defaults with caller's input
    merged_input = {**ACTOR_DEFAULTS.get(actor_key, {}), **run_input}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Start actor run
            run_url = f"{BASE_URL}/acts/{actor_id}/runs?token={token}"
            resp = requests.post(
                run_url,
                json=merged_input,
                timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            run_data  = resp.json().get("data", {})
            run_id    = run_data.get("id")
            dataset_id = run_data.get("defaultDatasetId")

            if not run_id:
                log.error("apify_no_run_id", actor=actor_key, response=run_data)
                return None

            log.info("apify_run_started", actor=actor_key, run_id=run_id, attempt=attempt)

            if not wait_for_finish:
                return [{"run_id": run_id, "dataset_id": dataset_id}]

            # Poll for completion
            status_url = f"{BASE_URL}/actor-runs/{run_id}?token={token}"
            elapsed    = 0
            poll_interval = 3

            while elapsed < timeout_secs:
                time.sleep(poll_interval)
                elapsed += poll_interval
                status_resp = requests.get(status_url, timeout=REQUEST_TIMEOUT)
                status_data = status_resp.json().get("data", {})
                status      = status_data.get("status", "")

                if status == "SUCCEEDED":
                    break
                elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    log.error("apify_run_failed", actor=actor_key, status=status)
                    return None

            # Fetch results
            items_url = f"{BASE_URL}/datasets/{dataset_id}/items?token={token}&clean=true"
            items_resp = requests.get(items_url, timeout=REQUEST_TIMEOUT)
            items_resp.raise_for_status()
            items = items_resp.json()

            log.info("apify_run_complete", actor=actor_key, items=len(items))
            time.sleep(RATE_LIMIT_DELAY)   # Rate limit between calls
            return items

        except requests.exceptions.RequestException as e:
            log.warning("apify_request_error", actor=actor_key, attempt=attempt, error=str(e))
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)   # Exponential backoff
            else:
                log.error("apify_max_retries", actor=actor_key)
                return None

    return None


def run_google_search(query: str, pipeline_id: str, num_results: int = 10) -> list[dict]:
    """Convenience wrapper for Google search."""
    result = run_actor(
        "google_search",
        {"queries": query, "maxPagesPerQuery": 1, "resultsPerPage": num_results},
        pipeline_id
    )
    return result or []


def crawl_website(url: str, pipeline_id: str, max_pages: int = 6) -> list[dict]:
    """Convenience wrapper for website crawling."""
    result = run_actor(
        "website_crawler",
        {"startUrls": [{"url": url}], "maxCrawlPages": max_pages, "saveMarkdown": True},
        pipeline_id
    )
    return result or []


def scrape_linkedin_profiles(query: str, pipeline_id: str, max_results: int = 5) -> list[dict]:
    """Convenience wrapper for LinkedIn profile search."""
    result = run_actor(
        "linkedin_search",
        {"searchQuery": query, "maxResults": max_results},
        pipeline_id
    )
    return result or []


def scrape_reddit(query: str, pipeline_id: str, max_items: int = 30) -> list[dict]:
    """Convenience wrapper for Reddit scraping."""
    result = run_actor(
        "reddit_scraper",
        {"searches": [query], "maxItems": max_items, "sort": "relevance", "time": "year"},
        pipeline_id
    )
    return result or []
