# Skill: p08-strategic-watchouts

## Trigger
Activate when user says any of:
- "run p08", "p08 for [brand]", "pipeline 8 for [brand]"
- "watchouts for [brand]"
- "risks for [brand]"
- "should we pitch [brand]"
- "is [brand] safe to pitch"
- "red flags for [brand]"
- "pitch timing for [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p08_strategic_watchouts.pipeline import StrategicWatchoutsPipeline
p = StrategicWatchoutsPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Scans for layoffs, leadership changes, controversies, budget freezes, legal trouble. Produces a GREEN / AMBER / RED verdict that affects how aggressive P11 outreach should be.

## Key Output Fields
- `overall_verdict` — GREEN / AMBER / RED
  - GREEN = full pitch, normal tone
  - AMBER = soften slightly, avoid bold ROI claims
  - RED = don't pitch hard, wait or flag to sales team
- `watchout_flags` — specific risks found
- `leadership_stability` — STABLE / CHANGING / UNCERTAIN
- `budget_risk` — LOW / MEDIUM / HIGH
- `controversy_level` — NONE / MINOR / SIGNIFICANT / SEVERE
- `timing_recommendation` — "Pitch now" / "Wait 3 months" / "Soften pitch"

## Integration
P11 outreach automatically reads `overall_verdict` from P08 and adjusts tone.

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p08_strategic_watchouts/pipeline.py`
