# Pipeline 08 — Strategic Watchouts · Skill File

## Identity
- **Pipeline ID:** `p08_strategic_watchouts`
- **Class:** `StrategicWatchoutsPipeline`
- **File:** `pipelines/p08_strategic_watchouts/pipeline.py`

## Purpose
Answers: *"Are there any red flags that should make us soften or delay our pitch — leadership chaos, budget freezes, controversies, layoffs, legal trouble?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p08_strategic_watchouts.pipeline import StrategicWatchoutsPipeline
p = StrategicWatchoutsPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Data Sources
| Source | What it gets |
|--------|-------------|
| Google Search x3 | Layoffs, controversies, leadership changes, budget cuts |
| News snippets | Company crisis, restructuring signals |
| Claude synthesis | Risk verdict + recommendations |

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `overall_verdict` | string | GREEN / AMBER / RED |
| `watchout_flags` | array | List of specific risks found |
| `leadership_stability` | string | STABLE / CHANGING / UNCERTAIN |
| `budget_risk` | string | LOW / MEDIUM / HIGH |
| `controversy_level` | string | NONE / MINOR / SIGNIFICANT / SEVERE |
| `timing_recommendation` | string | "Pitch now" / "Wait 3 months" / "Soften pitch" |
| `pitch_approach_modifier` | string | How to adjust the outreach tone |

## Verdict Guide
```
GREEN = Full pitch, normal tone
AMBER = Soften slightly, avoid bold ROI claims, acknowledge challenges
RED   = Don't pitch hard; wait or skip; flag to sales team
```

## Integration with P11 Outreach
P11 reads `watchout_verdict` from P08. If AMBER → outreach is softened. If RED → pitch is de-escalated. This is automatic.

## Common Issues & Fixes
- **False RED on healthy brand** → Google search may have surfaced old news; check `watchout_flags` manually
- **All GREEN for a brand you know is struggling** → add "layoffs" or "restructuring" to search

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p08_strategic_watchouts/pipeline.py`
