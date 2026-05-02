# P06 — Experiential Footprint ⭐ Highest Priority Pipeline

The most critical pipeline for StepOneXP. Builds a complete picture of every event, activation, and experiential marketing effort the brand has run — then identifies the exact gaps StepOneXP can fill.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | 4 event-specific Google searches: brand events, activations, experiential campaigns, pop-ups + Instagram media scrape | `google-search-scraper` · `instagram-scraper` |
| **L2 EXTRACT** | Filter results by event keywords (`activation`, `pop-up`, `event`, `launch`, `stall`, `fest`); extract event name, date, location, format | Python keyword filter + parser |
| **L3 SYNTHESISE** | Build events timeline; score maturity; identify format/geography gaps; write pitch angle and opening line | Claude Haiku |

## Output fields

| Field | Type | Description |
|-------|------|-------------|
| `events_timeline[]` | object[] | Full event history with format/scale/location/quality |
| `experiential_maturity_score` | 1–5 | How sophisticated their experiential program is |
| `formats_used` | string[] | Event formats they have done |
| `formats_missing` | string[] | High-fit formats they have NEVER done |
| `geographies_covered` | string[] | Cities/regions activated |
| `geographies_missing` | string[] | Key markets not yet reached |
| `pitch_angle` | string | The strongest StepOneXP pitch based on gaps |
| `opening_line_for_pitch` | string | First sentence of the outreach email |

## Why this pipeline matters
StepOneXP's pitch is most compelling when it references a specific gap — a format the brand hasn't tried, a city they haven't activated in, or a consumer segment they've missed. This pipeline generates that specificity.

## Cost estimate
~$0.04/run (4 searches + 1 Instagram + 1 Haiku synthesis)
