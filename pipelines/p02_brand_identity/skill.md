# Pipeline 02 — Brand Identity · Skill File

## Identity
- **Pipeline ID:** `p02_brand_identity`
- **Class:** `BrandIdentityPipeline`
- **File:** `pipelines/p02_brand_identity/pipeline.py`

## Purpose
Answers: *"What does this brand look like — colours, fonts, tone, personality — so StepOneXP can pitch activations that match the brand's visual identity?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p02_brand_identity.pipeline import BrandIdentityPipeline
p = BrandIdentityPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Data Sources
| Source | What it gets |
|--------|-------------|
| Homepage HTML crawl | CSS colour variables, font-family declarations |
| Logo/image URLs | Visual identity signals |
| About page text | Brand voice and tone |
| Claude synthesis | Structured brand profile |

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `primary_colors` | array | `["#FFFFFF", "#74C8C3"]` |
| `primary_fonts` | array | `["Helvetica Neue", "Georgia"]` |
| `brand_tone` | string | Warm / Bold / Minimal / Playful |
| `brand_personality` | string | 50-word description |
| `visual_style` | string | Photography-led / Icon-heavy / Text-focused |
| `brand_voice_keywords` | array | `["real beauty", "confidence", "inclusive"]` |
| `activation_recommendations` | array | StepOneXP-specific activation ideas |

## Common Issues & Fixes
- **No colours extracted** → site may use CSS custom properties; crawler captures rendered HTML but not computed styles
- **Generic tone** → brand's About page not found; check `company_url/about`
- **Empty fonts** → site uses Google Fonts loaded dynamically; font name may appear in `<link>` tags

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p02_brand_identity/pipeline.py`
