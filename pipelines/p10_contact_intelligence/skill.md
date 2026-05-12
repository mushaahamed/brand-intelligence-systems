# Pipeline 10 — Contact Intelligence · Skill File

## Identity
- **Pipeline ID:** `p10_contact_intelligence`
- **Class:** `ContactIntelligencePipeline`
- **File:** `pipelines/p10_contact_intelligence/pipeline.py`

## Purpose
Answers: *"What's the actual email address for each person P09 found — verified or pattern-inferred — so we can reach them directly?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p10_contact_intelligence.pipeline import ContactIntelligencePipeline
# P10 needs P09 output as input
p09_output = {
    'buying_committee': [
        {'name': 'Priya Nair', 'title': 'VP Marketing', 'company': 'HUL', 'linkedin_url': None}
    ]
}
p = ContactIntelligencePipeline('Dove', 'https://dove.com', 'FMCG Skincare')
p._p09_output = p09_output  # inject P09 data
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Architecture
1. Takes `buying_committee` from P09 as input
2. For each person → Hunter.io email finder API
3. If Hunter finds verified email → use it
4. If not → pattern-infer using company domain pattern
5. Returns enriched contact list with confidence scores

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `contacts` | array | Enriched contact objects |
| `contacts[].name` | string | "Priya Nair" |
| `contacts[].email` | string/null | "priya.nair@hul.com" |
| `contacts[].email_confidence` | int 0-100 | 78 |
| `contacts[].email_status` | string | verified / pattern-inferred / not found |
| `contacts[].linkedin` | string/null | LinkedIn URL |
| `contacts[].channel_recommendation` | string | email / linkedin / both |
| `email_pattern` | string | `{first}.{last}@hul.com` |
| `verified_emails` | int | 2 |
| `total_contacts` | int | 4 |

## Email Confidence Guide
```
90-100 = Verified (Hunter.io confirmed deliverable)
60-89  = Pattern-inferred (domain pattern matched, not verified)
0-59   = Low confidence (guessed from name + domain)
```

## APIs Used
- **Hunter.io** — email finder and domain pattern search
  - Token: `HUNTER_API_KEY` env var
  - Rate limit: 25 requests/month on free tier; 500 on paid

## Common Issues & Fixes
- **All emails "pattern-inferred"** → Hunter.io couldn't verify; emails are still usable, just verify before cold outreach
- **No emails found** → company uses custom email domain (e.g. `@dove.com` vs `@hul.com`); P10 infers from domain patterns
- **Low confidence scores** → brand uses first-name-only emails or initials; outreach via LinkedIn DM recommended instead

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p10_contact_intelligence/pipeline.py`
