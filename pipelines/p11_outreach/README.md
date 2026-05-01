# P11 — Outreach Sequence

Generates a personalised 4-touch outreach sequence (email + LinkedIn) for each decision maker, using all upstream pipeline intelligence as personalisation context. Uses Claude Sonnet (not Haiku) for higher-quality writing.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | Aggregates outputs from P01–P10 (no new external fetch) | Orchestrator context |
| **L2 EXTRACT** | Distils 6 personalisation variables: opening_line, events_gap, reputation_angle, watchout, icp_score, pitch_angle | Python extractor |
| **L3 SYNTHESISE** | Writes 4-touch sequence per contact applying 5S formula and role-based tone | **Claude Sonnet** (higher quality) |

## The 4-Touch Sequence

| Touch | Channel | Day | Purpose |
|-------|---------|-----|---------|
| Touch 1 | Email | Day 1 | First impression — personalised hook + single ask |
| Touch 2 | LinkedIn | Day 4 | Connection request + brief value message |
| Touch 3 | Email | Day 9 | Follow-up — different angle, new proof point |
| Touch 4 | Email | Day 16 | Breakup email — friendly, no pressure, leaves door open |

## The 5S Formula
Every touch follows this structure:
1. **Signal** — Specific observation about their brand/activity
2. **Specific** — Name a concrete event, campaign, or gap
3. **Short** — Max 80 words (email) / 300 chars (LinkedIn)
4. **Social proof** — One StepOneXP client or result
5. **Single CTA** — One clear ask only

## Tone by role type
| Role | Lead With |
|------|-----------|
| ECONOMIC_BUYER | Business outcomes, ROI |
| EVENTS_SPECIALIST | Creative formats, innovation |
| INITIATOR | Ease of execution, partnership |
| INFLUENCER | Brand-building vision |

## Why Sonnet (not Haiku)?
Outreach quality directly impacts revenue. The extra cost (~$0.10/run) is worth the quality uplift for client-facing copy.

## Cost estimate
~$0.12/run (0 fetches + Claude Sonnet for 3–5 contacts × 4 touches each)
