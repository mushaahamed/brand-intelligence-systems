# P07 — Reputation Research

Mines Reddit, review platforms, and social mentions to build a genuine picture of how consumers actually feel about the brand — not the brand's own marketing spin. Reddit is the highest-signal source because it contains unfiltered authentic opinions.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | Reddit scrape for brand mentions · Google search for reviews + social sentiment · Twitter/social mentions search | `trudax/reddit-scraper` · `google-search-scraper` |
| **L2 EXTRACT** | Extract per-Reddit post: subreddit, score, comment count, title, body snippet; parse review star ratings and text | Python parser |
| **L3 SYNTHESISE** | Map all signals → reputation score, themes, watchout, opportunity | Claude Haiku |

## Output fields

| Field | Type | Description |
|-------|------|-------------|
| `overall_reputation_score` | 1.0–5.0 | Composite reputation rating |
| `reddit_key_themes` | string[] | What Reddit actually says about the brand |
| `common_customer_complaints` | string[] | Top pain points |
| `common_customer_praise` | string[] | What customers love |
| `brand_community_strength` | enum | How engaged is the organic fanbase |
| `viral_moments` | string[] | Any viral incidents (positive/negative) |
| `influencer_sentiment` | enum | How influencers talk about the brand |
| `reputation_watchout` | string | What to avoid in the pitch |
| `reputation_opportunity` | string | Community/loyalty angle to leverage |

## Why Reddit first
Reddit has low brand-managed content and high authentic opinion density. A brand scoring 4.5 on Google but getting torn apart on r/india tells a very different story — and that story changes how StepOneXP pitches.

## Cost estimate
~$0.04/run (Reddit scrape + 3 searches + 1 Haiku synthesis)
