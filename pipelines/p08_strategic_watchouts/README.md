# P08 — Strategic Watchouts

Scans for risk signals before the pitch: leadership churn, budget freezes, active controversies, known agency conflicts. Produces a GREEN / AMBER / RED verdict with specific timing and tone recommendations.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | 5 targeted Google searches: layoffs/cost cuts, CMO/marketing leadership changes, controversies/lawsuits, recent funding news, existing agency partners | `google-search-scraper` |
| **L2 EXTRACT** | Parse news dates, people names, sentiment words (laid off, fired, controversy, raised, hired) | Python NER-lite parser |
| **L3 SYNTHESISE** | Risk-weight all signals → verdict + timing + tone recommendations | Claude Haiku |

## Output fields

| Field | Type | Description |
|-------|------|-------------|
| `overall_verdict` | GREEN/AMBER/RED | Go / Proceed with care / Hold |
| `leadership_changes[]` | object[] | Who changed roles + implication for the pitch |
| `active_controversies` | string[] | Open brand controversies |
| `funding_status` | string | Latest funding signal |
| `known_agency_relationships` | string[] | Incumbent agencies (competition awareness) |
| `cost_cutting_signals` | boolean | Any signs of budget freeze |
| `timing_recommendation` | string | When to approach |
| `pitch_tone_adjustment` | string | How to adjust the pitch tone |

## Why this matters
Pitching a brand during a CMO transition with a creativity-first pitch is a common fail mode. A new CMO needs quick wins; an ROI pitch lands better. This pipeline prevents that mistake.

## Cost estimate
~$0.02/run (5 searches + 1 Haiku synthesis)
