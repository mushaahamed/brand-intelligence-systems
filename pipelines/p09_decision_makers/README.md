# P09 — Decision Makers

Identifies the 3–5 most relevant people to approach at the target company using LinkedIn search and public profile data. Maps each person to a role in the buying committee and scores them by decision relevance.

## Layer breakdown

| Layer | Action | Tool |
|-------|--------|------|
| **L1 RAW FETCH** | LinkedIn search for 4 target role types: Economic Buyer (CMO/VP Marketing), Initiator (Brand Manager), Events Specialist (Events Manager), Influencer (CEO/Growth Head) | `apify/linkedin-profile-search` + Google fallback |
| **L2 EXTRACT** | Parse name, title, company, LinkedIn URL, tenure, previous company; verify person is at target company | Python validator |
| **L3 SYNTHESISE** | Map verified profiles → buying committee with role types, scores, priority, and personalisation hooks | Claude Haiku |

## Output fields

| Field | Type | Description |
|-------|------|-------------|
| `buying_committee[].name` | string | Person's full name |
| `buying_committee[].title` | string | Current job title |
| `buying_committee[].role_type` | enum | Their role in the buying decision |
| `buying_committee[].decision_relevance_score` | 1–5 | How relevant they are to the buying decision |
| `buying_committee[].outreach_priority` | HIGH/MEDIUM/LOW | Who to contact first |
| `buying_committee[].personalisation_hook` | string | Specific detail to use in outreach |
| `primary_contact` | string | The single best first contact |

## Target roles (in priority order)
1. **Economic Buyer** — CMO, VP Marketing, Brand Director (holds budget)
2. **Events Specialist** — Events Manager, Experiential Lead (most receptive)
3. **Initiator** — Brand Manager, Marketing Manager (likely to initiate)
4. **Influencer** — CEO, CCO, Growth Head (can unlock decisions)

## Cost estimate
~$0.05/run (4 LinkedIn searches + 1 Google fallback + 1 Haiku synthesis)
