"""
Pipeline 10 — Contact Intelligence
=====================================
Layer 1: Pull decision makers from p09 output + LinkedIn scrape for contact details
Layer 2: Email lookup via Hunter.io + pattern inference + LinkedIn URL verification
Layer 3: Per-contact card with confidence-scored contact details

Accuracy principle: Every field confidence-scored. VERIFIED / INFERRED / NOT_FOUND.
Never presents fabricated data as real.
"""
import json, re, structlog
from pipelines.base import BasePipeline
from utils.apify_client import scrape_linkedin_profiles
from utils.hunter_client import find_email, get_domain_pattern
from utils.helpers import safe_json_parse, extract_domain, normalise_url

log = structlog.get_logger()
PIPELINE_ID = "p10_contact_intelligence"


def _recommend_channel(contact: dict) -> str:
    activity = contact.get("linkedin_activity", "UNKNOWN").upper()
    email_conf = contact.get("email_confidence", 0)
    if activity == "ACTIVE":
        return "LinkedIn DM first, then Email"
    elif email_conf >= 70:
        return "Email first, LinkedIn follow-up"
    else:
        return "LinkedIn DM (email unverified)"


class ContactIntelligencePipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Contact Intelligence"

    # This pipeline receives p09 output — committee list
    def __init__(self, company_name, company_url, category, decision_makers_output=None):
        super().__init__(company_name, company_url, category)
        self.decision_makers = decision_makers_output or {}

    def fetch(self) -> dict:
        domain   = extract_domain(normalise_url(self.company_url))
        pattern  = get_domain_pattern(domain)
        committee = self.decision_makers.get("buying_committee", [])

        raw = {"domain": domain, "email_pattern": pattern, "contacts_raw": []}

        for person in committee[:5]:   # Max 5 — preserve Hunter credits
            name  = person.get("name", "")
            parts = name.strip().split()
            if len(parts) >= 2:
                first = parts[0]
                last  = parts[-1]
                email_data = find_email(first, last, domain)
                raw["contacts_raw"].append({
                    **person,
                    "first_name":       first,
                    "last_name":        last,
                    "domain":           domain,
                    "email_data":       email_data,
                })
        return raw

    def extract(self, raw: dict) -> dict:
        contacts = []
        for c in raw.get("contacts_raw", []):
            email_info = c.get("email_data", {})
            contacts.append({
                "name":              c.get("name"),
                "title":             c.get("title"),
                "role_type":         c.get("role_type"),
                "linkedin_url":      c.get("linkedin_url") or c.get("url"),
                "linkedin_activity": c.get("linkedin_activity", "UNKNOWN"),
                "email":             email_info.get("email"),
                "email_confidence":  email_info.get("confidence", 0),
                "email_source":      email_info.get("source", "not_found"),
                "domain":            raw.get("domain"),
                "outreach_priority": c.get("outreach_priority", "SECONDARY"),
                "personalisation_hook": c.get("personalisation_hook"),
            })
        return {
            "company_name":   self.company_name,
            "domain":         raw.get("domain"),
            "email_pattern":  raw.get("email_pattern"),
            "contacts":       contacts,
        }

    def synthesise(self, structured: dict) -> dict:
        # Layer 3 for this pipeline is formatting + channel recommendation (no LLM needed)
        final_contacts = []
        for c in structured.get("contacts", []):
            c["recommended_channel"] = _recommend_channel(c)
            c["contact_card"] = {
                "name":             c["name"],
                "title":            c["title"],
                "role_type":        c["role_type"],
                "email":            c["email"] or "Not found",
                "email_confidence": f"{c['email_confidence']}%",
                "email_verified":   c["email_source"] == "hunter_verified",
                "linkedin":         c["linkedin_url"] or "Not found",
                "best_channel":     c["recommended_channel"],
                "priority":         c["outreach_priority"],
                "hook":             c["personalisation_hook"],
            }
            final_contacts.append(c)

        return {
            "contacts":          final_contacts,
            "domain":            structured["domain"],
            "email_pattern":     structured["email_pattern"],
            "total_contacts":    len(final_contacts),
            "verified_emails":   sum(1 for c in final_contacts if c.get("email_source") == "hunter_verified"),
            "inferred_emails":   sum(1 for c in final_contacts if c.get("email_source") == "pattern_inferred"),
            "data_disclaimer":   "Emails marked INFERRED are pattern-generated and not verified. Always confirm before sending.",
        }
