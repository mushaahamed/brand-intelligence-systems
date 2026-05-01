"""
Pipeline 11 — Personalised Outreach
=====================================
Layer 1: Compile all outputs from p01-p10 into a unified context object
Layer 2: Extract the 6 personalisation variables (signal, gap, hook, tone, proof, cta angle)
Layer 3: Generate email + LinkedIn message per primary contact using Claude Sonnet

The 5S Formula: Signal → Specific → Short → Social proof → Single CTA
Max 120 words for email. Max 300 chars for LinkedIn note.
"""
import json, structlog
from pipelines.base import BasePipeline
from utils.claude_client import write_outreach, synthesise
from utils.helpers import safe_json_parse

log = structlog.get_logger()
PIPELINE_ID = "p11_outreach"

SEQUENCE_PROMPT = """You are a B2B sales writer for StepOneXP, an experiential marketing agency in India (350+ events, APAC footprint).

Write a 3-touch outreach sequence for this contact. Each message must be distinct and reference different angles.

Return ONLY valid JSON:
{
  "touch_1": {
    "channel": "email",
    "subject_line": "Subject line under 60 chars",
    "message": "Full email under 120 words. Signal-specific opening. No generic phrases.",
    "send_day": 1
  },
  "touch_2": {
    "channel": "linkedin",
    "message": "LinkedIn message under 300 chars. Reference the email briefly.",
    "send_day": 4
  },
  "touch_3": {
    "channel": "email",
    "subject_line": "Follow-up subject",
    "message": "Follow-up email under 80 words. New angle — competitor or case study.",
    "send_day": 9
  },
  "touch_4": {
    "channel": "email",
    "subject_line": "Final touch subject",
    "message": "Closing email under 60 words. Leave door open.",
    "send_day": 16
  }
}
Rules: No banned words (leverage, unlock, seamless, robust, game-changer, revolutionize).
Each touch must reference specific data from the context. No generic templates."""


class OutreachPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Personalised Outreach"

    def __init__(self, company_name, company_url, category, all_pipeline_outputs=None):
        super().__init__(company_name, company_url, category)
        self.all_outputs = all_pipeline_outputs or {}

    def fetch(self) -> dict:
        # No external fetching — compiles from previous pipeline outputs
        return {"pipeline_outputs": self.all_outputs}

    def extract(self, raw: dict) -> dict:
        outputs = raw.get("pipeline_outputs", {})

        # Extract the 6 personalisation variables
        p01 = outputs.get("p01_company_overview",    {}).get("output", {})
        p05 = outputs.get("p05_brand_activity",       {}).get("output", {})
        p06 = outputs.get("p06_experiential_footprint",{}).get("output", {})
        p07 = outputs.get("p07_reputation_research",  {}).get("output", {})
        p08 = outputs.get("p08_strategic_watchouts",  {}).get("output", {})
        p09 = outputs.get("p09_decision_makers",      {}).get("output", {})
        p10 = outputs.get("p10_contact_intelligence", {}).get("output", {})
        p04 = outputs.get("p04_competitor_mapping",   {}).get("output", {})

        contacts   = p10.get("contacts", [])
        committee  = p09.get("buying_committee", [])
        primary    = next((c for c in contacts if c.get("outreach_priority") == "PRIMARY"), contacts[0] if contacts else {})
        committee_primary = next((c for c in committee if c.get("outreach_priority") == "PRIMARY"), committee[0] if committee else {})

        return {
            "company_name":     self.company_name,
            "contact_name":     primary.get("name") or committee_primary.get("name", "there"),
            "contact_role":     primary.get("title") or committee_primary.get("title", ""),
            "contact_email":    primary.get("email"),
            "contact_linkedin": primary.get("linkedin_url"),
            "recent_signal":    p05.get("last_major_campaign") or p05.get("activity_summary", ""),
            "events_gap":       p06.get("pitch_angle", ""),
            "events_history":   p06.get("opening_line_for_pitch", ""),
            "watchout_verdict": p08.get("overall_verdict", "GREEN"),
            "pitch_angle":      p06.get("pitch_angle", ""),
            "competitor_signal": p04.get("competitive_urgency", ""),
            "reputation_opportunity": p07.get("reputation_opportunity", ""),
            "recommended_service": p01.get("recommended_service", ""),
            "all_contacts":     contacts,
            "personalisation_hook": committee_primary.get("personalisation_hook", ""),
        }

    def synthesise(self, structured: dict) -> dict:
        context_str = json.dumps({k: v for k, v in structured.items() if k != "all_contacts"}, indent=2)

        user_data = f"""CONTACT: {structured['contact_name']} ({structured['contact_role']})
COMPANY: {structured['company_name']}
CATEGORY: {self.category}

PERSONALISATION CONTEXT:
{context_str}

STEPONEXP PROOF POINT: 350+ events delivered across India and APAC. Sectors: HR tech, fintech, retail, FMCG.
"""
        result = synthesise(SEQUENCE_PROMPT, user_data, max_tokens=1000)
        sequence = None
        if result:
            sequence = safe_json_parse(result)

        if not sequence:
            sequence = {
                "touch_1": {
                    "channel": "email",
                    "subject_line": f"{self.company_name} x StepOneXP",
                    "message": f"Hi {structured['contact_name'].split()[0]},\n\n{structured.get('events_gap','')}\n\nWe've delivered 350+ events across India and APAC. Worth a 20-minute call?\n\nBest,\nStepOneXP",
                    "send_day": 1,
                }
            }

        return {
            "primary_contact": {
                "name":     structured["contact_name"],
                "title":    structured["contact_role"],
                "email":    structured["contact_email"],
                "linkedin": structured["contact_linkedin"],
            },
            "outreach_sequence": sequence,
            "all_contacts":      structured.get("all_contacts", []),
            "personalisation_variables_used": {
                "signal":      structured.get("recent_signal"),
                "gap":         structured.get("events_gap"),
                "hook":        structured.get("personalisation_hook"),
                "watchout":    structured.get("watchout_verdict"),
                "pitch_angle": structured.get("pitch_angle"),
            },
        }
