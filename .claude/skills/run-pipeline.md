# Skill: run-pipeline

## Trigger
Activate when user says any of:
- "run p09 for Dove"
- "run pipeline 11 on Nike"
- "test decision makers for Mamaearth"
- "run outreach for Zomato"
- `/run-pipeline p09 "Dove"`

## CRITICAL RULE — NO QUESTIONS IF INFO IS IN THE MESSAGE
If the user gave a pipeline + brand name → run immediately, no questions.
Only ask if the pipeline number AND brand name are both completely missing.

---

## Pipeline Mapping

| User says | Folder | Class |
|-----------|--------|-------|
| p01 / company / overview | p01_company_overview | CompanyOverviewPipeline |
| p02 / brand / identity | p02_brand_identity | BrandIdentityPipeline |
| p03 / market / position | p03_market_position | MarketPositionPipeline |
| p04 / competitor | p04_competitor_mapping | CompetitorMappingPipeline |
| p05 / activity / campaigns | p05_brand_activity | BrandActivityPipeline |
| p06 / experiential / events / footprint | p06_experiential_footprint | ExperientialFootprintPipeline |
| p07 / reputation / reddit | p07_reputation_research | ReputationResearchPipeline |
| p08 / watchouts / risks | p08_strategic_watchouts | StrategicWatchoutsPipeline |
| p09 / decision makers / people | p09_decision_makers | DecisionMakersPipeline |
| p10 / contacts / intelligence | p10_contact_intelligence | ContactIntelligencePipeline |
| p11 / outreach / emails | p11_outreach | OutreachPipeline |
| p12 / tracking | p12_tracking | TrackingPipeline |

## Default values when not specified
- `company_url` → `https://www.{brand-slug}.com` (e.g. brand=Dove → `https://www.dove.com`)
- `category` → `"Consumer Brand India"`

---

## Execute Immediately

```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.PIPELINE_FOLDER.pipeline import PIPELINE_CLASS
p = PIPELINE_CLASS('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

After running, show a clean summary of key output fields (not raw JSON dump).

## What NOT to do
- ❌ Do NOT ask "What fields should the JSON output include?"
- ❌ Do NOT ask for confirmation before running
- ❌ Do NOT show menus or numbered options
- ✅ Just run it and show results
