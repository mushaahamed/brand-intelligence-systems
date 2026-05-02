"""
Pipeline 10 — Contact Intelligence
=====================================
Uses Apify's harvestapi/linkedin-profile-search to look up each person from P09
and extract their LinkedIn URL, email (when available), and profile details.

No Hunter.io — Apify only. Falls back to email pattern inference if the actor
doesn't return an email directly.

Accuracy principle: Every field confidence-scored. VERIFIED / INFERRED / NOT_FOUND.
Never presents fabricated data as real.
"""
import re, json, structlog
from concurrent.futures import ThreadPoolExecutor, as_completed
from pipelines.base import BasePipeline
from utils.apify_client import scrape_linkedin_profiles
from utils.helpers import safe_json_parse, extract_domain, normalise_url

log = structlog.get_logger()
PIPELINE_ID = "p10_contact_intelligence"

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')


def _infer_email(first: str, last: str, domain: str) -> dict:
    """Pattern-infer the most likely email. Clearly marked as INFERRED."""
    f = first.lower().strip()
    l = last.lower().strip()
    return {
        "email":      f"{f}.{l}@{domain}",
        "confidence": 20,
        "source":     "pattern_inferred",
        "all_patterns": [
            f"{f}.{l}@{domain}",
            f"{f}{l}@{domain}",
            f"{f[0]}{l}@{domain}",
            f"{f}@{domain}",
        ],
    }


def _extract_email_from_item(item: dict) -> str | None:
    """Extract any email found in LinkedIn actor result."""
    for field in ["email", "emailAddress", "contactEmail", "workEmail"]:
        val = item.get(field, "")
        if val and EMAIL_RE.match(str(val)):
            return str(val)
    # Also scan text fields
    for field in ["summary", "about", "description"]:
        text = item.get(field, "")
        if text:
            m = EMAIL_RE.search(str(text))
            if m:
                return m.group(0)
    return None


def _recommend_channel(email_source: str, li_url: str) -> str:
    if email_source == "linkedin_verified":
        return "Email first (verified via LinkedIn), then LinkedIn DM"
    elif email_source == "pattern_inferred" and li_url:
        return "LinkedIn DM first — email is inferred only"
    elif email_source == "pattern_inferred":
        return "Email (inferred — verify before sending)"
    elif li_url:
        return "LinkedIn DM (no email found)"
    else:
        return "Research contact details manually"


class ContactIntelligencePipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Contact Intelligence"

    def __init__(self, company_name, company_url, category, decision_makers_output=None):
        super().__init__(company_name, company_url, category)
        self.decision_makers = decision_makers_output or {}

    def _lookup_one(self, person: dict, domain: str) -> dict:
        """Look up a single person on LinkedIn. Designed to run in a thread."""
        name  = person.get("name", "")
        parts = name.strip().split()
        first = parts[0] if parts else ""
        last  = parts[-1] if len(parts) > 1 else ""
        li_url = person.get("linkedin_url") or ""

        query = f"{name} {self.company_name}"
        li_results = []
        try:
            li_results = scrape_linkedin_profiles(
                query, PIPELINE_ID, max_results=2, timeout_secs=20
            ) or []
        except Exception as e:
            log.warning("p10_linkedin_error", name=name, error=str(e))

        best = None
        for item in li_results:
            item_name = (item.get("fullName") or item.get("name") or
                         f"{item.get('firstName','')} {item.get('lastName','')}".strip()).lower()
            if any(p.lower() in item_name for p in name.split() if len(p) > 2):
                best = item; break
        if not best and li_results:
            best = li_results[0]

        email_val    = None
        email_source = "not_found"
        if best:
            email_val = _extract_email_from_item(best)
            if email_val:
                email_source = "linkedin_verified"
            if not li_url:
                li_url = (best.get("profileUrl") or best.get("linkedinUrl") or
                          best.get("url") or "")

        if not email_val and first and last and domain:
            inferred     = _infer_email(first, last, domain)
            email_val    = inferred["email"]
            email_source = "pattern_inferred"

        return {
            **person,
            "first_name":       first,
            "last_name":        last,
            "domain":           domain,
            "email":            email_val,
            "email_source":     email_source,
            "email_confidence": 70 if email_source == "linkedin_verified" else 20,
            "linkedin_url":     li_url,
            "linkedin_data":    best or {},
        }

    def fetch(self) -> dict:
        domain    = extract_domain(normalise_url(self.company_url))
        committee = self.decision_makers.get("buying_committee", [])
        raw       = {"domain": domain, "contacts_raw": []}

        # Max 3 people, all lookups in parallel — cuts P10 time from ~2min to ~25s
        targets = [p for p in committee[:3] if p.get("name")]
        log.info("p10_parallel_lookup_start", people=len(targets))

        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = {ex.submit(self._lookup_one, p, domain): p for p in targets}
            for f in as_completed(futures, timeout=30):
                try:
                    raw["contacts_raw"].append(f.result())
                except Exception as e:
                    log.warning("p10_lookup_failed", error=str(e))

        log.info("p10_lookup_done", contacts=len(raw["contacts_raw"]))
        return raw

    def extract(self, raw: dict) -> dict:
        contacts = []
        for c in raw.get("contacts_raw", []):
            li_data = c.get("linkedin_data", {})
            # Enrich personalisation hook from LinkedIn bio if available
            hook = c.get("personalisation_hook") or ""
            if not hook and li_data:
                hook = (li_data.get("summary") or li_data.get("about") or
                        li_data.get("headline") or "")[:200]

            contacts.append({
                "name":              c.get("name"),
                "title":             c.get("title"),
                "role_type":         c.get("role_type"),
                "linkedin_url":      c.get("linkedin_url") or c.get("url"),
                "linkedin_activity": c.get("linkedin_activity", "UNKNOWN"),
                "email":             c.get("email"),
                "email_confidence":  c.get("email_confidence", 0),
                "email_source":      c.get("email_source", "not_found"),
                "domain":            raw.get("domain"),
                "outreach_priority": c.get("outreach_priority", "SECONDARY"),
                "personalisation_hook": hook,
            })
        return {
            "company_name":  self.company_name,
            "domain":        raw.get("domain"),
            "email_pattern": "{first}.{last}@" + (raw.get("domain") or ""),
            "contacts":      contacts,
        }

    def synthesise(self, structured: dict) -> dict:
        final_contacts = []
        for c in structured.get("contacts", []):
            c["recommended_channel"] = _recommend_channel(
                c.get("email_source", "not_found"),
                c.get("linkedin_url", "")
            )
            c["contact_card"] = {
                "name":             c["name"],
                "title":            c["title"],
                "role_type":        c["role_type"],
                "email":            c["email"] or "Not found — pattern infer or research manually",
                "email_confidence": f"{c['email_confidence']}%",
                "email_verified":   c["email_source"] == "linkedin_verified",
                "linkedin":         c["linkedin_url"] or "Not found",
                "best_channel":     c["recommended_channel"],
                "priority":         c["outreach_priority"],
                "hook":             c["personalisation_hook"],
            }
            final_contacts.append(c)

        verified   = sum(1 for c in final_contacts if c.get("email_source") == "linkedin_verified")
        inferred   = sum(1 for c in final_contacts if c.get("email_source") == "pattern_inferred")
        no_email   = sum(1 for c in final_contacts if c.get("email_source") == "not_found")

        return {
            "contacts":        final_contacts,
            "domain":          structured["domain"],
            "email_pattern":   structured["email_pattern"],
            "total_contacts":  len(final_contacts),
            "verified_emails": verified,
            "inferred_emails": inferred,
            "no_email_found":  no_email,
            "data_disclaimer": (
                "Emails marked INFERRED are pattern-generated (first.last@domain) — not verified. "
                "Emails marked VERIFIED were found directly on LinkedIn profiles."
            ) if inferred > 0 else None,
        }
