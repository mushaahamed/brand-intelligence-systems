# Pipeline 12 — Tracking · Skill File

## Identity
- **Pipeline ID:** `p12_tracking`
- **Class:** `TrackingPipeline`
- **File:** `pipelines/p12_tracking/pipeline.py`

## Purpose
Answers: *"How do we track whether a prospect opened our email, clicked a link, or engaged — and what's their engagement score?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p12_tracking.pipeline import TrackingPipeline
p = TrackingPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `tracking_records` | array | One record per contact |
| `tracking_records[].contact_name` | string | "Priya Nair" |
| `tracking_records[].pixel_url` | string | Tracking pixel URL |
| `tracking_records[].click_links` | array | Tracked CTA links |
| `tracking_records[].engagement_score` | int 0-100 | 0 (pre-send) |
| `tracking_records[].status` | string | NOT_SENT / SENT / OPENED / CLICKED |

## How Tracking Works
1. Each contact gets a unique tracking pixel (1×1 image URL)
2. When the email is opened → pixel fires → engagement score increases
3. CTA links are wrapped in redirect URLs
4. Click events update engagement score
5. Score feeds back into P09 priority ranking on next run

## Common Issues & Fixes
- **Tracking pixel blocked** → many corporate firewalls block tracking pixels; LinkedIn DM tracking not available
- **Score stuck at 0** → email not opened yet or image loading blocked; try plain-text follow-up

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p12_tracking/pipeline.py`
