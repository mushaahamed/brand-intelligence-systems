# Skill: p01-company-overview

## Trigger
Activate when user says any of:
- "run p01", "p01 for [brand]", "pipeline 1 for [brand]"
- "company overview for [brand]"
- "ICP score for [brand]"
- "run overview on [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p01_company_overview.pipeline import CompanyOverviewPipeline
p = CompanyOverviewPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Crawls the brand website + Google → produces company profile and ICP fit score for StepOneXP pitch.

## Key Output Fields
- `icp_fit_score` (0-100) — higher = better fit for StepOneXP
- `experiential_readiness` — HIGH / MEDIUM / LOW
- `business_model` — B2C / B2B / B2B2C
- `employee_count_range` — 1-10 / 11-50 / 51-200 / 200-1000 / 1000+
- `funding_status` — Bootstrapped / Seed / Series A-C+ / Public
- `recommended_service` — which StepOneXP service to lead with
- `company_narrative` — 100-word summary

## ICP Score Logic
B2C +25 · 200+ employees +25 · VC/Public +25 · India presence +25 = max 100

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p01_company_overview/pipeline.py`
