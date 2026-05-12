# Skill: p04-competitor-mapping

## Trigger
Activate when user says any of:
- "run p04", "p04 for [brand]", "pipeline 4 for [brand]"
- "competitors of [brand]"
- "competitor mapping for [brand]"
- "who competes with [brand]"
- "competitive landscape for [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p04_competitor_mapping.pipeline import CompetitorMappingPipeline
p = CompetitorMappingPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Finds top 3-5 competitors, crawls their websites, and identifies what they're doing in experiential marketing. This data feeds directly into P11 Touch 3 (the "competitive intelligence email").

## Key Output Fields
- `competitors` — array of competitor objects
  - `.name` — competitor brand name
  - `.experiential_activity` — what they're doing in events/activations
  - `.threat_level` — HIGH / MEDIUM / LOW
- `competitive_urgency` — HIGH / MEDIUM / LOW (overall market pressure)
- `pitch_angle` — how to frame the competitive threat in outreach

## Note
P11 outreach Touch 3 (competitive intel email) pulls directly from this pipeline's output. Fix P04 if Touch 3 is naming the wrong competitor.

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p04_competitor_mapping/pipeline.py`
