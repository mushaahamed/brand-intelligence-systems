# Skill: p02-brand-identity

## Trigger
Activate when user says any of:
- "run p02", "p02 for [brand]", "pipeline 2 for [brand]"
- "brand identity for [brand]"
- "brand colours for [brand]", "brand fonts for [brand]"
- "tone of voice for [brand]", "brand personality for [brand]"

## NO QUESTIONS — Execute immediately.
If brand name is in the message, run it. Default URL = `https://www.[brand].com`, default category = `Consumer Brand India`.

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p02_brand_identity.pipeline import BrandIdentityPipeline
p = BrandIdentityPipeline('COMPANY_NAME', 'COMPANY_URL', 'CATEGORY')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## What It Does
Extracts brand colours, fonts, tone of voice, and visual identity from the brand's homepage and About page. Used to ensure StepOneXP activations feel on-brand.

## Key Output Fields
- `primary_colors` — hex codes e.g. `["#FFFFFF", "#74C8C3"]`
- `primary_fonts` — e.g. `["Helvetica Neue", "Georgia"]`
- `brand_tone` — Warm / Bold / Minimal / Playful / Premium
- `brand_personality` — 50-word description
- `visual_style` — Photography-led / Icon-heavy / Text-focused
- `brand_voice_keywords` — key messaging words used by the brand
- `activation_recommendations` — StepOneXP activation ideas matching the brand's identity

## GitHub File
`https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p02_brand_identity/pipeline.py`
