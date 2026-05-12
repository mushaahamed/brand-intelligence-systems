# Skill: p01-company-overview

## Trigger
User pastes the GitHub link for p01, or says "run p01", "company overview", "ICP score"

## Step 1 — Ask this one question
"What's the brand name and website URL?"

## Step 2 — Do the analysis using these exact steps

**Crawl the website:**
- Fetch the homepage using WebFetch
- Fetch /about, /about-us, /team, /press pages

**Search Google for:**
- "[brand] employees founded funding revenue"
- "[brand] investors series funding headquarters India"

**From all the data, produce this exact output:**

```
COMPANY OVERVIEW — [Brand Name]
================================
Business Model: B2C / B2B / B2B2C / SaaS / Other
Industry Vertical: [specific sub-vertical]
Founded: [year or Unknown]
Employee Count: 1-10 / 11-50 / 51-200 / 200-1000 / 1000+
Funding Status: Bootstrapped / Seed / Series A / Series B / Series C+ / Public / Unknown
HQ City: [city]
Geography: [countries/cities active]
Revenue Range: [estimate]

ICP FIT SCORE: [0-100]
  B2C brand         → +25
  200+ employees    → +25
  VC-backed/Public  → +25
  India presence    → +25

Experiential Readiness: HIGH / MEDIUM / LOW
Marketing Maturity: [1-5]
Website Quality: [1-5]
Recommended Service: [which StepOneXP service to lead with]

Company Narrative:
[100-word summary of what the company does, who they serve, and why they matter]

Key Facts:
• [fact 1]
• [fact 2]
• [fact 3]

Sources Used: [URLs]
```
