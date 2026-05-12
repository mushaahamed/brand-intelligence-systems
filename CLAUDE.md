# Brand Intelligence System — Claude Guide

## What This Project Is
A 12-pipeline brand intelligence system for **StepOneXP** (experiential marketing agency, India).
Given a brand name + URL, it runs 12 parallel pipelines and produces a full pitch intelligence report.

**Live on Railway:** Auto-deploys on every push to `main`.
**Frontend:** Dark-mode UI at `/` — neon green (`#00D37A`) theme.
**Backend:** FastAPI + Python. `orchestrator.py` runs all 12 pipelines.

---

## Available Skills (14 total)

### Utility Skills
| Skill file | Trigger | What it does |
|------------|---------|-------------|
| `github-sync.md` | Paste any GitHub URL from this repo | Fetches raw file → writes locally → syntax check. NO QUESTIONS. |
| `run-pipeline.md` | "run [pipeline] for [brand]" (generic) | Fallback runner if no specific pipeline skill matched |

### Pipeline Skills — one per pipeline, no questions, runs immediately
| Skill file | Triggers | Pipeline |
|------------|---------|---------|
| `p01-company-overview.md` | "run p01", "company overview for X", "ICP score for X" | P01 — Company size, ICP score, funding |
| `p02-brand-identity.md` | "run p02", "brand identity for X", "brand colours for X" | P02 — Colours, fonts, tone of voice |
| `p03-market-position.md` | "run p03", "market position for X", "brand sentiment for X" | P03 — Sentiment, share of voice, perception gap |
| `p04-competitor-mapping.md` | "run p04", "competitors of X", "competitive landscape for X" | P04 — Competitor list + urgency score |
| `p05-brand-activity.md` | "run p05", "recent campaigns of X", "budget signal for X" | P05 — Campaigns, partnerships, budget signal |
| `p06-experiential-footprint.md` | "run p06", "events history for X", "experiential maturity of X" | P06 — Events timeline, maturity score |
| `p07-reputation-research.md` | "run p07", "reputation of X", "reddit sentiment for X" | P07 — Reddit + review sentiment, reputation score |
| `p08-strategic-watchouts.md` | "run p08", "risks for X", "should we pitch X" | P08 — Risk flags, GREEN/AMBER/RED verdict |
| `p09-decision-makers.md` | "run p09", "decision makers for X", "who to contact at X" | P09 — Buying committee (3-5 people guaranteed) |
| `p10-contact-intelligence.md` | "run p10", "find emails for X", "contact intelligence for X" | P10 — Email lookup via Hunter.io |
| `p11-outreach.md` | "run p11", "outreach for X", "write emails for X" | P11 — 4-touch sequences per contact (Arjun persona) |
| `p12-tracking.md` | "run p12", "tracking for X", "engagement pixel for X" | P12 — Engagement tracking pixel + scoring |

---

## Pipeline Execution Order
```
P01-P09  →  run in PARALLEL (ThreadPoolExecutor)
              ↓
            P10  (needs P09 buying_committee)
              ↓
            P11  (needs P09+P10 contacts + P01-P08 brand data)
              ↓
            P12  (needs P11 sequences)
```

---

## Key Architecture

### P09 — 4-Tier Contact Guarantee (never returns empty)
1. Apify LinkedIn scraper (real people)
2. GPT brand knowledge — runs if < 3 found, merges with Tier 1
3. Universal inference — runs if < 2 total, targets 3+
4. Python safety net — 3 role placeholders if GPT fails

### FMCG Brand → Parent Company (P09 knows this)
Dove/Lux/Surf → HUL · Maggi/KitKat → Nestlé · Gillette/Ariel → P&G · Pepsi/Lays → PepsiCo · Coke/Thums Up → Coca-Cola India

### P11 — Arjun Persona + Touch Lengths
Touch 1: 150-200 words (email) · Touch 2: 150-200 chars (LinkedIn) · Touch 3: 250-320 words (competitor intel email) · Touch 4: 100-130 words (warm close)

### Frontend Color Theme
Neon green `#00D37A` — CSS var `--indigo`. Version stamp: `?v=20260512e`.

---

## Project Structure
```
brand-intelligence-system/
├── CLAUDE.md                          ← This file
├── orchestrator.py                    ← Runs all 12 pipelines
├── .claude/
│   └── skills/
│       ├── github-sync.md             ← Paste GitHub URL → write file
│       ├── run-pipeline.md            ← Generic pipeline runner
│       ├── p01-company-overview.md
│       ├── p02-brand-identity.md
│       ├── p03-market-position.md
│       ├── p04-competitor-mapping.md
│       ├── p05-brand-activity.md
│       ├── p06-experiential-footprint.md
│       ├── p07-reputation-research.md
│       ├── p08-strategic-watchouts.md
│       ├── p09-decision-makers.md
│       ├── p10-contact-intelligence.md
│       ├── p11-outreach.md
│       └── p12-tracking.md
├── pipelines/
│   ├── base.py                        ← BasePipeline (fetch→extract→synthesise)
│   ├── p01_company_overview/
│   │   ├── pipeline.py
│   │   ├── skill.md                   ← Pipeline-specific docs + run command
│   │   ├── prompt.md
│   │   └── schema.json
│   └── ... (p02-p12 same structure)
├── frontend/
│   ├── index.html
│   ├── app.js                         ← ?v=20260512e
│   └── style.css                      ← Neon green theme
├── utils/
│   ├── apify_client.py
│   ├── claude_client.py               ← OpenAI GPT calls
│   └── helpers.py
└── config/settings.py                 ← OPENAI_MODEL, OPENAI_MODEL_FULL
```

---

## Environment Variables
```
OPENAI_API_KEY    → GPT-4o and GPT-4o-mini
APIFY_TOKEN_1     → Primary (P01, P06, P09)
APIFY_TOKEN_2     → Secondary (P04, P07)
HUNTER_API_KEY    → Email lookup (P10)
```
Check: `python -c "from config.settings import OPENAI_MODEL; print('env ok')"`

## GitHub Repo
`https://github.com/mushaahamed/brand-intelligence-systems`
