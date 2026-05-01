"""
Shared utility functions used across all pipeline modules.
"""
import re
import json
import hashlib
import structlog
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

log = structlog.get_logger()


# URL / DOMAIN UTILS

def extract_domain(url_or_name: str) -> str:
    """Extract clean domain from URL or company name.
    Falls back to urlparse when tldextract cannot reach the internet.
    """
    if url_or_name.startswith("http"):
        try:
            import tldextract
            extracted = tldextract.extract(url_or_name)
            if extracted.domain and extracted.suffix:
                return "{}.{}".format(extracted.domain, extracted.suffix).lower()
        except Exception:
            pass
        parsed = urlparse(url_or_name)
        host = parsed.netloc or parsed.path
        return host.lstrip("www.").lower()
    clean = re.sub(r"[^a-z0-9]", "", url_or_name.lower())
    return "{}.com".format(clean)


def normalise_url(url: str) -> str:
    if not url.startswith("http"):
        return "https://{}".format(url)
    return url


def company_to_search_query(company_name: str, suffix: str = "") -> str:
    clean = company_name.strip()
    return "{} {}".format(clean, suffix).strip() if suffix else clean


# TEXT UTILS

def truncate(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x20-\x7E\n]", "", text)
    return text.strip()


def extract_sentences(text: str, max_sentences: int = 5) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:max_sentences])


def safe_json_parse(text: str) -> Optional[dict]:
    """Parse JSON from LLM output -- handles markdown code blocks."""
    if not text:
        return None
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    log.warning("json_parse_failed", preview=text[:100])
    return None


# SCORING UTILS

def score_to_label(score: int, thresholds: dict = None) -> str:
    if thresholds is None:
        thresholds = {33: "LOW", 66: "MEDIUM", 100: "HIGH"}
    for threshold, label in sorted(thresholds.items()):
        if score <= threshold:
            return label
    return list(thresholds.values())[-1]


def calculate_icp_score(
    company_data=None,
    employee_count: int = 0,
    is_vc_backed: bool = False,
    has_india_presence: bool = False,
    is_b2c: bool = None,
) -> int:
    """
    ICP fit score for StepOneXP (0-100).

    Two call styles:
      calculate_icp_score(dict_with_keys)
      calculate_icp_score(is_b2c=True, employee_count=300, ...)
      calculate_icp_score(True, 300, True, True)   # positional
    """
    score = 0

    if is_b2c is not None or not isinstance(company_data, dict):
        b2c = is_b2c if is_b2c is not None else bool(company_data)
        score += 25 if b2c else 0
        score += 25 if employee_count >= 200 else 0
        score += 25 if is_vc_backed else 0
        score += 25 if has_india_presence else 0
        return min(score, 100)

    # dict style
    d = company_data
    model = d.get("business_model", "").upper()
    score += {"B2C": 25, "B2B2C": 20, "B2B": 10}.get(model, 5)
    employees = d.get("employee_count_range", "")
    score += {"1000+": 25, "200-1000": 20, "51-200": 12, "11-50": 5, "1-10": 0}.get(employees, 0)
    funding = d.get("funding_status", "").lower()
    score += 25 if any(k in funding for k in ("vc", "public", "series")) else 10
    geo = d.get("geography", "").lower()
    score += 25 if "india" in geo else 0
    return min(score, 100)


# OUTPUT UTILS

def make_run_id(company_name: str) -> str:
    """Generate unique run ID: slug_YYYYMMDD_HHMMSS_hash6"""
    ts  = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    hsh = hashlib.md5(company_name.lower().encode()).hexdigest()[:6]
    slug = re.sub(r"[^a-z0-9]", "_", company_name.lower()).strip("_")
    return "{}_{}_{}" .format(slug, ts, hsh)


def timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"
