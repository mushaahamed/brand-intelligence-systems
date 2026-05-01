"""
Hunter.io client for email finding and verification.
Free tier: 25 lookups/month. All results confidence-scored.
"""
import requests
import structlog
from typing import Optional
from config.settings import HUNTER_API_KEY, REQUEST_TIMEOUT

log = structlog.get_logger()
BASE_URL = "https://api.hunter.io/v2"


def find_email(
    first_name: str,
    last_name: str,
    domain: str,
) -> dict:
    """
    Find an email address for a person at a given domain.

    Returns:
        {
            "email": str | None,
            "confidence": int (0-100),
            "source": "hunter_verified" | "pattern_inferred" | "not_found",
            "pattern": str (e.g. "{first}.{last}@domain.com")
        }
    """
    result = {
        "email": None,
        "confidence": 0,
        "source": "not_found",
        "pattern": None,
    }

    if not HUNTER_API_KEY:
        log.warning("hunter_no_key", hint="Set HUNTER_API_KEY in .env")
        return _infer_email(first_name, last_name, domain)

    try:
        resp = requests.get(
            f"{BASE_URL}/email-finder",
            params={
                "domain":      domain,
                "first_name":  first_name,
                "last_name":   last_name,
                "api_key":     HUNTER_API_KEY,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})

        if data.get("email"):
            result["email"]      = data["email"]
            result["confidence"] = data.get("confidence", 0)
            result["source"]     = "hunter_verified"
            log.info("hunter_found", email=data["email"], confidence=data.get("confidence"))
        else:
            # Fall back to pattern inference
            result = _infer_email(first_name, last_name, domain)

    except requests.exceptions.RequestException as e:
        log.warning("hunter_error", error=str(e))
        result = _infer_email(first_name, last_name, domain)

    return result


def get_domain_pattern(domain: str) -> Optional[str]:
    """
    Fetch the email pattern for a domain (e.g. {first}.{last}@domain.com).
    Uses Hunter's domain search endpoint.
    """
    if not HUNTER_API_KEY:
        return None
    try:
        resp = requests.get(
            f"{BASE_URL}/domain-search",
            params={"domain": domain, "api_key": HUNTER_API_KEY, "limit": 1},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return data.get("pattern")
    except Exception:
        return None


def _infer_email(first_name: str, last_name: str, domain: str) -> dict:
    """
    Pattern-based email inference when Hunter is unavailable.
    Uses the most common corporate email patterns.
    Clearly marked as INFERRED — never presented as verified.
    """
    first = first_name.lower().strip()
    last  = last_name.lower().strip()
    patterns = [
        f"{first}.{last}@{domain}",
        f"{first}{last}@{domain}",
        f"{first[0]}{last}@{domain}",
        f"{first}@{domain}",
    ]
    return {
        "email":      patterns[0],   # Most common pattern
        "confidence": 25,            # Low confidence — inferred only
        "source":     "pattern_inferred",
        "pattern":    "{first}.{last}@domain",
        "all_patterns": patterns,
    }
