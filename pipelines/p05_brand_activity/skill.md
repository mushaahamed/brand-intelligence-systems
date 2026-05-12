# Pipeline 05 — Brand Activity · Skill File

## Identity
- **Pipeline ID:** `p05_brand_activity`
- **Class:** `BrandActivityPipeline`
- **File:** `pipelines/p05_brand_activity/pipeline.py`

## Purpose
Answers: *"What has this brand actually been doing in marketing over the last 24 months — campaigns, partnerships, sponsorships — and what does their budget signal look like?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p05_brand_activity.pipeline import BrandActivityPipeline
p = BrandActivityPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Data Sources
| Source | What it gets |
|--------|-------------|
| Google Search x3 | Recent campaigns, PR, partnerships, sponsorships |
| News snippets | Campaign names, dates, brand collaborations |
| Claude synthesis | Structured activity timeline |

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `recent_campaigns` | array | Named campaigns with dates |
| `last_major_campaign` | string | "Real Beauty — Cannes 2024" |
| `budget_signal` | string | HIGH / MEDIUM / LOW |
| `partnership_types` | array | Influencer / Celebrity / Sport / CSR |
| `digital_vs_physical` | string | Skew of spend — digital-heavy or balanced |
| `campaign_frequency` | string | How often they launch major campaigns |
| `experiential_gap` | string | What's missing that StepOneXP can fill |

## Common Issues & Fixes
- **Old campaigns only** → brand has low recent PR; still useful — shows they need fresh activation
- **Empty campaigns** → try adding "India" or "campaign 2024 2025" to search

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p05_brand_activity/pipeline.py`
