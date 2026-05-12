# Skill: p06-experiential-footprint

## Trigger
Activate when user says any of:
- "run p06", "p06 for [brand]", "pipeline 6 for [brand]"
- "experiential footprint for [brand]"
- "events history for [brand]"
- "has [brand] done experiential"
- "experiential maturity of [brand]"
- "events score for [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p06_experiential_footprint.pipeline import ExperientialFootprintPipeline
p = ExperientialFootprintPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Searches for the brand's history in experiential marketing — events, pop-ups, roadshows, exhibitions, sponsorships. Produces a maturity score so StepOneXP knows whether to sell the concept or sell an upgrade.

## Key Output Fields
- `events_timeline` — named events with year and type
- `experiential_maturity_score` — 1-5
  - 1 = Never done experiential
  - 3 = Regular activations, no flagship
  - 5 = Full experiential programme
- `events_frequency` — Regular / Occasional / Rare / None
- `event_types_used` — Pop-up / Roadshow / Exhibition / Concert
- `biggest_event` — largest known activation
- `experiential_gap` — what format they haven't tried yet
- `stepone_recommendation` — which StepOneXP format fits best

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p06_experiential_footprint/pipeline.py`
