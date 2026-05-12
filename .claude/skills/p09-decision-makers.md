# Skill: p09-decision-makers

## Trigger
Activate when user says any of:
- "run p09", "p09 for [brand]", "pipeline 9 for [brand]"
- "decision makers for [brand]"
- "who to contact at [brand]"
- "buying committee for [brand]"
- "find people at [brand]"
- "who manages marketing at [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p09_decision_makers.pipeline import DecisionMakersPipeline
p = DecisionMakersPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Finds 3-5 marketing decision makers via Apify LinkedIn scraper + GPT knowledge. Uses a 4-tier guarantee so buying_committee is NEVER empty.

## 4-Tier Guarantee
1. Apify LinkedIn employee scraper
2. GPT brand knowledge — runs if < 3 found, MERGES results
3. Universal inference — runs if < 2 total
4. Python safety net — 3 role-based placeholders if all else fails

## FMCG Brand → Parent Company
Dove/Lux/Surf → HUL · Maggi/KitKat → Nestlé · Gillette/Ariel → P&G · Pepsi/Lays → PepsiCo · Coke/Thums Up → Coca-Cola India

## Key Output Fields
- `buying_committee` — array of 3-5 people
  - `.name`, `.title`, `.company`
  - `.role_type` — Economic Buyer / Influencer / Champion
  - `.outreach_priority` — PRIMARY / SECONDARY
  - `.linkedin_url` — profile URL or null
  - `.decision_relevance_score` — 0-5
  - `.personalisation_hook` — research note for outreach
- `primary_contact` — top person's name
- `confidence_level` — HIGH / MEDIUM / LOW
- `parent_company` — e.g. "HUL" for Dove

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p09_decision_makers/pipeline.py`
