# Pipeline 04 — Competitor Mapping · Skill File

## Identity
- **Pipeline ID:** `p04_competitor_mapping`
- **Class:** `CompetitorMappingPipeline`
- **File:** `pipelines/p04_competitor_mapping/pipeline.py`

## Purpose
Answers: *"Who are their top 3-5 competitors, what are those competitors doing in experiential, and how does that create urgency for our pitch?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p04_competitor_mapping.pipeline import CompetitorMappingPipeline
p = CompetitorMappingPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Data Sources
| Source | What it gets |
|--------|-------------|
| Google Search x3 | Competitor names, their campaigns, market comparison |
| Competitor website crawl | Their positioning and messaging |
| Claude synthesis | Competitor profiles + urgency score |

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `competitors` | array | List of competitor objects |
| `competitors[].name` | string | "Nivea" |
| `competitors[].experiential_activity` | string | What they're doing in events |
| `competitors[].threat_level` | string | HIGH / MEDIUM / LOW |
| `competitive_urgency` | string | HIGH / MEDIUM / LOW |
| `pitch_angle` | string | How to frame the competitive threat in outreach |

## Usage in Outreach (P11)
The competitor data from P04 feeds directly into Touch 3 of the outreach sequence — the "competitive intelligence email" that names a specific competitor and what they're doing. Keep this pipeline healthy for best outreach quality.

## Common Issues & Fixes
- **Generic competitor list** → add the brand's category to search queries
- **No experiential activity found** → this is a GOOD pitch angle (competitor gap)

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p04_competitor_mapping/pipeline.py`
