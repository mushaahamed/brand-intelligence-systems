"""
Pipeline 11 — Personalised Outreach (Human-Grade, GPT-4o)
===========================================================
Compiles ALL 10 pipeline outputs into rich intel, then generates a
4-touch outreach sequence that reads like a person who did 2 hours
of research — not a template.

Touch structure:
  Touch 1 (Day 1)  — Email. 3-4 sentences. Specific signal. Soft CTA.
  Touch 2 (Day 3)  — LinkedIn. <180 chars. Reference email. One question.
  Touch 3 (Day 8)  — Email. Competitor angle — name them, what they're doing.
  Touch 4 (Day 15) — Email. Short close. No pressure.

Uses GPT-4o for human-quality prose.
"""
import json, structlog
from pipelines.base import BasePipeline
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse
from config.settings import OPENAI_MODEL_FULL

log = structlog.get_logger()
PIPELINE_ID = "p11_outreach"

SYSTEM_PROMPT = """You are a senior outreach specialist at StepOneXP, an experiential marketing agency in India (350+ events, FMCG · D2C · fintech · retail).

You write cold outreach that reads like it came from a person who spent 2 hours researching this exact brand — not a template generator.

ABSOLUTE RULES:
1. Touch 1 = MAXIMUM 4 sentences. Every word earns its place.
2. NEVER open with: "I hope this finds you well", "I wanted to reach out", "I came across your profile", "I noticed", "As a fellow"
3. NEVER use: leverage, unlock, seamless, game-changer, revolutionize, empower, synergy, holistic, cutting-edge, innovative, impactful
4. ALWAYS reference the contact's actual title and real company data from the context
5. Touch 3 MUST name a specific competitor and what they're actively doing in experiential
6. Tone = peer-to-peer, direct, confident. Not salesy. Not sycophantic.
7. If watchout_verdict is AMBER, soften slightly. If RED, don't pitch hard.

Return ONLY valid JSON — no preamble, no explanation:
{
  "touch_1": {
    "channel": "email",
    "subject_line": "6-9 words. Specific to their situation. NOT generic.",
    "message": "3-4 sentences. Sentence 1: their specific signal (a real campaign, a gap, a competitor move). Sentence 2: what StepOneXP has done at similar scale. Sentence 3: single direct question as CTA. Sign off: just your first name.",
    "send_day": 1
  },
  "touch_2": {
    "channel": "linkedin",
    "message": "Under 180 chars. Reference that you emailed. Ask one specific question. Sound human.",
    "send_day": 3
  },
  "touch_3": {
    "channel": "email",
    "subject_line": "Names a competitor OR references a specific gap",
    "message": "4-5 sentences. Open with competitor intel — name the brand, say what they're doing in experiential specifically. Bridge to the gap this brand has. One proof point or case study reference from StepOneXP. CTA — specific ask.",
    "send_day": 8
  },
  "touch_4": {
    "channel": "email",
    "subject_line": "Last one from me",
    "message": "2-3 sentences. Acknowledge you've been persistent. Offer something concrete (a deck, a 30-min call, a relevant case study PDF). No pressure. Human close.",
    "send_day": 15
  }
}"""


class OutreachPipeline(BasePipeline):
    pipeline_id   = PIPELINE_ID
    pipeline_name = "Personalised Outreach"

    def __init__(self, company_name, company_url, category, all_pipeline_outputs=None):
        super().__init__(company_name, company_url, category)
        self.all_outputs = all_pipeline_outputs or {}

    def fetch(self) -> dict:
        return {"pipeline_outputs": self.all_outputs}

    def extract(self, raw: dict) -> dict:
        outputs = raw.get("pipeline_outputs", {})

        def _out(key): return outputs.get(key, {}).get("output", {})

        p01 = _out("p01_company_overview")
        p04 = _out("p04_competitor_mapping")
        p05 = _out("p05_brand_activity")
        p06 = _out("p06_experiential_footprint")
        p07 = _out("p07_reputation_research")
        p08 = _out("p08_strategic_watchouts")
        p09 = _out("p09_decision_makers")
        p10 = _out("p10_contact_intelligence")

        # ── Primary contact ───────────────────────────────────────────
        contacts  = p10.get("contacts", [])
        committee = p09.get("buying_committee", [])
        primary_c = next((c for c in contacts  if c.get("outreach_priority") == "PRIMARY"), contacts[0]  if contacts  else {})
        primary_p = next((c for c in committee if c.get("outreach_priority") == "PRIMARY"), committee[0] if committee else {})

        contact_name  = primary_c.get("name")  or primary_p.get("name",  "there")
        contact_title = primary_c.get("title") or primary_p.get("title", "")
        contact_email = primary_c.get("email")
        contact_li    = primary_c.get("linkedin_url") or primary_p.get("linkedin_url")
        contact_hook  = primary_p.get("personalisation_hook", "")
        li_activity   = primary_p.get("linkedin_activity", "UNKNOWN")

        # ── Competitor intel ──────────────────────────────────────────
        comp_intel = []
        for c in (p04.get("competitors") or [])[:3]:
            comp_intel.append({
                "name":            c.get("name"),
                "positioning":     c.get("brand_positioning", ""),
                "events_activity": c.get("events_activity", "UNKNOWN"),
                "events_desc":     c.get("events_description", ""),
                "gap":             c.get("experiential_gap", ""),
            })

        # ── Campaign intel ────────────────────────────────────────────
        campaigns    = p05.get("recent_campaigns", [])
        last_campaign = campaigns[0] if campaigns else None

        # ── Events intel ──────────────────────────────────────────────
        events_done    = p06.get("events_timeline",  [])
        events_missing = p06.get("formats_missing",  [])
        maturity       = p06.get("experiential_maturity_score", 0)
        pitch_angle    = p06.get("pitch_angle",           "")
        opening_line   = p06.get("opening_line_for_pitch","")

        return {
            "company_name":      self.company_name,
            "category":          self.category,
            "contact_name":      contact_name,
            "contact_title":     contact_title,
            "contact_email":     contact_email,
            "contact_linkedin":  contact_li,
            "contact_hook":      contact_hook,
            "li_activity":       li_activity,
            # brand
            "business_model":    p01.get("business_model", ""),
            "icp_score":         p01.get("icp_fit_score"),
            "readiness":         p01.get("experiential_readiness", ""),
            "recommended_svc":   p01.get("recommended_service", ""),
            # campaigns
            "last_campaign":     last_campaign,
            "all_campaigns":     campaigns[:3],
            "upcoming_window":   p05.get("upcoming_opportunity_window", ""),
            # events
            "events_done":       events_done[:3],
            "events_missing":    events_missing[:3],
            "maturity_score":    maturity,
            "pitch_angle":       pitch_angle,
            "opening_line":      opening_line,
            # competitors
            "competitors":       comp_intel,
            "comp_urgency":      p04.get("competitive_urgency", "NO"),
            "white_space":       p04.get("experiential_white_space", ""),
            "comp_pitch_angle":  p04.get("recommended_pitch_angle", ""),
            # risk
            "watchout":          p08.get("overall_verdict", "GREEN"),
            "pitch_tone":        p08.get("pitch_tone_adjustment", ""),
            "timing":            p08.get("timing_recommendation", "PURSUE NOW"),
            # reputation
            "reputation":        p07.get("reputation_label", ""),
            "rep_opportunity":   p07.get("reputation_opportunity", ""),
            # contacts list
            "all_contacts":      contacts,
        }

    def synthesise(self, structured: dict) -> dict:
        # ── Format competitor block ───────────────────────────────────
        comp_lines = ""
        for c in structured.get("competitors", []):
            if c.get("name"):
                comp_lines += (
                    f"\n  • {c['name']}: {c.get('positioning','')}"
                    f" | Events: {c.get('events_activity','?')} — {c.get('events_desc','')}"
                    f" | Gap: {c.get('gap','')}"
                )

        # ── Format campaign block ─────────────────────────────────────
        lc = structured.get("last_campaign") or {}
        campaign_line = ""
        if lc.get("name"):
            campaign_line = (
                f"{lc['name']} ({lc.get('date','')}) via {lc.get('channel','')} — "
                f"{lc.get('description','')}"
            )

        # ── Format events block ───────────────────────────────────────
        events_done = structured.get("events_done", [])
        events_text = ""
        if events_done:
            events_text = "; ".join(
                f"{e.get('event_name','?')} ({e.get('date','')} · {e.get('brand_role','?')})"
                for e in events_done
            )
        else:
            events_text = "No confirmed events found — potential first-mover opportunity"

        user_data = f"""CONTACT: {structured['contact_name']} — {structured['contact_title']} at {structured['company_name']}
LinkedIn activity: {structured.get('li_activity','UNKNOWN')}
Personalisation hook: {structured.get('contact_hook','')}

COMPANY:
  Name: {structured['company_name']} | Category: {structured['category']}
  Model: {structured.get('business_model','')} | ICP Score: {structured.get('icp_score','?')}/100
  Readiness: {structured.get('readiness','')} | Recommended service: {structured.get('recommended_svc','')}

BRAND ACTIVITY (recent):
  Last campaign: {campaign_line or 'None found'}
  Upcoming window: {structured.get('upcoming_window','Unknown')}

EXPERIENTIAL FOOTPRINT:
  Maturity: {structured.get('maturity_score','?')}/5
  Events confirmed: {events_text}
  Missing formats: {', '.join(structured.get('events_missing',[])) or 'Unknown'}
  Pitch angle: {structured.get('pitch_angle','')}
  Opening line hint: {structured.get('opening_line','')}

COMPETITOR INTELLIGENCE:{comp_lines or ' No competitor data'}
  Competitive urgency: {structured.get('comp_urgency','NO')}
  White space: {structured.get('white_space','')}
  Comp pitch angle: {structured.get('comp_pitch_angle','')}

TONE CALIBRATION:
  Watchout verdict: {structured.get('watchout','GREEN')} (GREEN=confident, AMBER=measured, RED=do not pitch hard)
  Pitch tone guidance: {structured.get('pitch_tone','')}
  Timing: {structured.get('timing','PURSUE NOW')}

REPUTATION:
  Label: {structured.get('reputation','')}
  Opportunity: {structured.get('rep_opportunity','')}

STEPONEXP PROOF:
  350+ events · India & APAC · FMCG, D2C, fintech, retail, HR tech
  Known for: consumer pop-ups, city roadshows, product launches, brand days, IPL/cricket activations

Write the 4-touch sequence. Reference EXACT competitor names, campaign names, and the person's title.
Make Touch 3 sting — name the competitor, say what they're doing, and make the reader feel the gap.
"""
        result = synthesise(SYSTEM_PROMPT, user_data, model=OPENAI_MODEL_FULL, max_tokens=1800)

        sequence = None
        if result:
            sequence = safe_json_parse(result)

        if not sequence:
            # Fallback — still better than nothing
            first = structured['contact_name'].split()[0]
            comp1 = (structured.get("competitors") or [{}])[0].get("name", "a key competitor")
            camp  = (structured.get("last_campaign") or {}).get("name", "your recent campaign")
            sequence = {
                "touch_1": {
                    "channel": "email",
                    "subject_line": f"Experiential gap — {self.company_name}",
                    "message": (
                        f"Hi {first},\n\n"
                        f"{camp} caught my attention. "
                        f"Given {self.company_name}'s scale in {self.category}, the experiential layer is the obvious next unlock — "
                        f"and it's one most D2C brands in your space haven't fully figured out yet.\n\n"
                        f"We've run 350+ activations across India for brands at exactly this stage. Worth 20 minutes?\n\n"
                        f"Thanks"
                    ),
                    "send_day": 1,
                },
                "touch_2": {
                    "channel": "linkedin",
                    "message": (
                        f"Hi {first}, dropped you an email about experiential for {self.company_name}. "
                        f"Curious — is consumer activation on your roadmap for this year?"
                    ),
                    "send_day": 3,
                },
                "touch_3": {
                    "channel": "email",
                    "subject_line": f"What {comp1} is doing in experiential",
                    "message": (
                        f"Hi {first},\n\n"
                        f"{comp1} has been running consumer activations and pop-ups actively this year — "
                        f"they're building the kind of direct consumer touchpoints that digital alone can't replicate.\n\n"
                        f"{self.company_name} has the brand equity to do this better. "
                        f"We did a 12-city roadshow for a D2C brand at similar scale — 3× higher conversion vs paid digital.\n\n"
                        f"Happy to share the brief if it's useful."
                    ),
                    "send_day": 8,
                },
                "touch_4": {
                    "channel": "email",
                    "subject_line": "Last one from me",
                    "message": (
                        f"Hi {first},\n\n"
                        f"I know I've been persistent — I'll leave it here. "
                        f"If activations ever make it onto {self.company_name}'s agenda, we'd love to be in that conversation.\n\n"
                        f"Take care."
                    ),
                    "send_day": 15,
                },
            }

        return {
            "primary_contact": {
                "name":     structured["contact_name"],
                "title":    structured.get("contact_title"),
                "email":    structured.get("contact_email"),
                "linkedin": structured.get("contact_linkedin"),
            },
            "outreach_sequence":  sequence,
            "all_contacts":       structured.get("all_contacts", []),
            "competitor_intel_used": structured.get("competitors", []),
            "personalisation_variables_used": {
                "signal":      (structured.get("last_campaign") or {}).get("name"),
                "gap":         structured.get("pitch_angle"),
                "hook":        structured.get("contact_hook"),
                "watchout":    structured.get("watchout"),
                "competitors": [c.get("name") for c in structured.get("competitors", []) if c.get("name")],
                "events_done": len(structured.get("events_done", [])),
                "maturity":    structured.get("maturity_score"),
            },
        }
