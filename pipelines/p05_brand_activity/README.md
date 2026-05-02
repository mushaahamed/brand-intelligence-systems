# P05 — Brand Activity

Captures the brand's recent marketing and campaign footprint across digital, traditional, and social channels to identify timing windows and budget signals for the StepOneXP pitch.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | 4 Google searches: recent campaigns, marketing news, social media activity, upcoming launches + Instagram scrape | `google-search-scraper` · `instagram-scraper` |
| **L2 EXTRACT** | Parse campaign names, dates, channel types from snippets; filter to last 18 months | Python regex + date parser |
| **L3 SYNTHESISE** | Map campaign timeline → cadence, budget signal, seasonal pattern, opportunity window | Claude Haiku |

## Output fields

| Field | Type | Description |
|-------|------|-------------|
| `recent_campaigns[]` | object[] | Campaign name, type, date, description |
| `social_content_cadence` | enum | How frequently they post |
| `dominant_content_themes` | string[] | What they talk about most |
| `seasonal_pattern` | string | When they spend heavily |
| `budget_signal` | HIGH/MEDIUM/LOW | Inferred marketing budget |
| `upcoming_opportunity_window` | string | Best time to pitch |
| `channel_mix` | string[] | Which channels they use |
| `experiential_readiness` | string | Current experiential maturity |

## Cost estimate
~$0.03/run (4 searches + 1 Instagram scrape + 1 Haiku synthesis)
