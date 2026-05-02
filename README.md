# BrandScope — Brand Intelligence & Outreach Automation

**BrandScope** is a production-grade brand research and outreach automation system built for **StepOneXP**, an experiential marketing agency. It takes three inputs — a company name, website URL, and a one-line category description — and produces a complete intelligence dossier with personalised, multi-touch outreach sequences for every key decision-maker at the target company.

The system runs 12 sequential pipelines, each enforcing a strict three-layer architecture: real data is fetched first, then structured, then reasoned over by an LLM. No output is ever generated from a model call alone — every insight is grounded in scraped, retrieved, or verified data.

---

## What It Produces

Given a single company as input, BrandScope outputs:

- An **ICP fit score** (0–100) measuring alignment with StepOneXP's ideal client profile
- A **brand identity profile** with hex colors extracted directly from CSS files and font stack analysis
- A **market position report** with sentiment scoring and share-of-voice assessment
- A **competitor map** with 4–6 direct competitors, their experiential activity, and identified white space
- A **campaign activity timeline** with budget signal and upcoming opportunity windows
- A complete **experiential footprint** — every event, sponsorship, activation, and brand presence ever found
- An **authentic reputation score** sourced from Reddit threads and review platforms
- A **strategic watchout verdict** (GREEN / AMBER / RED) based on financial, leadership, and PR risk signals
- A **buying committee** with named individuals, LinkedIn activity levels, and personalisation hooks
- **Verified or inferred email addresses** for each committee member via Hunter.io
- A **4-touch outreach sequence** (email + LinkedIn) written per-contact, referencing actual competitor names, campaign signals, and experiential gaps
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
  P09 output → P10 (contact lookup)
  P10 output → P11 (outreach generation, receives all P01-P10)
  P11 output → P12 (tracking setup)
```

### The Three-Layer Contract

Every pipeline inherits from `BasePipeline` (an abstract base class) and must implement exactly three methods. The `.run()` method enforces this order and cannot be bypassed:

```
Layer 1 — fetch()
  Pull raw data from Apify actors, direct HTTP crawls, Hunter.io API,
  or Reddit. No LLM is called here. Raw data is stored as-is.

Layer 2 — extract()
  A Python parser transforms the raw response into a clean, typed
  structured dict. Fields are normalised, truncated, and filtered.
  Still no LLM.

Layer 3 — synthesise()
  The structured dict is formatted into a prompt and sent to the LLM
  (GPT-4o-mini for most pipelines, GPT-4o for outreach writing only).
  The model returns a defined JSON schema. The output is parsed and
  validated before being returned.
```

**Example — P01 Company Overview:**
- `fetch()` crawls up to 4 pages of the company website via direct HTTP + BeautifulSoup, then runs two parallel Google searches via Apify for funding, team size, and news signals
- `extract()` prioritises "about", "team", "investor", and "press" pages, assembles up to 6 text chunks (800 chars each), and collects news snippets
- `synthesise()` sends the structured text to GPT-4o-mini with a system prompt that returns `business_model`, `industry_vertical`, `employee_count_range`, `funding_status`, `icp_fit_score`, `experiential_readiness`, and `company_narrative`

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
│  GET  /track/dashboard/{id} (per-contact score + status) │
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

### P01 — Company Overview

**Fetch:** Direct HTTP crawl of up to 4 pages (prioritising `/about`, `/team`, `/investor`, `/press`). Two parallel Google searches via Apify for funding, headcount, and news signals.

**Extract:** Selects and truncates the most relevant page sections. Collects up to 10 news snippets with titles and descriptions.

**Synthesise (GPT-4o-mini):** Returns `business_model`, `industry_vertical`, `employee_count_range`, `funding_status`, `key_facts[]`, `company_narrative`, `recommended_service`, `icp_fit_score` (0–100), and `experiential_readiness` (LOW / MEDIUM / HIGH).

**ICP Score Calculation:**
| Signal | Points |
|--------|--------|
| B2C business model | +25 |
| 200+ employees | +25 |
| VC-backed or Series A+ | +25 |
| India presence | +25 |

---

### P02 — Brand Identity

**Fetch:** Direct HTTP request to the company homepage. Parses `<link rel="stylesheet">` tags, fetches up to 5 CSS files. Also crawls up to 3 pages for homepage copy.

**Extract:** Regex-parses all CSS and inline HTML for hex colours (`#rrggbb`) and RGB values, counting frequency of each. Filters near-white and near-black values. Extracts `font-family` declarations. Collects homepage copy for tone analysis.

**Synthesise (GPT-4o-mini):** Returns `primary_colors[]` (top hex values by frequency), `secondary_colors[]`, `primary_fonts[]`, `brand_tone`, `brand_voice_keywords[]`, `brand_maturity`, `missing_brand_elements[]`, and `experiential_design_angle` — a note on how brand identity should inform activation design.

**Key differentiator:** Colors are extracted from actual CSS files, not inferred from images or brand guidelines.

---

### P03 — Market Position

**Fetch:** Two parallel Google searches via Apify targeting search sentiment, brand perception, and share-of-voice signals against competitors.

**Extract:** Filters for results containing sentiment keywords. Collects titles, snippets, and publication dates.

**Synthesise (GPT-4o-mini):** Returns `brand_sentiment` (POSITIVE / NEUTRAL / NEGATIVE / MIXED), `share_of_voice_level` (DOMINANT / HIGH / MEDIUM / LOW / NICHE), `perception_gap_score` (1–5), `search_visibility`, `pitch_implication`, and `recommended_positioning` for the agency pitch.

---

### P04 — Competitor Mapping

**Fetch:** Two parallel Google searches to identify direct competitors. For each identified competitor, crawls their website.

**Extract:** Identifies 4–6 competitor names and basic positioning from search results.

**Synthesise (GPT-4o-mini):** For each competitor, returns `name`, `brand_positioning`, `events_activity` (ACTIVE / OCCASIONAL / NONE), `events_description`, and `experiential_gap`. At the map level: `experiential_white_space` (the gap none of them are filling), `competitive_urgency` (YES / NO), and `recommended_pitch_angle`.

---

### P05 — Brand Activity

**Fetch:** Two parallel Google searches targeting campaigns, partnerships, PR, and marketing activity in the last 24 months.

**Extract:** Filters for campaign and marketing keywords. Extracts dated signals.

**Synthesise (GPT-4o-mini):** Returns `recent_campaigns[]` (each with name, date, channel, description, estimated reach), `budget_signal` (ENTERPRISE / MID-MARKET / STARTER / UNKNOWN), `last_major_campaign`, `campaign_frequency`, `digital_vs_experiential_ratio`, and `upcoming_opportunity_window` — a forward-looking note on timing for an agency pitch.

---

### P06 — Experiential Footprint

**Fetch:** Two broad Google searches targeting events, sponsorships, activations, pop-ups, roadshows, awards, CSR, and campaign launches.

**Extract:** Filters results against 30+ event-related keywords. If the strict filter finds nothing, all results are passed to the LLM with an instruction to infer from training knowledge.

**Synthesise (GPT-4o-mini):** Returns a full `events_timeline[]` — each entry has `event_name`, `date`, `format` (Conference / Product launch / Consumer activation / Sponsorship / Pop-up / Roadshow / Award / CSR), `scale` (Intimate / Mid / Large / Mass), `location`, `brand_role` (Host / Sponsor / Participant), and `production_quality`. At the summary level: `experiential_maturity_score` (1–5), `formats_used[]`, `formats_missing[]`, `events_frequency`, `pitch_angle`, and `opening_line_for_pitch` — a ready-to-use first sentence for the outreach email referencing a real gap or event.

---

### P07 — Reputation Research

**Fetch:** Parallel execution — Reddit scrape via Apify and a Google search targeting Trustpilot, Reddit, and customer feedback pages. Both complete concurrently.

**Extract:** Formats Reddit posts with subreddit, upvote score, title, and body (truncated to 200 chars). Collects review snippets.

**Synthesise (GPT-4o-mini):** Returns `overall_reputation_score` (0–100), `reputation_label` (STRONG / GOOD / NEUTRAL / MIXED / POOR), `reddit_sentiment`, `reddit_key_themes[]`, `reddit_top_complaints[]`, `reddit_top_praise[]`, `nps_signal`, `brand_community_strength`, `recent_controversy`, `reputation_watchout` (what the agency must know before pitching), and `reputation_opportunity` (a positive signal to reference in outreach).

**Key differentiator:** Reddit is the primary signal source — authentic, unmoderated consumer opinion rather than brand-managed review platforms.

---

### P08 — Strategic Watchouts

**Fetch:** Two parallel Google searches targeting layoffs, CMO changes, restructuring, PR controversies, and agency/budget signals from the last 12 months.

**Extract:** Assembles dated signals with titles and snippets.

**Synthesise (GPT-4o-mini):** Returns `overall_verdict` (GREEN / AMBER / RED), `verdict_reasoning`, `financial_distress_signals[]`, `leadership_changes[]` (each with role, change description, date, and implication for vendor timing), `pr_controversies[]`, `marketing_freeze_detected` (boolean), `existing_agency_signals[]`, `timing_recommendation` (PURSUE NOW / WAIT 30 DAYS / WAIT 60 DAYS / AVOID), and `pitch_tone_adjustment` — explicit guidance on how the agent should calibrate their approach.

**P11 reads this verdict and adjusts outreach tone accordingly:** GREEN = confident, AMBER = measured, RED = do not pitch hard.

---

### P09 — Decision-Maker Identification

**Fetch:** Two Google searches with quoted company name targeting CMO, VP Marketing, Head of Marketing, Head of Brand, Events Manager, and Marketing Director LinkedIn profiles.

**Extract:** Parses LinkedIn-format titles from search result titles (e.g. "First Last - Title at Company | LinkedIn"). Extracts name, role, LinkedIn URL, and snippet. Deduplicates by name.

**Synthesise (GPT-4o-mini):** Returns a `buying_committee[]` — each person has `name`, `title`, `role_type` (Economic Buyer / Initiator / Events Specialist / Influencer), `company_tenure_months`, `linkedin_url`, `linkedin_activity` (ACTIVE / MODERATE / DORMANT / UNKNOWN), `decision_relevance_score` (1–5), `outreach_priority` (PRIMARY / SECONDARY / AVOID), and `personalisation_hook` — a specific sentence about this person to reference in outreach.

---

### P10 — Contact Intelligence

**Fetch:** Receives the P09 buying committee. For each of the top 5 contacts, calls Hunter.io's `email-finder` endpoint with first name, last name, and company domain. Also calls Hunter.io's domain lookup to infer the company-wide email pattern.

**Extract:** Produces per-contact records with email, confidence score (0–100), and source (`hunter_verified` / `pattern_inferred` / `not_found`).

**Synthesise (no LLM):** Adds `recommended_channel` per contact based on LinkedIn activity level and email confidence. Computes aggregate stats: total contacts, verified emails, inferred emails. Includes a data disclaimer for pattern-inferred addresses.

---

### P11 — Outreach Sequences

**Fetch:** Receives all P01–P10 outputs as a single context object.

**Extract:** Assembles a rich structured brief: contact details from P09 + P10, competitor intel from P04, last campaign from P05, experiential footprint and pitch angle from P06, watchout verdict from P08, reputation opportunity from P07, and ICP score from P01.

**Synthesise (GPT-4o):** Writes a 4-touch sequence for the primary contact. The model is instructed to write as a senior outreach specialist who has spent two hours researching this exact brand.

Touch structure:
| Touch | Channel | Timing | Content |
|-------|---------|--------|---------|
| 1 | Email | Day 1 | 3–4 sentences. Opens with a specific, real signal (a campaign, a gap, a competitor move). One direct question as CTA. |
| 2 | LinkedIn | Day 3 | Under 180 characters. References Touch 1. Single specific question. |
| 3 | Email | Day 8 | 4–5 sentences. Names a specific competitor and what they are actively doing in experiential. Bridges to the gap. |
| 4 | Email | Day 15 | 2–3 sentences. Acknowledges persistence. Concrete offer (deck / call / case study). No pressure close. |

The model is explicitly prohibited from opening with "I hope this finds you well", "I wanted to reach out", "I noticed", or using words like leverage, seamless, game-changer, synergy, or innovative.

For non-PRIMARY contacts, the full committee list is returned for manual outreach.

---

### P12 — Tracking Setup

**Fetch:** Receives P11 outreach sequences.

**Extract:** For each contact (up to 5), generates a 12-character MD5 tracking ID seeded with company name, contact name, and a UUID.

**Synthesise (no LLM):** Injects a 1×1 transparent GIF tracking pixel (`<img src="/track/open/{id}" ...>`) into each email touch. Wraps links as `/track/click/{id}/{touch}?redirect={url}`. Returns the full `tracked_sequence` alongside a `dashboard_entry` per contact with initial status `NOT_SENT` and the full scoring rubric.

**Engagement scoring model:**
| Event | Points | Status Threshold |
|-------|--------|-----------------|
| Email opened (first time) | +1 | OPENED |
| Email opened (3+ times) | +3 | OPENED |
| Link clicked | +5 | ENGAGED |
| LinkedIn accepted | +4 | ENGAGED |
| Reply received | +10 | WARM |
| Meeting booked | +20 | HOT |

---

## Frontend

The frontend is a single-page application served directly by FastAPI at `/`. It communicates with the backend via polling at 1-second intervals.

### Analysis View

While the 12 pipelines run, the UI shows:
- A live progress bar with pipeline count (e.g. "7/12 done · 3 running")
- A grid of 12 pipeline cards, each showing state (waiting / scanning / done / error) and a one-line finding as each pipeline completes
- A terminal-style log feed that streams every pipeline event in real time, with timestamps and type-coloured lines (start / info / done / error / complete)
- An elapsed timer

### Results View

On completion, the full report is loaded and rendered into tabbed panels:

- **Overview** — ICP score with visual bar, strategic verdict banner (GREEN / AMBER / RED), company summary
- **Brand Identity** — colour swatches rendered from extracted hex values, font list, tone assessment
- **Market** — sentiment, share of voice, perception gap
- **Competitors** — competitor cards with experiential activity and gap analysis
- **Events** — experiential timeline, maturity score, formats missing
- **Reputation** — Reddit sentiment, praise and complaint themes, NPS signal
- **Watchouts** — verdict, leadership changes, timing recommendation
- **Decision Makers** — buying committee with relevance scores and personalisation hooks
- **Contacts** — verified/inferred email cards with recommended outreach channel
- **Outreach** — 4-touch sequence rendered per contact, copy-ready
- **Tracking** — per-contact tracking IDs, pixel URLs, dashboard links

### Multi-Person Outreach

The contacts and outreach panels list all committee members identified by P09 and P10, not just the primary contact. Each contact card shows their email confidence level and recommended channel.

### PDF Export

The rendered report can be exported as a PDF directly from the browser using the browser's native print-to-PDF functionality, formatted to avoid mid-card page breaks.

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
| `OPENAI_API_KEY` | Yes | OpenAI API key — used for all LLM synthesis |
| `APIFY_TOKEN_1` | Yes | Apify token for P01 (Company Overview) and P02 (Brand Identity) |
| `APIFY_TOKEN_2` | No | Apify token for P03 (Market Position) and P04 (Competitor Mapping) |
| `APIFY_TOKEN_3` | No | Apify token for P05 (Brand Activity) and P06 (Experiential Footprint) |
| `APIFY_TOKEN_4` | No | Apify token for P07 (Reputation Research) and P08 (Strategic Watchouts) |
| `APIFY_TOKEN_5` | No | Apify token for P09 (Decision Makers) and P10 (Contact Intelligence) |
| `HUNTER_API_KEY` | No | Hunter.io key for email lookup in P10 |
| `APP_ENV` | No | `development` or `production` (default: `development`) |
| `LOG_LEVEL` | No | Structlog level (default: `INFO`) |
| `OUTPUT_DIR` | No | Directory for JSON report output (default: `./outputs`) |
| `MAX_RETRIES` | No | Retry count for API calls (default: `2`) |
| `REQUEST_TIMEOUT` | No | HTTP request timeout in seconds (default: `30`) |
| `RATE_LIMIT_DELAY` | No | Seconds between Apify calls (default: `1`) |
| `API_HOST` | No | FastAPI bind address (default: `0.0.0.0`) |
| `API_PORT` | No | FastAPI port (default: `8000`) |
| `TRACKING_BASE` | No | Base URL for tracking pixel and click endpoints. Set to your deployed URL in production. |
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
| `pipeline_log` | array | Full timestamped log feed (type: start / info / done / error / complete) |
| `result` | object | Summary object on completion (null while running) |
| `run_id` | string | ID to use with `/report/{run_id}` |
| `elapsed` | float | Total seconds elapsed on completion |

---

### GET /report/{run_id}

Fetch the full persisted report from disk.

Returns the complete 12-pipeline output JSON including all `pipelines[key].output` objects.

---

### GET /reports

List all saved reports, sorted by most recent.

**Response:**
```json
{
  "reports": [
    {
      "run_id": "mamaearth-a1b2c3",
      "company": "Mamaearth",
      "completed_at": "2025-05-02T14:30:00",
      "status": "success",
      "elapsed": 127.4
    }
  ]
}
```

---

### GET /track/open/{tracking_id}

Returns a 1×1 transparent GIF. Increments open count and engagement score for the tracking record.

First open: +1 point. Subsequent opens (3+): +3 points.

---

### GET /track/click/{tracking_id}/{touch}?redirect={url}

Logs a link click event (+5 points) and redirects the recipient to `redirect`. The `touch` parameter identifies which touch in the sequence was clicked.

---

### POST /track/event

Log a manual engagement event (LinkedIn accepted, reply received, meeting booked).

**Request body:**
```json
{
  "tracking_id": "abc123def456",
  "event_type": "reply",
  "touch": 1,
  "metadata": {}
}
```

---

### GET /track/dashboard/{tracking_id}

Returns the current engagement state for a contact.

**Response:**
```json
{
  "tracking_id": "abc123def456",
  "score": 11,
  "status": "WARM",
  "events": [...]
}
```

Status thresholds: COLD (0) → OPENED (1+) → ENGAGED (3+) → WARM (10+) → HOT (20+).

---

### GET /debug/{job_id}

Returns the full internal job state including traceback on failure. For development use.

---

### GET /config/check

Returns which API integrations are configured and ready.

---

### GET /health

Liveness check. Returns `{"status": "ok", "version": "2.0.0"}`.

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
│   ├── style.css            # Dark design system (neon green terminal aesthetic)
│   └── app.js               # API client, live terminal feed, report renderer
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
│   ├── claude_client.py     # OpenAI wrapper (GPT-4o-mini / GPT-4o)
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
