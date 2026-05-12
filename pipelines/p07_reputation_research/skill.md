# Pipeline 07 — Reputation Research · Skill File

## Identity
- **Pipeline ID:** `p07_reputation_research`
- **Class:** `ReputationResearchPipeline`
- **File:** `pipelines/p07_reputation_research/pipeline.py`

## Purpose
Answers: *"What do real consumers think of this brand on Reddit, review platforms, and social — is there a reputation risk we need to factor into the pitch timing?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p07_reputation_research.pipeline import ReputationResearchPipeline
p = ReputationResearchPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Data Sources
| Source | What it gets |
|--------|-------------|
| Google Search x3 | Reddit threads, reviews, consumer complaints, news |
| Reddit site:reddit.com search | Authentic consumer voice |
| Review sites (G2, Trustpilot snippets) | Rating signals |
| Claude synthesis | Sentiment scoring + key themes |

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `overall_reputation_score` | int 0-100 | 72 |
| `reputation_label` | string | STRONG / GOOD / MIXED / WEAK / DAMAGED |
| `reddit_sentiment` | string | POSITIVE / NEUTRAL / NEGATIVE |
| `top_positive_themes` | array | What consumers praise |
| `top_negative_themes` | array | What consumers complain about |
| `controversy_flags` | array | Any active controversies |
| `nps_signal` | string | HIGH / MEDIUM / LOW |
| `pitch_timing_note` | string | Whether now is a good time to pitch |

## Common Issues & Fixes
- **MIXED on a well-known brand** → expected; use positive themes in pitch and avoid controversy topics
- **No Reddit data** → brand is niche; score defaults to NEUTRAL — not a red flag

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p07_reputation_research/pipeline.py`
