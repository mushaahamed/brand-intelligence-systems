# Skill: p07-reputation-research

## Trigger
Activate when user says any of:
- "run p07", "p07 for [brand]", "pipeline 7 for [brand]"
- "reputation of [brand]"
- "reddit sentiment for [brand]"
- "what do people say about [brand]"
- "reputation score for [brand]"
- "consumer reviews for [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p07_reputation_research.pipeline import ReputationResearchPipeline
p = ReputationResearchPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Scrapes Reddit threads, review platforms, and news for authentic consumer opinion. Produces a reputation score and flags any controversies that should affect pitch timing or tone.

## Key Output Fields
- `overall_reputation_score` — 0-100
- `reputation_label` — STRONG / GOOD / MIXED / WEAK / DAMAGED
- `reddit_sentiment` — POSITIVE / NEUTRAL / NEGATIVE
- `top_positive_themes` — what consumers praise
- `top_negative_themes` — what consumers complain about
- `controversy_flags` — active controversies if any
- `nps_signal` — HIGH / MEDIUM / LOW
- `pitch_timing_note` — whether now is a good time to pitch

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p07_reputation_research/pipeline.py`
