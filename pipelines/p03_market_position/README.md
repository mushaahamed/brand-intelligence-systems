# P03 — Market Position

Analyses how the target brand is perceived in public discourse — search snippets, news, and aggregated review sentiment — then frames how that position affects the StepOneXP pitch angle.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | 4 Google searches: brand perception, brand vs competitors, recent news, review sentiment | `apify/google-search-scraper` |
| **L2 STRUCTURED EXTRACT** | Parse titles, snippets, dates per result; deduplicate overlapping sources | Python regex + dict |
| **L3 SYNTHESISE** | Map snippets → share_of_voice, sentiment, perception gap, pitch implication | Claude Haiku |

## Output fields

| Field | Type | Description |
|-------|------|-------------|
| `share_of_voice_level` | HIGH/MEDIUM/LOW | How prominently the brand appears in organic search |
| `brand_sentiment` | enum | Dominant emotional tone across all sources |
| `perception_gap_score` | 1–5 | Gap between how the brand wants to be seen vs how it is |
| `recent_sentiment_shift` | string | Direction of change if detectable |
| `key_brand_associations` | string[] | Words/concepts that cluster around the brand |
| `top_media_channels` | string[] | Where the brand gets the most coverage |
| `pitch_implication` | string | One-line strategic implication for the outreach |

## Cost estimate
~$0.02/run (4 search queries + 1 Haiku synthesis call)
