# Pipeline 06 — Experiential Footprint · Skill File

## Identity
- **Pipeline ID:** `p06_experiential_footprint`
- **Class:** `ExperientialFootprintPipeline`
- **File:** `pipelines/p06_experiential_footprint/pipeline.py`

## Purpose
Answers: *"Has this brand done experiential marketing before — events, pop-ups, sponsorships, activations — and how mature are they at it? This determines whether we're selling them on the concept or on upgrading their existing approach."*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p06_experiential_footprint.pipeline import ExperientialFootprintPipeline
p = ExperientialFootprintPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Data Sources
| Source | What it gets |
|--------|-------------|
| Google Search x3 | Events, pop-ups, activations, exhibition participation |
| News/PR snippets | Named events with dates and scale |
| Claude synthesis | Maturity score + timeline |

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `events_timeline` | array | Named events with year and type |
| `experiential_maturity_score` | int 1-5 | 3 |
| `events_frequency` | string | Regular / Occasional / Rare / None |
| `event_types_used` | array | Pop-up / Roadshow / Exhibition / Concert |
| `biggest_event` | string | Largest known activation |
| `experiential_gap` | string | What format they haven't tried |
| `stepone_recommendation` | string | Which StepOneXP format fits best |

## Maturity Score Guide
```
1 = Never done experiential
2 = Tried 1-2 small activations
3 = Regular activations, no flagship
4 = Has own events, sponsorships
5 = Full experiential programme
```

## Common Issues & Fixes
- **Score = 1 for big brand** → likely their events are under parent company; check P04 competitor data
- **Events timeline empty** → brand is digital-native; strong pitch angle for first physical activation

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p06_experiential_footprint/pipeline.py`
