# Skill: p12-tracking

## Trigger
Activate when user says any of:
- "run p12", "p12 for [brand]", "pipeline 12 for [brand]"
- "tracking for [brand]"
- "set up tracking for [brand]"
- "engagement tracking for [brand]"
- "pixel for [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p12_tracking.pipeline import TrackingPipeline
p = TrackingPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Generates unique tracking pixels and click-redirect links for each contact in the outreach sequence. Enables engagement scoring so the sales team knows who opened and clicked.

## Key Output Fields
- `tracking_records` — one record per contact
  - `.contact_name`
  - `.pixel_url` — 1×1 tracking image URL
  - `.click_links` — wrapped CTA links
  - `.engagement_score` — 0-100 (starts at 0, increases on open/click)
  - `.status` — NOT_SENT / SENT / OPENED / CLICKED

## Engagement Score
Fires when email is opened (pixel loads) or CTA is clicked. Score feeds back into P09 priority ranking on next brand run.

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p12_tracking/pipeline.py`
