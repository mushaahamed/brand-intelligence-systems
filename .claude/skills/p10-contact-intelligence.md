# Skill: p10-contact-intelligence

## Trigger
Activate when user says any of:
- "run p10", "p10 for [brand]", "pipeline 10 for [brand]"
- "contact intelligence for [brand]"
- "find emails for [brand]"
- "email addresses for [brand]"
- "Hunter.io for [brand]"
- "verify contacts for [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p10_contact_intelligence.pipeline import ContactIntelligencePipeline
p = ContactIntelligencePipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Takes the buying_committee from P09 and looks up email addresses via Hunter.io. Infers email pattern from company domain and returns confidence scores.

## Key Output Fields
- `contacts` — enriched contact list
  - `.name`, `.title`, `.company`
  - `.email` — found or pattern-inferred
  - `.email_confidence` — 0-100
  - `.email_status` — verified / pattern-inferred / not found
  - `.linkedin` — URL or null
  - `.channel_recommendation` — email / linkedin / both
- `email_pattern` — e.g. `{first}.{last}@hul.com`
- `verified_emails` — count of Hunter-verified emails
- `total_contacts` — total contacts enriched

## Email Confidence Guide
- 90-100 = Hunter.io verified deliverable
- 60-89 = Pattern-inferred, not verified
- 0-59 = Low confidence, use LinkedIn DM instead

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p10_contact_intelligence/pipeline.py`
