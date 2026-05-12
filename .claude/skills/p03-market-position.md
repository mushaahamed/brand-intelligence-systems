# Skill: p03-market-position

## Trigger
Activate when user says any of:
- "run p03", "p03 for [brand]", "pipeline 3 for [brand]"
- "market position for [brand]"
- "brand sentiment for [brand]"
- "share of voice for [brand]"
- "how is [brand] perceived"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p03_market_position.pipeline import MarketPositionPipeline
p = MarketPositionPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Searches Google for brand perception signals, reviews, and competitor mentions. Produces a sentiment + share-of-voice profile used in the StepOneXP pitch to show where the brand sits in its category.

## Key Output Fields
- `brand_sentiment` — POSITIVE / NEUTRAL / NEGATIVE / MIXED
- `share_of_voice_level` — HIGH / MEDIUM / LOW
- `perception_gap_score` — 1-5 (how far perception lags reality)
- `positioning_summary` — how the brand is positioned in market
- `key_differentiators` — what makes them stand out
- `vulnerability_points` — where competitors can attack
- `experiential_gap` — where StepOneXP can add the most value

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p03_market_position/pipeline.py`
