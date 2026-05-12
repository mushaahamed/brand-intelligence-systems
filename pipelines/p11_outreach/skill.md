# Pipeline 11 — Outreach · Skill File

## Identity
- **Pipeline ID:** `p11_outreach`
- **Class:** `OutreachPipeline`
- **File:** `pipelines/p11_outreach/pipeline.py`

## Purpose
Answers: *"What exactly should we say to each person — a personalised 4-touch outreach sequence (email + LinkedIn) that sounds like Arjun, not an AI?"*

## Run Command
```bash
cd "C:\Users\musha ahamed\OneDrive\Documents\brand-intelligence-system" && python -c "
import json
from pipelines.p11_outreach.pipeline import OutreachPipeline
p = OutreachPipeline('Dove', 'https://dove.com', 'FMCG Skincare')
r = p.run()
print(json.dumps(r.get('output', r), indent=2))
"
```

## Architecture
1. Takes contacts from P10 (enriched with emails, roles)
2. Takes brand research from P01-P08 (campaigns, competitors, watchouts)
3. For each contact → GPT-4o generates a full 4-touch sequence
4. Touch 1: Email Day 1 (150-200 words, 4 structured paragraphs)
5. Touch 2: LinkedIn Day 3 (150-200 chars)
6. Touch 3: Email Day 8 (250-320 words, competitive intel)
7. Touch 4: Email Day 15 (100-130 words, warm close)

## Persona
**Arjun** — Senior Account Manager at StepOneXP, writes like he spent 2 hours researching this exact brand and person.

## AI Model
`gpt-4o` (OPENAI_MODEL_FULL) — used for all outreach generation (never gpt-4o-mini for this pipeline).

## Key Output Fields
| Field | Type | Example |
|-------|------|---------|
| `sequences` | array | One sequence per contact |
| `sequences[].contact` | object | Name, title, company |
| `sequences[].touch_1` | object | `{subject, body}` — Day 1 email |
| `sequences[].touch_2` | object | `{message}` — Day 3 LinkedIn |
| `sequences[].touch_3` | object | `{subject, body}` — Day 8 competitor email |
| `sequences[].touch_4` | object | `{subject, body}` — Day 15 warm close |
| `primary_contact` | object | Top person + their sequence |

## Touch Specifications (Current)
```
Touch 1 — Email Day 1:      150-200 words, 4 paragraphs
Touch 2 — LinkedIn Day 3:   150-200 chars MAX
Touch 3 — Email Day 8:      250-320 words, competitive intel, names specific competitor
Touch 4 — Email Day 15:     100-130 words, warm close, leaves value
```

## Role-Based Framing (in SYSTEM_PROMPT)
| Title | Frame |
|-------|-------|
| CEO / MD / Founder | Category dominance, competitive moat, market share |
| CMO / VP Marketing | Brand equity, earned media, portfolio strategy |
| Brand Manager | Execution quality, end-to-end delivery, no vendor chaos |
| Growth / Performance | CAC, conversion, measurable outcomes |
| Category Manager | Point-of-decision visibility, channel presence |

## Banned Words (in SYSTEM_PROMPT)
leverage, unlock, seamless, game-changer, revolutionize, empower, synergy, holistic, cutting-edge, innovative, impactful

## Forbidden Openers
"I hope this finds you well", "I wanted to reach out", "I came across your profile", "I noticed", "As a fellow"

## P08 Watchout Integration
- `watchout_verdict = GREEN` → full confident pitch
- `watchout_verdict = AMBER` → soften tone, no bold ROI claims
- `watchout_verdict = RED` → de-escalate pitch, don't push hard

## Common Issues & Fixes
- **Outreach sounds generic** → check `personalisation_hook` from P09 — if it says "verify on LinkedIn" the contact is inferred, not real
- **Touch 3 competitor is wrong** → fix P04 competitor mapping; P11 pulls directly from P04 output
- **All sequences same tone** → check `role_type` from P09 — if all "Economic Buyer", P10 didn't differentiate roles

## Edit This Pipeline
GitHub: `https://github.com/mushaahamed/brand-intelligence-systems/blob/main/pipelines/p11_outreach/pipeline.py`
