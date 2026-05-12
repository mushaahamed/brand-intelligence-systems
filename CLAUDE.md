# Brand Intelligence System — Claude Guide

## What This Project Is
A 12-pipeline brand intelligence system for **StepOneXP** (experiential marketing agency, India).
Given a brand name + URL, it runs 12 parallel pipelines and produces a full pitch intelligence report.

**Live on Railway:** Deployed automatically on every push to `main`.
**Frontend:** Dark-mode React-style UI at `/` — neon green (`#00D37A`) theme.
**Backend:** FastAPI + Python, `orchestrator.py` runs all 12 pipelines.

---

## Available Skills

### `/github-sync` — Paste GitHub URL → Auto-write file
When the user pastes a GitHub URL from this repo, fetch the raw content and write it locally.
Skill file: `.claude/skills/github-sync.md`

### `/run-pipeline` — Run any pipeline by name
Run a single pipeline for testing without running the full 12-pipeline suite.
Skill file: `.claude/skills/run-pipeline.md`

---

## Pipeline Map

| ID | Folder | What it does | Key output |
|----|--------|-------------|------------|
| P01 | `p01_company_overview` | Company size, ICP score, funding | `icp_fit_score`, `experiential_readiness` |
| P02 | `p02_brand_identity` | Colours, fonts, tone, brand voice | `primary_colors`, `brand_tone` |
| P03 | `p03_market_position` | Sentiment, share of voice, gap | `brand_sentiment`, `perception_gap_score` |
| P04 | `p04_competitor_mapping` | Competitor list + urgency | `competitors`, `competitive_urgency` |
| P05 | `p05_brand_activity` | Recent campaigns, budget signal | `recent_campaigns`, `budget_signal` |
| P06 | `p06_experiential_footprint` | Events history, maturity score | `events_timeline`, `experiential_maturity_score` |
| P07 | `p07_reputation_research` | Reddit + review sentiment | `overall_reputation_score`, `reputation_label` |
| P08 | `p08_strategic_watchouts` | Risk flags, pitch timing | `overall_verdict`, `timing_recommendation` |
| P09 | `p09_decision_makers` | Buying committee (3-5 people) | `buying_committee`, `primary_contact` |
| P10 | `p10_contact_intelligence` | Email addresses + confidence | `contacts`, `email_pattern` |
| P11 | `p11_outreach` | 4-touch outreach sequences | `sequences` per contact |
| P12 | `p12_tracking` | Engagement tracking pixel | `tracking_records` |

Each pipeline has its own `skill.md` with full details, run command, and common fixes.

---

## Execution Order
```
P01-P09 run in PARALLEL (ThreadPoolExecutor)
     ↓
P10 (needs P09 buying_committee)
     ↓
P11 (needs P09 + P10 contacts, plus P01-P08 brand data)
     ↓
P12 (needs P11 sequences)
```

---

## Key Architecture Decisions

### P09 — 4-Tier Contact Guarantee
Never returns empty buying_committee:
1. Apify LinkedIn scraper
2. GPT brand knowledge (runs if < 3 found, merges results)
3. Universal inference (runs if < 2 total)
4. Python safety net (3 role-based placeholders if GPT fails)

### P11 — "Arjun" Persona
Outreach written as Arjun (senior account manager at StepOneXP).
Touch 1: 150-200 words | Touch 3: 250-320 words competitive intel | Touch 4: 100-130 words close.

### Frontend Color Theme
Neon green (`#00D37A`) — CSS var `--indigo`. All `rgba(99,102,241,...)` replaced with `rgba(0,211,122,...)`.

---

## Project Structure
```
brand-intelligence-system/
├── orchestrator.py          # Runs all 12 pipelines
├── pipelines/
│   ├── base.py              # BasePipeline (fetch→extract→synthesise)
│   ├── p01_company_overview/
│   │   ├── pipeline.py      # Pipeline code
│   │   ├── skill.md         # ← Claude skill file for this pipeline
│   │   ├── prompt.md        # LLM prompts
│   │   └── schema.json      # Output schema
│   └── ... (p02-p12 same structure)
├── frontend/
│   ├── index.html
│   ├── app.js               # Version stamp: ?v=20260512e
│   └── style.css            # Neon green theme
├── utils/
│   ├── apify_client.py      # Apify actor calls
│   ├── claude_client.py     # OpenAI GPT calls (via OpenAI SDK)
│   └── helpers.py           # safe_json_parse, make_run_id etc.
├── config/settings.py       # OPENAI_MODEL, OPENAI_MODEL_FULL etc.
├── CLAUDE.md                # ← This file
└── .claude/
    └── skills/
        ├── github-sync.md   # Paste GitHub URL → write file
        └── run-pipeline.md  # Run any pipeline on command
```

---

## Environment Variables
```
OPENAI_API_KEY       → GPT-4o and GPT-4o-mini
APIFY_TOKEN_1        → Primary Apify token (P01, P06, P09)
APIFY_TOKEN_2        → Secondary Apify token (P04, P07)
HUNTER_API_KEY       → Email lookup (P10)
```

Check: `python -c "from config.settings import OPENAI_MODEL; print('env ok')"`

---

## GitHub Repo
`https://github.com/mushaahamed/brand-intelligence-systems`

Deployed on Railway — every push to `main` triggers auto-deploy.
