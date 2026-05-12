# Skill: p01-company-overview

## Trigger
"run p01", "company overview", "ICP score for [brand]", "overview of [brand]"

## Step 1 — Ask
"What's the brand name and website URL?"

## Step 2 — Do this yourself using WebFetch and web search

Fetch these pages from their website:
- Homepage
- /about or /about-us
- /team or /press

Search the web for:
- "[brand] employees founded funding revenue"
- "[brand] investors headquarters India"

## Step 3 — Produce this output

```
COMPANY OVERVIEW — [Brand]
==========================
Business Model: B2C / B2B / B2B2C / SaaS
Industry: [vertical]
Founded: [year]
Employees: 1-10 / 11-50 / 51-200 / 200-1000 / 1000+
Funding: Bootstrapped / Seed / Series A / B / C+ / Public / Unknown
HQ: [city]
Geography: [where active]

ICP FIT SCORE: [X]/100
  B2C brand → +25 pts
  200+ employees → +25 pts
  VC-backed or Public → +25 pts
  India presence → +25 pts

Experiential Readiness: HIGH / MEDIUM / LOW
Recommended StepOneXP Service: [service name]

Summary: [100 words on what the company does and why they're a fit]

Key Facts:
• [fact from research]
• [fact]
• [fact]
```
