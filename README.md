# BrandScope — Brand Intelligence & Outreach Automation System

> Built for the **StepOneXP Hackathon** · Experiential Marketing Agency, India

BrandScope takes two inputs — a company name and a one-line category — and produces a complete brand intelligence dossier with personalised outreach sequences, delivered through a 12-pipeline friction architecture.

---

## What it does

| Input | Output |
|-------|--------|
| Company name + website + one-line category | Full brand dossier (12 pipeline outputs) |

The system runs every client through 12 sequential pipelines, each with three mandatory layers:

```
L1: RAW FETCH    →  real data from Apify actors / Hunter.io
L2: STRUCTURED EXTRACT  →  Python parser transforms raw → clean JSON
L3: SYNTHESISE   →  Claude Haiku/Sonnet produces the final insight
```

No pipeline can shortcut this. Every output is grounded in scraped data.

---

## 12 Pipelines

| # | Pipeline | Purpose | Key Output |
|---|----------|---------|------------|
| P01 | Company Overview | Business model, size, funding, ICP fit | `icp_fit_score` (0–100) |
| P02 | Brand Identity | CSS color extraction, fonts, tone | `primary_colors`, `brand_voice_keywords` |
| P03 | Market Position | Search sentiment, share of voice | `brand_sentiment`, `pitch_implication` |
| P04 | Competitor Mapping | 4–6 direct competitors, experiential gaps | `experiential_white_space` |
| P05 | Brand Activity | Campaign timeline, budget signals | `upcoming_opportunity_window` |
| P06 | Experiential Footprint ⭐ | Every event/activation ever done | `experiential_maturity_score`, `opening_line_for_pitch` |
| P07 | Reputation Research | Reddit + reviews, authentic sentiment | `overall_reputation_score`, `reputation_watchout` |
| P08 | Strategic Watchouts | Leadership changes, controversies, timing | `overall_verdict` (GREEN/AMBER/RED) |
| P09 | Decision Makers | Buying committee with relevance scores | `buying_committee`, `personalisation_hook` |
| P10 | Contact Intelligence | Verified emails, recommended channel | `email_confidence`, `recommended_channel` |
| P11 | Outreach Sequence | 4-touch email + LinkedIn sequence | 4 ready-to-send messages per contact |
| P12 | Tracking Setup | Pixel tracking, engagement scoring | `dashboard_entries`, status thresholds |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI Backend                   │
│  POST /analyse  →  background task  →  12 pipelines │
│  GET  /status/{job_id}   (polling)                  │
│  GET  /report/{run_id}   (full JSON)                │
│  GET  /track/open/{id}   (pixel GIF)                │
│  GET  /track/click/{id}/{touch}  (redirect)         │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│               Orchestrator (orchestrator.py)         │
│  P01 → P02 → P03 → P04 → P05 → P06                 │
│       → P07 → P08 → P09 → P10(p09) → P11(all) → P12│
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│          Each Pipeline: BasePipeline ABC             │
│   fetch()  →  extract()  →  synthesise()  →  dict   │
└─────────────────────────────────────────────────────┘
```

### Data flow between pipelines
- P09 output → P10 (passes buying committee for contact lookup)
- All P01–P10 outputs → P11 (personalisation context for outreach)
- P11 output → P12 (generates tracking IDs + pixels)

---

## API Stack (all free tiers)

| Service | Purpose | Free Limit |
|---------|---------|-----------|
| [Apify](https://apify.com) | Web scraping actors | $5/month free (~500 actor runs) |
| [Anthropic Claude](https://anthropic.com) | LLM synthesis | Pay-per-token (Haiku ~$0.001/run) |
| [Hunter.io](https://hunter.io) | Email lookup | 25 searches/month |

### Apify Token Rotation (5 accounts)
```
Group 1 (APIFY_TOKEN_1) → P01, P02
Group 2 (APIFY_TOKEN_2) → P03, P04
Group 3 (APIFY_TOKEN_3) → P05, P06
Group 4 (APIFY_TOKEN_4) → P07, P08
Group 5 (APIFY_TOKEN_5) → P09, P10
```

---

## Cost per full analysis run

| Layer | Model/Service | Approx cost |
|-------|--------------|-------------|
| 12× L1 Fetches | Apify actors | ~$0.05 |
| 11× L3 Synthesis | Claude Haiku | ~$0.04 |
| 1× L3 Outreach | Claude Sonnet | ~$0.10 |
| Email lookup | Hunter.io free | $0 |
| **Total** | | **~$0.19/run** |

---

## Setup

### 1. Clone and install
```bash
git clone https://github.com/mushaahamed/brand-intelligence-system.git
cd brand-intelligence-system
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in all API keys
```

Required keys in `.env`:
```
APIFY_TOKEN_1=apify_api_xxxx
APIFY_TOKEN_2=apify_api_xxxx
APIFY_TOKEN_3=apify_api_xxxx
APIFY_TOKEN_4=apify_api_xxxx
APIFY_TOKEN_5=apify_api_xxxx
ANTHROPIC_API_KEY=sk-ant-xxxx
HUNTER_API_KEY=xxxx
```

### 3. Test APIs
```bash
python -m pytest tests/ -v
```

### 4. Run the API server
```bash
uvicorn api.main:app --reload --port 8000
```

### 5. Open the frontend
Navigate to `http://localhost:8000` — the FastAPI server also serves the frontend.

Or open `frontend/index.html` directly in your browser (works against `localhost:8000`).

### 6. CLI usage (no server needed)
```bash
python orchestrator.py "Mamaearth" "https://mamaearth.in" "D2C skincare brand targeting millennial women in India"
```
Output saved to `outputs/{run_id}.json`.

---

## Running a smoke test
```bash
SMOKE=1 python -m pytest tests/test_apis.py::TestSmoke -v
```
Runs P01 against Mamaearth with all real APIs — takes ~90 seconds.

---

## Repository structure

```
brand-intelligence-system/
├── api/
│   ├── main.py              # FastAPI app + tracking endpoints
│   └── models.py            # Pydantic request/response models
├── config/
│   ├── settings.py          # Central config (tokens, models, paths)
│   └── apify_config.py      # Actor IDs + token group mapping
├── frontend/
│   ├── index.html           # Single-page app
│   ├── style.css            # Dark design system
│   └── app.js               # API client + result renderer
├── pipelines/
│   ├── base.py              # Abstract BasePipeline (3-layer enforcer)
│   ├── p01_company_overview/
│   │   ├── pipeline.py
│   │   ├── prompt.md
│   │   ├── schema.json
│   │   └── README.md
│   ├── p02_brand_identity/   … (same structure)
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
│   ├── apify_client.py      # Actor runner + token rotation
│   ├── claude_client.py     # Haiku/Sonnet wrappers
│   ├── hunter_client.py     # Email lookup + pattern inference
│   └── helpers.py           # Shared utilities
├── tests/
│   ├── test_apis.py         # API + unit + integration tests
│   └── conftest.py
├── orchestrator.py          # Chains all 12 pipelines
├── requirements.txt
├── .env.example
└── README.md
```

---

## ICP Fit Score (0–100)

The ICP score tells StepOneXP how strong a fit the target company is for their services:

| Signal | Points |
|--------|--------|
| B2C brand (vs B2B) | +25 |
| 200+ employees | +25 |
| VC-backed or Series A+ | +25 |
| India presence (HQ or major market) | +25 |

| Score | Verdict |
|-------|---------|
| 75–100 | Strong ICP Fit ✓ |
| 40–74 | Medium Fit |
| 0–39 | Low Fit |

---

## Engagement Tracking

Every outreach email gets a 1×1 transparent GIF tracking pixel and link wrapping. Engagement is scored:

| Event | Points | Status Unlock |
|-------|--------|---------------|
| Email opened | +1 | OPENED |
| Link clicked | +5 | ENGAGED |
| LinkedIn accepted | +4 | ENGAGED |
| Email/LinkedIn reply | +10 | WARM |
| Meeting booked | +20 | HOT |

---

## Unique selling points for the hackathon

1. **3-Layer Friction** — No output ever comes from a single LLM call. Every insight is grounded in real scraped data.
2. **CSS Color Extraction** — Brand colors are pulled directly from the company's CSS files, not Google Images.
3. **Reddit-First Reputation** — Authentic consumer opinion, not brand-managed reviews.
4. **Role-Typed Outreach** — Pitch tone changes automatically based on the contact's role (CMO vs Events Manager vs CEO).
5. **Full tracking loop** — From first email send to meeting booked, all in one system.

---

## License
MIT — build on it, improve it, ship it.

Built by **mushaahamed** for the StepOneXP Hackathon 2024.
