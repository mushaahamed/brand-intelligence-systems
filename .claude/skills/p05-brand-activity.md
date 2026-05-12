# Skill: p05-brand-activity

## Trigger
Activate when user says any of:
- "run p05", "p05 for [brand]", "pipeline 5 for [brand]"
- "brand activity for [brand]"
- "recent campaigns of [brand]"
- "what has [brand] been doing"
- "marketing activity for [brand]"
- "budget signal for [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p05_brand_activity.pipeline import BrandActivityPipeline
p = BrandActivityPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Searches for the brand's marketing activity over the last 24 months — campaigns, PR, partnerships, sponsorships — and infers budget signal. Used in outreach to reference real campaigns and show the rep has done their research.

## Key Output Fields
- `recent_campaigns` — named campaigns with dates
- `last_major_campaign` — most notable recent campaign
- `budget_signal` — HIGH / MEDIUM / LOW (inferred spend level)
- `partnership_types` — Influencer / Celebrity / Sport / CSR
- `digital_vs_physical` — where their spend is skewed
- `campaign_frequency` — how often they launch major campaigns
- `experiential_gap` — what StepOneXP can fill

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p05_brand_activity/pipeline.py`
