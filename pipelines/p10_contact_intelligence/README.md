# P10 — Contact Intelligence

Takes the buying committee from P09 and finds verified email addresses and optimal outreach channels for each person using Hunter.io with pattern inference fallback.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | Hunter.io email finder per contact · Company domain email pattern lookup | `hunter.io` API (25 free/month) |
| **L2 EXTRACT** | Parse email, confidence score, verification status; infer pattern if Hunter returns no result | Python Hunter client |
| **L3 SYNTHESISE** | Map contact data → recommended channel per person + data disclaimer | Claude Haiku |

## Email confidence tiers

| Confidence | Source | Meaning |
|------------|--------|---------|
| 90–100% | `HUNTER_VERIFIED` | Hunter confirmed email is deliverable |
| 60–89% | `HUNTER_PATTERN` | Hunter pattern match, not individually verified |
| 25–59% | `PATTERN_INFERRED` | Inferred from company pattern (e.g. first@domain.com) |
| 0% | `NOT_FOUND` | No data found |

## Channel recommendation logic

| Condition | Recommended Channel |
|-----------|---------------------|
| Confidence ≥ 70 + active LinkedIn | EMAIL_AND_LINKEDIN |
| Confidence ≥ 70, low LinkedIn | EMAIL_FIRST |
| Confidence < 70 or NOT_FOUND | LINKEDIN_FIRST |

## Rate limits
- Hunter.io free: 25 lookups/month across all pipeline runs
- Rotation: Each of the 5 Apify accounts maps to a different Hunter.io account (if needed)
- Fallback: Pattern inference always runs if Hunter is exhausted

## Data compliance
All contact data is scraped from public sources. Usage must comply with GDPR (EU), PDPA (India), and CAN-SPAM (email). The `data_disclaimer` field in every output contains the compliance notice.

## Cost estimate
~$0.02/run (Hunter.io free tier + 1 Haiku synthesis)
