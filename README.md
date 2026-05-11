# BrandScope — Brand Intelligence & Outreach Automation

**BrandScope** is a production-grade brand research and outreach automation system built for **StepOneXP**, an experiential marketing agency. It takes three inputs — a company name, website URL, and a one-line category description — and produces a complete intelligence dossier with personalised, multi-touch outreach sequences for every key decision-maker at the target company.

The system runs 12 sequential pipelines, each enforcing a strict three-layer architecture: real data is fetched first, then structured, then reasoned over by an LLM. No output is ever generated from a model call alone — every insight is grounded in scraped, retrieved, or verified data.

---

## What It Produces

Given a single company as input, BrandScope outputs:

- An **ICP fit score** (0–100) measuring alignment with StepOneXP's ideal client profile
- A **brand identity profile** with hex colors extracted from CSS files, inline style blocks, and logo images — five-layer extraction with third-party color filtering
- A **market position report** with sentiment scoring, share-of-voice assessment, and perception gap analysis
- A **competitor map** with 4–6 direct competitors, their experiential activity levels, positioning, and identified white space
- A **campaign activity timeline** with budget signal and upcoming opportunity windows
- A complete **experiential footprint** — every event, sponsorship, activation, and brand presence mapped across formats, geographies, and scales
- An **authentic reputation score** sourced from Reddit discussions, review platforms, and community signals
- A **strategic watchout verdict** (GREEN / AMBER / RED) based on financial, leadership, and PR risk signals
- A **buying committee** with named individuals, LinkedIn profiles, LinkedIn activity levels, and personalisation hooks
- **Email addresses** for each committee member — verified via Hunter.io where possible, pattern-inferred from domain structure where not
- **4-touch outreach sequences** written per contact, per role, referencing actual competitor names, campaign signals, and experiential gaps
- **Engagement tracking infrastructure** with scoring pixels, click-redirect links, and per-contact dashboards

All 12 pipeline outputs are persisted to disk as a single structured JSON report.

---

## Architecture

### Execution Model

Pipelines P01 through P09 run in parallel using a `ThreadPoolExecutor` with 4 workers. After all nine complete, P10 through P12 run sequentially because each depends on the previous stage's output:

```
Phase 1 (parallel, 4 workers)
  P01  P02  P03  P04  P05  P06  P07  P08  P09
   └──────────────────────────────────────┘
              ↓  (all complete)
Phase 2 (sequential)
  P09 output → P10 (contact enrichment)
  P10 output → P11 (outreach generation, receives all P01-P10)
  P11 output → P12 (tracking setup)
```

### The Three-Layer Contract

Every pipeline inherits from `BasePipeline` (an abstract base class) and must implement exactly three methods. The `.run()` method enforces this order and cannot be bypassed:

```
Layer 1 — fetch()
  Pull raw data from Apify actors, direct HTTP crawls, Hunter.io,
  or Reddit. No LLM is called here. Raw data is stored as-is.

Layer 2 — extract()
  A Python parser transforms the raw response into a clean, typed
  structured dict. Fields are normalised, truncated, and filtered.
  Still no LLM.

Layer 3 — synthesise()
  The structured dict is formatted into a prompt and sent to an LLM.
  The model returns a defined JSON schema. The output is parsed and
  validated before being returned.
```

### System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                        │
│  POST /analyse  →  background task  →  12 pipelines      │
│  GET  /status/{job_id}      (1-second polling)           │
│  GET  /report/{run_id}      (full JSON report)           │
│  GET  /reports              (list all saved reports)     │
│  GET  /debug/{job_id}       (full job state + traceback) │
│  GET  /track/open/{id}      (1×1 tracking pixel GIF)     │
│  GET  /track/click/{id}/{touch}  (scored redirect)       │
│  POST /track/event          (LinkedIn/reply/meeting log) │
│  GET  /health               (liveness check)             │
│  GET  /config/check         (API key validation)         │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│              orchestrator.py                             │
│  ThreadPoolExecutor(4) → P01-P09 parallel               │
│  Sequential: P10 → P11 → P12                            │
│  progress_cb + log_cb → live terminal stream            │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│          BasePipeline ABC  (pipelines/base.py)          │
│   fetch()  →  extract()  →  synthesise()  →  dict       │
└─────────────────────────────────────────────────────────┘
```

---

## The 12 Pipelines

---

### P01 — Company Overview

**Signal sources:**
- Direct HTTP crawl of up to 4 pages, prioritising `/about`, `/team`, `/investor`, `/press`, `/story`
- Two parallel Google searches via Apify: one for funding / headcount / founding signals, one for LinkedIn and investor information

**Fetch:** Crawls up to 4 website pages. Runs two parallel Google searches for funding, team size, and news signals. Returns raw HTML text and search snippets.

**Extract:** Prioritises about/team/investor pages. Assembles up to 6 text chunks (800 chars each). Collects up to 10 news snippets with titles and descriptions.

**Synthesise:** Returns a structured company overview with ICP scoring.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `business_model` | string | B2C / B2B / B2B2C / D2C / Marketplace / SaaS |
| `industry_vertical` | string | Category as described (e.g. "D2C skincare") |
| `founding_year` | string | Year founded if found |
| `employee_count_range` | string | e.g. "201–500" |
| `funding_status` | string | Bootstrapped / Seed / Series A / Series B+ / Listed / PE-backed / Unknown |
| `revenue_range` | string | Estimated annual revenue range if found |
| `hq_city` | string | Primary office city |
| `geography` | string | Operating geographies |
| `company_narrative` | string | 2–3 sentence summary of what the company does and why |
| `key_facts` | array | Up to 5 specific facts: founding year, notable investors, user base, awards |
| `icp_fit_score` | integer | 0–100 composite score (see scoring table below) |
| `experiential_readiness` | string | LOW / MEDIUM / HIGH — derived from ICP score |
| `recommended_service` | string | Which StepOneXP service line to pitch |
| `sources_used` | array | URLs and search queries that produced the data |

**ICP Score calculation (four 25-point signals):**

| Signal | Points | Logic |
|--------|--------|-------|
| B2C / D2C / consumer-facing business model | +25 | Only consumer brands benefit from experiential |
| 200+ employees | +25 | Indicates marketing budget and org structure to run events |
| VC-backed, listed, or Series A+ | +25 | Budget signal — funded companies invest in brand |
| India operations confirmed | +25 | StepOneXP operates in India |

Score → Readiness: 0–39 = LOW, 40–69 = MEDIUM, 70–100 = HIGH

**Powers:** P11 (ICP score, readiness, and recommended service go into outreach personalisation)

---

### P02 — Brand Identity

**Signal sources:**
- Direct HTTP request to homepage (full HTML)
- Up to 6 linked CSS stylesheets fetched and parsed
- Inline `<style>` blocks extracted from HTML (critical for Next.js / Shopify sites)
- Brand logo image extracted and dominant colors sampled via ColorThief
- `<meta name="theme-color">` tag (browser chrome color — 100% intentional)
- Apify web crawl of up to 3 pages for homepage copy

**Fetch:** Full HTML of homepage. Fetches linked CSS files. Finds brand logo image and extracts dominant colors. Returns raw HTML, CSS text, logo URL, and logo color palette.

**Extract:** Five-layer color extraction pipeline:

| Layer | Source | Confidence |
|-------|--------|-----------|
| 1 | Logo image — ColorThief palette extraction | Highest |
| 2 | `<meta name="theme-color">` | Very high — browser-facing brand color |
| 3 | CSS custom properties (`--primary`, `--brand-*`, `--accent-*`) | High — design tokens |
| 4 | Inline `<style>` block colors | High — modern JS sites embed CSS here |
| 5 | Semantic selector colors (buttons, CTAs, hero, nav) | Medium |
| 6 | Frequency-fallback from all CSS | Low |

Third-party colors are filtered out: Facebook blue, Instagram gradient, WhatsApp green, Razorpay blue, Paytm, Google Chrome palette, Bootstrap defaults.

**Synthesise:** LLM has training knowledge of major brands and uses it to validate or correct extracted colors (e.g. for Dove, it knows the palette is white + red even if CSS extraction misses it). Returns:

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `primary_colors` | array | 2–4 hex values forming the core brand palette |
| `secondary_colors` | array | Supporting palette colors |
| `primary_fonts` | array | Font family names from CSS declarations |
| `brand_tone` | string | Bold / Playful / Premium / Natural / Technical / Minimal / Warm |
| `visual_style` | string | Description of visual design approach |
| `brand_maturity` | string | Startup / Growing / Established / Premium / Iconic |
| `tagline` | string | Brand tagline if found on homepage |
| `brand_voice_keywords` | array | Up to 8 words that describe how the brand speaks |
| `missing_brand_elements` | array | Brand elements not present (e.g. no consistent icon system) |
| `experiential_design_angle` | string | How the brand identity should inform activation design |

**Powers:** P11 (brand tone and visual identity inform outreach messaging style). PDF report color swatches.

---

### P03 — Market Position

**Signal sources:**
- Two parallel Google searches via Apify: one targeting brand perception / reputation / 2024-2025, one targeting competitive comparisons and recent campaigns

**Fetch:** Two parallel searches. Returns up to 16 search results with titles, snippets, and dates.

**Extract:** Separates result titles from full snippets. Passes both to the LLM with explicit segmentation.

**Synthesise:** Assesses how the brand is positioned in the market relative to competitors and in media coverage.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `share_of_voice_level` | string | HIGH / MEDIUM / LOW — brand's search presence vs category |
| `share_of_voice_reasoning` | string | 1–2 sentence evidence for the assessment |
| `brand_sentiment` | string | POSITIVE / NEUTRAL / NEGATIVE / MIXED |
| `sentiment_signals` | array | Up to 3 specific headlines or snippets driving sentiment |
| `self_positioning_keywords` | array | How the brand describes itself (from brand copy) |
| `market_perception_keywords` | array | How external sources describe the brand |
| `perception_gap_score` | integer | 1–5 — 1 = fully aligned, 5 = major gap between self-description and market view |
| `perception_gap_reasoning` | string | Why the gap score was assigned |
| `category_leadership_claim` | boolean | Does the brand claim category leadership? |
| `leadership_claim_verified` | boolean | Is that claim supported by external sources? |
| `recent_sentiment_shift` | string | IMPROVING / STABLE / DECLINING / UNKNOWN |
| `market_position_summary` | string | 2–3 sentence synthesis of current market standing |
| `pitch_implication` | string | What this positioning means for how StepOneXP should pitch |

**Powers:** P11 (pitch_implication feeds into outreach tone and framing)

---

### P04 — Competitor Mapping

**Signal sources:**
- Two parallel Google searches via Apify: one for direct competitor comparisons, one for brand vs alternatives
- LLM training knowledge as primary source — GPT-4o has deep knowledge of Indian FMCG, D2C, fintech, and consumer brand categories
- Website crawl of top 2 identified competitors (max 2 pages each) as supplementary enrichment

**Two-source strategy:**
1. **Google search** identifies competitor names from search results
2. **LLM knowledge** (primary) analyses each competitor using training data — their positioning, event history, marketing spend, and experiential activity
3. **Website content** (supplementary) updates the analysis with any new positioning copy found

**Fetch:** Parallel Google searches for competitors. Crawls up to 2 competitor websites for homepage copy.

**Extract:** Identifies up to 4 competitor names from search results. Collects up to 400 chars of text per competitor website.

**Synthesise:** Produces a complete competitive intelligence map.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `competitors` | array | List of competitor objects (see below) |
| `experiential_white_space` | string | Which competitor has the biggest experiential gap and why |
| `competitive_urgency` | string | YES / NO — should StepOneXP reference competitor activity in pitch? |
| `recommended_pitch_angle` | string | Specific angle using competitor intel for the pitch |

**Per-competitor fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Competitor brand name |
| `brand_positioning` | string | Their actual market positioning in one sentence |
| `positioning_style` | string | Premium / Value / Technical / Community / Bold / Natural / Playful |
| `marketing_activity_level` | string | HIGH / MEDIUM / LOW |
| `events_activity` | string | YES / NO / UNKNOWN |
| `events_description` | string | Specific events or activation types they run |
| `digital_presence_score` | integer | 1–5 estimated digital marketing presence |
| `experiential_gap` | string | What experiential opportunity they are missing |
| `threat_level_to_brand` | string | HIGH / MEDIUM / LOW threat to the target company |

**Powers:** P11 (competitor names, events descriptions, and white space feed directly into Touch 3 of every outreach sequence)

---

### P05 — Brand Activity

**Signal sources:**
- Two parallel Google searches via Apify: one for campaigns / launches / events in 2024-2025, one for partnerships / collaborations / PR

**Fetch:** Parallel Google searches for recent marketing activity. Returns up to 20 dated news items.

**Extract:** Assembles items with date, title, and snippet. Passes up to 20 items to the LLM.

**Synthesise:** Maps the brand's marketing calendar and identifies timing opportunities.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `recent_campaigns` | array | List of campaigns (each with name, date, channel, description) |
| `product_launches` | array | Recent product or feature launches |
| `pr_activity_level` | string | HIGH / MEDIUM / LOW |
| `social_content_cadence` | string | Daily / Weekly / Monthly / Sporadic / Unknown |
| `partnerships_collaborations` | array | Notable brand partnerships found |
| `seasonal_pattern` | string | Which seasons or events the brand activates around |
| `marketing_silence_periods` | string | Any gaps of 60+ days with no visible activity |
| `budget_signal` | string | HIGH / MEDIUM / LOW estimated marketing budget |
| `budget_signal_reasoning` | string | Evidence for the budget assessment |
| `last_major_campaign` | string | Name and date of most recent campaign |
| `upcoming_opportunity_window` | string | When the next likely activation window is |
| `activity_summary` | string | 2–3 sentences on their marketing cadence and style |

**Powers:** P11 (`last_major_campaign` feeds into Touch 1 as the opening personalisation signal. `upcoming_opportunity_window` times the pitch)

---

### P06 — Experiential & Events Footprint

**Signal sources:**
- Two broad Google searches via Apify: one for events / activations / sponsorships / pop-ups / roadshows 2023-2025, one for campaigns / awards / CSR / experiences
- LLM training knowledge supplements search — when search finds nothing, the LLM uses its knowledge of the brand's known event history

**Fetch:** Two searches using 30+ keyword combinations. Returns up to 20 results.

**Extract:** Applies a broad keyword filter covering: event, launch, activation, conference, roadshow, pop-up, experience, festival, summit, meet, sponsor, campaign, award, concert, exhibition, partner, workshop, marathon, CSR, flagship, tour. Falls back to all results if strict filter finds nothing.

**Synthesise:** Maps the complete experiential footprint with a scored maturity assessment.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `events_timeline` | array | List of event objects (see below) |
| `experiential_maturity_score` | integer | 1–5 (see scoring table) |
| `maturity_score_reasoning` | string | Specific evidence for the score assigned |
| `formats_used` | array | Every event format type the brand has done |
| `formats_missing` | array | Formats appropriate for this brand's scale that they haven't done |
| `geography_of_events` | array | Cities and regions where they have activated |
| `last_event_months_ago` | integer | Months since most recent event (null if unknown) |
| `events_frequency` | string | Monthly / Quarterly / Annual / Sporadic / Never identified |
| `pitch_angle` | string | One specific sentence about what StepOneXP can offer based on the actual gap |
| `opening_line_for_pitch` | string | Ready-to-use first sentence for the outreach email referencing a real event or gap |
| `confidence_level` | string | HIGH / MEDIUM / LOW — based on how much hard evidence was found |

**Per-event fields:**

| Field | Type | Description |
|-------|------|-------------|
| `event_name` | string | Name or description of the event |
| `date` | string | YYYY-MM or approximate year |
| `format` | string | Conference / Product launch / Consumer activation / Sponsorship / Pop-up / Roadshow / Award / CSR / Partnership activation / Virtual |
| `scale` | string | Intimate (<100) / Mid (100-500) / Large (500-2000) / Mass (2000+) / Unknown |
| `location` | string | City, country, or "Multiple cities" or "Online" |
| `brand_role` | string | Host / Sponsor / Participant / Co-host |
| `production_quality` | string | DIY / Standard / Premium / World-class / Unknown |
| `source` | string | Search snippet or "training knowledge" if inferred |

**Maturity score (1–5):**

| Score | Description |
|-------|-------------|
| 1 | Never done any events — pure first-mover opportunity |
| 2 | 1–2 events, ad-hoc, no consistent programme |
| 3 | Regular events, 1–2 formats, limited geography |
| 4 | Multi-format programme, multiple cities, consistent calendar |
| 5 | Sophisticated multi-city experiential programme, multiple formats, large budgets |

**Powers:** P11 (`pitch_angle` and `opening_line_for_pitch` are used verbatim as hints to the outreach writer. `formats_missing` feeds into Touch 1 and Touch 3 gap framing)

---

### P07 — Reputation Research

**Signal sources:**
- Apify Reddit scraper — searches for brand review / experience discussions (up to 15 posts)
- Two parallel Google searches via Apify — one for customer reviews / complaints / Reddit 2024, one for brand reputation / controversy / awards
- LLM training knowledge as primary source — always provides genuine brand reputation data for known brands

**Two-source strategy:**
1. **LLM knowledge** (primary) — GPT-4o has training knowledge of brand sentiment, controversies, NPS signals, and community strength for virtually every major consumer brand
2. **Reddit + Google** (supplementary) — adds real, recent user discussions. When found, overrides specific fields (`reddit_sentiment`, `reddit_key_themes`, `recent_controversy`)

**Fetch:** Parallel Reddit scrape and Google search. Returns up to 15 Reddit posts and 16 search snippets.

**Extract:** Formats Reddit posts with subreddit name, upvote score, title, and body (truncated to 200 chars). Collects review snippets from search.

**Synthesise:** LLM knowledge call runs first, always producing substantive output. If Reddit or review data was found, a second enrichment call updates specific fields with real community data.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `overall_reputation_score` | integer | 0–100 composite reputation score |
| `reputation_label` | string | STRONG / GOOD / NEUTRAL / MIXED / POOR |
| `reddit_sentiment` | string | POSITIVE / NEUTRAL / NEGATIVE / MIXED / NO_DATA |
| `reddit_key_themes` | array | Topics customers actually discuss about this brand |
| `reddit_top_complaints` | array | Real, specific complaints from Reddit / reviews |
| `reddit_top_praise` | array | Real, specific praise from Reddit / reviews |
| `review_platform_sentiment` | string | POSITIVE / NEUTRAL / NEGATIVE / MIXED / NO_DATA |
| `common_customer_complaints` | array | Recurring issues from review platforms |
| `common_customer_praise` | array | Recurring positives from review platforms |
| `nps_signal` | string | HIGH / MEDIUM / LOW / UNKNOWN — estimated Net Promoter Signal |
| `brand_community_strength` | string | STRONG / MODERATE / WEAK / NONE |
| `recent_controversy` | string | Any known controversy in the past 24 months, or null |
| `reputation_watchout` | string | Key risk StepOneXP must know before pitching (e.g. "Brand is under price pressure — don't lead with premium positioning") |
| `reputation_opportunity` | string | Positive signal to reference in outreach (e.g. "Dove's Real Beauty campaign has sustained strong community loyalty — reference it in outreach") |

**Powers:** P11 (`reputation_opportunity` referenced in outreach. `reputation_watchout` calibrates pitch tone)

---

### P08 — Strategic Watchouts

**Signal sources:**
- Two parallel Google searches via Apify: one for layoffs / restructuring / CMO changes / controversy 2024-2025, one for funding / revenue / agency relationships / campaign signals

**Fetch:** Two searches targeting risk signals. Returns up to 16 results.

**Extract:** Assembles dated signals with titles and snippets. Passes up to 25 signals to the LLM.

**Synthesise:** Produces a risk assessment with explicit pitch timing and tone guidance.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `overall_verdict` | string | GREEN / AMBER / RED |
| `verdict_reasoning` | string | 1–2 sentence explanation |
| `financial_distress_signals` | array | Any layoff, restructuring, or revenue concern signals found |
| `leadership_changes` | array | Each has: `role`, `change`, `date`, `implication` (e.g. "New CMO = new vendor relationships possible") |
| `pr_controversies` | array | Any brand PR crisis or scandal signals |
| `marketing_freeze_detected` | boolean | Evidence that marketing spend has been paused |
| `marketing_freeze_details` | string | Context if freeze detected, else null |
| `existing_agency_signals` | array | Any evidence of existing agency relationships |
| `timing_recommendation` | string | PURSUE NOW / WAIT 30 DAYS / WAIT 60 DAYS / AVOID |
| `timing_reasoning` | string | Specific reason for the timing call |
| `pitch_tone_adjustment` | string | Explicit guidance: how should StepOneXP adjust their approach? |

**Verdict guide:**
- **GREEN** — No distress signals. Leadership stable. Marketing active. Pursue immediately.
- **AMBER** — Some signals (restructuring noise, leadership in flux). Proceed with measured tone.
- **RED** — Clear distress signals (mass layoffs, CMO vacant, marketing freeze). Do not pitch aggressively.

**Powers:** P11 (verdict directly controls outreach tone — GREEN = confident, AMBER = measured, RED = very soft. `timing_recommendation` determines when to send)

---

### P09 — Decision-Maker Identification

**Signal sources:**
- Four parallel Google searches via Apify targeting LinkedIn profiles of CMOs, VP Marketing, Head of Marketing, Brand Managers, Events Managers, Category Managers
- Direct HTTP scrape of company `/about`, `/team`, `/leadership`, `/people` pages
- LLM training knowledge as primary source — GPT-4o knows org structures for virtually every major Indian and global consumer brand

**Two-source strategy:**
1. **LLM knowledge** (primary) — always runs first. Knows that Dove → HUL (Hindustan Unilever), Gillette → P&G India, Maggi → Nestlé India etc. Identifies real named contacts with their titles and roles.
2. **Google search** (supplementary) — finds LinkedIn profile URLs for people already identified by LLM. These URLs are stitched onto the knowledge contacts.

**Deduplication:** Results are merged by normalised name. Search contacts (with LinkedIn URLs) take priority. Knowledge contacts fill gaps up to 5 total.

**Fetch:** 4 parallel Google searches + team page scrape. Returns all raw search results and page text.

**Extract:** Formats each result as `RESULT: title | URL: url | INFO: snippet`. Builds a LinkedIn URL map by scanning all result URLs for `linkedin.com/in/` patterns.

**Synthesise:** Knowledge call → search extraction → merge → LinkedIn URL attachment. Falls back to a third knowledge call if merged result is empty.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `buying_committee` | array | List of contact objects (see below) |
| `primary_contact` | string | Name of the best first person to reach out to |
| `parent_company` | string | Parent company if this is a product brand (e.g. "Hindustan Unilever" for Dove), else null |
| `total_contacts_found` | integer | Number of contacts in the buying committee |
| `confidence_level` | string | HIGH / MEDIUM / LOW |
| `committee_gap` | string | Which role is missing from the committee, or "None" |

**Per-contact fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Full name |
| `title` | string | Exact job title |
| `company` | string | The company they work at (may be parent company) |
| `role_type` | string | Economic Buyer / Initiator / Events Specialist / Influencer |
| `linkedin_url` | string | LinkedIn profile URL or null |
| `linkedin_activity` | string | ACTIVE / MODERATE / LOW / UNKNOWN |
| `decision_relevance_score` | integer | 1–5 — how much decision-making power over experiential budget |
| `outreach_priority` | string | PRIMARY / SECONDARY |
| `personalisation_hook` | string | One specific verifiable fact about this person to reference in outreach |

**Role type guide:**
- **Economic Buyer** — signs the PO (CMO, VP Marketing, CEO for small cos)
- **Initiator** — identifies the need and brings in the agency (Brand Head, Events Lead)
- **Events Specialist** — executes activations (Events Manager, BTL Manager)
- **Influencer** — shapes the brief (Brand Manager, Category Manager, Growth Lead)

**Powers:** P10 (buying committee is the input). P11 (all contact fields used for personalisation)

---

### P10 — Contact Intelligence

**Signal sources:**
- Hunter.io `email-finder` API — verified email lookup by first name, last name, domain
- Hunter.io domain search — infers email pattern for the company domain
- Pattern inference — `{first}.{last}@domain.com` as fallback

**No Apify calls — runs instantly (~0s).**

**Fetch:** Loops over top 5 buying committee members from P09. Calls Hunter.io for each. Infers email from domain pattern as fallback.

**Extract:** Produces per-contact records with email, confidence score, source, and all inferred pattern variants.

**Synthesise (no LLM):** Adds `recommended_channel` based on whether a LinkedIn URL and verified email are available. Returns aggregate stats.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `contacts` | array | Enriched contact objects (see below) |
| `domain` | string | Company email domain (e.g. `hul.com`) |
| `email_pattern` | string | Standard pattern for this company (e.g. `{first}.{last}@hul.com`) |
| `total_contacts` | integer | Number of contacts processed |
| `verified_emails` | integer | Count of Hunter.io-verified addresses |
| `inferred_emails` | integer | Count of pattern-inferred addresses |
| `data_disclaimer` | string | Shown when emails are inferred — directs to use LinkedIn DM where available |

**Per-contact enrichment fields (added to P09 data):**

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Best available email address, or null |
| `email_confidence` | integer | 0–100 — Hunter.io confidence score or 25 for pattern-inferred |
| `email_source` | string | `hunter_verified` / `pattern_inferred` / `not_found` |
| `all_patterns` | array | All plausible email format variants for this person |
| `recommended_channel` | string | "LinkedIn DM first" / "Email (pattern-inferred)" / "Research manually" |

**Powers:** P11 (email and LinkedIn URL fed into outreach sequences). P12 (email used for tracking records)

---

### P11 — Personalised Outreach Sequences

**Signal sources:**
- All P01–P10 outputs (compiled into a single rich context object)
- One LLM call per contact using GPT-4o — role-specific framing, competitor intel, and real personalisation signals

**Fetch:** Receives the full pipeline output bundle as input.

**Extract:** Compiles a structured brief per contact:
- Contact details: name, title, role type, outreach priority, LinkedIn activity, personalisation hook (from P09 + P10)
- Brand context: ICP score, business model, readiness (from P01)
- Campaign intel: last campaign name, date, channel, upcoming window (from P05)
- Experiential footprint: maturity score, confirmed events, missing formats, pitch angle, opening line hint (from P06)
- Competitor intel: each competitor's name, positioning, events activity, and gap (from P04)
- Risk calibration: watchout verdict, tone guidance, timing recommendation (from P08)
- Reputation: label and opportunity signal (from P07)

**Synthesise:** One GPT-4o call per contact. Each produces a 4-touch sequence with role-specific framing.

**Role-based framing rules applied:**
- CEO / Founder → ROI, competitive threat, market share
- CMO / VP Marketing → brand equity, earned attention, competitive differentiation
- Brand Manager → tactical execution, budget efficiency, vendor management
- Growth / Performance → CAC, attribution, measurable conversion
- Category Manager → on-ground visibility, shelf pull, point-of-decision presence

**Output schema (top level):**

| Field | Type | Description |
|-------|------|-------------|
| `contacts_sequences` | array | One entry per contact (see below) |
| `primary_contact` | object | The PRIMARY-priority contact |
| `outreach_sequence` | object | The primary contact's sequence (backward compat) |
| `personalisation_variables_used` | object | Signal, gap, hook, watchout, competitors used |

**Per-contact sequence:**

| Field | Type | Description |
|-------|------|-------------|
| `contact` | object | Name, title, email, LinkedIn, role, priority, hook |
| `sequence` | object | touch_1 through touch_4 |
| `personalisation_vars` | object | Which signals drove this specific sequence |

**Touch structure:**

| Touch | Channel | Day | Content rules |
|-------|---------|-----|---------------|
| 1 | Email | 1 | 3–4 sentences. Specific real signal. No forbidden openers. One question CTA. |
| 2 | LinkedIn | 3 | Under 180 chars. References Touch 1. One specific question. |
| 3 | Email | 8 | 4–5 sentences. Names a specific competitor and what they're doing in experiential. Bridges to the gap from this person's role angle. One proof point. CTA. |
| 4 | Email | 15 | 2–3 sentences. Acknowledges persistence. Concrete offer (deck / call / case study). No pressure close. |

**Forbidden words and phrases (enforced in system prompt):** "I hope this finds you well", "I wanted to reach out", "I noticed", "I came across", leverage, unlock, seamless, game-changer, revolutionize, empower, synergy, holistic, cutting-edge, innovative, impactful.

**Powers:** P12 (sequences are wrapped with tracking infrastructure)

---

### P12 — Tracking Setup

**Signal sources:** P11 outreach sequences (no external calls)

**No Apify calls. No LLM calls. Runs instantly.**

**Fetch:** Receives P11 output.

**Extract:** For each of up to 5 contacts, generates a 12-character MD5 tracking ID seeded with company name, contact name, and a UUID.

**Synthesise (no LLM):** Injects tracking infrastructure into each sequence. Returns dashboard entries and setup instructions.

**Output schema:**

| Field | Type | Description |
|-------|------|-------------|
| `tracking_records` | array | One record per contact (see below) |
| `tracking_base_url` | string | Base URL for all tracking endpoints |
| `setup_instructions` | array | Steps to activate tracking after deployment |

**Per-tracking-record fields:**

| Field | Type | Description |
|-------|------|-------------|
| `contact_name` | string | Name of the contact |
| `contact_email` | string | Email address for this contact |
| `tracking_id` | string | 12-char MD5 ID for this contact |
| `tracked_sequence` | object | Full sequence with tracking pixels and redirect links injected |
| `dashboard_entry` | object | Initial dashboard state (see below) |

**Tracking pixel:** `<img src="{BASE}/track/open/{id}" width="1" height="1" style="display:none" alt="" />` — appended to every email touch.

**Link wrapping:** All URLs in email messages are wrapped as `{BASE}/track/click/{id}/{touch}?redirect={url}`.

**Dashboard entry:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | NOT_SENT → OPENED → ENGAGED → WARM → HOT |
| `engagement_score` | integer | Starts at 0, updated by tracking events |
| `next_action` | string | "Send Touch 1" initially |
| `scoring_rubric` | object | Points per event type |

**Engagement scoring model:**

| Event | Points | Status threshold |
|-------|--------|-----------------|
| Email opened (first time) | +1 | OPENED (1+) |
| Email opened (3+ times) | +3 | — |
| Link clicked | +5 | ENGAGED (5+) |
| LinkedIn accepted | +4 | ENGAGED |
| Reply received | +10 | WARM (10+) |
| Meeting booked | +20 | HOT (20+) |

**Note:** Apple Mail Privacy Protection pre-fetches tracking pixels — treat open events as directional only. Clicks and replies are the reliable engagement signals.

---

## Frontend

The frontend is a single-page application served directly by FastAPI at `/`. It communicates with the backend via polling at 1-second intervals during analysis.

### Analysis View

While the 12 pipelines run, the UI shows:
- A live progress bar with pipeline count (e.g. "7/12 done · 3 running")
- A grid of 12 pipeline cards, each showing state (waiting / scanning / done / error) and a one-line finding as each pipeline completes
- A terminal-style log feed streaming every pipeline event with timestamps
- An elapsed timer

### Results View

On completion, the full report is loaded and rendered into tabbed panels:

- **Overview** — ICP score with full-circle ring gauge, strategic verdict banner (GREEN / AMBER / RED), company summary card
- **Brand Identity** — color swatches rendered from extracted hex values, font list, tone and maturity assessment
- **Market** — sentiment, share of voice, perception gap, pitch implication
- **Competitors** — competitor cards with positioning, events activity, and experiential gap
- **Events** — experiential timeline, 1–5 maturity score, formats used vs missing
- **Reputation** — Reddit sentiment, praise and complaint themes, NPS signal, opportunity
- **Watchouts** — verdict, leadership changes, financial signals, timing recommendation
- **Decision Makers** — buying committee with relevance scores, LinkedIn links, and personalisation hooks
- **Contacts** — email confidence cards with recommended outreach channel
- **Outreach** — 4-touch sequences rendered per contact with one-click copy
- **Tracking** — per-contact tracking IDs, pixel URLs, engagement scoring status

### PDF Export

The rendered report is exported as a professional white-background A4 PDF using the browser's native print-to-PDF. Layout highlights:
- Clean typography with Inter font
- Cover page: full-circle ICP ring gauge, key metrics, intelligence summary strip
- Competitor table with color-coded Events YES/NO badges
- Events timeline in chronological list format
- People cards with role badges and email patterns
- Full outreach sequences with touch-type color coding (green for email, blue for LinkedIn)

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/mushaahamed/brand-intelligence-system.git
cd brand-intelligence-system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your API keys
```

At minimum, `OPENAI_API_KEY` is required. Apify tokens are needed for web scraping and Google search. Hunter.io is needed for email lookup.

### 3. Validate API configuration

```bash
curl http://localhost:8000/config/check
```

### 4. Start the server

```bash
uvicorn api.main:app --reload --port 8000
```

### 5. Open the frontend

Navigate to `http://localhost:8000`. Enter a company name, website URL, and one-line category description, then click **Run Full Analysis**.

### 6. CLI usage (no server required)

```bash
python orchestrator.py "Mamaearth" "https://mamaearth.in" "D2C skincare brand targeting millennial women in India"
```

Output is saved to `outputs/{run_id}.json`.

### 7. Run tests

```bash
python -m pytest tests/ -v
```

Smoke test (runs P01 against a real company with live APIs, ~90 seconds):

```bash
SMOKE=1 python -m pytest tests/test_apis.py::TestSmoke -v
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | API key for all LLM synthesis calls (P01–P09, P11) |
| `APIFY_TOKEN_1` | Yes | Apify token — used for P01 and P02 search and scraping |
| `APIFY_TOKEN_2` | No | Apify token — P03 and P04 |
| `APIFY_TOKEN_3` | No | Apify token — P05 and P06 |
| `APIFY_TOKEN_4` | No | Apify token — P07 and P08 |
| `APIFY_TOKEN_5` | No | Apify token — P09 and P10 |
| `HUNTER_API_KEY` | No | Hunter.io API key for email finder in P10 |
| `APP_ENV` | No | `development` or `production` (default: `development`) |
| `LOG_LEVEL` | No | Structlog level (default: `INFO`) |
| `OUTPUT_DIR` | No | Directory for JSON report output (default: `./outputs`) |
| `MAX_RETRIES` | No | Retry count for API calls (default: `2`) |
| `REQUEST_TIMEOUT` | No | HTTP request timeout in seconds (default: `30`) |
| `RATE_LIMIT_DELAY` | No | Seconds between Apify calls (default: `1`) |
| `API_HOST` | No | FastAPI bind address (default: `0.0.0.0`) |
| `API_PORT` | No | FastAPI port (default: `8000`) |
| `TRACKING_BASE` | No | Base URL for tracking endpoints (set to your deployed URL in production) |
| `ACTOR_TIMEOUT` | No | Apify actor run timeout in seconds (default: `60`) |

If only one Apify token is available, set `APIFY_TOKEN_1` and leave the rest blank — the system falls back to using token 1 for all pipeline groups.

---

## API Reference

### POST /analyse

Start a full 12-pipeline analysis run.

**Request body:**
```json
{
  "company_name": "Mamaearth",
  "company_url": "https://mamaearth.in",
  "category": "D2C skincare brand targeting millennial women in India"
}
```

**Response:**
```json
{
  "job_id": "mamaearth-a1b2c3",
  "status": "started",
  "message": "Analysis running — poll /status/mamaearth-a1b2c3"
}
```

---

### GET /status/{job_id}

Poll for run progress. Returns the full pipeline log on every call.

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `running` / `complete` / `failed` |
| `progress` | integer | 0–100 |
| `pipeline_label` | string | Human-readable name of the currently active pipeline |
| `pipelines_done` | array | Keys of completed pipelines |
| `running_pipelines` | array | Keys of currently executing pipelines |
| `pipeline_summaries` | object | One-line finding per completed pipeline |
| `pipeline_log` | array | Full timestamped log feed |
| `result` | object | Summary object on completion (null while running) |
| `run_id` | string | ID to use with `/report/{run_id}` |
| `elapsed` | float | Total seconds elapsed on completion |

---

### GET /report/{run_id}

Fetch the full persisted report from disk. Returns the complete 12-pipeline output JSON including all `pipelines[key].output` objects.

---

### GET /reports

List all saved reports, sorted by most recent.

---

### GET /track/open/{tracking_id}

Returns a 1×1 transparent GIF. Increments open count and engagement score. First open: +1 point. Subsequent opens (3+): +3 points.

---

### GET /track/click/{tracking_id}/{touch}?redirect={url}

Logs a link click event (+5 points) and redirects the recipient to `redirect`. The `touch` parameter identifies which email in the sequence was clicked.

---

### POST /track/event

Log a manual engagement event (LinkedIn accepted, reply received, meeting booked).

---

### GET /health

Liveness check. Returns `{"status": "ok", "version": "2.0.0"}`.

---

### GET /config/check

Returns which API integrations are configured and ready.

---

## Repository Structure

```
brand-intelligence-system/
├── api/
│   ├── main.py              # FastAPI app, background task runner, tracking endpoints
│   └── models.py            # Pydantic request/response models
├── config/
│   ├── settings.py          # Central config — all env vars loaded here
│   └── apify_config.py      # Actor IDs and token group mapping
├── frontend/
│   ├── index.html           # Single-page application
│   ├── style.css            # Dark design system
│   └── app.js               # API client, live terminal feed, report renderer, PDF export
├── pipelines/
│   ├── base.py              # BasePipeline ABC — enforces 3-layer contract
│   ├── p01_company_overview/
│   │   ├── pipeline.py      # fetch / extract / synthesise implementation
│   │   ├── prompt.md        # System prompt for Layer 3
│   │   └── schema.json      # Expected output schema
│   ├── p02_brand_identity/
│   ├── p03_market_position/
│   ├── p04_competitor_mapping/
│   ├── p05_brand_activity/
│   ├── p06_experiential_footprint/
│   ├── p07_reputation_research/
│   ├── p08_strategic_watchouts/
│   ├── p09_decision_makers/
│   ├── p10_contact_intelligence/
│   ├── p11_outreach/
│   └── p12_tracking/
├── utils/
│   ├── apify_client.py      # Actor runner with token rotation and retry logic
│   ├── claude_client.py     # LLM client wrapper for all synthesis calls
│   ├── hunter_client.py     # Email finder and domain pattern lookup
│   ├── web_scraper.py       # Direct HTTP crawl with BeautifulSoup
│   └── helpers.py           # ICP scoring, text utilities, JSON parsing
├── tests/
│   ├── test_apis.py         # Unit, integration, and smoke tests
│   └── conftest.py
├── orchestrator.py          # Parallel + sequential pipeline runner with live callbacks
├── requirements.txt
└── .env.example
```

---

## License

MIT
