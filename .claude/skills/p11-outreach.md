# Skill: p11-outreach

## Trigger
Activate when user says any of:
- "run p11", "p11 for [brand]", "pipeline 11 for [brand]"
- "outreach for [brand]"
- "generate emails for [brand]"
- "write outreach for [brand]"
- "outreach sequence for [brand]"
- "4-touch for [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p11_outreach.pipeline import OutreachPipeline
p = OutreachPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Generates a personalised 4-touch outreach sequence per contact, written as Arjun (Senior Account Manager, StepOneXP). Uses brand research from P01-P08 and contacts from P09-P10. Powered by GPT-4o.

## Touch Specifications
| Touch | Channel | Day | Length |
|-------|---------|-----|--------|
| Touch 1 | Email | Day 1 | 150-200 words, 4 paragraphs |
| Touch 2 | LinkedIn | Day 3 | 150-200 chars max |
| Touch 3 | Email | Day 8 | 250-320 words, competitor intel |
| Touch 4 | Email | Day 15 | 100-130 words, warm close |

## Role-Based Framing
- CEO/MD → category dominance, competitive moat
- CMO/VP Marketing → brand equity, earned media
- Brand Manager → execution quality, end-to-end delivery
- Growth/Performance → CAC, conversion, attribution
- Category Manager → point-of-decision visibility

## Key Output Fields
- `sequences` — one sequence per contact
  - `.contact` — name, title, company
  - `.touch_1` — `{subject, body}`
  - `.touch_2` — `{message}`
  - `.touch_3` — `{subject, body}`
  - `.touch_4` — `{subject, body}`
- `primary_contact` — top contact + their full sequence

## Watchout Integration
Reads P08 `overall_verdict`: GREEN = full pitch · AMBER = softened · RED = de-escalated

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p11_outreach/pipeline.py`
