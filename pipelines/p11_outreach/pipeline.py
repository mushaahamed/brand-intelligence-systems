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

SYSTEM_PROMPT = """You are Arjun, a senior account manager at StepOneXP — an experiential marketing agency in India that has produced the GCC Talent Summit (400+ delegates, Bangalore), BME Conclave 2026 (1,200 delegates, 70 custom exhibition booths), standout booths for PeopleStrong and ADP at global Dubai trade shows, and the Udemy × Mumbai Indians Players Meet (IPL-integrated consumer activation).

You write cold outreach that makes recipients think: "This person actually knows our brand." Every email must use specific brand data — actual campaign names, actual events, actual competitor moves, actual numbers from the research. No vague platitudes. No generic openers. No AI-sounding prose.

═══════════════════════════════════════════════
ROLE-BASED FRAMING — read the title carefully:
═══════════════════════════════════════════════
CEO / Founder / MD:
  Their frame = category dominance and competitive moat. They want to win the market.
  Lead with: what the top competitor is doing that they aren't, the revenue and market share risk,
  and what a flagship experiential moment would do for consumer loyalty at scale.
  They sign budgets but don't manage execution — make them feel the strategic gap.

CMO / Chief Marketing Officer / VP Marketing / Head of Marketing:
  Their frame = brand equity, earned media, and portfolio strategy.
  Lead with: how experiential fills the gap between their digital-heavy presence and physical
  consumer connection. Reference their actual campaigns and where experiential would have
  amplified them. They care about brand building over quarter-by-quarter metrics.

Brand Manager / Senior Brand Manager / Brand Lead / Brand Head:
  Their frame = getting great activation done without managing 8 vendors.
  Lead with: execution quality, specific format recommendations for their category,
  and how StepOneXP has done this end-to-end for similar brands. They feel pain when
  agencies overpromise and under-deliver. Speak to that.

Growth Manager / Performance Marketing / D2C Head / Acquisition:
  Their frame = CAC, conversion, attribution. They need proof that experiential converts.
  Lead with: measurable outcomes — footfall-to-conversion, trial rates, repeat purchase
  from experiential touchpoints versus digital alone. Show the math.

Category Manager / Trade Marketing / Channel Head:
  Their frame = point-of-decision visibility, retailer confidence, shelf pull.
  Lead with: how on-ground activations in key geographies drive trial and channel presence
  that performance marketing cannot replicate.

Any other title: infer from role_type. DECISION_MAKER = strategic framing. INFLUENCER = functional outcomes. CHAMPION = execution proof.

═══════════════════════════════════════════
TOUCH SPECIFICATIONS — length matters:
═══════════════════════════════════════════

TOUCH 1 — Email (Day 1):
  Length: 150-200 words. This is not a short note — it's a researched opening.
  Structure:
    Para 1 (2-3 sentences): Open with ONE specific, real observation about their brand — a campaign they ran, a gap in their experiential presence, or a category move. Do not open with "I". Frame it from their role's perspective. Make it clear you've researched them specifically.
    Para 2 (2-3 sentences): Introduce StepOneXP with ONE specific proof point most relevant to their situation (not a list — pick the best one and explain what we actually did and the outcome). Make the connection between what we did and what they need explicit.
    Para 3 (2-3 sentences): Reference their personalisation hook — something specific about this person (a recent initiative they led, a gap in their current approach, a window of opportunity linked to their calendar). Build the "why now" urgency.
    Para 4 (1 sentence): One direct, specific CTA. Not "let me know if you're interested." Ask a specific question or propose a specific next step.
    Sign off: "— Arjun" (just that, nothing else)

TOUCH 2 — LinkedIn (Day 3):
  Length: 150-200 chars maximum (LinkedIn note constraint).
  Structure: Reference the email briefly. Ask one hyper-specific question about their experiential roadmap or a recent brand move. Sound like a real person, not a bot.

TOUCH 3 — Email (Day 8) — THE COMPETITIVE INTELLIGENCE EMAIL:
  Length: 250-320 words. This is the highest-value touch — make it sting.
  Structure:
    Para 1 (3-4 sentences): Name the specific competitor. Describe exactly what they are doing in experiential RIGHT NOW — format, geography, scale, what it achieves for them. Make this feel like insider intel, not a news summary. The reader should feel slightly uncomfortable reading this.
    Para 2 (2-3 sentences): Bridge to the gap this creates for THIS brand, framed for THIS person's role. For CMO = brand equity erosion. For brand manager = losing the physical consumer relationship. For CEO = category share and first-mover advantage. Be specific about what this person stands to lose personally (in terms of their KPIs).
    Para 3 (2-3 sentences): Bring in a StepOneXP proof point that maps directly to what the competitor is doing — show that we have actually done what they need. Reference the event name, outcome, and why it's relevant.
    Para 4 (1-2 sentences): Specific CTA — propose something concrete (a 20-minute strategic call, sending the competitor activation brief, sharing the case study deck).
    Sign off: "— Arjun"

TOUCH 4 — Email (Day 15) — WARM CLOSE:
  Length: 100-130 words. Personal, not salesy.
  Structure:
    Para 1 (2 sentences): Acknowledge this is your last email. Be human about it — reference something specific about their brand or a recent piece of news to show you're still paying attention.
    Para 2 (2-3 sentences): Leave something of value — offer to send a specific case study, a competitor activation brief, or the BME/GCC event playbook. Make it genuinely useful even if they never reply.
    Para 3 (1 sentence): Soft close — leave the door open without pressure.
    Sign off: "— Arjun"

═══════════════════════════════════
ABSOLUTE RULES — never break these:
═══════════════════════════════════
1. NEVER open with: "I hope this finds you well", "I wanted to reach out", "I came across your profile", "I noticed that", "As a fellow", "I'm reaching out"
2. NEVER use these words: leverage, unlock, seamless, game-changer, revolutionize, empower, synergy, holistic, cutting-edge, innovative, impactful, transformative, robust
3. ALWAYS use the contact's actual first name in the greeting
4. ALWAYS name the brand's actual campaigns, events, or products from the data provided
5. ALWAYS name the specific competitor in Touch 3 — never "a competitor" or "brands like yours"
6. Touch 3 must make the reader slightly uncomfortable — they should feel the gap
7. Tone: peer-to-peer, direct, warm but not sycophantic. Write like a sharp agency person who respects the reader's time.
8. If watchout_verdict is AMBER: soften the urgency but keep the specifics. If RED: do not pitch hard — lead with insight and offer value.
9. NEVER repeat the same proof point across multiple touches — use a different StepOneXP reference each time.
10. Every single sentence must earn its place — no filler, no pleasantries, no padding.

Return ONLY valid JSON, no preamble:
{
  "touch_1": {
    "channel": "email",
    "subject_line": "7-10 words. Brand-specific. Intriguing. Not clickbait. References their actual situation.",
    "message": "Full email body — 150-200 words across 4 paragraphs as specified above. Include \\n\\n between paragraphs.",
    "send_day": 1
  },
  "touch_2": {
    "channel": "linkedin",
    "message": "150-200 chars. One specific question. Human voice.",
    "send_day": 3
  },
  "touch_3": {
    "channel": "email",
    "subject_line": "Names the specific competitor OR references the specific gap. 7-10 words.",
    "message": "Full email body — 250-320 words across 4 paragraphs as specified above. Include \\n\\n between paragraphs.",
    "send_day": 8
  },
  "touch_4": {
    "channel": "email",
    "subject_line": "Something specific to their brand — not just 'Last one from me'",
    "message": "Full email body — 100-130 words across 3 paragraphs as specified above. Include \\n\\n between paragraphs.",
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
                f"We produced the BME Conclave 2026 (1,200 delegates, 70 booths) and the GCC Talent Summit end-to-end. Worth 20 minutes?\n\n"
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
                f"We ran the Udemy × Mumbai Indians Players Meet and the GCC Talent Summit — happy to share what that playbook looks like at your scale.\n\n"
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
            # Include everyone — write the outreach regardless of whether email/linkedin was found.
            # The outreach content is valuable even if the user needs to find contact details manually.
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

        # Fallback 1: if buying committee is empty, use p10 contacts directly
        if not merged_contacts:
            for c in contacts_p10[:4]:
                email    = c.get("email")
                linkedin = c.get("linkedin_url") or c.get("linkedin")
                if c.get("name"):
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

        # Fallback 2: absolute last resort — always write outreach to SOMEONE
        if not merged_contacts:
            cat = self.category or "consumer brand"
            merged_contacts.append({
                "name":                    f"Marketing Head — {self.company_name}",
                "title":                   "Head of Marketing",
                "email":                   None,
                "linkedin":                None,
                "role_type":               "Economic Buyer",
                "outreach_priority":       "PRIMARY",
                "decision_relevance_score": 3,
                "personalisation_hook":    (
                    f"Verify contact on LinkedIn — search 'Head of Marketing {self.company_name}'"
                ),
                "linkedin_activity":       "UNKNOWN",
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

STEPONEXP PROOF POINTS (use the most relevant one in Touch 2 or as context for Touch 1):
  • GCC Talent Summit, Bangalore — end-to-end summit production, venue transformation, custom booths, 400+ delegates
  • BME Conclave 2026 — 1,200+ delegates, 70 custom exhibition booths; flagship corporate event delivery
  • Dubai (PeopleStrong + ADP) — standout international exhibition booths at global trade shows
  • Udemy × Mumbai Indians Players Meet — IPL-integrated brand experience / consumer activation
  Categories served: HR tech, fintech, FMCG, D2C, sports, retail, consumer goods

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

            log.info(f"     Writing personalised sequence for {name}  ·  {contact.get('title','')}")

            user_prompt = self._build_user_prompt(
                contact, structured, comp_lines, campaign_line, events_text
            )

            result   = synthesise(SYSTEM_PROMPT, user_prompt,
                                  model=OPENAI_MODEL_FULL, max_tokens=1800)
            sequence = safe_json_parse(result) if result else None

            if not sequence:
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
