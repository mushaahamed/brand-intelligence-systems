"""
Pipeline 12 — Outreach Tracking Logic
========================================
Layer 1: Generate tracking pixel URL + tracked links for all email touches
Layer 2: Build engagement scoring model per contact
Layer 3: Return tracking-enabled outreach package + status dashboard schema

Engagement scoring:
  Email opened (once):    +1 pt
  Email opened (3+ times):+3 pts
  Link clicked:           +5 pts
  LinkedIn accepted:      +4 pts
  Reply received:         +10 pts
  Meeting booked:         +20 pts
"""
import uuid, hashlib, structlog
from datetime import datetime
from pipelines.base import BasePipeline
from utils.helpers import timestamp
from config.settings import TRACKING_BASE

log = structlog.get_logger()
PIPELINE_ID = "p12_tracking"


def _make_tracking_id(company: str, contact_name: str, touch: int) -> str:
    raw = f"{company}:{contact_name}:{touch}:{uuid.uuid4()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _tracking_pixel_html(tracking_id: str) -> str:
    return f'<img src="{TRACKING_BASE}/open/{tracking_id}" width="1" height="1" style="display:none" alt="" />'


def _tracked_link(url: str, tracking_id: str, touch: int) -> str:
    return f"{TRACKING_BASE}/click/{tracking_id}/{touch}?redirect={url}"


class TrackingPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Outreach Tracking"

    def __init__(self, company_name, company_url, category, outreach_output=None):
        super().__init__(company_name, company_url, category)
        self.outreach = outreach_output or {}

    def fetch(self) -> dict:
        return {"outreach": self.outreach}

    def extract(self, raw: dict) -> dict:
        outreach  = raw.get("outreach", {})
        contacts  = outreach.get("all_contacts", [outreach.get("primary_contact", {})])
        sequence  = outreach.get("outreach_sequence", {})

        tracking_records = []
        for contact in contacts[:5]:
            name = contact.get("name", "Unknown")
            tid  = _make_tracking_id(self.company_name, name, 1)
            tracking_records.append({
                "contact_name":  name,
                "contact_email": contact.get("email"),
                "tracking_id":   tid,
                "sequence":      sequence,
                "status":        "NOT_SENT",
                "engagement_score": 0,
                "events":        [],
            })
        return {"company_name": self.company_name, "tracking_records": tracking_records}

    def synthesise(self, structured: dict) -> dict:
        records = structured.get("tracking_records", [])
        enhanced = []
        for record in records:
            tid = record["tracking_id"]
            seq = record.get("sequence", {})

            # Add tracking pixel and links to each email touch
            tracked_touches = {}
            for touch_key, touch in seq.items():
                if touch.get("channel") == "email":
                    msg = touch.get("message", "")
                    pixel = _tracking_pixel_html(tid)
                    tracked_touches[touch_key] = {
                        **touch,
                        "message_with_tracking": msg + f"\n\n{pixel}",
                        "tracking_pixel_url":    f"{TRACKING_BASE}/open/{tid}",
                    }
                else:
                    tracked_touches[touch_key] = touch

            enhanced.append({
                **record,
                "tracked_sequence": tracked_touches,
                "dashboard_entry":  {
                    "company":            self.company_name,
                    "contact":            record["contact_name"],
                    "email":              record["contact_email"],
                    "status":             "NOT_SENT",
                    "engagement_score":   0,
                    "last_activity":      None,
                    "next_action":        "Send Touch 1",
                    "next_action_date":   None,
                    "tracking_id":        tid,
                    "scoring_rubric": {
                        "email_opened_once":    1,
                        "email_opened_3x":      3,
                        "link_clicked":         5,
                        "linkedin_accepted":    4,
                        "reply_received":       10,
                        "meeting_booked":       20,
                    },
                },
            })

        return {
            "tracking_records":  enhanced,
            "tracking_base_url": TRACKING_BASE,
            "setup_instructions": [
                "Deploy the FastAPI backend to get a public URL",
                f"Update TRACKING_BASE in config to your deployed URL",
                "Tracking endpoints: GET /track/open/{{id}} and GET /track/click/{{id}}/{{touch}}",
                "Apple Mail Privacy Protection inflates open rates — treat clicks and replies as primary signals",
            ],
        }
