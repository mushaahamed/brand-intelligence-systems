"""
Fast direct HTTP web scraper — replaces Apify website-content-crawler.
Takes 2-8s instead of 60s. Returns the same data shape: list of {url, text, markdown}.
"""
import re
import structlog
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

log = structlog.get_logger()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

PRIORITY_PATHS = ["about", "team", "investor", "press", "story", "company", "founder", "mission", "who-we-are"]


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "svg", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r'\s+', ' ', text).strip()


def _fetch_page(url: str, timeout: int = 8) -> dict | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return None
        if "text/html" not in r.headers.get("content-type", ""):
            return None
        text = _html_to_text(r.text)
        if len(text) < 100:
            return None
        return {"url": r.url, "text": text[:5000], "markdown": text[:5000]}
    except Exception:
        return None


def _get_priority_links(html: str, base_url: str, domain: str, max_links: int = 6) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    priority = []
    others = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(base_url, href)
        p = urlparse(full)
        if not p.scheme.startswith("http"):
            continue
        if domain not in p.netloc:
            continue
        norm = full.split("?")[0].split("#")[0].rstrip("/")
        if norm in seen or norm == base_url.rstrip("/"):
            continue
        seen.add(norm)
        path = p.path.lower()
        if any(kw in path for kw in PRIORITY_PATHS):
            priority.append(full)
        else:
            others.append(full)
    return (priority + others)[:max_links]


def fast_crawl(url: str, max_pages: int = 4) -> list[dict]:
    """
    Crawl a website using direct HTTP requests (no Apify Docker spinup).
    Returns list of {url, text, markdown} dicts — same shape as Apify crawler output.
    """
    log.info("fast_crawl_start", url=url, max_pages=max_pages)
    pages = []

    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if r.status_code != 200:
            log.warning("fast_crawl_homepage_failed", url=url, status=r.status_code)
            return []

        final_url = r.url
        domain = urlparse(final_url).netloc
        text = _html_to_text(r.text)
        pages.append({"url": final_url, "text": text[:5000], "markdown": text[:5000]})

        links = _get_priority_links(r.text, final_url, domain, max_links=max_pages + 2)

        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = {ex.submit(_fetch_page, link): link for link in links[: max_pages - 1]}
            for f in as_completed(futures, timeout=12):
                if len(pages) >= max_pages:
                    break
                try:
                    result = f.result()
                    if result:
                        pages.append(result)
                except Exception:
                    pass

    except Exception as e:
        log.error("fast_crawl_error", url=url, error=str(e))

    log.info("fast_crawl_done", url=url, pages=len(pages))
    return pages
