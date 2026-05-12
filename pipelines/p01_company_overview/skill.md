# Pipeline 01 — Company Overview · Skill File

## Identity
- **Pipeline ID:** `p01_company_overview`
- **Class:** `CompanyOverviewPipeline`
- **File:** `pipelines/p01_company_overview/pipeline.py`

## Purpose
Answers: *"What kind of company is this, do they have budget, and are they a good ICP fit for StepOneXP?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p01_company_overview.pipeline import CompanyOverviewPipeline
p = CompanyOverviewPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Data Sources
| Source | What it gets |
|--------|-------------|
| Fast HTTP crawl (4 pages) | About, team, press pages |
| Google Search x2 | Funding, employees, founding year |
| Claude Haiku synthesis | Structured JSON output |

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `icp_fit_score` | int 0-100 | 85 |
| `business_model` | string | B2C |
| `experiential_readiness` | string | HIGH / MEDIUM / LOW |
| `employee_count_range` | string | 1000+ |
| `funding_status` | string | Public |
| `marketing_maturity_score` | int 1-5 | 4 |
| `recommended_service` | string | Which StepOneXP service to pitch |
| `company_narrative` | string | 100-word summary |
| `key_facts` | array | 3-5 specific facts |

## ICP Scoring Logic
```
B2C brand         → +25 pts
200+ employees    → +25 pts
VC-backed/Public  → +25 pts
India presence    → +25 pts
Max               = 100 pts
```

## Common Issues & Fixes
- **No pages crawled** → check `company_url` is correct, try with/without `www.`
- **Low ICP score** → expected for B2B/small brands — check `experiential_readiness` separately
- **Empty key_facts** → website may block crawlers; try a known-good URL

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p01_company_overview/pipeline.py`
