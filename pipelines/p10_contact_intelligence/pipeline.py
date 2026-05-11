"""
Pipeline 10 — Contact Intelligence

Takes the buying committee from P09 and enriches each person with:
  - Email: pattern-inferred from first.last@domain.com (clearly marked)
  - LinkedIn URL: forwarded from P09 if found, otherwise null
  - Recommended channel: LinkedIn DM if URL found, else email (inferred)

No Apify calls — this runs instantly (~0s). The LinkedIn actor was unreliable
and LinkedIn rarely exposes emails publicly anyway. Pattern inference is honest
and gives the sales rep a starting point.
"""
import re, structlog
from pipelines.base import BasePipeline
from utils.helpers import extract_domain, normalise_url

log = structlog.get_logger()
PIPELINE_ID = "p10_contact_intelligence"


def _infer_email(first: str, last: str, domain: str) -> dict:
    f = re.sub(r'[^a-z]', '', first.lower().strip())
    l = re.sub(r'[^a-z]', '', last.lower().strip())
    if not f or not l or not domain:
        return {"email": None, "confidence": 0, "source": "not_found"}
    return {
        "email":      f"{f}.{l}@{domain}",
        "confidence": 25,
        "source":     "pattern_inferred",
        "all_patterns": [
            f"{f}.{l}@{domain}",
            f"{f}{l}@{domain}",
            f"{f[0]}{l}@{domain}",
            f"{f}@{domain}",
        ],
    }


def _recommend_channel(linkedin_url: str, email_source: str) -> str:
    if linkedin_url and "linkedin.com/in" in linkedin_url:
        return "LinkedIn DM first — direct profile link available"
    elif email_source == "pattern_inferred":
        return "Email (pattern-inferred — verify before sending)"
    return "Research contact details manually on LinkedIn"


class ContactIntelligencePipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Contact Intelligence"

    def __init__(self, company_name, company_url, category, decision_makers_output=None):
        super().__init__(company_name, company_url, category)
        self.decision_makers = decision_makers_output or {}

    def fetch(self) -> dict:
        domain    = extract_domain(normalise_url(self.company_url))
        committee = self.decision_makers.get("buying_committee", [])
        contacts  = []

        for person in committee[:5]:
            name = person.get("name", "").strip()
            if not name:
                continue
            parts = name.split()
            first = parts[0] if parts else ""
            last  = parts[-1] if len(parts) > 1 else ""

            email_data = _infer_email(first, last, domain)
            li_url     = person.get("linkedin_url") or ""

            contacts.append({
                **person,
                "first_name":       first,
                "last_name":        last,
                "domain":           domain,
                "email":            email_data["email"],
                "email_confidence": email_data["confidence"],
                "email_source":     email_data["source"],
                "linkedin_url":     li_url,
            })

        log.info(f"     {len(contacts)} contacts enriched · Email patterns inferred for {domain}")
        return {"domain": domain, "contacts_raw": contacts}

    def extract(self, raw: dict) -> dict:
        contacts = []
        for c in raw.get("contacts_raw", []):
            contacts.append({
                "name":              c.get("name"),
                "title":             c.get("title"),
                "role_type":         c.get("role_type"),
                "linkedin_url":      c.get("linkedin_url"),
                "linkedin_activity": c.get("linkedin_activity", "UNKNOWN"),
                "email":             c.get("email"),
                "email_confidence":  c.get("email_confidence", 0),
                "email_source":      c.get("email_source", "not_found"),
                "domain":            raw.get("domain"),
                "outreach_priority": c.get("outreach_priority", "SECONDARY"),
                "personalisation_hook": c.get("personalisation_hook", ""),
            })
        return {
            "company_name":  self.company_name,
            "domain":        raw.get("domain"),
            "email_pattern": "{first}.{last}@" + (raw.get("domain") or ""),
            "contacts":      contacts,
        }

    def synthesise(self, structured: dict) -> dict:
        final = []
        for c in structured.get("contacts", []):
            c["recommended_channel"] = _recommend_channel(
                c.get("linkedin_url", ""), c.get("email_source", "not_found")
            )
            c["contact_card"] = {
                "name":             c["name"],
                "title":            c["title"],
                "email":            c["email"] or "Not found",
                "email_confidence": f"{c['email_confidence']}% (pattern-inferred)",
                "linkedin":         c["linkedin_url"] or "Not found — search manually",
                "best_channel":     c["recommended_channel"],
                "priority":         c["outreach_priority"],
            }
            final.append(c)

        inferred = sum(1 for c in final if c.get("email_source") == "pattern_inferred")
        return {
            "contacts":        final,
            "domain":          structured["domain"],
            "email_pattern":   structured["email_pattern"],
            "total_contacts":  len(final),
            "verified_emails": 0,
            "inferred_emails": inferred,
            "data_disclaimer": (
                "Emails are pattern-inferred (first.last@domain) — not verified. "
                "Use LinkedIn DM where a profile link is available."
            ) if inferred > 0 else None,
        }
