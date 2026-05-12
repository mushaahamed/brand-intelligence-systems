# Pipeline 03 — Market Position · Skill File

## Identity
- **Pipeline ID:** `p03_market_position`
- **Class:** `MarketPositionPipeline`
- **File:** `pipelines/p03_market_position/pipeline.py`

## Purpose
Answers: *"How is this brand perceived vs competitors — what's their share of voice, sentiment, and where's the positioning gap we can exploit in our pitch?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p03_market_position.pipeline import MarketPositionPipeline
p = MarketPositionPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Data Sources
| Source | What it gets |
|--------|-------------|
| Google Search x3 | Brand reviews, sentiment signals, competitor mentions |
| News snippets | Earned media, PR presence |
| Claude synthesis | Structured positioning analysis |

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `brand_sentiment` | string | POSITIVE / NEUTRAL / NEGATIVE / MIXED |
| `share_of_voice_level` | string | HIGH / MEDIUM / LOW |
| `perception_gap_score` | int 1-5 | 3 |
| `positioning_summary` | string | How the brand is positioned |
| `key_differentiators` | array | What makes them stand out |
| `vulnerability_points` | array | Where competitors can attack |
| `experiential_gap` | string | Where StepOneXP adds value |

## Common Issues & Fixes
- **All NEUTRAL sentiment** → brand has low search presence; try adding "India" to search
- **Low share of voice** → accurate for challenger brands — good pitch angle (they need attention)

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p03_market_position/pipeline.py`
