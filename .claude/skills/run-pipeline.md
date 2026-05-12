# Skill: run-pipeline

## Trigger
Use this skill when the user wants to run or test a specific pipeline, e.g.:
- "run p09 for Dove"
- "test p11 outreach for Nike"
- "run the decision makers pipeline on Mamaearth"
- "run pipeline 3 for Zomato"
- "test this pipeline" (after editing a pipeline file)
- `/run-pipeline p09 "Dove" "https://dove.com"`

## What This Skill Does
Runs a single pipeline (any of p01–p12) for a given brand and shows the output. Useful for testing changes without running the full 12-pipeline orchestration.

## Steps

1. **Identify pipeline** from user's message:
   - Number only (e.g. "p9", "pipeline 9", "09") → resolve to folder name using the mapping below
   - Name mentioned (e.g. "decision makers", "outreach", "contacts") → resolve to pipeline ID

2. **Get brand details** — ask the user for any missing info:
   - `company_name` (required) — e.g. "Dove"
   - `company_url` (optional, default to "https://www.{brand}.com") — e.g. "https://dove.com"
   - `category` (optional, default to "Consumer Brand India") — e.g. "FMCG Skincare"

3. **Run the pipeline** using this Python command:
   ```bash
   cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
   import json
   from pipelines.PIPELINE_FOLDER.pipeline import PIPELINE_CLASS
   p = PIPELINE_CLASS('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
   result = p.run()
   print(json.dumps(result.get('output', result), indent=2))
   "
   ```

4. **Show the output** — format key fields as a readable summary, not raw JSON dump.

5. **If error** — show the error, diagnose the likely cause, and suggest a fix.

## Pipeline Mapping

| User says | Folder | Class name |
|-----------|--------|-----------|
| p01, company overview, overview | p01_company_overview | CompanyOverviewPipeline |
| p02, brand identity, brand | p02_brand_identity | BrandIdentityPipeline |
| p03, market position, market | p03_market_position | MarketPositionPipeline |
| p04, competitors, competitor mapping | p04_competitor_mapping | CompetitorMappingPipeline |
| p05, brand activity, campaigns | p05_brand_activity | BrandActivityPipeline |
| p06, experiential, events footprint | p06_experiential_footprint | ExperientialFootprintPipeline |
| p07, reputation, reddit | p07_reputation_research | ReputationResearchPipeline |
| p08, watchouts, risks | p08_strategic_watchouts | StrategicWatchoutsPipeline |
| p09, decision makers, people | p09_decision_makers | DecisionMakersPipeline |
| p10, contacts, intelligence | p10_contact_intelligence | ContactIntelligencePipeline |
| p11, outreach, emails | p11_outreach | OutreachPipeline |
| p12, tracking | p12_tracking | TrackingPipeline |

## Quick Reference — What Each Pipeline Does

- **P01** → Company size, ICP score, funding status, business model
- **P02** → Brand colours, fonts, tone of voice, visual identity
- **P03** → Market sentiment, share of voice, brand perception gap
- **P04** → Competitor list with profiles and competitive urgency score
- **P05** → Recent campaigns, PR activity, partnerships (last 24 months)
- **P06** → Events history, sponsorships, experiential maturity score
- **P07** → Reddit + review sentiment, reputation score, NPS signals
- **P08** → Risk flags, leadership changes, controversies, watchout verdict
- **P09** → Decision makers (buying committee) with LinkedIn + personalisation hooks
- **P10** → Email addresses via Hunter.io, email pattern, verification status
- **P11** → 4-touch outreach sequences (email + LinkedIn) personalised per contact
- **P12** → Engagement tracking pixel + click scoring model config

## Environment
All pipelines need these env vars set (already in Railway, use .env locally):
- `OPENAI_API_KEY`
- `APIFY_TOKEN_1` / `APIFY_TOKEN_2`
- `HUNTER_API_KEY`

Check with: `python -c "from config.settings import OPENAI_MODEL; print('env ok')"`
