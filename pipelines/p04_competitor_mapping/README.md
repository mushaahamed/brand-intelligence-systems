# P04 — Competitor Mapping

Four-layer pipeline that identifies competitors, scrapes their sites, extracts per-competitor experiential activity, and synthesises the competitive landscape with a clear white-space opportunity for StepOneXP.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1a RAW FETCH** | Google search: "competitors of {company}" + "{category} top brands India" | `apify/google-search-scraper` |
| **L1b IDENTIFY** | Claude Haiku extracts competitor name list from search snippets | `claude-haiku` |
| **L1c SCRAPE** | Website crawler on each identified competitor domain | `apify/website-content-crawler` |
| **L2 EXTRACT** | Parse title, description, events/campaigns mentions per competitor site | Python parser |
| **L3 SYNTHESISE** | Map all competitor data → structured comparison + white space | Claude Haiku |

## Output fields

| Field | Type | Description |
|-------|------|-------------|
| `competitors[].name` | string | Competitor brand name |
| `competitors[].brand_positioning` | string | One-sentence positioning |
| `competitors[].events_activity` | HIGH/MEDIUM/LOW/NONE | Experiential activity level |
| `competitors[].experiential_gap` | string | Specific untapped opportunity |
| `competitors[].threat_level` | HIGH/MEDIUM/LOW | Direct threat to target brand |
| `experiential_white_space` | string | The single biggest market gap |
| `recommended_pitch_angle` | string | How StepOneXP frames the pitch |
| `market_maturity` | enum | Overall market stage |

## Cost estimate
~$0.06/run (2 searches + 4–6 site crawls + 1 identify call + 1 synthesis call)
