# Pipeline 09 — Decision Makers · Skill File

## Identity
- **Pipeline ID:** `p09_decision_makers`
- **Class:** `DecisionMakersPipeline`
- **File:** `pipelines/p09_decision_makers/pipeline.py`

## Purpose
Answers: *"Who exactly should we contact at this brand — who owns experiential marketing budget, who influences it, and who will champion us internally?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p09_decision_makers.pipeline import DecisionMakersPipeline
p = DecisionMakersPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Architecture — 4-Tier Guarantee (NEVER returns empty)

```
Tier 1: Apify LinkedIn Employees Scraper (real people via Google SERP)
         ↓ if < 3 people found
Tier 2: GPT brand knowledge (FMCG parent resolution: Dove→HUL, Maggi→Nestlé etc.)
         MERGES with Tier 1 results
         ↓ if < 2 people total
Tier 3: Universal inference (generates realistic contacts with accurate titles)
         MERGES with existing results
         ↓ if GPT crashes / returns null
Tier 4: Python safety net — returns 3 role-based placeholders
```

## FMCG Brand → Parent Company Mapping (in prompt)
| Brand | Parent Company |
|-------|---------------|
| Dove, Lux, Lifebuoy, Surf | HUL (Hindustan Unilever) |
| Maggi, KitKat, Nescafé | Nestlé India |
| Gillette, Ariel, Pampers | P&G India |
| Pepsi, Lay's, Kurkure | PepsiCo India |
| Coca-Cola, Thums Up, Sprite | Coca-Cola India |

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `buying_committee` | array | 3-5 decision maker objects |
| `buying_committee[].name` | string | "Priya Nair" |
| `buying_committee[].title` | string | "Executive Director, Beauty & Wellbeing" |
| `buying_committee[].role_type` | string | Economic Buyer / Influencer / Champion |
| `buying_committee[].outreach_priority` | string | PRIMARY / SECONDARY |
| `buying_committee[].linkedin_url` | string/null | LinkedIn profile URL |
| `buying_committee[].decision_relevance_score` | int 0-5 | 4 |
| `buying_committee[].personalisation_hook` | string | Research hook for outreach |
| `primary_contact` | string | Top person's name |
| `confidence_level` | string | HIGH / MEDIUM / LOW |
| `parent_company` | string/null | "HUL" for Dove |

## Apify Actor Used
`automation-lab/linkedin-company-employees-scraper`
- Uses Google SERP — no LinkedIn cookie required
- Token: `APIFY_TOKEN_1`

## Common Issues & Fixes
- **Only 1 person returned** → was fixed by making Tier 2 run when < 3; re-run to verify
- **Placeholder names (e.g. "VP Marketing — Dove")** → Tier 4 fired; real people can't be found automatically — verify manually on LinkedIn
- **Wrong company (wrong HUL person for Dove)** → check `parent_company` field; expected for subsidiary brands

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p09_decision_makers/pipeline.py`
