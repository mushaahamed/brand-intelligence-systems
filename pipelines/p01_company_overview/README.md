# Pipeline 01 — Company Overview

## What It Does
Answers: *What kind of company is this, how big are they, and do they have the budget and appetite for experiential marketing?*

## 3-Layer Architecture

| Layer | Action | Tools |
|-------|--------|-------|
| Layer 1 — FETCH | Crawl website (8 pages) + LinkedIn company + 2 Google searches | `apify/website-content-crawler`, `harvestapi/linkedin-company-scraper`, `apify/google-search-scraper` |
| Layer 2 — EXTRACT | Parse website text from About/Team/Press pages. Extract LinkedIn employee count, founding year, HQ. Collect news snippets for funding signals. | Python parser |
| Layer 3 — SYNTHESISE | Claude Haiku reads structured data → produces JSON with all output fields | Claude API (`claude-haiku-4-5-20251001`) |

## Output Fields

| Field | Type | Description |
|-------|------|-------------|
| `business_model` | string | B2B / B2C / B2B2C / Marketplace / SaaS / Other |
| `industry_vertical` | string | Specific sub-vertical |
| `founding_year` | int\|null | Year company was founded |
| `employee_count_range` | string | 1-10 / 11-50 / 51-200 / 200-1000 / 1000+ |
| `funding_status` | string | Bootstrapped / Seed / Series A–C+ / Public / Unknown |
| `geography` | string | Countries/cities where active |
| `hq_city` | string | Primary headquarters city |
| `revenue_range` | string | Estimated range |
| `marketing_maturity_score` | int 1-5 | 1=none, 5=multi-channel campaigns |
| `website_quality_score` | int 1-5 | 1=basic, 5=world-class |
| `icp_fit_score` | int 0-100 | Fit score for StepOneXP pitch |
| `experiential_readiness` | string | HIGH / MEDIUM / LOW |
| `recommended_service` | string | Which StepOneXP service to lead with |
| `company_narrative` | string | 100-word summary |
| `key_facts` | array | 3-5 specific facts from research |
| `sources_used` | array | URLs used |

## ICP Scoring Logic
```
B2C brand:         +25 pts
200+ employees:    +25 pts
VC-backed/Public:  +25 pts
India presence:    +25 pts
─────────────────────────
Maximum:           100 pts
```

## Apify Account Used
Group 1 token (`APIFY_TOKEN_1`)

## Estimated Cost
~$0.04 per run (3 actor calls × ~$0.013 avg)
