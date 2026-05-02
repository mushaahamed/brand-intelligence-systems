"""
Pipeline 11 — Personalised Outreach (Human-Grade, GPT-4o)
===========================================================
Compiles ALL 10 pipeline outputs into rich intel, then generates a
4-touch outreach sequence PER CONTACT in the buying committee — each
one uniquely personalised to that person's role, seniority, and hook.

Touch structure:
  Touch 1 (Day 1)  — Email. 3-4 sentences. Specific signal. Soft CTA.
  Touch 2 (Day 3)  — LinkedIn. <180 chars. Reference email. One question.
  Touch 3 (Day 8)  — Email. Competitor angle — name them, what they're doing.
  Touch 4 (Day 15) — Email. Short close. No pressure.

Uses GPT-4o (one call per contact) for human-quality, role-specific prose.
"""
import json, structlog
from pipelines.base import BasePipeline
from utils.claude_client import synthesise
from utils.helpers import safe_json_parse
from config.settings import OPENAI_MODEL_FULL

log = structlog.get_logger()
PIPELINE_ID = "p11_outreach"

SYSTEM_PROMPT = """You are a senior outreach specialist at StepOneXP, an experiential marketing agency in India (350+ events, FMCG · D2C · fintech · retail).

You write cold outreach that reads like it came from a person who spent 2 hours researching this exact brand AND this specific individual — not a template generator.

ROLE-BASED FRAMING (critical — apply based on the contact's role_type and title):
- CEO / Founder (DECISION_MAKER): Lead with ROI, competitive threat, and market timing. They care about winning category share.
- CMO / VP Marketing (DECISION_MAKER or INFLUENCER): Lead with strategic brand-building and competitive differentiation. They care about earned attention and brand equity.
- Brand Manager / Sr. Brand Manager (INFLUENCER or CHAMPION): Lead with tactical execution, formats that work at their scale, and proof of results. They care about execution quality and budget efficiency.
- Growth / Performance Manager (INFLUENCER): Lead with conversion data, cost-per-acquisition comparisons, and measurable outcomes. They care about CAC and attribution.
- Category Manager (INFLUENCER or CHAMPION): Lead with channel-specific activation and in-store/on-ground presence. They care about visibility at point-of-decision.
- Any other title: Use the role_type to infer framing — DECISION_MAKER = strategic, INFLUENCER = functional, CHAMPION = executional.

ABSOLUTE RULES:
1. Touch 1 = MAXIMUM 4 sentences. Every word earns its place.
2. NEVER open with: "I hope this finds you well", "I wanted to reach out", "I came across your profile", "I noticed", "As a fellow"
3. NEVER use: leverage, unlock, seamless, game-changer, revolutionize, empower, synergy, holistic, cutting-edge, innovative, impactful
4. ALWAYS reference the contact's actual title, their real company data, and their personalisation hook
5. Touch 3 MUST name a specific competitor and what they're actively doing in experiential
6. Tone = peer-to-peer, direct, confident. Not salesy. Not sycophantic.
7. If watchout_verdict is AMBER, soften slightly. If RED, don't pitch hard.
8. Each touch must feel like it was written FOR this specific person — their pain, their angle, their stakes.

Return ONLY valid JSON — no preamble, no explanation:
{
  "touch_1": {
    "channel": "email",
    "subject_line": "6-9 words. Specific to their situation. NOT generic.",
    "message": "3-4 sentences. Sentence 1: their specific signal (a real campaign, a gap, a competitor move — framed for their role). Sentence 2: what StepOneXP has done at similar scale, stated from their angle. Sentence 3: single direct question as CTA. Sign off: just your first name.",
    "send_day": 1
  },
  "touch_2": {
    "channel": "linkedin",
    "message": "Under 180 chars. Reference that you emailed. Ask one specific question relevant to their role. Sound human.",
    "send_day": 3
  },
  "touch_3": {
    "channel": "email",
    "subject_line": "Names a competitor OR references a specific gap",
    "message": "4-5 sentences. Open with competitor intel — name the brand, say what they're doing in experiential specifically. Bridge to the gap this brand has, framed for this person's role (CMO = brand equity gap, brand manager = execution gap, CEO = revenue gap). One proof point or case study reference from StepOneXP. CTA — specific ask.",
    "send_day": 8
  },
  "touch_4": {
    "channel": "email",
    "subject_line": "Last one from me",
    "message": "2-3 sentences. Acknowledge you've been persistent. Offer something concrete (a deck, a 30-min call, a relevant case study PDF). No pressure. Human close.",
    "send_day": 15
  }
}"""


def _build_fallback_sequence(first_name: str, company_name: str, category: str,
                              comp_name: str, campaign_name: str) -> dict:
    """Minimal fallback sequence when GPT-4o call fails."""
    return {
        "touch_1": {
            "channel": "email",
            "subject_line": f"Experiential gap — {company_name}",
            "message": (
                f"Hi {first_name},\n\n"
                f"{campaign_name} caught my attention. "
                f"Given {company_name}'s scale in {category}, the experiential layer is the obvious next move — "
                f"and most brands at your stage haven't fully figured it out yet.\n\n"
                f"We've run 350+ activations across India for brands at exactly this stage. Worth 20 minutes?\n\n"
                f"Thanks"
            ),
            "send_day": 1,
        },
        "touch_2": {
            "channel": "linkedin",
            "message": (
                f"Hi {first_name}, dropped you an email about experiential for {company_name}. "
                f"Curious — is consumer activation on your roadmap this year?"
            ),
            "send_day": 3,
        },
        "touch_3": {
            "channel": "email",
            "subject_line": f"What {comp_name} is doing in experiential",
            "message": (
                f"Hi {first_name},\n\n"
                f"{comp_name} has been running consumer activations and pop-ups actively this year — "
                f"building the kind of direct consumer touchpoints that digital alone can't replicate.\n\n"
                f"{company_name} has the brand equity to do this better. "
                f"We did a 12-city roadshow for a D2C brand at similar scale — 3× higher conversion vs paid digital.\n\n"
                f"Happy to share the brief if it's useful."
            ),
            "send_day": 8,
        },
        "touch_4": {
            "channel": "email",
            "subject_line": "Last one from me",
            "message": (
                f"Hi {first_name},\n\n"
                f"I know I've been persistent — I'll leave it here. "
                f"If activations ever make it onto {company_name}'s agenda, we'd love to be in that conversation.\n\n"
                f"Take care."
            ),
            "send_day": 15,
        },
    }


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

        # ── Buying committee (p09) + contact details (p10) ──────────────
        contacts_p10  = p10.get("contacts", [])
        committee_p09 = p09.get("buying_committee", [])

        # Build a lookup from p10: name (lowercased) -> contact record
        p10_by_name = {c.get("name", "").lower(): c for c in contacts_p10 if c.get("name")}

        # Merge committee members with their p10 contact details (email/linkedin)
        merged_contacts = []
        for person in committee_p09[:4]:  # max 4
            name = person.get("name", "")
            p10_match = p10_by_name.get(name.lower(), {})
            email   = p10_match.get("email") or person.get("email")
            linkedin = (p10_match.get("linkedin_url") or person.get("linkedin_url")
                        or p10_match.get("linkedin") or person.get("linkedin"))
            # Skip contacts with no reachable channel
            if not email and not linkedin:
                continue
            merged_contacts.append({
                "name":                    name,
                "title":                   person.get("title", ""),
                "email":                   email,
                "linkedin":                linkedin,
                "role_type":               person.get("role_type", "INFLUENCER"),
                "outreach_priority":       person.get("outreach_priority", "SECONDARY"),
                "decision_relevance_score": person.get("decision_relevance_score", 50),
                "personalisation_hook":    person.get("personalisation_hook", ""),
                "linkedin_activity":       person.get("linkedin_activity", "UNKNOWN"),
            })

        # Fallback: if buying committee is empty, use p10 contacts directly
        if not merged_contacts:
            for c in contacts_p10[:4]:
                email    = c.get("email")
                linkedin = c.get("linkedin_url") or c.get("linkedin")
                if not email and not linkedin:
                    continue
                merged_contacts.append({
                    "name":                    c.get("name", ""),
                    "title":                   c.get("title", ""),
                    "email":                   email,
                    "linkedin":                linkedin,
                    "role_type":               c.get("role_type", "INFLUENCER"),
                    "outreach_priority":       c.get("outreach_priority", "SECONDARY"),
                    "decision_relevance_score": c.get("decision_relevance_score", 50),
                    "personalisation_hook":    c.get("personalisation_hook", ""),
                    "linkedin_activity":       c.get("linkedin_activity", "UNKNOWN"),
                })

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
        campaigns     = p05.get("recent_campaigns", [])
        last_campaign = campaigns[0] if campaigns else None

        # ── Events intel ──────────────────────────────────────────────
        events_done    = p06.get("events_timeline",  [])
        events_missing = p06.get("formats_missing",  [])
        maturity       = p06.get("experiential_maturity_score", 0)
        pitch_angle    = p06.get("pitch_angle",           "")
        opening_line   = p06.get("opening_line_for_pitch","")

        return {
            "company_name":    self.company_name,
            "category":        self.category,
            # Merged/enriched contacts list (primary source of truth for p11)
            "merged_contacts": merged_contacts,
            # Brand context
            "business_model":  p01.get("business_model", ""),
            "icp_score":       p01.get("icp_fit_score"),
            "readiness":       p01.get("experiential_readiness", ""),
            "recommended_svc": p01.get("recommended_service", ""),
            # Campaigns
            "last_campaign":   last_campaign,
            "all_campaigns":   campaigns[:3],
            "upcoming_window": p05.get("upcoming_opportunity_window", ""),
            # Events
            "events_done":     events_done[:3],
            "events_missing":  events_missing[:3],
            "maturity_score":  maturity,
            "pitch_angle":     pitch_angle,
            "opening_line":    opening_line,
            # Competitors
            "competitors":     comp_intel,
            "comp_urgency":    p04.get("competitive_urgency", "NO"),
            "white_space":     p04.get("experiential_white_space", ""),
            "comp_pitch_angle": p04.get("recommended_pitch_angle", ""),
            # Risk
            "watchout":        p08.get("overall_verdict", "GREEN"),
            "pitch_tone":      p08.get("pitch_tone_adjustment", ""),
            "timing":          p08.get("timing_recommendation", "PURSUE NOW"),
            # Reputation
            "reputation":      p07.get("reputation_label", ""),
            "rep_opportunity": p07.get("reputation_opportunity", ""),
        }

    def _build_user_prompt(self, contact: dict, structured: dict,
                           comp_lines: str, campaign_line: str,
                           events_text: str) -> str:
        """Build the per-contact user prompt for GPT-4o."""
        # Role-specific pain point guidance
        role_type  = contact.get("role_type", "INFLUENCER")
        title      = contact.get("title", "")
        title_low  = title.lower()

        if any(t in title_low for t in ["ceo", "founder", "managing director", "md"]):
            pain_guidance = (
                "This is the CEO/Founder. Focus on: market share vs competitors, "
                "ROI of experiential vs digital spend, and the risk of competitors owning "
                "consumer touchpoints they don't. Frame everything in terms of winning the category."
            )
        elif any(t in title_low for t in ["cmo", "chief marketing", "vp marketing", "head of marketing",
                                           "marketing director"]):
            pain_guidance = (
                "This is the CMO/VP Marketing. Focus on: brand equity, earned media, "
                "the strategic gap between their digital-heavy presence and competitors' "
                "experiential moves. Frame as a brand-building imperative, not just activation."
            )
        elif any(t in title_low for t in ["brand manager", "sr. brand", "senior brand",
                                           "brand lead", "brand head"]):
            pain_guidance = (
                "This is a Brand Manager. Focus on: tactical execution quality, formats that "
                "drive trial and repeat purchase at their category scale, budget efficiency, "
                "and how StepOneXP handles end-to-end so they don't have to manage 5 vendors."
            )
        elif any(t in title_low for t in ["growth", "performance", "acquisition", "d2c"]):
            pain_guidance = (
                "This is a Growth/Performance person. Focus on: measurable CAC from experiential "
                "vs paid digital, conversion rates from direct consumer touchpoints, "
                "attribution data from past activations."
            )
        elif any(t in title_low for t in ["category", "trade", "channel"]):
            pain_guidance = (
                "This is a Category/Trade Manager. Focus on: on-ground visibility, "
                "point-of-decision presence, and activations that drive shelf pull and "
                "retailer confidence."
            )
        elif role_type == "DECISION_MAKER":
            pain_guidance = (
                "This is a decision maker. Lead with strategic framing — competitive threat, "
                "brand equity risk, and market timing."
            )
        elif role_type == "CHAMPION":
            pain_guidance = (
                "This is a champion/internal advocate. Focus on executional proof — "
                "specific formats, timelines, and how StepOneXP makes their job easier."
            )
        else:
            pain_guidance = (
                "This is an influencer. Lead with functional outcomes relevant to their "
                "specific domain and how StepOneXP delivers measurable results."
            )

        return f"""CONTACT TO WRITE FOR:
  Name: {contact['name']}
  Title: {contact['title']}
  Role type: {contact['role_type']} | Priority: {contact['outreach_priority']}
  Decision relevance score: {contact['decision_relevance_score']}/100
  LinkedIn activity: {contact.get('linkedin_activity', 'UNKNOWN')}
  Personalisation hook: {contact.get('personalisation_hook', 'None found')}

ROLE-SPECIFIC PAIN POINT GUIDANCE:
  {pain_guidance}

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

Write the 4-touch sequence for {contact['name']} ({contact['title']}).
Frame EVERY touch through their specific role lens (see pain point guidance above).
Reference EXACT competitor names, campaign names, and this person's title.
Make Touch 3 sting — name the competitor, say what they're doing, and make THIS reader feel the gap from THEIR role's perspective.
"""

    def synthesise(self, structured: dict) -> dict:
        # ── Shared context blocks (built once, reused per contact) ────
        comp_lines = ""
        for c in structured.get("competitors", []):
            if c.get("name"):
                comp_lines += (
                    f"\n  • {c['name']}: {c.get('positioning','')}"
                    f" | Events: {c.get('events_activity','?')} — {c.get('events_desc','')}"
                    f" | Gap: {c.get('gap','')}"
                )

        lc = structured.get("last_campaign") or {}
        campaign_line = ""
        if lc.get("name"):
            campaign_line = (
                f"{lc['name']} ({lc.get('date','')}) via {lc.get('channel','')} — "
                f"{lc.get('description','')}"
            )

        events_done = structured.get("events_done", [])
        if events_done:
            events_text = "; ".join(
                f"{e.get('event_name','?')} ({e.get('date','')} · {e.get('brand_role','?')})"
                for e in events_done
            )
        else:
            events_text = "No confirmed events found — potential first-mover opportunity"

        comp_name    = (structured.get("competitors") or [{}])[0].get("name", "a key competitor")
        campaign_name = lc.get("name", "your recent campaign")

        # ── Per-contact GPT-4o loop ───────────────────────────────────
        contacts_sequences = []
        merged_contacts    = structured.get("merged_contacts", [])

        for contact in merged_contacts:
            name  = contact.get("name", "there")
            first = name.split()[0] if name else "there"

            log.info("p11_outreach.generating_sequence",
                     contact=name, title=contact.get("title",""),
                     role=contact.get("role_type","?"))

            user_prompt = self._build_user_prompt(
                contact, structured, comp_lines, campaign_line, events_text
            )

            result   = synthesise(SYSTEM_PROMPT, user_prompt,
                                  model=OPENAI_MODEL_FULL, max_tokens=1800)
            sequence = safe_json_parse(result) if result else None

            if not sequence:
                log.warning("p11_outreach.gpt_fallback", contact=name)
                sequence = _build_fallback_sequence(
                    first, structured["company_name"],
                    structured["category"], comp_name, campaign_name
                )

            # Derive role-specific pain point and signal for personalisation_vars
            hook       = contact.get("personalisation_hook", "")
            pitch_angle = structured.get("pitch_angle", "")
            watchout   = structured.get("watchout", "GREEN")
            role_type  = contact.get("role_type", "INFLUENCER")
            title_low  = contact.get("title", "").lower()

            if any(t in title_low for t in ["ceo", "founder", "md"]):
                pain_point = "Competitive market share loss if experiential gap persists"
            elif any(t in title_low for t in ["cmo", "vp marketing", "chief marketing"]):
                pain_point = "Brand equity stagnating without physical consumer touchpoints"
            elif any(t in title_low for t in ["brand manager", "brand lead"]):
                pain_point = "Execution quality and vendor fragmentation for on-ground activations"
            elif any(t in title_low for t in ["growth", "performance"]):
                pain_point = "CAC from digital channels rising — experiential not in attribution model"
            else:
                pain_point = pitch_angle or "Experiential gap vs category competitors"

            contacts_sequences.append({
                "contact": {
                    "name":                    contact["name"],
                    "title":                   contact["title"],
                    "email":                   contact.get("email"),
                    "linkedin":                contact.get("linkedin"),
                    "role_type":               contact.get("role_type", "INFLUENCER"),
                    "outreach_priority":       contact.get("outreach_priority", "SECONDARY"),
                    "decision_relevance_score": contact.get("decision_relevance_score", 50),
                    "personalisation_hook":    contact.get("personalisation_hook", ""),
                    "linkedin_activity":       contact.get("linkedin_activity", "UNKNOWN"),
                },
                "sequence": sequence,
                "personalisation_vars": {
                    "signal":          hook or campaign_name,
                    "pain_point":      pain_point,
                    "competitor_used": comp_name,
                    "watchout":        watchout,
                },
            })

        # ── Backward-compat: expose primary contact's data at top level ─
        primary_entry = next(
            (e for e in contacts_sequences
             if e["contact"].get("outreach_priority") == "PRIMARY"),
            contacts_sequences[0] if contacts_sequences else None,
        )

        primary_contact = {}
        outreach_sequence = {}
        if primary_entry:
            primary_contact   = primary_entry["contact"]
            outreach_sequence = primary_entry["sequence"]

        return {
            # New multi-contact schema
            "contacts_sequences": contacts_sequences,
            # Backward compatibility
            "primary_contact":    primary_contact,
            "outreach_sequence":  outreach_sequence,
            "competitor_intel_used": structured.get("competitors", []),
            # Legacy personalisation_variables_used kept for compatibility
            "personalisation_variables_used": {
                "signal":      lc.get("name"),
                "gap":         structured.get("pitch_angle"),
                "hook":        (primary_contact or {}).get("personalisation_hook"),
                "watchout":    structured.get("watchout"),
                "competitors": [c.get("name") for c in structured.get("competitors", []) if c.get("name")],
                "events_done": len(structured.get("events_done", [])),
                "maturity":    structured.get("maturity_score"),
            },
        }
